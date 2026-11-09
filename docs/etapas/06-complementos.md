# Etapa 6 — Complementos: teses e orientações, FAPs do Nordeste, BDTD/Oasisbr

**Status:** concluída (BDTD/Oasisbr só sondados) · **Comando:** `python -m ingest.carga.parte6_complementos`
**Código:** `ingest/carga/parte6_complementos.py` · **Relatório:** `ingest/relatorios/parte6_complementos.md`
**Decisões:** D-011 (IBICT)

## Teses e dissertações (CAPES)

- **Fonte**: Catálogo de Teses e Dissertações da CAPES (CC-BY), anos-base 2022–2024. São cerca de 1,5 GB de CSV, lidos em *streaming*.
- **Filtro**: só trabalhos dos programas do recorte (etapa 2).
- **Orientador → pesquisador**: o `ID_PESSOA_ORIENTADOR` é mapeado pelo registro de IDs (`capes_id_pessoa`) e depois pelos aliases da revisão, chegando ao UUID canônico do perfil.

| Item | Valor |
|---|---|
| **Teses e dissertações do recorte** | **15.048** (de 267.381 no Brasil) |
| Orientador ligado a um perfil | 15.038 (99,9%); 4.238 orientadores distintos |
| Por grau | dissertações 10.214 · teses 4.600 · produtos técnicos de mestrado profissional (software, patente, protocolo etc.) ≈ 230 |

O resumo é guardado com no máximo 4.000 caracteres. O nome do autor (discente) é público no catálogo e é exibido.

## FAPs do Nordeste

As 9 fundações estaduais foram identificadas entre os financiadores declarados nas publicações (OpenAlex):

| FAP | UF | Publicações do recorte |
|---|---|---|
| FACEPE | PE | 1.960 |
| FAPESB | BA | 1.414 |
| FUNCAP | CE | 1.263 |
| FAPEMA | MA | 943 |
| FAPESQ | PB | 592 |
| FAPEAL | AL | 284 |
| FAPITEC | SE | 231 |
| FAPEPI | PI | 226 |
| FAPERN | RN | 54 |

No total, 6.837 publicações declaram alguma FAP do NE. O financiamento vem dos agradecimentos registrados no Crossref e no OpenAlex, então é **subnotificado**; a FAPERN, provavelmente, aparece pouco por isso.

## BDTD / Oasisbr (IBICT)

Uma sondagem única, **sem retry**, confirmou que o bloqueio do firewall de 9/11 expirou (as duas APIs responderam 200). A coleta não foi feita: fica para uma próxima etapa, via OAI-PMH, com ritmo conservador (D-011).

## Saídas

`theses.csv`, `funders_ne.csv`. UUIDs em `ingest/dados/ids/thesis.csv`.
