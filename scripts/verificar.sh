#!/usr/bin/env bash
# Verificação local equivalente à CI: lint/tipos do Python, typecheck/build do app e migrações num Postgres vazio.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== Python"; .venv/bin/ruff check ingest --select E,F,W,I --ignore E501 && .venv/bin/mypy --config-file ingest/pyproject.toml ingest
echo "== Árvore do quiz"; .venv/bin/python -m ingest.carga.validar_arvore_quiz estatico   # ids, órfãos, ciclos, profundidade (sem banco)
echo "== App (typecheck + build no Docker)"; docker compose build -q web
echo "== Migrações num banco vazio (descartável, duas rodadas)"
docker compose up -d --wait db >/dev/null
docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists ci_verificacao && createdb -U "$POSTGRES_USER" ci_verificacao'
for rodada in 1 2; do
  for f in ingest/sql/migracoes/*.sql; do
    docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d ci_verificacao -v ON_ERROR_STOP=1 -q --single-transaction -f $f" >/dev/null
  done
  echo "rodada $rodada ok"
done
docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" ci_verificacao'
echo "tudo ok"
