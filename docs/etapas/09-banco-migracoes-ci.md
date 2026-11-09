# Etapa 9 — Banco de dados, migrações e CI (Fase B)

**Status:** concluída · **Comandos:** `./scripts/carregar_banco.sh`, `./scripts/migrar.sh`, `./scripts/verificar.sh`
**Arquivos:** `docker-compose.yml`, `docker-compose.prod.yml`, `ingest/sql/migracoes/`, `ingest/sql/carga.sql`, `.github/workflows/ci.yml`
**Decisões:** D-019 (Fase B), D-022 (migrações SQL), D-026 (o que vai para o git)

## Banco

- **PostgreSQL 16.4 no Docker**, publicado só em `127.0.0.1:5432`. Em produção (`docker-compose.prod.yml`), nenhuma porta é publicada.
- Credenciais em `POSTGRES_*` no `.env`; a senha local foi gerada aleatoriamente. O `.env` nunca vai para o git.
- Extensões: `pg_trgm` e `unaccent`, com o invólucro **`f_unaccent`** (IMMUTABLE), porque `unaccent()` não pode ser usada em índice. Foi o primeiro bug que o teste real do SQL pegou.

## Migrações versionadas (D-022)

SQL numerado em `ingest/sql/migracoes/`, aplicado por `scripts/migrar.sh`, numa transação por migração, registrado em `schema_migrations`:

| Migração | Conteúdo |
|---|---|
| `0001_schema_inicial` | 22 tabelas: municípios, instituições, identificadores, relações, fila de revisão, programas, pesquisadores, aliases, identificadores, docentes, publicações, autorias, tópicos, financiadores, coautorias, teses, FAPs |
| `0002_resumo_e_filtros` | Visões materializadas `mv_resumo`, `mv_pesquisador_busca`, `mv_instituicao_stats` (home de 2,5 s para 0,35 s) |
| `0003_fotos` | `researcher_photos` |
| `0004_instituicao_areas` | `mv_instituicao_areas` (página de instituição de 2,5 s para 0,2 s) |
| `0005_mapa` | `work_authorships.countries` e visões do mapa: `mv_work_inst`, `mv_mapa_producao`, `mv_mapa_colaboracao`, `mv_inst_externo` |
| `0006_indices_perfil` | Índices de coautoria pelos dois lados (página de pesquisador de 4,4 s para ~0,02 s) |

Regras: nunca editar uma migração já aplicada, e toda migração deve poder rodar duas vezes.

## Carga

`ingest/sql/carga.sql` carrega os CSVs de `ingest/dados/processados/` com *upsert*, numa única transação, e no fim atualiza as visões materializadas.

- Testada com duas cargas seguidas e resultado idêntico (idempotente), sem aliases órfãos nem autorias do NE sem pesquisador.
- Decisões da fila não são sobrescritas por "pendente".
- Pares repetidos entre filas são deduplicados.

## Qualidade e CI

- **`scripts/verificar.sh`** (local): ruff, mypy, typecheck e build do app no Docker, e todas as migrações aplicadas duas vezes num banco vazio descartável.
- **`.github/workflows/ci.yml`**: os mesmos três blocos. Roda quando o repositório tiver remoto no GitHub.

## Backup e restauração (D-027)

| Comando | O que faz |
|---|---|
| `./scripts/backup.sh [--sem-banco]` | Pacote datado em `BACKUP_DIR` (padrão `~/Backups/ciencia-nordeste`, permissão só do dono) com o registro de UUIDs, as decisões de revisão, o `pg_dump` do banco, um manifesto e checksums SHA-256. Mantém os 14 mais recentes; cópia extra opcional em `BACKUP_COPIA_EXTRA` |
| `./scripts/restaurar.sh PACOTE` | Só verifica (checksums e manifesto); não altera nada |
| `./scripts/restaurar.sh PACOTE --ids [--destino DIR]` | Restaura os IDs e as decisões; se o atual for diferente, exige `--forcar` e guarda o atual como `*.antes-<data>` |
| `./scripts/restaurar.sh PACOTE --banco --forcar` | Recria o banco a partir do dump |

Testado em 2026-11-09: pacote de 129 MB (dump de 113 MB); IDs restaurados idênticos aos em uso; as proteções contra sobrescrever funcionaram; restauração completa do banco num banco descartável com contagens idênticas.

O `docker-compose.yml` fixa `name: ciencia-nordeste`, para que renomear a pasta não crie um banco novo e vazio.

## Git

- Repositório local, sem remoto, com o branch `main`.
- O git guarda **só código e documentação** (D-026, que substitui D-020).
- Ficam fora: `.env`, caches, dados brutos (1,8 GB), processados (618 MB), fotos, relatórios gerados, o registro de UUIDs e as decisões de revisão.
- O registro de UUIDs e as decisões de revisão **não são regeneráveis**: use `scripts/backup.sh`.
- **Não faça `git checkout` de commits anteriores a `f9451a7` na pasta de trabalho**: isso sobrescreve esses arquivos com versões antigas, e voltar ao `main` os apaga (incidente de 2026-11-09, recuperado sem perda; D-027).
