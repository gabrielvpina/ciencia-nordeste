# Etapa 2 — Programas de pós-graduação e docentes (CAPES)

**Status:** concluída · **Comando:** `python -m ingest.carga.parte2_capes` (depende da etapa 1)
**Código:** `ingest/carga/parte2_capes.py` · **Relatório:** `ingest/relatorios/parte2_capes.md`
**Decisões:** D-014 (dados pessoais minimizados), D-017 (áreas ampliadas)

## Objetivo

Trazer os programas de pós-graduação stricto sensu do recorte e os docentes ligados a eles, ligar cada programa à sua instituição e dar a cada docente um **ID interno estável de pesquisador**.

## Fonte e recorte

- **CAPES Dados Abertos** (CC-BY): conjuntos "Programas" e "Docentes" de 2021 a 2024, anos-base **2022–2024** (2025 ainda não publicado). Os CSVs são baixados respeitando o `Crawl-delay: 10` do portal.
- **Filtro**: `SG_UF_PROGRAMA` num estado do NE **e** área de avaliação do recorte. São elas: Medicina I, II e III, Enfermagem, Odontologia, Farmácia, Saúde Coletiva, Nutrição, Educação Física, Ciências Biológicas I, II e III, Biotecnologia, Biodiversidade, Ciências Agrárias I, Ciência de Alimentos, Zootecnia/Recursos Pesqueiros e Medicina Veterinária.

## Ligação programa → instituição

1. Código e-MEC da CAPES (`CD_ENTIDADE_EMEC`) contra o e-MEC da etapa 1 (identificador comum).
2. Sem e-MEC: nome exato na mesma UF.
3. Senão, fila de revisão. A instituição ligada ganha o identificador `capes_entidade`.

## Resultado

| Item | Valor |
|---|---|
| **Programas distintos** (2022–2024) | **313** (284 em 2024) |
| Ligados a instituição | 303 por e-MEC + 4 por nome exato; **6 sem vínculo** |
| Por UF (2024) | BA 61 · PE 56 · CE 51 · PB 32 · RN 26 · MA 16 · PI 16 · SE 14 · AL 12 |
| Por conceito (2024) | 3: 76 · 4: 105 · 5: 73 · 6: 20 · 7: 5 · A (novos): 4 · 2: 1 |
| **Docentes distintos** (ID_PESSOA) | **5.583** (5.143 em 2024) |
| Com bolsa de produtividade CNPq (2024) | 1.022 |
| Em mais de um programa | 1.503 |
| Vínculos docente × programa × ano | 20.120 (de 332.773 linhas lidas no Brasil) |

Programas sem instituição ligada: as unidades da **Fiocruz** na Bahia (Gonçalo Moniz) e em Pernambuco (Aggeu Magalhães), que a CAPES registra com o e-MEC da Fiocruz nacional (RJ), e o **campus de Bananeiras da UFPB**, sem e-MEC informado.

## LGPD

Não gravamos `NR_DOCUMENTO_DOCENTE` (CPF mascarado), `TP_DOCUMENTO_DOCENTE`, `AN_NASCIMENTO_DOCENTE` nem `DS_FAIXA_ETARIA`.

## Saídas

`graduate_programs.csv`, `program_faculty.csv`, `researchers_capes.csv`, `researcher_identifiers_capes.csv`, `institution_identifiers_capes.csv`, `institution_review_queue_capes.csv`. UUIDs em `ingest/dados/ids/graduate_program.csv` e `ingest/dados/ids/researcher.csv`.

## Histórico

A primeira versão (só saúde e biológicas) tinha 190 programas e 3.724 docentes. A ampliação do recorte (D-017) acrescentou agrárias, alimentos, veterinária e biodiversidade, sem mudar os UUIDs que já existiam.
