#!/usr/bin/env bash
# Remove um cadastro do quiz pelo código de remoção (D-041), a pedido do titular. Rode no servidor (ou localmente).
# Uso: ./scripts/quiz_remover.sh K7QM-4TZP
set -euo pipefail
cd "$(dirname "$0")/.."
codigo="$(echo "${1:-}" | tr '[:lower:]' '[:upper:]' | tr -d ' ')"
if ! [[ "$codigo" =~ ^[A-Z0-9]{4}-[A-Z0-9]{4}$ ]]; then
  echo "uso: $0 XXXX-XXXX (o código mostrado depois do cadastro)" >&2
  exit 1
fi
n=$(docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"WITH d AS (DELETE FROM quiz_participantes WHERE codigo_remocao = '$codigo' RETURNING 1) SELECT count(*) FROM d\"")
if [ "$n" = "1" ]; then
  echo "cadastro $codigo removido."
  echo "Lembre: os backups antigos (scripts/backup.sh) ainda o contêm até serem substituídos; responda na issue sem repetir dados."
else
  echo "nenhum cadastro com o código $codigo." >&2
  exit 2
fi
