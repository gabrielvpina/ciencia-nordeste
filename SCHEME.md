# SCHEME.md — Ciência Nordeste

> Repositório aberto da pesquisa em ciências da vida do Nordeste: saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas
> Status (2026-11-09): dados prontos (Partes 0–2 e 4–7; a 3 aguarda resposta da LAI). Fases B e C (núcleo) concluídas: banco e app rodando localmente. Fase D adiada até a produção; Fase E pendente.
> Alvo de produção: VPS próprio (Linux + Docker)
> Versão anterior (plataforma nacional "Rede Ciência BR"): substituída em 2026-11-09, ver `docs/decisoes.md` (D-009)
> Recorte ampliado para ciências agrárias, biológicas e veterinária em 2026-11-09 (D-017)
> Nome: "Integra Nordeste" passou a "Ciência Nordeste" em 2026-11-09 (D-021)

---

## 0. Estado atual (resumo)

| Frente | Situação |
|---|---|
| Dados | 753 instituições, 313 programas, 5.583 docentes, 144.891 pesquisadores, 110.783 publicações (2022–2026; 91.769 em revistas com Qualis), 15.047 teses e dissertações, 35.724 perfis temáticos, 43 fotos com licença livre |
| Identidade | 2.653 docentes ligados a perfis OpenAlex por regra aprovada (D-018); 5.336 pares de pesquisadores e 53 de instituições aguardam revisão manual |
| Banco | PostgreSQL 16 + pgvector no Docker; 7 migrações (`ingest/sql/migracoes/`); carga idempotente (`scripts/carregar_banco.sh`); 111 mil vetores com índice HNSW |
| App | Next.js 14.2.35 no Docker (http://localhost:3000): tela inicial com busca unificada (nome e **tema**, semântica PT/EN) e acesso ao painel e ao quiz; painel (`/painel`) com mapa próprio do NE (modos produção, colaboração, áreas); perfis de pesquisador, instituição e programa com rede de colaboração em arco |
| Quiz (branch `quiz`, etapa 13) | "Que cientista é você?": cadastro curto (D-037), 10 perguntas por facetas, match com até 5 pesquisadores de outras instituições e índice de compatibilidade (D-036), banners em PNG gerados no servidor |
| Qualidade | `scripts/verificar.sh` (ruff, mypy, typecheck, build, migrações num banco vazio) e CI do GitHub Actions pronta |
| Pendências do responsável | revisar as filas; enviar o pedido LAI (`docs/pedido_lai_cnpq.md`); domínio e VPS para a produção; depois, cliente ORCID de produção |

Como atualizar tudo: Parte 1 → 2 → 5 → 4 → revisão (`consolidar`) → 6 → 7 → `./scripts/carregar_banco.sh` (detalhes em `ingest/README.md`).

## 1. Visão em uma frase

Um repositório público que reúne, a partir de **dados abertos**, as instituições, programas de pós-graduação, grupos de pesquisa, pesquisadores, docentes e a produção científica dos **últimos 5 anos** em **ciências da vida** (saúde, biomedicina, biotecnologia, genética, microbiologia, ciências agrárias e biológicas, veterinária e ciência de alimentos) nos **9 estados do Nordeste**, para que gestores, pesquisadores e financiadores encontrem quem faz o quê, onde, e com quem colaborar.

## 2. Problema

- A produção em ciências da vida do Nordeste está espalhada em Lattes, Sucupira, OpenAlex, repositórios institucionais e SciELO, sem uma visão regional integrada.
- Saúde humana, saúde animal, agricultura e ambiente se cruzam (arboviroses e vetores, zoonoses, segurança alimentar, bioprodutos do semiárido), mas os pesquisadores dessas áreas raramente se encontram.
- Perguntas simples não têm resposta rápida: "quem estuda arboviroses no Nordeste e com quem publica?", "quais programas de pós em genética existem no Piauí?", "que grupos de Pernambuco e da Bahia trabalham com doenças negligenciadas?", "quem faz biotecnologia de plantas da caatinga e com quem publica?", "quem pode ser banca externa nesse tema?".
- Pesquisadores e programas da região ficam pouco visíveis entre si e para parceiros de fora; colaborações entre estados do Nordeste são subaproveitadas.

## 3. Princípios do projeto

1. **Só dados abertos e licenciados para reuso**, com a licença de cada fonte registrada. Sem scraping da Plataforma Lattes, do DGP/CNPq ou do Google Acadêmico; sem contornar captcha, bloqueio ou limite de nenhum site; robots.txt respeitado (exceções só para APIs oficiais documentadas, D-003).
2. **Recorte claro e versionado.** Região, período e áreas ficam num único arquivo (`ingest/diagnostico/recorte.py`), usado por todas as etapas.
3. **Base pré-populada + perfil reivindicável.** No primeiro dia já existem perfis; o pesquisador entra (via ORCID) para corrigir e completar, não para começar do zero.
4. **Identidade com cautela.** Cada pesquisador tem um ID interno estável; cruzamentos sem identificador comum nunca mesclam perfis automaticamente (vão para fila de revisão).
5. **LGPD desde o início.** Transparência sobre a origem de cada dado, mínimo de dados pessoais (nada de CPF, data de nascimento ou contato sem autorização), opção de ocultar/remover perfil.
6. **Simples de operar em um único VPS.** Docker Compose, um banco só, backups automáticos.

## 4. Recorte

| Dimensão | Definição |
|---|---|
| Região | MA, PI, CE, RN, PB, PE, AL, SE, BA (instituição com sede no estado) |
| Período | Ano atual e os 4 anteriores (2022–2026 em 2026); `YEAR_START` sobrescreve |
| Áreas — produção (OpenAlex) | `primary_topic.field`: Medicine (27), Biochemistry, Genetics and Molecular Biology (13, inclui Biotechnology), Immunology and Microbiology (24), Neuroscience (28), Pharmacology, Toxicology and Pharmaceutics (30), Nursing (29), Dentistry (35), Health Professions (36), **Agricultural and Biological Sciences (11**: plantas, ecologia, alimentos, ciência animal, solos, insetos, aquática, agronomia), **Veterinary (34)**. Medido à parte: Biomedical Engineering (subfield 2204) |
| Áreas — pós-graduação (CAPES) | Áreas de avaliação: Medicina I, II e III, Enfermagem, Odontologia, Farmácia, Saúde Coletiva, Nutrição, Educação Física, Ciências Biológicas I, II e III, Biotecnologia, **Biodiversidade, Ciências Agrárias I, Ciência de Alimentos, Zootecnia / Recursos Pesqueiros, Medicina Veterinária** |
| Áreas — ensino (INEP) | Cursos CINE 09 (Saúde e bem-estar), 08 (Agricultura, silvicultura, pesca e veterinária) e 051 (Ciências biológicas) |
| Instituições | Universidades, institutos federais, faculdades, Fiocruz, Embrapa e outros institutos de pesquisa, hospitais de ensino, Lacens, órgãos de defesa agropecuária e empresas com produção científica, desde que com sede no NE |

Tamanho do recorte (cargas de 2026-11-09, recorte ampliado D-017):

| Item | Quantidade |
|---|---|
| Instituições do NE (ROR + INEP) | 753, após a retirada da FUNED (D-038) (225 com produção no OpenAlex, entre elas as unidades da Embrapa no NE e a EMPARN) |
| Programas de pós CAPES (2022–2024) | 313 distintos (284 em 2024: 155 de saúde e ciências biológicas, 114 de agrárias, alimentos, veterinária e biodiversidade, 15 de biotecnologia) |
| Docentes de pós (ID_PESSOA) | 5.583 |
| Works 2022–2026 | **110.783**, 91.769 em revistas com Qualis (Medicina 56,1 mil; Agrárias e Biológicas 26,1 mil; demais saúde e biomédicas 27,5 mil; Veterinária 1,1 mil) |
| Pesquisadores (autores com vínculo no NE) | 144.891 (57% com ORCID; 35.724 com 3+ works no período, que têm perfil temático para o quiz) |
| Coautorias entre pesquisadores do NE | 722,7 mil pares |
| Teses e dissertações (CAPES, 2022–2024) | 15.047, com orientador ligado ao perfil em 99,9% |
| Publicações com financiamento declarado de FAP do NE | 6.837 (FACEPE, FAPESB e FUNCAP à frente) |

## 5. Escopo do MVP

### Dentro
- Repositório navegável de **instituições, programas, pesquisadores e produção** do recorte, com filtros por estado, município, instituição, área e tema.
- Página de **pesquisador**: vínculo, programas (CAPES), tópicos, publicações do período, coautores, orientações (teses CAPES).
- Página de **instituição** e de **programa de pós** (conceito CAPES, área, docentes, produção).
- **Mapa próprio** do Nordeste (SVG, sem serviços externos) no painel (`/painel`, D-039), com modos produção, colaboração e áreas, e filtros por área, estado e período.
- **Rede de colaboração** em arco nos perfis: parceiros no NE e coautoria externa (Brasil fora do NE e países).
- Busca unificada em português, sem precisar de acento: pesquisador, instituição e programa.
- Login com **ORCID** para reivindicar o perfil; edição de informações complementares e foto. **Só na produção** (D-024).
- Página de privacidade e pedido de remoção/ocultação.

### Fora (por enquanto)
- Grupos de pesquisa completos (dependem de pedido LAI ao CNPq; piloto com portais das universidades).
- Infraestrutura e equipamentos (PNIPE sem dados abertos).
- Busca semântica por embeddings (fase 2).
- Mural de chamadas de colaboração (fase 2).
- Outras regiões e outras áreas.

## 6. Fontes de dados

| Fonte | Uso | Licença | Acesso |
|---|---|---|---|
| OpenAlex | instituições, autores, produção, tópicos, financiadores | CC0 | API com chave (recorte pequeno; snapshot não compensa) |
| ROR | lista canônica de organizações do NE, coordenadas, IDs externos | CC0 | dump no Zenodo |
| INEP — Censo da Educação Superior | cadastro de IES (código e-MEC, natureza, município IBGE), cursos | pública (LAI) | ZIP anual |
| IBGE | municípios e coordenadas das sedes | pública | API de Localidades + CSV derivado (MIT) |
| Wikidata | cruzamento ROR ↔ e-MEC (P6782 × P5148), fotos com licença livre | CC0 / por arquivo | SPARQL |
| CAPES Dados Abertos | programas, docentes, teses e orientações, produção declarada | CC-BY | CSV por ano |
| ORCID | identidade e reivindicação, afiliações | CC0 (arquivo) / termos da API | API pública, sob demanda |
| SciELO | metadados em português (cruzamento por DOI) | aberta | ArticleMeta |
| BDTD/Oasisbr (IBICT) | teses e repositórios do NE | metadados públicos | OAI-PMH / contato com o IBICT |
| CNPq (DGP, bolsistas PQ) | grupos de pesquisa | LAI | pedido via Fala.BR |

Detalhes, contagens e riscos: `ingest/relatorios/diagnostico_fontes.md`.

## 7. Stack proposta

| Camada | Escolha | Motivo |
|---|---|---|
| Web + API | **Next.js 14.2.35 (App Router) + TypeScript**, rodando só no Docker | Páginas públicas com bom SEO e API no mesmo projeto |
| Schema | **SQL puro + migrações numeradas** (`scripts/migrar.sh`) | O schema nasceu em SQL e o app só lê; ORM pode entrar na Fase D (D-022) |
| Banco | **PostgreSQL 16 + pgvector** (`pg_trgm`, `unaccent` com invólucro `f_unaccent`, `halfvec` + HNSW); visões materializadas para mapa e busca | Busca em português e busca semântica sem serviço de banco extra |
| Busca por tema | `multilingual-e5-base` (lote na GPU do Mac; consultas no serviço `servicos/embed`, CPU, rede interna) | Consulta em português alcança publicações em inglês (D-028) |
| Ingestão | **Python 3.12** (`ingest/`) | httpx, scripts idempotentes, saída em CSV para carga no Postgres |
| Autenticação | **Auth.js** com ORCID (previsto; desligado até a produção por `LOGIN_HABILITADO`) | ORCID comprova identidade |
| Mapa | Componente SVG próprio (`apps/web/components/mapa/`) com malha do IBGE embutida | Sem dependências nem APIs externas (D-025) |
| Proxy / HTTPS | **Caddy** | TLS automático |
| Orquestração | **Docker Compose** | Igual no computador e no VPS |

## 8. Modelo de dados

```
municipalities
  ibge_code (pk), name, uf, latitude, longitude, is_capital

institutions
  id (uuid estável), name, acronym, kind (universidade, instituto_federal, faculdade, centro_universitario,
  instituto_pesquisa, hospital, governo, empresa, outro), ror_types[], legal_nature (publica, privada, especial),
  admin_category, academic_org, uf, municipality_ibge -> municipalities, latitude, longitude, geo_source,
  is_active, works_count_openalex, sources[], updated_at

institution_identifiers
  institution_id, scheme (ror, openalex, emec, capes_entidade, wikidata, isni, grid, fundref),
  value, source, confidence, verified_at

institution_relations
  institution_id, related_institution_id, relation (parent, child, related, predecessor, successor), source

graduate_programs
  id (uuid), capes_code, name, degree (mestrado, doutorado, ...), modality, evaluation_area, knowledge_area,
  grade (conceito), institution_id, uf, municipality_name, status, base_years[]

researchers
  id (uuid estável, nunca muda), display_name, normalized_name, main_institution_id, orcid, is_capes_faculty,
  pq_category_latest, sources[], is_claimed, is_hidden, created_at, updated_at

researcher_aliases            (UUID que passou a apontar para outro perfil após aceite na revisão; nunca se apaga um UUID)
  alias_id, researcher_id, reason, created_at

researcher_openalex_stats     (métricas: ufs[], works_count_period, first/last_year, cited_by_count, h_index, top_topics[])

researcher_photos             (Commons com licença livre ou upload próprio)
  researcher_id, source, file_name, license, license_url, author, source_page_url, width, height

researcher_identifiers
  researcher_id, scheme (orcid, openalex, capes_id_pessoa, lattes*, scholar_url*, wikidata), value,
  source, confidence, verified_at          (* só quando informado pelo próprio pesquisador)

program_faculty
  program_id, researcher_id (ou capes_id_pessoa antes da resolução), base_year, category (permanente,
  colaborador, visitante), bond_type, pq_category

identity_review_queue
  id, entity (researcher, institution), candidate_a, candidate_b, evidence (json), score, status, decided_by, decided_at

works            (só o necessário; não espelhar o OpenAlex)
  id (uuid), openalex_id, doi, title, year, type, venue, language, is_oa, primary_field, primary_subfield,
  primary_topic, cited_by_count

work_authorships              (todas as autorias; coautores de fora do NE ficam sem researcher_id)
  work_id, author_order, researcher_id, openalex_author_id, author_name, is_corresponding, institution_ids[], is_ne, countries[]

topics
  id, openalex_id, name, subfield, field, domain

coauthorships    (aresta agregada)
  researcher_a_id, researcher_b_id, shared_works_count, last_year

theses           (CAPES: catálogo de teses e dissertações)
  id, capes_production_id, title, degree, year, defense_date, program_id, institution_id, author_name,
  advisor_name, advisor_researcher_id, keywords, abstract, full_text_url

funders / work_funders / funders_ne     (OpenAlex; funders_ne marca as 9 FAPs do NE)

institution_collaborations, researcher_topics, schema_migrations

work_keywords (1,08 mi) e work_embeddings (halfvec(768), índice HNSW) — busca por tema (D-028)

visões materializadas (atualizadas a cada carga): mv_resumo, mv_pesquisador_busca, mv_instituicao_stats,
  mv_instituicao_areas, mv_work_inst, mv_mapa_producao, mv_mapa_colaboracao, mv_inst_externo, mv_uf_ano_area,
  mv_work_qualis (com works_qualis nas contagens, D-033 e D-035)

qualis_periodicos, venue_issns                (Qualis Periódicos 2021-2024 e ISSNs das revistas, D-033)

researcher_embeddings   (perfil temático: média ponderada dos vetores das publicações, halfvec(768), HNSW; D-036)
quiz_sinal, quiz_opcao_work, quiz_meta        (sinais das opções do quiz pré-calculados por publicação; D-036)
quiz_participantes      (cadastro do quiz: nome, instituição, filiação, curso/programa, consentimento — sem e-mail;
                         gravado pelo papel quiz_escrita, só INSERT; o app não lê; retenção de 24 meses; D-037)

users, profile_claims, profile_extras, removal_requests   (camada da aplicação)
```

Índices: GIN `pg_trgm` em nomes normalizados (pesquisadores, instituições, tópicos); índices por `uf`, `municipality_ibge`, `primary_field`, `year`.

Regras de identidade:
- ORCID é o identificador de referência e a base da reivindicação.
- Cruzamento por identificador comum (ORCID, OpenAlex, ID_PESSOA da CAPES, ROR, e-MEC) entra com `confidence = 1`.
- Cruzamento sem identificador comum (nome + instituição/município) entra com `confidence < 1` e vai para `identity_review_queue`; só é aceito por decisão humana ou por regra explicitamente aprovada pelo responsável (D-018: candidato único + nome idêntico + instituição em comum). Aceitar cria um alias reversível; nada é apagado.
- IDs internos (UUID) são atribuídos uma única vez e guardados num registro persistente (`ingest/dados/ids/`, depois no banco).

## 9. Ingestão de dados (pasta `ingest/`)

| Parte | Conteúdo | Status |
|---|---|---|
| 0 | Diagnóstico de disponibilidade, tamanho e licença das fontes | concluída |
| 1 | Instituições do NE: ROR + OpenAlex + INEP + IBGE + Wikidata, com geolocalização e identificadores | concluída (754 instituições) |
| 2 | Programas de pós e docentes (CAPES) do recorte, ligados às instituições | concluída (313 programas, 5.583 docentes, recorte ampliado) |
| 3 | Grupos de pesquisa: pedido LAI ao CNPq + piloto com portais das universidades | pedido redigido |
| 4 | Pesquisadores: autores OpenAlex + docentes CAPES + ORCID, resolução de identidade | concluída; refeita com o recorte ampliado (D-017) |
| 5 | Produção do recorte (OpenAlex por lista de instituições do NE × fields do recorte), coautorias e tópicos | concluída; refeita com o recorte ampliado (D-017) |
| 6 | Complementos: teses e orientações (CAPES), financiamento (FAPs do NE), BDTD/Oasisbr | concluída (BDTD/Oasisbr só sondado; coleta via OAI-PMH pendente) |
| 7 | Fotos: upload próprio + Wikidata/Commons com licença livre; WebP, lado máx. 400 px, sem EXIF | concluída para o Commons (43 fotos); upload próprio na Fase D |
| — | Revisão de identidade: decisões, regra em lote, planilhas de pendentes e consolidação (`ingest/carga/revisao.py`) | em uso (2.653 aceites) |
| — | Geometria do mapa (`ingest/carga/gerar_mapa_ne.py`, malha do IBGE) | gerada e versionada |
| 8 | Busca por tema: palavras-chave + embeddings multilíngues (`ingest/carga/parte8_embeddings.py`) | concluída (110.762 vetores) |

Cuidados:
- O filtro do OpenAlex por estado (`geo.region`) perde instituições sem estado preenchido (ex.: UFPB). A partir da Parte 1, o recorte regional do OpenAlex usa a **lista de IDs de instituições do NE** gerada na Parte 1.
- Scripts idempotentes: rodar de novo não duplica nada; downloads são reaproveitados se não mudaram.
- Cache, retry com backoff, timeout e limite de taxa em todo acesso HTTP; User-Agent identificado com `CONTACT_EMAIL`.

## 10. Estrutura de pastas

```
/
├── SCHEME.md
├── docker-compose.yml / docker-compose.prod.yml
├── .env.example                  (o .env real nunca vai para o git)
├── .github/workflows/ci.yml
├── apps/web/                     Next.js: app/ (páginas e rotas /api), components/ (mapa/, Inicio, RedeEntidade, Avatar), lib/
│   └── components/mapa/          mapa próprio: geometria-ne.json, projecao.ts, MapaNordeste.tsx, mapa.css
├── ingest/
│   ├── diagnostico/              Parte 0 + módulos comuns (http, config, recorte, openalex)
│   ├── carga/                    Partes 1–7, revisão de identidade e geração do mapa
│   ├── sql/                      migracoes/NNNN_*.sql e carga.sql
│   ├── dados/                    brutos/, processados/, fotos/, ids/, revisao/   (fora do git; ids/ e decisoes.csv precisam de backup, D-026)
│   ├── relatorios/               saídas de cada execução (fora do git, D-026)
│   └── README.md
├── scripts/                      migrar.sh, carregar_banco.sh, verificar.sh, backup.sh, restaurar.sh
└── docs/
    ├── decisoes.md               D-001 a D-025
    └── pedido_lai_cnpq.md
```

## 11. Fases

### Fase A — Dados (concluída, salvo revisões e LAI)
- [x] Parte 0 — diagnóstico das fontes (nacional e recorte NE).
- [x] Parte 1 — instituições do NE.
- [x] Parte 2 — programas e docentes CAPES.
- [x] Pedido LAI ao CNPq redigido (`docs/pedido_lai_cnpq.md`).
- [ ] Pedido LAI enviado pelo Fala.BR (ação do responsável).
- [x] Chave do OpenAlex e `CONTACT_EMAIL` configurados.
- [x] Partes 4 e 5 — pesquisadores e produção.
- [x] Aceite em lote dos pares sem ambiguidade (D-018: 2.653 docentes ligados).
- [ ] Revisar manualmente os pares restantes (`ingest/dados/revisao/pendentes_*.csv`: 5.336 de pesquisadores, 53 de instituições).
- [ ] Coletar BDTD/Oasisbr via OAI-PMH (o bloqueio do IBICT expirou; ritmo conservador, D-011).
- [x] Parte 6 — complementos (teses e orientações, FAPs do NE).
- [x] Parte 7 — fotos (Wikidata/Commons com licença livre, WebP sem EXIF; avatar com iniciais como padrão).

### Fase B — Fundação da aplicação (concluída)
- [x] Docker Compose com Postgres 16 (pg_trgm, unaccent) e Next.js.
- [x] Schema a partir de `ingest/sql/` e carga dos CSVs processados (`scripts/carregar_banco.sh`).
- [x] Migrações versionadas: SQL numerado em `ingest/sql/migracoes/` + `scripts/migrar.sh` (D-022).
- [x] CI: `.github/workflows/ci.yml` (Python, app, migrações num banco vazio) e `scripts/verificar.sh` local. Roda no GitHub quando houver remoto.
- [x] Backup e restauração locais (`scripts/backup.sh`, `scripts/restaurar.sh`) e nome fixo do projeto no Docker (D-027).

### Fase C — Repositório público (núcleo concluído)
- [x] Busca com filtros (estado, área, docente) e paginação; busca unificada na barra lateral.
- [x] Páginas de pesquisador, instituição e programa; listas de instituições e programas.
- [x] Mapa próprio do Nordeste em SVG (sem APIs externas) com modos produção, colaboração, áreas e rede; filtros por área, estado e período (D-025).
- [x] Tela inicial = busca unificada (pesquisador, instituição, programa) + mapa; perfis com rede em arco (colaborações no NE e externas).
- [x] SEO básico (metadados por página, sitemap em blocos, robots) e página "Sobre os dados".
- [x] Busca por tema (vetorial multilíngue, híbrida, balanceada por idioma; precisão de 100% nas 20 consultas de teste) (D-028).
- [x] Perfil temático por pesquisador (`researcher_embeddings`), base do quiz e de "pesquisadores parecidos" (D-036).
- [ ] Quiz "Que cientista é você?" (branch `quiz`, etapa 13): estrutura, match e banners prontos; cadastro, interface e nova tela inicial (D-039) prontos.
- [ ] Filtro por município; página de resultados completa por tema; "pesquisadores parecidos" no perfil.
- [ ] Rede de coautoria pessoa × pessoa como grafo (hoje: arcos entre instituições e lista de coautores).

### Fase D — Contas e reivindicação (adiada até a produção, D-024)
- [ ] Login com ORCID; reivindicação automática quando o ORCID bate. **Adiado até a produção** (D-024; chave `LOGIN_HABILITADO`).
- [ ] Edição de informações complementares e foto.
- [ ] Ocultar perfil e pedido de remoção; fila de revisão de identidade (painel interno, substituindo as planilhas).

### Fase E — Produção no VPS
- [ ] Deploy conforme a seção 12; teste com pesquisadores e programas parceiros do NE.
- [ ] Antes do lançamento público: avaliar a migração do Next.js para a linha 15/16 e revisar se o mapeamento ID CAPES ↔ UUID pode ser público (D-020, D-023).

## 12. Produção no VPS

**Servidor mínimo:** 2 vCPU, 4 GB de RAM, 40–80 GB SSD, Ubuntu 24.04 LTS (o banco do recorte deve ficar abaixo de 2 GB).

Checklist:
- [ ] Usuário não-root com chave SSH; login por senha e root desativados.
- [ ] Firewall (`ufw`): só 22, 80 e 443; `fail2ban` para SSH.
- [ ] Docker + Docker Compose; Caddy emite o HTTPS.
- [ ] Postgres **sem** porta exposta para fora da rede do Docker.
- [ ] Segredos em `.env` no servidor, nunca no repositório.
- [ ] Backup diário com `pg_dump`, cópia externa (S3 compatível), retenção de 14 dias e teste de restauração mensal. Incluir o registro de IDs estáveis. (Local já pronto: `scripts/backup.sh` e `scripts/restaurar.sh`, testados; falta o agendamento e a cópia externa, D-027.)
- [ ] Atualizações de segurança automáticas; monitoramento de uptime; rotação de logs.
- [ ] Ingestão agendada: mensal (OpenAlex incremental), anual (CAPES, INEP, ROR quando houver nova versão).

## 13. LGPD e ética

- Usar apenas dados que já são públicos e relativos à atividade científica (produção, vínculo institucional, pós-graduação).
- Não armazenar nem exibir CPF (mesmo mascarado), ano de nascimento ou dados de contato vindos das fontes; contato só se o pesquisador informar.
- Em cada perfil: "Dados obtidos de fontes abertas (OpenAlex, CAPES, ORCID...). Este é você? Reivindique, corrija ou solicite remoção."
- Fotos: só upload próprio ou imagem com licença livre (com crédito); padrão é avatar com iniciais.
- Política de privacidade, responsável pelos dados e prazo para atender pedidos; base legal avaliada com orientação jurídica antes do lançamento.
- **Cadastro do quiz (D-037), primeira coleta de dados pessoais informados pelo próprio usuário:**
  - **base legal:** consentimento explícito (caixa não marcada por padrão, com a finalidade escrita);
  - **mínimo necessário:** nome, instituição, filiação e curso ou programa; sem e-mail ou outro contato; não se grava IP, respostas nem resultado;
  - **acesso:** gravação por um papel só de `INSERT`, e o app nunca lê os dados;
  - **retenção:** 24 meses, com expurgo automático;
  - **pedidos de acesso ou remoção:** pelo contato em `/sobre#privacidade-quiz`;
  - **backups:** contêm esses dados e são legíveis só pelo dono.

## 14. Métricas para validar

- Cobertura: % dos docentes CAPES do recorte com perfil ligado a um autor OpenAlex; % de perfis com ORCID.
- Qualidade: tamanho e tempo de resolução da fila de revisão; pedidos de correção.
- Uso: buscas por dia, cliques em perfis, perfis reivindicados, retorno em 30 dias.
- Impacto: colaborações entre estados do NE identificadas e contatos iniciados pela plataforma.

## 15. Riscos

| Risco | Mitigação |
|---|---|
| OpenAlex sem estado em parte das instituições (ex.: UFPB) | Recorte por lista de IDs de instituições do NE (Parte 1) |
| Cobertura menor de periódicos nacionais e da produção em português | SciELO, CAPES (produção declarada) e BDTD como complemento |
| Perfis duplicados ou mesclados errado | IDs estáveis, ORCID, fila de revisão, nada de mescla automática sem identificador |
| Grupos de pesquisa sem dados abertos | Pedido LAI; pilotos com universidades |
| Bloqueios de servidores (ex.: firewall do IBICT) | Limites de taxa conservadores; contato formal; nunca contornar |
| Dados pessoais | Minimização, transparência, remoção a pedido |
| Servidor único | Backups testados e restauração documentada |

## 16. Próximas ideias (pós-MVP)

- Busca semântica por tema ("quem estuda resistência antimicrobiana no semiárido?").
- Indicadores por estado e programa (painel para pró-reitorias e FAPs do NE).
- Integração com dados de saúde pública (DATASUS) e agropecuários (IBGE/PAM, Embrapa) para cruzar temas de pesquisa com necessidades regionais.
- Recorte temático "Uma só saúde" (saúde humana × animal × ambiental) como vitrine da integração entre áreas.
- Expansão para outras áreas ou regiões, mantendo o mesmo molde.
