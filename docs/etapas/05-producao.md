# Etapa 5 — Produção científica (OpenAlex)

**Status:** concluída · **Comando:** `python -m ingest.carga.parte5_producao [--recoletar]` (depende da etapa 1; exige `OPENALEX_API_KEY`)
**Código:** `ingest/carga/parte5_producao.py` · **Relatório:** `ingest/relatorios/parte5_producao.md`
**Decisões:** D-006 (API com chave em vez de snapshot), D-016 (filtro por lista de instituições), D-017 (recorte ampliado)

## Recorte

Publicações com pelo menos uma autoria em instituição do NE, ano de publicação entre **2022 e 2026** e *primary topic* num dos fields do recorte:

- **Saúde e biomédicas**: Medicine, Biochemistry/Genetics/Molecular Biology, Immunology and Microbiology, Neuroscience, Pharmacology, Nursing, Dentistry, Health Professions;
- **Ampliação**: Agricultural and Biological Sciences, Veterinary.

## Como funciona

- **Filtro** `authorships.institutions.lineage` com os 225 IDs OpenAlex da etapa 1, em 3 lotes de até 100. O filtro por estado (`geo.region`) perderia 111 instituições, entre elas a UFPB.
- **Paginação**: cursor (exige chave). Os lotes ficam em `ingest/dados/brutos/openalex/works_loteNN.jsonl.gz`, cada um com um marcador `.ok`, então uma reexecução não baixa de novo.
- **Deduplicação** das publicações que aparecem em mais de um lote.
- **Autorias truncadas**: a listagem do OpenAlex traz **só as 100 primeiras autorias**. As 195 publicações de consórcio (com mais de 100 autores) são buscadas de novo no endpoint individual, que é gratuito e traz até 5.000 autorias. Sem isso, autores do NE depois da posição 100 se perdiam.
- As autorias são gravadas em *streaming*, para não estourar a memória.

## Resultado

| Item | Valor |
|---|---|
| **Publicações** | **111.164** |
| Por ano | 2022: 19.132 · 2023: 21.088 · 2024: 24.365 · 2025: 23.849 · 2026: 22.730 |
| Por área | Medicina 56.279 · Agrárias e Biológicas 26.162 · Profissões da saúde 6.200 · Odontologia 6.198 · Bioquímica/Genética 4.642 · Enfermagem 3.238 · Imunologia/Microbiologia 3.083 · Neurociência 2.596 · Farmacologia 1.671 · Veterinária 1.095 |
| Por UF (uma publicação conta em cada UF envolvida) | PE 28.433 · BA 23.052 · CE 21.438 · PB 16.703 · RN 11.794 · MA 10.100 · PI 9.529 · SE 6.910 · AL 6.615 |
| Envolvendo 2 ou mais estados do NE | 18.537 |
| Idioma | inglês 60.890 · português 49.039 |
| Acesso aberto | diamond 48.798 · gold 19.837 · fechado 15.441 · híbrido 11.021 · green 9.114 · bronze 6.953 |
| Autorias | 907.205 (436.057 com instituição do NE); 336.386 autores distintos (143.952 com autoria no NE) |
| Tópicos / financiadores | 2.851 tópicos; 3.991 financiadores; 27.937 publicações com financiamento declarado |
| Custo no OpenAlex | 1.356 créditos ≈ **US$ 0,14** |

## Saídas

`works.csv`, `work_authorships_openalex.csv`, `topics.csv`, `work_topics.csv`, `funders.csv`, `work_funders.csv`. UUIDs em `ingest/dados/ids/work.csv`.

## Histórico

- Primeira coleta (só saúde e biomédicas): 83.902 publicações.
- Coleta refeita com o recorte ampliado: 111.164.
- A correção das autorias truncadas foi feita entre as duas.

## Pendências

- Palavras-chave (`keywords`) e resumos não foram coletados. Serão necessários para a busca por tema (proposta de busca vetorial).
