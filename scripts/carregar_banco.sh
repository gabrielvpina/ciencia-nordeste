#!/usr/bin/env bash
# Aplica as migrações (scripts/migrar.sh) e carrega os CSVs processados no Postgres do docker compose.
# Uso (na raiz do repositório):  ./scripts/carregar_banco.sh
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db
./scripts/migrar.sh
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f ingest/sql/carga.sql'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT relname AS tabela, n_live_tup AS linhas FROM pg_stat_user_tables ORDER BY relname;"'
