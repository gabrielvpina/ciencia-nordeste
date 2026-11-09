#!/usr/bin/env bash
# Backup do Ciência Nordeste: o que NÃO se regenera (D-026) + dump do banco.
#
# Conteúdo do pacote ciencia-nordeste-backup-AAAAMMDD-HHMMSS.tar.gz:
#   arquivos/ids/                 registro de UUIDs estáveis (ingest/dados/ids/)
#   arquivos/revisao/decisoes.csv decisões da revisão de identidade
#   banco.dump                    pg_dump (formato custom) do Postgres do docker compose (se estiver rodando)
#   MANIFESTO.txt                 data, commit, contagens, migrações aplicadas
#   SHA256SUMS                    checksums de tudo acima
#
# Uso:  ./scripts/backup.sh [--sem-banco]
# Configuração (.env, opcional):
#   BACKUP_DIR           pasta dos backups (padrão: ~/Backups/ciencia-nordeste)
#   BACKUP_RETENCAO      quantos backups manter (padrão: 14)
#   BACKUP_COPIA_EXTRA   segunda pasta para uma cópia, ex.: uma pasta sincronizada com a nuvem (opcional)
# O .env (segredos) NÃO entra no backup: guarde-o à parte, num gerenciador de senhas.
set -euo pipefail
cd "$(dirname "$0")/.."

ler_env() { [ -f .env ] && grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
DEST="$(ler_env BACKUP_DIR)"; DEST="${DEST:-$HOME/Backups/ciencia-nordeste}"
DEST="${DEST/#\~/$HOME}"
RETENCAO="$(ler_env BACKUP_RETENCAO)"; RETENCAO="${RETENCAO:-14}"
EXTRA="$(ler_env BACKUP_COPIA_EXTRA)"; EXTRA="${EXTRA/#\~/$HOME}"
COM_BANCO=1; [ "${1:-}" = "--sem-banco" ] && COM_BANCO=0

for f in ingest/dados/ids ingest/dados/revisao/decisoes.csv; do
  [ -e "$f" ] || { echo "ERRO: $f não existe — nada a proteger? Abortando." >&2; exit 1; }
done

STAMP="$(date +%Y%m%d-%H%M%S)"
NOME="ciencia-nordeste-backup-$STAMP.tar.gz"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/arquivos/revisao" "$DEST"
umask 077   # o pacote contém nomes de pesquisadores (dado pessoal público, mas não para circular): só o dono lê

cp -R ingest/dados/ids "$TMP/arquivos/ids"
cp ingest/dados/revisao/decisoes.csv "$TMP/arquivos/revisao/decisoes.csv"

MIGRACOES="(banco não incluído)"
if [ "$COM_BANCO" = 1 ]; then
  if docker compose ps --status running --services 2>/dev/null | grep -qx db; then
    docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner' > "$TMP/banco.dump"
    MIGRACOES="$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version FROM schema_migrations ORDER BY 1"' | paste -sd ',' - | sed 's/,/, /g')"
  else
    echo "AVISO: o Postgres do docker compose não está rodando; backup sem banco.dump (use --sem-banco para silenciar)." >&2
  fi
fi

{
  echo "Ciência Nordeste — backup $STAMP"
  echo "máquina: $(hostname)"
  echo "commit: $(git rev-parse --short HEAD 2>/dev/null || echo '?') $(git diff --quiet 2>/dev/null || echo '(com alterações não commitadas)')"
  echo "migrações: $MIGRACOES"
  echo
  echo "linhas por arquivo:"
  for f in "$TMP"/arquivos/ids/*.csv "$TMP/arquivos/revisao/decisoes.csv"; do
    printf "  %-28s %s\n" "$(basename "$f")" "$(($(wc -l < "$f") - 1))"
  done
  [ -f "$TMP/banco.dump" ] && echo "banco.dump: $(du -h "$TMP/banco.dump" | cut -f1)"
} > "$TMP/MANIFESTO.txt"

( cd "$TMP" && find . -type f ! -name SHA256SUMS | sort | xargs shasum -a 256 > SHA256SUMS )
tar -czf "$DEST/$NOME" -C "$TMP" .
tar -tzf "$DEST/$NOME" > /dev/null   # o pacote abre?
echo "backup: $DEST/$NOME ($(du -h "$DEST/$NOME" | cut -f1))"

if [ -n "$EXTRA" ]; then
  mkdir -p "$EXTRA" && cp "$DEST/$NOME" "$EXTRA/" && echo "cópia extra: $EXTRA/$NOME"
fi

# Rotação: mantém os $RETENCAO mais recentes em cada pasta.
for d in "$DEST" ${EXTRA:+"$EXTRA"}; do
  ls -1t "$d"/ciencia-nordeste-backup-*.tar.gz 2>/dev/null | tail -n +"$((RETENCAO + 1))" | while read -r velho; do
    rm -f "$velho" && echo "removido (retenção $RETENCAO): $(basename "$velho")"
  done
done
