-- Carga dos CSVs processados num Postgres com as migrações de ingest/sql/migracoes/ aplicadas (scripts/migrar.sh).
-- Rodar de um diretório onde 'ingest/' exista (no container do banco: /repo):
--     psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f ingest/sql/carga.sql
-- Antes: python -m ingest.carga.revisao consolidar  (gera researchers.csv, researcher_identifiers.csv, aliases, fila).
-- Idempotente: upsert em tudo; decisões já tomadas na fila não são sobrescritas por "pendente".

\set ON_ERROR_STOP on
BEGIN;

-- ------------------------------------------------------------------ municípios e instituições
CREATE TEMP TABLE _m (LIKE municipalities) ON COMMIT DROP;
\copy _m FROM 'ingest/dados/processados/municipalities.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO municipalities SELECT * FROM _m
ON CONFLICT (ibge_code) DO UPDATE SET name = EXCLUDED.name, uf = EXCLUDED.uf, latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude, is_capital = EXCLUDED.is_capital;

CREATE TEMP TABLE _i (
    id uuid, name text, name_ror text, acronym text, kind text, ror_types text, legal_nature text, admin_category text,
    academic_org text, uf char(2), municipality_ibge integer, municipality_source text, latitude double precision,
    longitude double precision, geo_source text, is_active boolean, established integer, website text,
    works_count_openalex integer, openalex_has_ne_region boolean, sources text, updated_at timestamptz
) ON COMMIT DROP;
\copy _i FROM 'ingest/dados/processados/institutions.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO institutions
SELECT id, name, NULLIF(name_ror, ''), NULLIF(acronym, ''), kind, string_to_array(NULLIF(ror_types, ''), '|'),
       NULLIF(legal_nature, ''), NULLIF(admin_category, ''), NULLIF(academic_org, ''), uf, municipality_ibge,
       NULLIF(municipality_source, ''), latitude, longitude, NULLIF(geo_source, ''), is_active, established,
       NULLIF(website, ''), works_count_openalex, openalex_has_ne_region, string_to_array(sources, '|'), updated_at
FROM _i
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, name_ror = EXCLUDED.name_ror, acronym = EXCLUDED.acronym,
    kind = EXCLUDED.kind, ror_types = EXCLUDED.ror_types, legal_nature = EXCLUDED.legal_nature,
    admin_category = EXCLUDED.admin_category, academic_org = EXCLUDED.academic_org, uf = EXCLUDED.uf,
    municipality_ibge = EXCLUDED.municipality_ibge, municipality_source = EXCLUDED.municipality_source,
    latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude, geo_source = EXCLUDED.geo_source,
    is_active = EXCLUDED.is_active, established = EXCLUDED.established, website = EXCLUDED.website,
    works_count_openalex = EXCLUDED.works_count_openalex, openalex_has_ne_region = EXCLUDED.openalex_has_ne_region,
    sources = EXCLUDED.sources, updated_at = EXCLUDED.updated_at;

CREATE TEMP TABLE _ii (LIKE institution_identifiers) ON COMMIT DROP;
\copy _ii FROM 'ingest/dados/processados/institution_identifiers.csv' WITH (FORMAT csv, HEADER true)
\copy _ii FROM 'ingest/dados/processados/institution_identifiers_capes.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO institution_identifiers SELECT DISTINCT ON (institution_id, scheme, value) * FROM _ii
ON CONFLICT (institution_id, scheme, value) DO UPDATE SET source = EXCLUDED.source, confidence = EXCLUDED.confidence,
    verified_at = EXCLUDED.verified_at;

CREATE TEMP TABLE _ir (institution_id uuid, related_institution_id text, related_ror text, relation text, source text) ON COMMIT DROP;
\copy _ir FROM 'ingest/dados/processados/institution_relations.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO institution_relations
SELECT DISTINCT ON (institution_id, related_ror, relation) institution_id, NULLIF(related_institution_id, '')::uuid, related_ror, relation, source FROM _ir
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------ programas
CREATE TEMP TABLE _p (
    id uuid, capes_code text, name text, degree text, modality text, evaluation_area text, evaluation_area_code integer,
    major_area text, knowledge_area text, basic_area text, grade text, status text, start_year integer, uf char(2),
    municipality_name text, institution_id text, institution_link_method text, capes_entity_code text, emec_code text,
    entity_acronym text, entity_name text, legal_nature_capes text, network_program text, base_years text,
    faculty_count_last_year integer
) ON COMMIT DROP;
\copy _p FROM 'ingest/dados/processados/graduate_programs.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO graduate_programs
SELECT id, capes_code, name, degree, modality, evaluation_area, evaluation_area_code, major_area, knowledge_area,
       basic_area, grade, status, start_year, uf, municipality_name, NULLIF(institution_id, '')::uuid,
       NULLIF(institution_link_method, ''), capes_entity_code, NULLIF(emec_code, ''), entity_acronym, entity_name,
       legal_nature_capes, network_program, string_to_array(base_years, '|')::integer[], faculty_count_last_year
FROM _p
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, grade = EXCLUDED.grade, status = EXCLUDED.status,
    evaluation_area = EXCLUDED.evaluation_area, institution_id = EXCLUDED.institution_id,
    institution_link_method = EXCLUDED.institution_link_method, base_years = EXCLUDED.base_years,
    faculty_count_last_year = EXCLUDED.faculty_count_last_year;

-- ------------------------------------------------------------------ pesquisadores (consolidados)
CREATE TEMP TABLE _r (id uuid, display_name text, normalized_name text, main_institution_id text, orcid text, capes_id_pessoa text,
    is_capes_faculty boolean, pq_category_latest text, sources text, updated_at timestamptz) ON COMMIT DROP;
\copy _r FROM 'ingest/dados/processados/researchers.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO researchers (id, display_name, normalized_name, main_institution_id, orcid, is_capes_faculty, pq_category_latest, sources, updated_at)
SELECT id, display_name, COALESCE(NULLIF(normalized_name, ''), upper(display_name)), NULLIF(main_institution_id, '')::uuid, NULLIF(orcid, ''), is_capes_faculty,
       NULLIF(pq_category_latest, ''), string_to_array(sources, '|'), updated_at
FROM _r
ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, normalized_name = EXCLUDED.normalized_name,
    main_institution_id = EXCLUDED.main_institution_id, orcid = EXCLUDED.orcid, is_capes_faculty = EXCLUDED.is_capes_faculty,
    pq_category_latest = EXCLUDED.pq_category_latest, sources = EXCLUDED.sources, updated_at = EXCLUDED.updated_at;

CREATE TEMP TABLE _ri (LIKE researcher_identifiers) ON COMMIT DROP;
\copy _ri FROM 'ingest/dados/processados/researcher_identifiers.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM researcher_identifiers;   -- recalculados a cada consolidação (as decisões ficam em decisoes.csv)
INSERT INTO researcher_identifiers SELECT DISTINCT ON (researcher_id, scheme, value) * FROM _ri;

CREATE TEMP TABLE _f (LIKE program_faculty) ON COMMIT DROP;
\copy _f FROM 'ingest/dados/processados/program_faculty_final.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM program_faculty;          -- recalculado (researcher_id muda quando um alias é aceito ou desfeito)
INSERT INTO program_faculty SELECT DISTINCT ON (program_id, researcher_id, base_year) * FROM _f;

-- Aliases: recriados a partir das decisões (desfazer uma decisão remove o alias e o docente volta como perfil próprio).
CREATE TEMP TABLE _al (LIKE researcher_aliases) ON COMMIT DROP;
\copy _al FROM 'ingest/dados/processados/researcher_aliases.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM researcher_aliases WHERE alias_id NOT IN (SELECT alias_id FROM _al);
INSERT INTO researcher_aliases SELECT * FROM _al
ON CONFLICT (alias_id) DO UPDATE SET researcher_id = EXCLUDED.researcher_id, reason = EXCLUDED.reason;
-- O UUID que virou alias deixa de existir como perfil separado (fica só como redirecionamento).
DELETE FROM researchers r USING researcher_aliases a WHERE r.id = a.alias_id AND NOT EXISTS (SELECT 1 FROM _r WHERE _r.id = r.id);

CREATE TEMP TABLE _ro (id uuid, display_name text, normalized_name text, main_institution_id text, main_institution text, ufs text,
    works_count_period integer, first_year integer, last_year integer, orcid text, openalex_ids text, works_count_total integer,
    cited_by_count integer, h_index_openalex text, top_topics text, source text, updated_at timestamptz) ON COMMIT DROP;
\copy _ro FROM 'ingest/dados/processados/researchers_openalex.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO researcher_openalex_stats
SELECT id, string_to_array(NULLIF(ufs, ''), '|'), works_count_period, first_year, last_year, works_count_total, cited_by_count,
       NULLIF(h_index_openalex, '')::integer, string_to_array(NULLIF(top_topics, ''), '|'), updated_at FROM _ro
ON CONFLICT (researcher_id) DO UPDATE SET ufs = EXCLUDED.ufs, works_count_period = EXCLUDED.works_count_period,
    first_year = EXCLUDED.first_year, last_year = EXCLUDED.last_year, works_count_total = EXCLUDED.works_count_total,
    cited_by_count = EXCLUDED.cited_by_count, h_index_openalex = EXCLUDED.h_index_openalex, top_topics = EXCLUDED.top_topics,
    updated_at = EXCLUDED.updated_at;

-- ------------------------------------------------------------------ fila de revisão (status vem das decisões)
CREATE TEMP TABLE _q (entity text, candidate_a text, candidate_b text, score numeric, evidence jsonb, status text,
    decided_by text, decided_at text, created_at timestamptz) ON COMMIT DROP;
\copy _q FROM 'ingest/dados/processados/review_queue.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO identity_review_queue (entity, candidate_a, candidate_b, score, evidence, status, decided_by, decided_at, created_at)
SELECT DISTINCT ON (entity, candidate_a, candidate_b) entity, candidate_a, candidate_b, score, evidence, status, NULLIF(decided_by, ''),
       NULLIF(decided_at, '')::timestamptz, created_at
FROM _q ORDER BY entity, candidate_a, candidate_b, (status <> 'pendente') DESC, score DESC
ON CONFLICT (entity, candidate_a, candidate_b) DO UPDATE SET score = EXCLUDED.score, evidence = EXCLUDED.evidence,
    status = CASE WHEN EXCLUDED.status <> 'pendente' THEN EXCLUDED.status ELSE identity_review_queue.status END,
    decided_by = COALESCE(EXCLUDED.decided_by, identity_review_queue.decided_by),
    decided_at = COALESCE(EXCLUDED.decided_at, identity_review_queue.decided_at);

-- ------------------------------------------------------------------ produção
CREATE TEMP TABLE _t (LIKE topics) ON COMMIT DROP;
\copy _t FROM 'ingest/dados/processados/topics.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO topics SELECT * FROM _t ON CONFLICT (openalex_id) DO UPDATE SET name = EXCLUDED.name, subfield = EXCLUDED.subfield,
    field = EXCLUDED.field, domain = EXCLUDED.domain;

CREATE TEMP TABLE _w (id uuid, openalex_id text, doi text, title text, year integer, publication_date date, type text, language text,
    venue text, venue_issn_l text, venue_openalex_id text, is_oa boolean, oa_status text, primary_topic_id text, primary_topic text,
    primary_subfield text, primary_field_id text, primary_field text, cited_by_count integer, pmid text, authors_count integer,
    ne_institutions_count integer, ne_ufs text, is_xpac boolean, updated_at timestamptz) ON COMMIT DROP;
\copy _w FROM 'ingest/dados/processados/works.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO works
SELECT id, openalex_id, NULLIF(doi, ''), title, year, publication_date, type, language, NULLIF(venue, ''), NULLIF(venue_issn_l, ''),
       NULLIF(venue_openalex_id, ''), is_oa, oa_status, NULLIF(primary_topic_id, ''), primary_topic, primary_subfield, primary_field_id,
       primary_field, cited_by_count, NULLIF(pmid, ''), authors_count, ne_institutions_count, string_to_array(NULLIF(ne_ufs, ''), '|'),
       is_xpac, updated_at
FROM _w
ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, cited_by_count = EXCLUDED.cited_by_count, is_oa = EXCLUDED.is_oa,
    oa_status = EXCLUDED.oa_status, primary_topic_id = EXCLUDED.primary_topic_id, primary_field = EXCLUDED.primary_field,
    authors_count = EXCLUDED.authors_count, ne_institutions_count = EXCLUDED.ne_institutions_count, ne_ufs = EXCLUDED.ne_ufs,
    updated_at = EXCLUDED.updated_at;

CREATE TEMP TABLE _wt (LIKE work_topics) ON COMMIT DROP;
\copy _wt FROM 'ingest/dados/processados/work_topics.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO work_topics SELECT DISTINCT ON (work_id, topic_openalex_id) * FROM _wt ON CONFLICT DO NOTHING;

CREATE TEMP TABLE _fu (LIKE funders) ON COMMIT DROP;
\copy _fu FROM 'ingest/dados/processados/funders.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO funders SELECT DISTINCT ON (openalex_id) * FROM _fu ON CONFLICT DO NOTHING;
CREATE TEMP TABLE _wf (LIKE work_funders) ON COMMIT DROP;
\copy _wf FROM 'ingest/dados/processados/work_funders.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO work_funders SELECT DISTINCT * FROM _wf ON CONFLICT DO NOTHING;

CREATE TEMP TABLE _wa (work_id uuid, researcher_id text, openalex_author_id text, author_name text, author_order integer,
    author_position text, is_corresponding boolean, institution_ids text, is_ne boolean, countries text) ON COMMIT DROP;
\copy _wa FROM 'ingest/dados/processados/work_authorships.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO work_authorships (work_id, author_order, researcher_id, openalex_author_id, author_name, author_position,
    is_corresponding, institution_ids, is_ne, countries)
SELECT DISTINCT ON (work_id, author_order) work_id, author_order, NULLIF(researcher_id, '')::uuid, NULLIF(openalex_author_id, ''),
       author_name, author_position, is_corresponding, string_to_array(NULLIF(institution_ids, ''), '|')::uuid[], is_ne,
       string_to_array(NULLIF(countries, ''), '|')
FROM _wa
ON CONFLICT (work_id, author_order) DO UPDATE SET researcher_id = EXCLUDED.researcher_id, institution_ids = EXCLUDED.institution_ids,
    is_ne = EXCLUDED.is_ne, countries = EXCLUDED.countries;

CREATE TEMP TABLE _rt (LIKE researcher_topics) ON COMMIT DROP;
\copy _rt FROM 'ingest/dados/processados/researcher_topics.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO researcher_topics SELECT DISTINCT ON (researcher_id, topic_openalex_id) * FROM _rt
ON CONFLICT (researcher_id, topic_openalex_id) DO UPDATE SET works_count = EXCLUDED.works_count;

CREATE TEMP TABLE _co (LIKE coauthorships) ON COMMIT DROP;
\copy _co FROM 'ingest/dados/processados/coauthorships.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO coauthorships SELECT * FROM _co
ON CONFLICT (researcher_a_id, researcher_b_id) DO UPDATE SET shared_works_count = EXCLUDED.shared_works_count,
    first_year = EXCLUDED.first_year, last_year = EXCLUDED.last_year;

CREATE TEMP TABLE _ic (LIKE institution_collaborations) ON COMMIT DROP;
\copy _ic FROM 'ingest/dados/processados/institution_collaborations.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO institution_collaborations SELECT * FROM _ic
ON CONFLICT (institution_a_id, institution_b_id) DO UPDATE SET shared_works_count = EXCLUDED.shared_works_count;

-- ------------------------------------------------------------------ complementos (Parte 6)
CREATE TEMP TABLE _th (id uuid, capes_production_id text, title text, degree text, year integer, defense_date text, program_id uuid,
    institution_id text, author_name text, author_capes_id text, advisor_name text, advisor_capes_id text, advisor_researcher_id text,
    keywords text, abstract text, language text, full_text_url text, research_line text, concentration_area text, pages text) ON COMMIT DROP;
\copy _th FROM 'ingest/dados/processados/theses.csv' WITH (FORMAT csv, HEADER true)
INSERT INTO theses
SELECT DISTINCT ON (capes_production_id) id, capes_production_id, title, degree, year,
       CASE WHEN defense_date ~ '^\d{4}-\d{2}-\d{2}$' THEN defense_date::date
            WHEN defense_date ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(defense_date, 'DD/MM/YYYY') END,
       program_id, NULLIF(institution_id, '')::uuid, author_name, NULLIF(author_capes_id, ''), advisor_name, NULLIF(advisor_capes_id, ''),
       (SELECT r.id FROM researchers r WHERE r.id = NULLIF(_th.advisor_researcher_id, '')::uuid),
       NULLIF(keywords, ''), NULLIF(abstract, ''), NULLIF(language, ''), NULLIF(full_text_url, ''), NULLIF(research_line, ''),
       NULLIF(concentration_area, ''), NULLIF(regexp_replace(pages, '\D', '', 'g'), '')::integer
FROM _th
ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, advisor_researcher_id = EXCLUDED.advisor_researcher_id,
    abstract = EXCLUDED.abstract, keywords = EXCLUDED.keywords;

CREATE TEMP TABLE _fn (LIKE funders_ne) ON COMMIT DROP;
\copy _fn FROM 'ingest/dados/processados/funders_ne.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM funders_ne;
INSERT INTO funders_ne SELECT DISTINCT ON (funder_openalex_id) * FROM _fn WHERE funder_openalex_id IN (SELECT openalex_id FROM funders);

-- ------------------------------------------------------------------ palavras-chave (Parte 8; os vetores são carregados à parte)
CREATE TEMP TABLE _kw (LIKE work_keywords) ON COMMIT DROP;
\copy _kw FROM 'ingest/dados/processados/work_keywords.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM work_keywords;
INSERT INTO work_keywords SELECT DISTINCT ON (work_id, keyword_id) * FROM _kw WHERE work_id IN (SELECT id FROM works);

-- ------------------------------------------------------------------ fotos (Parte 7; recriadas a cada carga)
CREATE TEMP TABLE _ph (LIKE researcher_photos) ON COMMIT DROP;
\copy _ph FROM 'ingest/dados/processados/researcher_photos.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM researcher_photos WHERE source = 'wikimedia_commons';
INSERT INTO researcher_photos SELECT DISTINCT ON (researcher_id) * FROM _ph WHERE researcher_id IN (SELECT id FROM researchers)
ON CONFLICT (researcher_id) DO NOTHING;   -- upload próprio (Fase D) prevalece sobre o Commons

-- ------------------------------------------------------------------ Qualis Periódicos e ISSNs das revistas (Parte 9; recriados a cada carga)
CREATE TEMP TABLE _qp (evento text, issn text, estrato text, titulo text, areas text) ON COMMIT DROP;
\copy _qp FROM 'ingest/dados/processados/qualis_periodicos.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM qualis_periodicos WHERE evento IN (SELECT DISTINCT evento FROM _qp);
INSERT INTO qualis_periodicos SELECT evento, issn, estrato, NULLIF(titulo, ''), string_to_array(NULLIF(areas, ''), '|') FROM _qp;

CREATE TEMP TABLE _vi (LIKE venue_issns) ON COMMIT DROP;
\copy _vi FROM 'ingest/dados/processados/venue_issns.csv' WITH (FORMAT csv, HEADER true)
DELETE FROM venue_issns;
INSERT INTO venue_issns SELECT DISTINCT * FROM _vi;

COMMIT;

-- Visões materializadas (migração 0002): atualizadas depois de cada carga.
REFRESH MATERIALIZED VIEW mv_resumo;
REFRESH MATERIALIZED VIEW mv_pesquisador_busca;
REFRESH MATERIALIZED VIEW mv_instituicao_stats;
REFRESH MATERIALIZED VIEW mv_instituicao_areas;
REFRESH MATERIALIZED VIEW mv_work_inst;
REFRESH MATERIALIZED VIEW mv_mapa_producao;
REFRESH MATERIALIZED VIEW mv_mapa_colaboracao;
REFRESH MATERIALIZED VIEW mv_inst_externo;
REFRESH MATERIALIZED VIEW mv_uf_ano_area;      -- depende de mv_work_inst
REFRESH MATERIALIZED VIEW mv_work_qualis;      -- migração 0010 (Parte 9)
