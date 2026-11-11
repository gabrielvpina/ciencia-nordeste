#!/usr/bin/env bash
# Publica uma nova versão NO SERVIDOR: código do GitHub e, se indicado, um backup com dados novos (guia de deploy, seção 9).
#
# Uso (no servidor, na raiz do repositório):
#   ./scripts/publicar.sh                       # só código: git pull, rebuild do que mudou, migrações, teste
#   ./scripts/publicar.sh PACOTE.tar.gz         # código + dados: também troca o banco pelo do backup (gerado com scripts/backup.sh)
#   ./scripts/publicar.sh --sim [PACOTE]        # mostra o plano e não executa nada
#   ./scripts/publicar.sh --rebuild-tudo        # reconstrói web e embed mesmo sem mudanças
#
# O que faz:
#   1. confere que está na main e sem alterações locais em arquivos versionados (deploy/ fica fora do git);
#   2. git pull --ff-only;
#   3. rebuild do app (web) se apps/web mudou, e do embed só se servicos/embed mudou (o build dele é pesado);
#   4. com PACOTE: confere os checksums e restaura ids e banco (o site pode dar erro por alguns minutos);
#   5. aplica migrações novas (scripts/migrar.sh) e reinicia o web;
#   6. testa o app por dentro (Caddy -> web) e pelo endereço público (SITE_URL do .env).
# Se algo falhar depois do pull, o commit anterior é mostrado para voltar: git checkout <commit> e rode de novo.
set -euo pipefail
cd "$(dirname "$0")/.."

SIM=0; TUDO=0; PACOTE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sim) SIM=1 ;;
    --rebuild-tudo) TUDO=1 ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    -*) echo "opção desconhecida: $1 (veja --help)" >&2; exit 1 ;;
    *) [ -z "$PACOTE" ] || { echo "ERRO: só um pacote por vez." >&2; exit 1; }; PACOTE="$1" ;;
  esac
  shift
done

passo() { printf '\n==> %s\n' "$*"; }
ler_env() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true; }

# ---- 1. pré-condições ----
command -v docker > /dev/null || { echo "ERRO: docker não encontrado." >&2; exit 1; }
[ -f .env ] || { echo "ERRO: .env não encontrado (veja o guia de deploy)." >&2; exit 1; }
[ -z "$PACOTE" ] || [ -f "$PACOTE" ] || { echo "ERRO: pacote não encontrado: $PACOTE" >&2; exit 1; }
RAMO=$(git rev-parse --abbrev-ref HEAD)
[ "$RAMO" = main ] || { echo "ERRO: o servidor está no branch '$RAMO'; volte para a main (git checkout main)." >&2; exit 1; }
git diff --quiet && git diff --cached --quiet || {
  echo "ERRO: há alterações locais em arquivos versionados. Veja com 'git status' e desfaça ('git restore <arquivo>') antes de publicar." >&2; exit 1; }

# ---- 2. código novo ----
ANTES=$(git rev-parse HEAD)
passo "Buscando o código (git pull)"
if [ "$SIM" = 1 ]; then
  git fetch -q origin main
  DEPOIS=$(git rev-parse origin/main)
else
  git pull --ff-only -q origin main
  DEPOIS=$(git rev-parse HEAD)
fi
if [ "$ANTES" = "$DEPOIS" ]; then
  echo "Código já atualizado ($(git log -1 --format='%h %s' "$ANTES"))."
  MUDOU=""
else
  echo "Commits novos:"; git log --format='  %h %s' "$ANTES..$DEPOIS"
  MUDOU=$(git diff --name-only "$ANTES" "$DEPOIS")
fi
muda() { [ "$TUDO" = 1 ] || grep -q "^$1" <<<"$MUDOU"; }

PLANO=()
muda apps/web/ && PLANO+=("rebuild web")
muda servicos/embed/ && PLANO+=("rebuild embed (demorado)")
[ -n "$PACOTE" ] && PLANO+=("restaurar dados de $(basename "$PACOTE")")
PLANO+=("migrações" "reiniciar web" "testes")
passo "Plano: $(IFS=';'; echo "${PLANO[*]}" | sed 's/;/ → /g')"
if [ "$SIM" = 1 ]; then echo "(--sim: nada foi executado)"; exit 0; fi
trap 'echo; echo "FALHOU. Para voltar ao código anterior: git checkout $ANTES && ./scripts/publicar.sh --rebuild-tudo (depois: git checkout main)" >&2' ERR

# ---- 3. imagens ----
if muda servicos/embed/; then passo "Reconstruindo o serviço embed"; docker compose up -d --build embed; fi
if muda apps/web/; then passo "Reconstruindo o app"; docker compose up -d --build web; fi

# ---- 4. dados ----
if [ -n "$PACOTE" ]; then
  passo "Conferindo o pacote"; ./scripts/restaurar.sh "$PACOTE"
  passo "Restaurando IDs e banco (o site pode responder com erro por alguns minutos)"
  ./scripts/restaurar.sh "$PACOTE" --ids --banco --forcar
fi

# ---- 5. migrações e reinício ----
passo "Aplicando migrações"; ./scripts/migrar.sh
docker compose exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM quiz_participantes WHERE criado_em < now() - interval '"'"'24 months'"'"'"' >/dev/null 2>&1 || true   # retenção do cadastro do quiz (D-037)
# a estrutura do quiz mudou (ou uma migração nova): recopia os sinais das opções para o banco (só Python do sistema + psql)
# migração nova (pode alterar dados, ex.: 0013): atualiza as visões e os perfis temáticos (só sem PACOTE: o backup já os traz)
if [ -z "$PACOTE" ] && muda ingest/sql/migracoes/; then
  passo "Atualizando visões e perfis temáticos"
  docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/atualizar_visoes.sql'
  docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/perfis_tematicos.sql'
fi
if muda apps/web/lib/quiz/arvore.json || muda ingest/sql/migracoes/ || muda ingest/carga/quiz_preparar.py; then
  passo "Preparando o quiz"; python3 -m ingest.carga.quiz_preparar
fi
passo "Reiniciando o app"; docker compose up -d; docker compose restart web

# ---- 6. testes ----
passo "Testando"
ok=0
if docker compose ps --services --status running | grep -qx caddy; then
  for _ in $(seq 1 30); do
    if docker compose exec -T caddy wget -q -O /dev/null http://web:3000/api/mapa 2>/dev/null; then ok=1; break; fi
    sleep 2
  done
  [ "$ok" = 1 ] && echo "app responde por dentro (Caddy → web): ok" || { echo "ERRO: o app não respondeu em 60 s. Veja: docker compose logs --tail 100 web" >&2; exit 1; }
else
  echo "(Caddy não está rodando: teste interno pulado)"
fi
SITE=$(ler_env SITE_URL)
if [[ "$SITE" == https://* ]]; then
  for rota in / /api/mapa; do
    cod=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$SITE$rota" || echo 000)
    echo "$SITE$rota → $cod"
    [ "$cod" = 200 ] || { echo "ERRO: $SITE$rota respondeu $cod. Veja: docker compose logs --tail 100 web caddy" >&2; exit 1; }
  done
fi

trap - ERR
docker image prune -f > /dev/null || true
passo "Publicado: $(git log -1 --format='%h %s')"
[ -n "$PACOTE" ] && echo "Dados restaurados de $(basename "$PACOTE"). Pode apagar o pacote do servidor quando quiser."
exit 0
