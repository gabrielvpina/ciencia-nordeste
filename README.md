<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/01-placa-horizontal-escuro.svg">
    <img src="assets/01-placa-horizontal.svg" alt="Ciência Nordeste" width="420">
  </picture>
</p>

# Ciência Nordeste

Repositório aberto da pesquisa em **ciências da vida** do Nordeste: saúde, biomedicina, biotecnologia, genética, microbiologia, ciências agrárias e biológicas e veterinária. Reúne, a partir de **dados abertos**, instituições, programas de pós-graduação, pesquisadores, publicações (2022–2026), teses e colaborações dos nove estados da região.

- Visão, recorte, modelo de dados e fases: **[SCHEME.md](SCHEME.md)**, a fonte de verdade do projeto.
- Ingestão de dados, passo a passo: **[ingest/README.md](ingest/README.md)**.

## Números atuais

| | |
|---|---|
| Instituições | 754 |
| Programas de pós-graduação | 313 |
| Pesquisadores | 144.891 (5.583 docentes de pós) |
| Publicações 2022–2026 | 111.164 |
| Teses e dissertações | 15.047 |

## Como rodar localmente

```bash
cp .env.example .env                       # preencha CONTACT_EMAIL, OPENALEX_API_KEY e POSTGRES_*
python3.12 -m venv .venv && .venv/bin/pip install -r ingest/requirements.txt
# dados (ordem completa em ingest/README.md): partes 1 → 2 → 5 → 4 → revisão → 6 → 7
./scripts/carregar_banco.sh                # Postgres 16 no Docker: migrações + carga dos CSVs
docker compose up -d embed web             # app em http://localhost:3000 (+ serviço da busca por tema)
./scripts/verificar.sh                     # lint, tipos, build e migrações num banco vazio
./scripts/backup.sh                        # backup do que não se regenera + dump do banco (~/Backups/ciencia-nordeste)
./scripts/atualizar_dados.sh               # atualização periódica dos dados (--sim mostra o plano; ver ingest/README.md)
```

## Índice da documentação (`docs/`)

### Etapas executadas — [`docs/etapas/`](docs/etapas/)

| # | Etapa | Status |
|---|---|---|
| 0 | [Diagnóstico de disponibilidade e tamanho das fontes](docs/etapas/00-diagnostico-fontes.md) | concluída |
| 1 | [Instituições do Nordeste](docs/etapas/01-instituicoes.md) | concluída |
| 2 | [Programas de pós-graduação e docentes (CAPES)](docs/etapas/02-pos-graduacao-capes.md) | concluída |
| 3 | [Grupos de pesquisa](docs/etapas/03-grupos-de-pesquisa.md) | aguardando pedido LAI |
| 4 | [Pesquisadores e resolução de identidade](docs/etapas/04-pesquisadores.md) | concluída |
| 5 | [Produção científica (OpenAlex)](docs/etapas/05-producao.md) | concluída |
| 6 | [Complementos: teses e orientações, FAPs do NE, BDTD/Oasisbr](docs/etapas/06-complementos.md) | concluída (BDTD/Oasisbr só sondados) |
| 7 | [Fotos de pesquisadores](docs/etapas/07-fotos.md) | concluída (Commons) |
| 8 | [Revisão de identidade e consolidação](docs/etapas/08-revisao-identidade.md) | em uso; revisão manual pendente |
| 9 | [Banco de dados, migrações e CI](docs/etapas/09-banco-migracoes-ci.md) | concluída |
| 10 | [Aplicação web](docs/etapas/10-aplicacao-web.md) | núcleo concluído |
| 11 | [Mapa próprio do Nordeste](docs/etapas/11-mapa-proprio.md) | concluída |
| 12 | [Busca vetorial por tema de pesquisa](docs/etapas/12-busca-vetorial.md) | concluída |

### Outros documentos

| Documento | Conteúdo |
|---|---|
| [docs/decisoes.md](docs/decisoes.md) | Registro de decisões técnicas, D-001 a D-032 (fontes, robots.txt, recorte, identidade, banco, app, mapa, interface, atualização dos dados) |
| [docs/pedido_lai_cnpq.md](docs/pedido_lai_cnpq.md) | Texto pronto do pedido de acesso à informação ao CNPq (grupos de pesquisa e bolsistas PQ) |

### Relatórios gerados (`ingest/relatorios/`, fora do git)

Saídas de cada etapa, geradas localmente ao rodar a ingestão (não são versionadas, D-026), com os números exatos de cada execução: `diagnostico_fontes`, `parte1_instituicoes`, `parte2_capes`, `parte4_pesquisadores`, `parte5_producao`, `parte6_complementos`, `parte7_fotos`, `parte9_qualis` (em `.md` e `.json`) e `revisao_consolidacao.json`. O diagnóstico nacional original está em `ingest/relatorios/arquivo/`.

## Fontes e licenças

OpenAlex (CC0), ROR (CC0), CAPES Dados Abertos (CC-BY), Qualis Periódicos 2021-2024 (CAPES/Sucupira, dados públicos), INEP e IBGE (dados públicos), Wikidata (CC0) e Wikimedia Commons (licenças livres por arquivo, com crédito). Sem dados da Plataforma Lattes nem do Google Acadêmico.

## O que está (e o que não está) no git

O repositório guarda **só código e documentação**. Dados, fotos, relatórios gerados, o registro de UUIDs estáveis (`ingest/dados/ids/`) e as decisões de revisão (`ingest/dados/revisao/decisoes.csv`) ficam apenas no disco (D-026). Os dois últimos **não são regeneráveis**: rode `./scripts/backup.sh` com frequência (e `./scripts/restaurar.sh PACOTE` para verificar ou restaurar). **Não faça `git checkout` de commits anteriores a `f9451a7` na pasta de trabalho**: isso sobrescreve e depois apaga esses arquivos (D-027).
