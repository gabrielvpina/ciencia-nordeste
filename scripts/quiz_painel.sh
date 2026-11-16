#!/usr/bin/env bash
# Resumo do quiz no terminal (só leitura): totais, cadastros por dia, vínculos, respostas e pesquisadores mais indicados
# e os últimos cadastros. Roda no servidor (ou na máquina local), na raiz do repositório, com o banco do docker compose.
#
# Uso:
#   ./scripts/quiz_painel.sh            # resumo + os 10 últimos cadastros
#   ./scripts/quiz_painel.sh 30         # resumo + os 30 últimos cadastros
#   ./scripts/quiz_painel.sh 0          # só o resumo, sem nomes na tela
#
# A sessão é aberta em modo só leitura: o script não altera nada. Os cadastros são dados pessoais (D-037):
# não exporte a saída para fora do servidor sem necessidade.
set -euo pipefail
cd "$(dirname "$0")/.."

N="${1:-10}"
[[ "$N" =~ ^[0-9]+$ ]] || { echo "uso: $0 [quantos últimos cadastros mostrar, padrão 10]" >&2; exit 1; }

docker compose exec -T db sh -c 'PGOPTIONS="-c default_transaction_read_only=on" psql -X -q -P pager=off -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v n='"$N" <<'SQL'
\echo '== Totais'
SELECT (SELECT count(*) FROM quiz_participantes)                                          AS pessoas,
       (SELECT count(*) FROM quiz_alinhamentos)                                           AS resultados,
       (SELECT count(*) FROM quiz_participantes WHERE criado_em >= now() - interval '1 day')  AS "pessoas 24 h",
       (SELECT count(*) FROM quiz_participantes WHERE criado_em >= now() - interval '7 days') AS "pessoas 7 dias",
       (SELECT min(criado_em)::date FROM quiz_participantes)                              AS primeiro,
       (SELECT max(criado_em)::date FROM quiz_participantes)                              AS "último";

\echo '== Cadastros por dia (últimos 14 dias)'
SELECT criado_em::date AS dia, count(*) AS pessoas
  FROM quiz_participantes WHERE criado_em >= now() - interval '14 days'
 GROUP BY 1 ORDER BY 1 DESC;

\echo '== Vínculo'
SELECT filiacao AS "vínculo", count(*) AS pessoas,
       round(100.0 * count(*) / nullif(sum(count(*)) OVER (), 0), 1) AS "%"
  FROM quiz_participantes GROUP BY 1 ORDER BY 2 DESC;

\echo '== Instituições (as 15 mais frequentes)'
SELECT coalesce(i.acronym, i.name, p.instituicao_texto) AS "instituição", count(*) AS pessoas
  FROM quiz_participantes p LEFT JOIN institutions i ON i.id = p.instituicao_id
 GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 15;

\echo '== Respostas mais escolhidas (30)'
SELECT r AS "opção", count(*) AS vezes
  FROM quiz_alinhamentos, unnest(respostas) AS r
 GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 30;

\echo '== Pesquisadores mais indicados (20; banner = entre os 5 do cartão)'
SELECT x.display_name AS pesquisador, count(*) AS vezes, count(m.posicao_banner) AS banner, round(avg(m.indice)) AS "índice médio"
  FROM quiz_matches m JOIN researchers x ON x.id = m.researcher_id
 GROUP BY x.id, x.display_name ORDER BY 2 DESC, 1 LIMIT 20;

SELECT (:n > 0) AS mostrar \gset
\if :mostrar
\echo '== Últimos cadastros'
SELECT to_char(p.criado_em AT TIME ZONE 'America/Recife', 'DD/MM HH24:MI') AS quando, p.nome,
       p.instituicao_texto AS "instituição", p.filiacao AS "vínculo", p.curso_texto AS curso,
       (SELECT count(*) FROM quiz_alinhamentos a WHERE a.participante_id = p.id) AS resultados
  FROM quiz_participantes p ORDER BY p.criado_em DESC LIMIT :n;
\endif
SQL
