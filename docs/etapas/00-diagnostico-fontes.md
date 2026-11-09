# Etapa 0 — Diagnóstico de disponibilidade e tamanho das fontes

**Status:** concluída · **Comando:** `python -m ingest.diagnostico.avaliar_fontes [--fonte X] [--year-start AAAA]`
**Código:** `ingest/diagnostico/` · **Relatórios:** `ingest/relatorios/diagnostico_fontes.{md,json}` e `ingest/relatorios/arquivo/`
**Decisões:** D-001 a D-011

## Objetivo

Antes de baixar qualquer base, verificar para cada fonte: se está acessível, a forma de acesso, o tamanho, quantos registros entram no recorte, a licença, a frequência de atualização, os identificadores úteis para cruzamento e os riscos. Regra da etapa: **nunca baixar arquivos maiores que 50 MB**; usar só cabeçalhos, manifests, metadados e amostras.

## O que foi construído

- **Cliente HTTP comum** (`ingest/diagnostico/http.py`), reaproveitado por todas as etapas seguintes:
  - cache em disco (`ingest/.cache/`);
  - respeito ao robots.txt (RFC 9309), com exceções explícitas para APIs oficiais documentadas (D-003);
  - intervalo mínimo por host e `Crawl-delay`;
  - retry com backoff exponencial e `Retry-After`, mais timeout;
  - trava de tamanho;
  - certificados do sistema (`truststore`), porque sites gov.br não validam com o certifi;
  - User-Agent identificado com `CONTACT_EMAIL`.
- **Leituras parciais sem baixar o arquivo inteiro**:
  - diretório central de ZIPs remotos via `Range`, mais extração de um único arquivo de dentro do ZIP;
  - primeiros 256 KB de CSVs para colunas e estimativa de linhas;
  - quando o servidor ignora o `Range`, o cliente lê só o prefixo e fecha a conexão.
- **27 avaliações de fonte** em `ingest/diagnostico/fontes/`, agrupadas em instituições, CAPES, grupos de pesquisa, pesquisadores, produção, fotos e complementares. Um relatório JSON e Markdown traz a tabela-resumo e as estimativas de disco, tempo e custo.

## Histórico

1. **Diagnóstico nacional** (Brasil, 2020–2026): o escopo original da plataforma "Rede Ciência BR". Ficou arquivado em `ingest/relatorios/arquivo/diagnostico_fontes_brasil_2020-2026.*`.
2. **Mudança de escopo** para o Nordeste, ciências da saúde e biomédicas, últimos 5 anos (D-009). O recorte foi centralizado em `ingest/diagnostico/recorte.py` (D-010) e o diagnóstico foi refeito.
3. Depois, o recorte foi ampliado para ciências agrárias, biológicas e veterinária (D-017). **O relatório atual do diagnóstico é anterior a essa ampliação**: seus números são do recorte de saúde. Os números do recorte final estão nas etapas 1 a 7.

## Principais achados

| Fonte | Achado | Recomendação |
|---|---|---|
| OpenAlex | API com cobrança por uso (US$ 0,0001 por chamada de lista; sem chave, US$ 0,10/dia por IP; com chave gratuita, US$ 1/dia). **111 instituições do NE estão sem `geo.region`** (a UFPB entre elas), e o filtro por estado perde cerca de 15% da produção | usar, filtrando por **lista de instituições**, não por estado |
| Snapshot do OpenAlex (S3) | 629 GB de works para aproveitar 0,015% | descartado; API com chave |
| ROR | Dump CC0 de 37 MB no Zenodo; 225 organizações no NE, com coordenadas e IDs externos | usar |
| INEP | Microdados do Censo da Educação Superior; a tabela de IES (1 MB dentro de um ZIP de 436 MB) foi lida inteira por `Range`: 604 IES no NE | usar |
| dados.gov.br | A API exige token (HTTP 401) | complementar |
| CAPES | O portal bloqueia `/api/` no robots.txt e pede `Crawl-delay: 10`; usamos as páginas HTML e os arquivos. Datastore CKAN com só 1.000 linhas de prévia | usar (CSV por ano) |
| CNPq / DGP | Sem download em lote oficial; `dadosabertos.cnpq.br` bloqueado no robots.txt | pedido LAI (etapa 3) |
| ORCID | API pública documentada; na amostra de 500 autores do NE, 67% não têm nenhum emprego registrado | usar só sob demanda (reivindicação) |
| SciELO | ArticleMeta não filtra por região nem área; o cruzamento por ISSN com o OpenAlex deu 9.256 works do recorte de saúde | complementar |
| BDTD / Oasisbr (IBICT) | Firewall bloqueou uma busca booleana longa (403 e depois conexão recusada); parei de acessar (D-011). O bloqueio já expirou | complementar, via OAI-PMH |
| Wikidata | 29 de 4.632 pessoas com ORCID e vínculo no NE têm foto | complementar (etapa 7) |
| PNIPE / MCTI | SPA sem API documentada | acordo ou pedido LAI |

## Problemas encontrados e como foram tratados

- **Conflito entre robots.txt e APIs oficiais** (ORCID, Wikidata, IBGE): decidido pelo usuário, com exceções explícitas e justificadas (D-003).
- **Certificados ICP-Brasil** não validavam no certifi: adotado `truststore` (D-004).
- **Datastore da CAPES com prévia de 1.000 linhas**: linhas estimadas pelo tamanho do arquivo dividido pelos bytes médios por linha (D-005).
- **IBICT bloqueou o IP**: consultas limitadas a 11 termos, 5 s entre chamadas, sem contornar (D-011).

## Custo

O diagnóstico inteiro gastou menos de 200 créditos do OpenAlex (< US$ 0,02).
