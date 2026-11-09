# Etapa 1 — Instituições do Nordeste

**Status:** concluída · **Comando:** `python -m ingest.carga.parte1_instituicoes`
**Código:** `ingest/carga/parte1_instituicoes.py` · **Relatório:** `ingest/relatorios/parte1_instituicoes.md`
**Decisões:** D-012 (política de cruzamento), D-013 (IDs estáveis)

## Objetivo

Montar a tabela única de instituições do recorte, com geolocalização, tipo, natureza jurídica e todos os identificadores externos. Ela serve de base para ligar programas, pesquisadores e publicações.

## Fontes

| Fonte | O que entra |
|---|---|
| ROR v2.15 (2026-10-20, CC0) | Lista-base: 225 organizações do NE (filtro por país BR e `country_subdivision_code`), com coordenadas, siglas, nomes em português, relações e IDs externos (Wikidata, ISNI, GRID, FundRef) |
| OpenAlex | ID OpenAlex e produção das 225 organizações (consulta por ROR, em lotes de 100) |
| INEP, Censo da Educação Superior 2024 | 604 IES do NE com código e-MEC, categoria administrativa, organização acadêmica e município IBGE (só a tabela de IES, lida por `Range`) |
| IBGE | 1.794 municípios do NE (API de Localidades) e coordenadas das sedes (CSV derivado, MIT) |
| Wikidata | Cruzamento ROR ↔ e-MEC pelas propriedades P6782 × P5148 |

## Como funciona o cruzamento INEP ↔ ROR (D-012)

1. **Identificador comum** (confiança 1): Wikidata. Descoberta importante: a P5148 guarda o código e-MEC **em base64**, como nas URLs do e-MEC (`NTg2` → 586).
2. **Automático forte** (confiança 0,9): nome idêntico, ou sigla igual com nome parecido, **e** mesmo município, sem candidato concorrente.
3. **Fila de revisão**: todos os demais pares parecidos.

A similaridade de nomes ignora palavras genéricas ("Universidade", "Centro Universitário") e nomes de lugar do NE, que geravam falsos pares.

## Resultado

| Item | Valor |
|---|---|
| **Instituições unificadas** | **754** (ROR + IES do INEP sem correspondente) |
| Com ID OpenAlex | 225; vira a lista `openalex_institution_ids_ne.txt`, filtro da etapa 5 |
| Sem `geo.region` do NE no OpenAlex | 111 (recuperadas graças à lista) |
| Vínculos INEP ↔ ROR | 32 pelo Wikidata + 43 por nome/sigla + município |
| Pares para revisão | 49 |
| Relações (ROR) | 54 (18 entre instituições do NE) |
| Com coordenadas | 754 (225 pelo ROR/GeoNames, o restante pela sede do município) |
| Por natureza | 538 privadas, 48 públicas, 18 especiais, 150 sem informação (organizações só do ROR) |
| Por UF | BA 170 · PE 163 · CE 131 · MA 77 · PB 58 · PI 54 · AL 39 · RN 36 · SE 26 |

As unidades da Embrapa no NE e a EMPARN estão incluídas (conferido depois da ampliação do recorte).

## Saídas

`ingest/dados/processados/`: `municipalities.csv`, `institutions.csv`, `institution_identifiers.csv`, `institution_relations.csv`, `institution_review_queue.csv`, `openalex_institution_ids_ne.txt`. UUIDs em `ingest/dados/ids/institution.csv` (fora do git; precisa de backup, D-026).

## Problemas e lições

- **Bug do base64**: na primeira execução, o cruzamento pelo Wikidata deu só 2 vínculos. Corrigido, passou a 32. O registro de IDs gerado pela execução com bug foi descartado uma única vez (D-013), porque nada o consumia.
- **Ruído na fila de revisão**: resolvido ignorando palavras genéricas e nomes de lugar no cálculo de similaridade.
- **Idempotência**: uma segunda execução seguida não cria nenhum ID novo.

## Pendências

- Revisar os 49 pares da fila (`ingest/dados/revisao/pendentes_instituicoes.csv`).
- Autores que assinam só "Embrapa" (a sede, no DF) ficam fora do recorte mesmo trabalhando no NE.
