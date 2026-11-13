#!/usr/bin/env bash
# Aplica, em ordem, as migrações de ingest/sql/migracoes/ que ainda não constam em schema_migrations.
# Cada migração roda numa transação. Banco já criado pelo antigo schema.sql: 0001 é marcada como baseline.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db >/dev/null
psqlc() { docker compose exec -T db sh -c "psql -v ON_ERROR_STOP=1 -X -q -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" $*"; }
psqlc -c "\"CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());\""
aplicadas=$(psqlc -tA -c "\"SELECT version FROM schema_migrations\"")
if [ -z "$aplicadas" ] && [ "$(psqlc -tA -c "\"SELECT to_regclass('public.institutions') IS NOT NULL\"")" = "t" ]; then
  psqlc -c "\"INSERT INTO schema_migrations (version) VALUES ('0001_schema_inicial')\""
  echo "baseline: 0001_schema_inicial (banco já existia)"
  aplicadas="0001_schema_inicial"
fi
for f in ingest/sql/migracoes/*.sql; do
  v=$(basename "$f" .sql)
  if ! grep -qx "$v" <<<"$aplicadas"; then
    echo "aplicando $v"
    psqlc --single-transaction -f "$f" >/dev/null
    psqlc -c "\"INSERT INTO schema_migrations (version) VALUES ('$v')\""
  fi
done
psqlc -tA -c "\"SELECT 'aplicadas: ' || string_agg(version, ', ' ORDER BY version) FROM schema_migrations\""
# Papel só de escrita do cadastro do quiz (0014, D-037): habilita o login com a senha do .env (QUIZ_DB_PASSWORD).
# A senha vai por variável do psql (via entrada padrão), nunca na linha de comando.
SENHA_QUIZ=$(grep -E '^QUIZ_DB_PASSWORD=' .env 2>/dev/null | tail -1 | cut -d= -f2- || true)
if [ -n "$SENHA_QUIZ" ] && [ "$(psqlc -tA -c "\"SELECT count(*) FROM pg_roles WHERE rolname = 'quiz_escrita'\"")" = "1" ]; then
  echo "ALTER ROLE quiz_escrita LOGIN PASSWORD :'senha';" | docker compose exec -T -e SENHA_QUIZ="$SENHA_QUIZ" db sh -c \
    'psql -v ON_ERROR_STOP=1 -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v senha="$SENHA_QUIZ"'
  echo "papel quiz_escrita: login habilitado"
fi
