# Etapa 8 — Revisão de identidade e consolidação

**Status:** em uso (aceite em lote aplicado; revisão manual pendente) · **Comando:** `python -m ingest.carga.revisao {aplicar-regra|exportar|importar|consolidar}`
**Código:** `ingest/carga/revisao.py` · **Relatório:** `ingest/relatorios/revisao_consolidacao.json`
**Decisões:** D-013 (IDs estáveis), D-018 (aceite em lote), D-026 (fora do git, com backup próprio)

## Princípios

- Cada pesquisador e cada instituição tem um **UUID estável**, atribuído uma única vez num registro persistente, só de acréscimo (`ingest/dados/ids/`).
- Cruzamento por identificador comum (ORCID, OpenAlex, ID CAPES, ROR, e-MEC) tem confiança 1.
- Cruzamento sem identificador comum (nome + instituição) **nunca mescla sozinho**. Ele vai para a fila e só é aceito por decisão humana ou por regra aprovada explicitamente pelo responsável.

## Mecânica

| Comando | O que faz |
|---|---|
| `aplicar-regra --decidido-por "Nome"` | Aplica a regra D-018: docente com **um único** candidato, nome idêntico e instituição em comum, sem que o autor seja candidato único de outro docente |
| `exportar` | Gera `ingest/dados/revisao/pendentes_pesquisadores.csv` e `pendentes_instituicoes.csv`, com a coluna `decisao` em branco |
| `importar ARQUIVO --decidido-por "Nome"` | Lê as linhas marcadas `aceito` ou `rejeitado` e grava em `decisoes.csv` |
| `consolidar` | Gera os arquivos unificados que o banco carrega: `researchers.csv`, `researcher_identifiers.csv`, `researcher_aliases.csv`, `program_faculty_final.csv` e `review_queue.csv` |

- As decisões ficam em `ingest/dados/revisao/decisoes.csv`: só acréscimo, com quem decidiu, quando e por qual regra. **Fica fora do git (D-026) e não é regenerável: precisa de backup.**
- **Aceitar cria um alias**: o UUID do docente CAPES passa a apontar para o UUID do autor OpenAlex. Nenhum UUID é apagado, e o app redireciona o endereço antigo para o novo perfil.
- **Rejeitar depois desfaz o alias** na próxima consolidação.
- O `capes_id_pessoa` de um docente ligado assim entra com confiança 0,95 (regra) ou 0,99 (revisão humana), nunca 1.

## Resultado (2026-11-09)

| Item | Valor |
|---|---|
| Aceitos pela regra D-018 | **2.653** docentes ligados ao perfil OpenAlex |
| Fora da regra | 2.068 docentes com mais de um candidato, 111 sem nome idêntico, 9 autores disputados por dois docentes |
| Pesquisadores após consolidar | 144.891 (139.308 só OpenAlex, 2.930 só CAPES, 2.653 nas duas bases) |
| **Pendentes de revisão manual** | **5.336 pares de pesquisadores** e **53 de instituições** |

Numa amostra, os pares de nota 0,95 eram praticamente sempre a mesma pessoa (diferença só de acento). Os de nota 0,8 (ex.: "R Lima") são fracos.

## Próximos passos

1. **Responsável:** revisar as planilhas de pendentes (preencher `decisao`), importar e consolidar.
2. Fase D: substituir as planilhas por um painel interno de revisão.
