# Etapa 4 — Pesquisadores e resolução de identidade

**Status:** concluída · **Comando:** `python -m ingest.carga.parte4_pesquisadores` (depende das etapas 1, 2 e 5; exige `OPENALEX_API_KEY`)
**Código:** `ingest/carga/parte4_pesquisadores.py` · **Relatório:** `ingest/relatorios/parte4_pesquisadores.md`
**Decisões:** D-015 (quem entra e como as identidades se resolvem)

> Ordem de execução: a etapa 5 (produção) roda **antes** desta, porque os pesquisadores do recorte saem das autorias das publicações do NE.

## Quem entra

- Todo autor do OpenAlex com **pelo menos uma autoria vinculada a instituição do NE** nas publicações do recorte.
- Os **docentes CAPES** da etapa 2.

Coautores de fora do NE ficam só nas autorias, com nome e ID OpenAlex, sem perfil próprio. Autorias sem ID de autor no OpenAlex não geram pesquisador.

## Como funciona

1. Agrega as autorias do NE por autor: publicações, instituições, anos e ORCID.
2. Busca os perfis dos autores no OpenAlex em lotes de 100 IDs (`filter=openalex:A1|A2|…`): nome e variantes, ORCID, métricas e tópicos.
3. **Une perfis do OpenAlex com o mesmo ORCID** num único UUID (identificador comum, confiança 1). São perfis fragmentados da mesma pessoa.
4. **Docente CAPES × autor OpenAlex**: não há identificador comum. Pares com sobrenome igual, primeiro nome compatível e instituição em comum vão para a **fila de revisão**, com score = 0,75 × similaridade do nome + 0,2 (teto de 0,95). **Nada é mesclado nesta etapa**; ver a [etapa de revisão](08-revisao-identidade.md).
5. Gera as arestas de coautoria entre pesquisadores do NE, só de publicações com até 50 autores, para que consórcios não criem ligações artificiais, e os pares de instituições que publicam juntas.
6. Prefere um nome em **alfabeto latino**. O OpenAlex às vezes escolhe uma transliteração em cirílico como nome de exibição (ex.: "Жозелио Фрейре де Карвалью" para Jozélio Freire de Carvalho).
7. Guarda os **países de cada autoria**, usados pelo mapa de rede da aplicação.

## Resultado

| Item | Valor |
|---|---|
| Autores do OpenAlex com autoria no NE | 143.952 |
| **Pesquisadores** (após unir perfis com o mesmo ORCID) | **141.961** (1.991 perfis unidos) |
| Com ORCID | 82.901 (58%) |
| Com 3 ou mais publicações no período | 35.806 |
| Docentes CAPES com candidato no OpenAlex | 4.841 de 5.583 (87%); 2.662 com candidato único e nome idêntico |
| Pares para revisão | 7.989 |
| Arestas de coautoria | 722.676 |
| Pares de instituições que publicam juntas | 4.203 (o maior é UFRPE–UFPE, com 1.847) |
| Custo no OpenAlex | ~1.170 chamadas (≈ US$ 0,12); reexecuções usam os perfis guardados em disco |

## Saídas

`researchers_openalex.csv`, `researcher_identifiers_openalex.csv`, `researcher_topics.csv`, `researcher_review_queue.csv`, `work_authorships.csv` (com `countries`), `coauthorships.csv`, `institution_collaborations.csv`. Perfis brutos em `ingest/dados/brutos/openalex/authors_ne.jsonl.gz`.

## Limitações

- Perfis sem ORCID podem continuar fragmentados (ex.: três perfis "Jozelio Carvalho"); a revisão e a futura reivindicação via ORCID resolvem isso.
- O ORCID não é consultado em massa; fica para a reivindicação de perfil (Fase D).
