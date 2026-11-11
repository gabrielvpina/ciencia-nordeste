#!/usr/bin/env bash
# Atualização periódica da base do Ciência Nordeste (ex.: a cada semestre).
# Recoleta as fontes abertas, refaz o processamento, recarrega o Postgres e confere o resultado.
#
# Uso (na raiz do repositório):
#   ./scripts/atualizar_dados.sh                       # atualização completa (várias horas; ver tempos abaixo)
#   ./scripts/atualizar_dados.sh --sim                 # só mostra o plano, não executa nada
#   ./scripts/atualizar_dados.sh --a-partir-de banco   # retoma de uma etapa (depois de uma falha)
#   ./scripts/atualizar_dados.sh --so producao,banco   # roda só as etapas listadas, na ordem do plano
#   ./scripts/atualizar_dados.sh --manter-cache        # reaproveita o cache HTTP (ingest/.cache): rápido, mas não traz novidades
#   ./scripts/atualizar_dados.sh --sem-embeddings      # pula keywords e vetores (a busca por tema fica sem as publicações novas)
#
# Etapas (ordem do ingest/README.md) e tempo aproximado:
#   backup         backup do registro de IDs, das decisões de revisão e do banco (scripts/backup.sh)
#   instituicoes   Parte 1 — ROR, INEP, IBGE, Wikidata                         ~5 min
#   capes          Parte 2 — programas e docentes (CAPES)                       ~10 min (crawl-delay da CAPES)
#   producao       Parte 5 — publicações do OpenAlex                            ~35 min, < US$ 0,15
#   qualis         Parte 9 — estrato Qualis das revistas (planilha da Sucupira em ingest/dados/brutos/capes/qualis/)  ~1 min
#   pesquisadores  Parte 4 — perfis de autor e coautorias                       ~30–60 min
#   revisao        regra D-018 nos pares novos + consolidação; exporta os pendentes para revisão manual
#   complementos   Parte 6 — teses e orientações (baixa ~1,5 GB), FAPs          ~20–40 min
#   fotos          Parte 7 — fotos com licença livre (Wikidata/Commons)          ~10 min
#   keywords       Parte 8 — palavras-chave do OpenAlex                          ~25 min, < US$ 0,20
#   embeddings     Parte 8 — vetores (só textos novos ou alterados; para os containers para liberar memória)
#   banco          migrações + carga dos CSVs + visões materializadas (scripts/carregar_banco.sh)
#   vetores        Parte 8 — grava os vetores no pgvector e reconstrói o índice HNSW
#   app            sobe de novo os serviços embed e web
#   conferencia    compara contagens antes/depois, testa o app e grava o relatório
#   backup-final   novo backup, já com a base atualizada
#
# Requisitos: .venv com ingest/requirements.txt (e requirements-embeddings.txt, salvo com --sem-embeddings),
# .env com CONTACT_EMAIL e OPENALEX_API_KEY, Docker em execução.
# O período vai de YEAR_START (.env, 2022) ao ano corrente: no ano novo, ele entra sozinho na coleta e no app.
set -euo pipefail
cd "$(dirname "$0")/.."

ETAPAS=(backup instituicoes capes producao qualis pesquisadores revisao complementos fotos keywords embeddings banco vetores app conferencia backup-final)
SIM=0; A_PARTIR=""; SO=""; MANTER_CACHE=0; SEM_EMB=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sim) SIM=1 ;;
    --a-partir-de) A_PARTIR="$2"; shift ;;
    --so) SO="$2"; shift ;;
    --manter-cache) MANTER_CACHE=1 ;;
    --sem-embeddings) SEM_EMB=1 ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) echo "opção desconhecida: $1 (veja --help)" >&2; exit 1 ;;
  esac
  shift
done
valida() { for e in "$@"; do [[ " ${ETAPAS[*]} " == *" $e "* ]] || { echo "etapa desconhecida: $e" >&2; exit 1; }; done; }
[ -n "$A_PARTIR" ] && valida "$A_PARTIR"
[ -n "$SO" ] && valida ${SO//,/ }

# ---- plano: quais etapas rodam nesta execução ----
PLANO=(); ativo=$([ -z "$A_PARTIR" ] && echo 1 || echo 0)
for e in "${ETAPAS[@]}"; do
  [ "$e" = "$A_PARTIR" ] && ativo=1
  [ "$ativo" = 1 ] || continue
  [ -n "$SO" ] && [[ ",$SO," != *",$e,"* ]] && continue
  [ "$SEM_EMB" = 1 ] && [[ "$e" =~ ^(keywords|embeddings|vetores)$ ]] && continue
  PLANO+=("$e")
done
echo "Plano: ${PLANO[*]}"
echo "Cache HTTP: $([ "$MANTER_CACHE" = 1 ] && echo 'reaproveitado (--manter-cache)' || echo 'ignorado: respostas novas em todas as fontes')"
[ "$SIM" = 1 ] && exit 0

# ---- pré-requisitos ----
PY=.venv/bin/python
[ -x "$PY" ] || { echo "ERRO: .venv não encontrado (veja ingest/README.md, 'Preparar o ambiente')." >&2; exit 1; }
ler_env() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true; }
[ -n "$(ler_env CONTACT_EMAIL)" ] && [ -n "$(ler_env OPENALEX_API_KEY)" ] || { echo "ERRO: defina CONTACT_EMAIL e OPENALEX_API_KEY no .env." >&2; exit 1; }
docker info > /dev/null 2>&1 || { echo "ERRO: o Docker não está rodando." >&2; exit 1; }
if [[ " ${PLANO[*]} " == *" embeddings "* ]]; then
  "$PY" -c "import sentence_transformers" 2>/dev/null || { echo "ERRO: instale ingest/requirements-embeddings.txt no .venv (ou use --sem-embeddings)." >&2; exit 1; }
fi

# ---- uma execução por vez; tudo vai para um log ----
TRAVA=ingest/dados/.atualizacao.lock
mkdir -p ingest/dados ingest/relatorios
if ! mkdir "$TRAVA" 2>/dev/null; then echo "ERRO: já há uma atualização em andamento ($TRAVA). Se não houver, apague a pasta." >&2; exit 1; fi
trap 'rmdir "$TRAVA" 2>/dev/null || true' EXIT
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="ingest/relatorios/atualizacao-$STAMP.log"
RELATORIO="ingest/relatorios/atualizacao-$STAMP.md"
exec > >(tee -a "$LOG") 2>&1
[ "$MANTER_CACHE" = 1 ] || export INGEST_SEM_CACHE=1
RECOLETAR=$([ "$MANTER_CACHE" = 1 ] && echo "" || echo "--recoletar")

sql() { docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tA -F'|' -c \"$1\""; }
CONTAGEM="SELECT 'publicacoes', count(*) FROM works UNION ALL SELECT 'pesquisadores', count(*) FROM researchers
  UNION ALL SELECT 'instituicoes', count(*) FROM institutions UNION ALL SELECT 'programas', count(*) FROM graduate_programs
  UNION ALL SELECT 'teses', count(*) FROM theses UNION ALL SELECT 'vetores', count(*) FROM work_embeddings
  UNION ALL SELECT 'ultimo_ano', coalesce(max(year), 0) FROM works"
contar() { docker compose up -d --wait db > /dev/null 2>&1 && sql "$CONTAGEM" || true; }
ANTES="ingest/dados/.contagem-antes"
[ -f "$ANTES" ] && [ -n "$A_PARTIR" ] || contar > "$ANTES"    # ao retomar, mantém a contagem do início

passo() { echo; echo "======== $(date +%H:%M:%S) · $1 ========"; }
INICIO=$(date +%s)
for e in "${PLANO[@]}"; do
  passo "$e"
  case "$e" in
    backup)        if [ -e ingest/dados/ids ] && [ -e ingest/dados/revisao/decisoes.csv ]; then ./scripts/backup.sh
                   else echo "primeira execução (sem ingest/dados/ids nem decisões de revisão): nada a proteger, backup pulado"; fi ;;
    instituicoes)  "$PY" -m ingest.carga.parte1_instituicoes ;;
    capes)         "$PY" -m ingest.carga.parte2_capes ;;
    producao)      "$PY" -m ingest.carga.parte5_producao $RECOLETAR ;;
    qualis)        "$PY" -m ingest.carga.parte9_qualis ;;
    pesquisadores) "$PY" -m ingest.carga.parte4_pesquisadores $RECOLETAR ;;
    revisao)       "$PY" -m ingest.carga.revisao aplicar-regra --decidido-por "regra D-018 (atualização $STAMP)"
                   "$PY" -m ingest.carga.revisao consolidar
                   "$PY" -m ingest.carga.revisao exportar ;;
    complementos)  "$PY" -m ingest.carga.parte6_complementos ;;
    fotos)         "$PY" -m ingest.carga.parte7_fotos ;;
    keywords)      "$PY" -m ingest.carga.parte8_embeddings coletar-keywords $RECOLETAR ;;
    embeddings)    echo "parando os containers para liberar memória para o modelo…"
                   docker compose stop > /dev/null
                   "$PY" -m ingest.carga.parte8_embeddings embeddings ;;
    banco)         ./scripts/carregar_banco.sh ;;
    vetores)       "$PY" -m ingest.carga.parte8_embeddings carregar
                   docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/perfis_tematicos.sql' ;;
    app)           docker compose up -d --wait embed web ;;
    conferencia)
      contar > ingest/dados/.contagem-depois
      ALERTA=0
      {
        echo "# Atualização dos dados — $STAMP"; echo
        echo "Etapas: ${PLANO[*]}  "
        echo "Duração: $(( ($(date +%s) - INICIO) / 60 )) min · cache HTTP: $([ "$MANTER_CACHE" = 1 ] && echo reaproveitado || echo ignorado) · log: \`$LOG\`"; echo
        echo "| Item | Antes | Depois | Diferença |"; echo "|---|---:|---:|---:|"
        while IFS='|' read -r item depois; do
          antes=$(grep "^$item|" "$ANTES" | cut -d'|' -f2); antes=${antes:-0}
          dif=$((depois - antes)); marca=""
          # queda de mais de 2% num total é suspeita (fonte fora do ar, filtro quebrado…)
          if [ "$item" != ultimo_ano ] && [ "$antes" -gt 0 ] && [ $((dif * 100 / antes)) -lt -2 ]; then marca=" ⚠"; ALERTA=1; fi
          echo "| $item | $antes | $depois | $dif$marca |"
        done < ingest/dados/.contagem-depois
        echo
        pend=$(awk 'FNR > 1' ingest/dados/revisao/pendentes_*.csv 2>/dev/null | wc -l | tr -d ' ')
        echo "Pares pendentes de revisão manual (linhas nos pendentes_*.csv): ${pend:-0}. Ver ingest/README.md, 'Revisão de identidade'."; echo
        for url in "/" "/api/mapa" "/api/busca?q=ufpe" "/api/tema?q=dengue"; do
          cod=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "http://127.0.0.1:3000$url" || echo 000)
          echo "- \`$url\` → HTTP $cod"; [ "$cod" = 200 ] || ALERTA=1
        done
        echo; [ "$ALERTA" = 1 ] && echo "**Atenção:** há quedas acima de 2% ou rotas com erro. Confira antes de publicar; o backup da etapa \"backup\" permite voltar (scripts/restaurar.sh)." \
                              || echo "Tudo conferido: nenhuma queda acima de 2% e todas as rotas responderam."
      } | tee "$RELATORIO"
      echo "relatório: $RELATORIO" ;;
    backup-final)  ./scripts/backup.sh ;;
  esac
done
rm -f ingest/dados/.contagem-antes ingest/dados/.contagem-depois
echo; echo "Atualização concluída em $(( ($(date +%s) - INICIO) / 60 )) min. Log: $LOG"
