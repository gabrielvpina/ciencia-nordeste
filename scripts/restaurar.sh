#!/usr/bin/env bash
# Restaura (ou só verifica) um backup gerado por scripts/backup.sh.
#
# Uso:
#   ./scripts/restaurar.sh PACOTE.tar.gz                    só verifica: checksums e conteúdo (não altera nada)
#   ./scripts/restaurar.sh PACOTE.tar.gz --ids [--destino DIR]
#        restaura ids/ e revisao/decisoes.csv em ingest/dados/ (ou em DIR, para conferência);
#        se já existirem e forem diferentes, exige --forcar e guarda os atuais como *.antes-<data>
#   ./scripts/restaurar.sh PACOTE.tar.gz --banco --forcar
#        recria o banco do docker compose a partir do banco.dump (APAGA o conteúdo atual do banco)
set -euo pipefail
cd "$(dirname "$0")/.."

PACOTE="${1:-}"; shift || true
[ -f "$PACOTE" ] || { echo "uso: $0 PACOTE.tar.gz [--ids [--destino DIR]] [--banco] [--forcar]" >&2; exit 1; }
IDS=0; BANCO=0; FORCAR=0; DESTINO="ingest/dados"
while [ $# -gt 0 ]; do
  case "$1" in
    --ids) IDS=1 ;; --banco) BANCO=1 ;; --forcar) FORCAR=1 ;;
    --destino) DESTINO="$2"; shift ;;
    *) echo "opção desconhecida: $1" >&2; exit 1 ;;
  esac
  shift
done

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar -xzf "$PACOTE" -C "$TMP"
( cd "$TMP" && shasum -a 256 -c --quiet SHA256SUMS ) || { echo "ERRO: checksums não conferem — pacote corrompido." >&2; exit 1; }
echo "checksums ok"; echo; cat "$TMP/MANIFESTO.txt"; echo

if [ "$IDS" = 1 ]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$DESTINO/revisao"
  for par in "ids:$DESTINO/ids" "revisao/decisoes.csv:$DESTINO/revisao/decisoes.csv"; do
    origem="$TMP/arquivos/${par%%:*}"; alvo="${par#*:}"
    if [ -e "$alvo" ] && ! diff -rq "$origem" "$alvo" > /dev/null; then
      [ "$FORCAR" = 1 ] || { echo "ERRO: $alvo existe e é diferente do backup. Use --forcar (o atual será guardado como $alvo.antes-$STAMP)." >&2; exit 1; }
      mv "$alvo" "$alvo.antes-$STAMP" && echo "atual guardado em $alvo.antes-$STAMP"
    fi
    rm -rf "$alvo"; cp -R "$origem" "$alvo"; echo "restaurado: $alvo"
  done
fi

if [ "$BANCO" = 1 ]; then
  [ -f "$TMP/banco.dump" ] || { echo "ERRO: este backup não tem banco.dump." >&2; exit 1; }
  [ "$FORCAR" = 1 ] || { echo "ERRO: restaurar o banco apaga o conteúdo atual. Repita com --forcar." >&2; exit 1; }
  docker compose up -d --wait db > /dev/null
  docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' < "$TMP/banco.dump"
  echo "banco restaurado"
fi

[ "$IDS" = 0 ] && [ "$BANCO" = 0 ] && echo "(só verificação; nada foi alterado)"
exit 0
