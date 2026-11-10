# ingest — camada de dados do Ciência Nordeste

Scripts Python que levantam e (nas próximas partes) carregam dados abertos sobre a pesquisa biomédica,
em saúde, biotecnologia e genética dos últimos 5 anos no Nordeste: instituições, programas de pós, docentes,
pesquisadores, grupos de pesquisa e produção. O recorte (UFs, período, áreas) fica em `diagnostico/recorte.py` (D-009, D-010).
Fonte de verdade do projeto: [`../SCHEME.md`](../SCHEME.md). Decisões técnicas: [`../docs/decisoes.md`](../docs/decisoes.md).

## Regras

- Só fontes abertas ou com licença de reuso; a licença de cada fonte fica registrada no relatório.
- Sem scraping da Plataforma Lattes, do DGP ou do Google Acadêmico. Não contornar captcha, bloqueio ou limite.
- robots.txt respeitado pelo cliente HTTP; exceções só para APIs oficiais documentadas (D-003).
- Segredos só no `.env` (veja `../.env.example`).

## Preparar o ambiente

Requisitos de máquina e programas, a planilha do Qualis e o caminho completo de um clone até o site: [`../docs/rodar-localmente.md`](../docs/rodar-localmente.md).

```bash
# na raiz do repositório
python3.12 -m venv .venv            # 3.12 ou mais novo
.venv/bin/pip install -r ingest/requirements.txt   # httpx, python-dotenv, truststore
cp .env.example .env                # preencha POSTGRES_PASSWORD, CONTACT_EMAIL e OPENALEX_API_KEY
```

| Variável | Uso |
|---|---|
| `CONTACT_EMAIL` | Vai no User-Agent (`ache-um-pesquisador-diagnostico/0.1 (...; mailto:...)`). |
| `OPENALEX_API_KEY` | Chave gratuita do OpenAlex (US$ 1/dia). Sem ela: US$ 0,10/dia compartilhado por IP e sem cursor paging. |
| `DADOS_GOV_BR_TOKEN` | Opcional. Token da API do dados.gov.br (sem ele o portal responde 401). |
| `YEAR_START` | Ano inicial do recorte. Use `2022` para reproduzir a base publicada; sem valor, vira (ano atual − 4). |
| `INGEST_SEM_CACHE` | `1` ignora o cache HTTP em todas as partes (o `atualizar_dados.sh` liga sozinho). |
| `AMOSTRA_ORCID` | Tamanho da amostra OpenAlex×ORCID na Parte 0 (padrão 500). |

## Parte 0 — diagnóstico de fontes

```bash
python -m ingest.diagnostico.avaliar_fontes                      # todas as fontes
python -m ingest.diagnostico.avaliar_fontes --listar             # ids e grupos
python -m ingest.diagnostico.avaliar_fontes --fonte ror          # uma fonte
python -m ingest.diagnostico.avaliar_fontes --fonte capes        # um grupo
python -m ingest.diagnostico.avaliar_fontes --year-start 2018 --sem-cache
```

Saídas:

- `relatorios/diagnostico_fontes.json`: dados brutos (resultado por fonte, chamadas feitas, estimativas);
- `relatorios/diagnostico_fontes.md`: relatório legível com tabela-resumo, detalhes e estimativas finais.

Com `--fonte`, o resultado das outras fontes é mantido a partir do JSON anterior (se o `YEAR_START` for o mesmo).

Comportamento:

- cache das respostas em `ingest/.cache/` (apague a pasta ou use `--sem-cache` para refazer);
- nunca baixa mais que 50 MB por arquivo: usa HEAD, manifests, metadados e leituras parciais com `Range`
  (diretório central de ZIPs, primeiros 256 KB de CSVs);
- uma fonte com erro não interrompe as outras: o erro vai para o relatório;
- intervalo mínimo por host e `Crawl-delay` respeitados (a CAPES pede 10 s, então o grupo `capes` leva ~10 min sem cache).

### Estrutura

```
ingest/
├── pyproject.toml        # metadados, ruff e mypy
├── requirements.txt
├── diagnostico/
│   ├── avaliar_fontes.py   # CLI
│   ├── config.py           # .env, limites, exceções de robots.txt, intervalos por host
│   ├── http.py             # cliente HTTP: cache, robots, retry, Range, ZIP/CSV parcial
│   ├── openalex.py         # contagens e group_by
│   ├── relatorio.py        # JSON + Markdown + estimativas finais
│   └── fontes/             # um módulo por grupo de fontes (1 a 7)
└── relatorios/
```

Para adicionar uma fonte: escreva uma função `def minha_fonte(ctx: Contexto) -> ResultadoFonte` no módulo do
grupo e inclua em `AVALIACOES` desse módulo.

## Parte 1 — instituições do Nordeste

```bash
python -m ingest.carga.parte1_instituicoes
```

Une ROR (lista-base por UF), OpenAlex, INEP (IES, código e-MEC, natureza, município IBGE), IBGE (municípios e coordenadas)
e o cruzamento ROR ↔ e-MEC do Wikidata. Gera em `dados/processados/`: `municipalities.csv`, `institutions.csv`,
`institution_identifiers.csv`, `institution_relations.csv`, `institution_review_queue.csv` e
`openalex_institution_ids_ne.txt` (filtro da Parte 5). Relatório: `relatorios/parte1_instituicoes.md`. Política de cruzamento: D-012.

## Parte 2 — programas de pós e docentes (CAPES)

```bash
python -m ingest.carga.parte2_capes        # depende da Parte 1
```

Baixa os CSVs de programas e docentes dos anos do recorte (`dados/brutos/capes/`), filtra NE × áreas de saúde e gera
`graduate_programs.csv`, `program_faculty.csv`, `researchers_capes.csv`, `researcher_identifiers_capes.csv`,
`institution_identifiers_capes.csv` e `institution_review_queue_capes.csv`. Relatório: `relatorios/parte2_capes.md`.
Dados pessoais minimizados (D-014).

## Parte 5 — produção (rodar antes da 4)

```bash
python -m ingest.carga.parte5_producao      # exige OPENALEX_API_KEY; ~1.000 chamadas, ~35 min, < US$ 0,15
```

Works com autoria em instituição do NE (lista da Parte 1, via lineage) × fields de saúde × período. Gera `works.csv`,
`work_authorships_openalex.csv`, `topics.csv`, `work_topics.csv`, `funders.csv` e `work_funders.csv`. Relatório:
`relatorios/parte5_producao.md`. Lotes já coletados não são baixados de novo (`--recoletar` força).

## Parte 9 — Qualis Periódicos (depois da 5)

```bash
python -m ingest.carga.parte9_qualis        # ~20 s; lê a planilha e os brutos da Parte 5, sem chamadas à rede
```

Entrada manual: na [consulta de periódicos do Qualis](https://sucupira-legado.capes.gov.br/sucupira/public/consultas/coleta/veiculoPublicacaoQualis/listaConsultaGeralPeriodicos.jsf)
escolha o evento "Classificações de periódicos quadriênio 2021-2024", exporte a planilha e salve em
`dados/brutos/capes/qualis/qualis-2021-2024.xlsx` (colunas ISSN, Título, Área de Avaliação, Estrato). Gera `qualis_periodicos.csv` e
`venue_issns.csv` (todos os ISSNs de cada revista). Relatório com a cobertura: `relatorios/parte9_qualis.md`. A planilha não entra no
backup, mas os dados ficam no dump do banco (D-033).

## Parte 4 — pesquisadores

```bash
python -m ingest.carga.parte4_pesquisadores # depende das Partes 1, 2 e 5
```

Busca os perfis dos autores do NE em lotes de 100, une perfis com o mesmo ORCID e manda os pares docente CAPES × autor
OpenAlex para a fila de revisão (sem mescla automática, D-015). Gera `researchers_openalex.csv`,
`researcher_identifiers_openalex.csv`, `researcher_topics.csv`, `researcher_review_queue.csv`, `work_authorships.csv`,
`coauthorships.csv` e `institution_collaborations.csv`. Relatório: `relatorios/parte4_pesquisadores.md`.

## Parte 8 — busca por tema (embeddings)

```bash
.venv/bin/pip install -r ingest/requirements-embeddings.txt   # torch, sentence-transformers, psycopg (pesado)
python -m ingest.carga.parte8_embeddings coletar-keywords
python -m ingest.carga.parte8_embeddings embeddings           # com 8 GB de RAM, feche o Docker Desktop antes
python -m ingest.carga.parte8_embeddings carregar             # depois de ./scripts/carregar_banco.sh
python -m ingest.carga.avaliar_busca_tema                     # com o app e o serviço embed no ar
```

Detalhes e resultados: `docs/etapas/12-busca-vetorial.md` (D-028).

## Revisão de identidade e consolidação

```bash
python -m ingest.carga.revisao aplicar-regra --decidido-por "Nome"   # regra D-018 (já aplicada uma vez)
python -m ingest.carga.revisao exportar                               # dados/revisao/pendentes_*.csv para revisar
python -m ingest.carga.revisao importar dados/revisao/pendentes_pesquisadores.csv --decidido-por "Nome"
python -m ingest.carga.revisao consolidar                             # gera researchers.csv, aliases, fila com status
```

Preencha a coluna `decisao` da planilha com `aceito` ou `rejeitado` (linhas em branco são ignoradas).

## Parte 7 — fotos

```bash
python -m ingest.carga.parte7_fotos         # ORCIDs do recorte → Wikidata (P18) → Commons; só licença livre; WebP ≤ 400 px sem EXIF
```

Fotos em `dados/fotos/<researcher_id>.webp` (servidas pelo app em `/foto/<id>`); crédito e licença em `researcher_photos.csv`.

## Parte 6 — complementos

```bash
python -m ingest.carga.parte6_complementos  # teses/orientações CAPES (baixa ~1,5 GB), FAPs do NE, sondagem do IBICT
```

## Mapa próprio

```bash
python -m ingest.carga.gerar_mapa_ne     # só quando a malha do IBGE mudar; grava apps/web/components/mapa/geometria-ne.json
```

## Banco e app (Fase B)

```bash
./scripts/carregar_banco.sh                 # sobe o Postgres, aplica as migrações e a carga
docker compose up -d web                    # http://localhost:3000
```

Ordem completa de uma atualização: Parte 1 → 2 → 5 → 9 → 4 → revisão (consolidar) → 6 → 7 → 8 (keywords, embeddings) → `carregar_banco.sh` → 8 (carregar).

## Atualização periódica (`scripts/atualizar_dados.sh`)

Um comando faz a ordem completa acima, com backup antes e depois e uma conferência no fim:

```bash
./scripts/atualizar_dados.sh --sim                 # mostra o plano
./scripts/atualizar_dados.sh                       # atualização completa (algumas horas)
./scripts/atualizar_dados.sh --a-partir-de banco   # retoma depois de uma falha
./scripts/atualizar_dados.sh --so producao,banco   # só algumas etapas
```

- **Respostas novas:** por padrão ignora o cache HTTP (`INGEST_SEM_CACHE=1`) e recoleta os lotes do OpenAlex (`--recoletar`). `--manter-cache` reaproveita tudo (útil só para refazer o processamento).
- **Período:** vai de `YEAR_START` (.env) ao ano corrente. Num ano novo, ele entra sozinho na coleta, e o app lê o período do banco.
- **Revisão de identidade:** a regra D-018 é aplicada aos pares novos; os demais vão para `dados/revisao/pendentes_*.csv` (revisão manual, como antes).
- **Memória:** a etapa `embeddings` para os containers do Docker para liberar memória para o modelo; `app` os sobe de novo.
- **Conferência:** grava `relatorios/atualizacao-<data>.md` com as contagens antes/depois (alerta para quedas acima de 2%) e um teste das rotas do app; o log completo fica em `relatorios/atualizacao-<data>.log`.
- **Se algo der errado:** o backup da primeira etapa permite voltar (`scripts/restaurar.sh PACOTE --ids --forcar` e `--banco --forcar`).

## IDs estáveis e carga no Postgres

- UUIDs internos ficam em `dados/ids/<entidade>.csv` (só acréscimo; faz parte do backup). Ver D-013.
- `sql/migracoes/NNNN_*.sql` criam e alteram as tabelas (aplicadas em ordem por `scripts/migrar.sh`, registradas em `schema_migrations`); `sql/carga.sql` carrega os CSVs (upsert) e atualiza as visões materializadas.
- Mudança de schema = nova migração numerada (nunca editar uma já aplicada). `scripts/verificar.sh` testa todas num banco vazio.

## Próximas partes

Feitas: 0, 1, 2, 5, 4. Próximas: 3 grupos (pedido LAI em `docs/pedido_lai_cnpq.md`), 6 complementos (teses/orientações CAPES, FAPs, BDTD), 7 fotos.
Ordem e justificativa na seção final de `relatorios/diagnostico_fontes.md`.
