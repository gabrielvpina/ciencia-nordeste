# Como rodar localmente e reproduzir a base

Este guia leva de um clone do repositório até o site rodando em `http://localhost:3000`, com a base de dados montada do zero a partir das fontes abertas. O repositório guarda só código e documentação (D-026): os dados são gerados pela ingestão, que roda na sua máquina.

## 1. Requisitos

### Máquina

| | Mínimo | Recomendado |
|---|---|---|
| Sistema | macOS ou Linux (no Windows, use WSL 2) | |
| Memória | 8 GB | 16 GB |
| Disco livre | 25 GB | 40 GB |
| Internet | estável; a ingestão baixa cerca de 3 GB | |

Para onde vai o disco: dados brutos (~1,8 GB) e processados (~0,9 GB) em `ingest/dados/`; imagens Docker (~5 GB, das quais 3,7 GB do serviço de busca por tema); banco (~3,3 GB); cache de build do Docker (até ~10 GB, limpe com `docker builder prune -f`); e, na busca por tema, as dependências de `ingest/requirements-embeddings.txt` (PyTorch, ~2 GB) e o modelo de linguagem.

### Programas

| Programa | Versão | Para quê |
|---|---|---|
| Git | qualquer recente | clonar o repositório |
| Docker com Compose v2 (Docker Desktop no macOS) | Compose 2.24 ou mais novo | banco (PostgreSQL 16 + pgvector), app e serviço de busca |
| Python | 3.12 ou mais novo | ingestão (`ingest/`) |

Não é preciso instalar Node.js: o app é compilado dentro do Docker (`apps/web/Dockerfile`, Node 20).

### Contas e chaves (gratuitas)

| Item | Obrigatório? | Onde conseguir |
|---|---|---|
| E-mail de contato (`CONTACT_EMAIL`) | sim | o seu; vai no User-Agent das requisições |
| Chave do OpenAlex (`OPENALEX_API_KEY`) | sim | <https://openalex.org/settings/api>. A coleta completa custa menos de US$ 0,40 dos créditos diários gratuitos |
| Token do dados.gov.br (`DADOS_GOV_BR_TOKEN`) | não | só o diagnóstico de fontes (Parte 0) o usa |

### Arquivo obtido à mão

O **Qualis Periódicos 2021-2024** não tem download em lote nem API, e o projeto não raspa formulários (D-002, D-033). Antes da ingestão:

1. Abra a [consulta de periódicos do Qualis na Plataforma Sucupira](https://sucupira-legado.capes.gov.br/sucupira/public/consultas/coleta/veiculoPublicacaoQualis/listaConsultaGeralPeriodicos.jsf).
2. Em "Evento de Classificação", escolha **Classificações de periódicos quadriênio 2021-2024**, consulte sem outros filtros e exporte a planilha.
3. Salve como `ingest/dados/brutos/capes/qualis/qualis-2021-2024.xlsx`. As colunas esperadas são ISSN, Título, Área de Avaliação e Estrato.

Sem esse arquivo, a etapa `qualis` para com uma mensagem explicando o que falta.

## 2. Preparar o ambiente

```bash
git clone https://github.com/gabrielvpina/ciencia-nordeste.git
cd ciencia-nordeste

cp .env.example .env          # preencha POSTGRES_PASSWORD, CONTACT_EMAIL e OPENALEX_API_KEY; mantenha YEAR_START=2022
python3.12 -m venv .venv
.venv/bin/pip install -r ingest/requirements.txt
.venv/bin/pip install -r ingest/requirements-embeddings.txt   # só para a busca por tema (pesado; ver passo 3)
```

## 3. Montar a base e subir o site

Um comando faz a ingestão inteira, carrega o banco, sobe o app e confere o resultado:

```bash
./scripts/atualizar_dados.sh --sim     # mostra o plano
./scripts/atualizar_dados.sh           # tudo; cerca de 3 a 4 horas
```

| Etapa | O que faz | Tempo aproximado |
|---|---|---|
| `instituicoes` | Parte 1: ROR, INEP, IBGE, Wikidata | 5 min |
| `capes` | Parte 2: programas de pós e docentes (CAPES Dados Abertos) | 10 min |
| `producao` | Parte 5: publicações do OpenAlex | 35 min |
| `qualis` | Parte 9: estrato Qualis das revistas (planilha do passo 1) | 1 min |
| `pesquisadores` | Parte 4: perfis de autor e coautorias | 30–60 min |
| `revisao` | regra automática de identidade (D-018) e consolidação | poucos min |
| `complementos` | Parte 6: teses e orientações (baixa ~1,5 GB) | 20–40 min |
| `fotos` | Parte 7: fotos com licença livre (Wikidata/Commons) | 10 min |
| `keywords`, `embeddings`, `vetores` | Parte 8: busca por tema | ~1–2 h (os vetores rodam na CPU) |
| `banco` | migrações, carga dos CSVs e visões materializadas | 5 min |
| `app`, `conferencia` | sobe o site e testa as rotas | 2 min |

- **Sem a busca por tema:** `./scripts/atualizar_dados.sh --sem-embeddings` pula a Parte 8 e não precisa do `requirements-embeddings.txt`. O site funciona, e a busca por tema fica só pelo texto.
- **Com 8 GB de memória:** a etapa `embeddings` para os containers sozinha; feche outros programas pesados.
- **Se algo falhar:** corrija e retome da etapa que parou: `./scripts/atualizar_dados.sh --a-partir-de <etapa>`. Os downloads já feitos ficam em cache (`ingest/.cache/`) e não são refeitos.
- A ordem e os comandos de cada parte, um a um, estão em [`ingest/README.md`](../ingest/README.md).

Ao final, o site está em **http://localhost:3000** e o relatório da execução em `ingest/relatorios/atualizacao-<data>.md`.

### Comandos do dia a dia

```bash
docker compose up -d embed web     # sobe o site (o banco sobe junto)
docker compose logs -f web         # logs do app
docker compose down                # para tudo (os dados do banco ficam no volume)
./scripts/verificar.sh             # o mesmo que a CI: lint, tipos, build e migrações num banco vazio
./scripts/backup.sh                # backup do que não se regenera + dump do banco
```

Mudou o app? `docker compose up -d --build web`. Uma migração nova em `ingest/sql/migracoes/`? `./scripts/migrar.sh`.

## 4. Reprodutibilidade: o que sai igual e o que não sai

O código, o recorte e as regras são os mesmos para qualquer pessoa. Os números podem diferir um pouco da base publicada, pelos motivos abaixo.

| Fator | Efeito | Como lidar |
|---|---|---|
| **As fontes mudam** (o OpenAlex é atualizado continuamente; a CAPES publica novos anos-base) | contagens um pouco diferentes a cada coleta | a data de cada coleta fica nos relatórios em `ingest/relatorios/` |
| **Período** | sem `YEAR_START`, o recorte vira (ano atual − 4) | mantenha `YEAR_START=2022` no `.env` |
| **Revisão manual de identidade** (pares docente CAPES × autor OpenAlex que a regra D-018 não decide) | sem as decisões, esses perfis ficam separados | os pares pendentes vão para `ingest/dados/revisao/pendentes_*.csv`; o processo está em `ingest/README.md` ("Revisão de identidade") |
| **IDs internos (UUID)** | um clone novo gera UUIDs novos, então os endereços `/pesquisador/<id>` não coincidem com os do site publicado | o registro em `ingest/dados/ids/` mantém os IDs estáveis entre atualizações na mesma máquina; faça backup dele |
| **Qualis** | depende da planilha baixada à mão | use o evento 2021-2024 (passo 1) |

O que **não** se regenera e precisa de backup (`./scripts/backup.sh`): o registro de IDs (`ingest/dados/ids/`) e as decisões de revisão (`ingest/dados/revisao/decisoes.csv`). Tudo o mais sai de novo da ingestão.

## 5. Regras do projeto

Valem para qualquer contribuição (detalhes em [`SCHEME.md`](../SCHEME.md) e [`docs/decisoes.md`](decisoes.md)):

- **Só fontes abertas ou com licença de reuso**, com a licença registrada no relatório de cada parte.
- **Sem scraping** da Plataforma Lattes, do DGP/CNPq ou do Google Acadêmico; sem contornar captcha, bloqueio ou limite; `robots.txt` respeitado (exceções só para APIs oficiais documentadas, D-003).
- **Segredos só no `.env`**, que nunca entra no git.
- **O git guarda só código e documentação** (D-026); dados, relatórios e fotos ficam fora.
- **Mudança de schema = nova migração numerada** em `ingest/sql/migracoes/`; nunca editar uma já aplicada.
- Antes de enviar mudanças, rode `./scripts/verificar.sh`.
