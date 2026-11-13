#!/usr/bin/env bash
# Aplica as migrações (scripts/migrar.sh) e carrega os CSVs processados no Postgres do docker compose.
# Uso (na raiz do repositório):  ./scripts/carregar_banco.sh
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db
./scripts/migrar.sh
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/carga.sql'
# Quiz (etapa 13): perfil temático por pesquisador (precisa dos vetores; sem eles, fica para a etapa "vetores") e sinais das opções
if [ "$(docker compose exec -T db sh -c 'psql -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) > 0 FROM work_embeddings"')" = "t" ]; then
  docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/perfis_tematicos.sql'
fi
python3 -m ingest.carga.quiz_preparar
docker compose exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM quiz_participantes WHERE criado_em < now() - interval '"'"'24 months'"'"'"' >/dev/null 2>&1 || true   # retenção do cadastro do quiz (D-037)
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT relname AS tabela, n_live_tup AS linhas FROM pg_stat_user_tables ORDER BY relname;"'
