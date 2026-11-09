-- Ciência Nordeste — tabelas geradas pela ingestão (Partes 1 e 2).
-- Alvo: PostgreSQL 16 com pg_trgm e unaccent. Os CSVs de ingest/dados/processados/ carregam direto
-- com \copy (ver ingest/sql/carga.sql). Listas ("a|b|c") viram text[] na carga.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- unaccent() não é IMMUTABLE e não pode ir em índice; este invólucro fixa o dicionário e pode.
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

-- ------------------------------------------------------------------ Parte 1
CREATE TABLE IF NOT EXISTS municipalities (
    ibge_code    integer PRIMARY KEY,
    name         text    NOT NULL,
    uf           char(2) NOT NULL,
    latitude     double precision,
    longitude    double precision,
    is_capital   boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS institutions (
    id                     uuid PRIMARY KEY,
    name                   text NOT NULL,
    name_ror               text,
    acronym                text,
    kind                   text NOT NULL,          -- universidade, centro_universitario, faculdade, instituto_federal, cefet,
                                                   -- ensino, hospital_saude, instituto_pesquisa, governo, empresa, ...
    ror_types              text[],
    legal_nature           text,                   -- publica | privada | especial | NULL (desconhecida)
    admin_category         text,                   -- categoria administrativa INEP
    academic_org           text,                   -- organização acadêmica INEP
    uf                     char(2) NOT NULL,
    municipality_ibge      integer REFERENCES municipalities (ibge_code),
    municipality_source    text,
    latitude               double precision,
    longitude              double precision,
    geo_source             text,                   -- ror_geonames | sede_municipio
    is_active              boolean,
    established            integer,
    website                text,
    works_count_openalex   integer,
    openalex_has_ne_region boolean,
    sources                text[] NOT NULL,
    updated_at             timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS institutions_uf_idx ON institutions (uf);
CREATE INDEX IF NOT EXISTS institutions_mun_idx ON institutions (municipality_ibge);
CREATE INDEX IF NOT EXISTS institutions_name_trgm ON institutions USING gin (lower(f_unaccent(name)) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS institution_identifiers (
    institution_id uuid NOT NULL REFERENCES institutions (id) ON DELETE CASCADE,
    scheme         text NOT NULL,                  -- ror, openalex, emec, capes_entidade, wikidata, isni, grid, fundref, inep_mantenedora
    value          text NOT NULL,
    source         text NOT NULL,
    confidence     numeric(3, 2) NOT NULL CHECK (confidence > 0 AND confidence <= 1),
    verified_at    timestamptz NOT NULL,
    PRIMARY KEY (institution_id, scheme, value)
);
CREATE INDEX IF NOT EXISTS institution_identifiers_lookup ON institution_identifiers (scheme, value);

CREATE TABLE IF NOT EXISTS institution_relations (
    institution_id         uuid NOT NULL REFERENCES institutions (id) ON DELETE CASCADE,
    related_institution_id uuid REFERENCES institutions (id),   -- NULL quando a relacionada está fora do NE
    related_ror            text NOT NULL,
    relation               text NOT NULL,                        -- parent, child, related, predecessor, successor
    source                 text NOT NULL,
    PRIMARY KEY (institution_id, related_ror, relation)
);

-- Fila única de revisão de identidade (instituições e, a partir da Parte 4, pesquisadores).
CREATE TABLE IF NOT EXISTS identity_review_queue (
    id          bigserial PRIMARY KEY,
    entity      text NOT NULL CHECK (entity IN ('institution', 'researcher')),
    candidate_a text NOT NULL,
    candidate_b text NOT NULL,
    score       numeric(4, 3),
    evidence    jsonb,
    status      text NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'aceito', 'rejeitado')),
    decided_by  text,
    decided_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entity, candidate_a, candidate_b)
);

-- ------------------------------------------------------------------ Parte 2
CREATE TABLE IF NOT EXISTS graduate_programs (
    id                      uuid PRIMARY KEY,
    capes_code              text NOT NULL UNIQUE,
    name                    text NOT NULL,
    degree                  text,
    modality                text,
    evaluation_area         text,
    evaluation_area_code    integer,
    major_area              text,
    knowledge_area          text,
    basic_area              text,
    grade                   text,                  -- conceito CAPES (texto: inclui "A" para programas novos)
    status                  text,
    start_year              integer,
    uf                      char(2) NOT NULL,
    municipality_name       text,
    institution_id          uuid REFERENCES institutions (id),
    institution_link_method text,
    capes_entity_code       text,
    emec_code               text,
    entity_acronym          text,
    entity_name             text,
    legal_nature_capes      text,
    network_program         text,
    base_years              integer[],
    faculty_count_last_year integer
);
CREATE INDEX IF NOT EXISTS graduate_programs_inst_idx ON graduate_programs (institution_id);

CREATE TABLE IF NOT EXISTS researchers (
    id                   uuid PRIMARY KEY,                -- estável: nunca muda (registro em ingest/dados/ids/researcher.csv)
    display_name         text NOT NULL,
    normalized_name      text NOT NULL,
    main_institution_id  uuid REFERENCES institutions (id),
    orcid                text,
    is_capes_faculty     boolean NOT NULL DEFAULT false,
    pq_category_latest   text,
    sources              text[] NOT NULL DEFAULT '{}',
    is_claimed           boolean NOT NULL DEFAULT false,
    is_hidden            boolean NOT NULL DEFAULT false,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS researchers_name_trgm ON researchers USING gin (normalized_name gin_trgm_ops);

-- UUIDs que passaram a apontar para outro pesquisador (mescla aceita na revisão). Nunca se apaga um UUID.
CREATE TABLE IF NOT EXISTS researcher_aliases (
    alias_id      uuid PRIMARY KEY,
    researcher_id uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    reason        text NOT NULL,
    created_at    timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS researcher_identifiers (
    researcher_id uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    scheme        text NOT NULL CHECK (scheme IN ('orcid', 'openalex', 'capes_id_pessoa', 'lattes', 'scholar_url', 'wikidata')),
    value         text NOT NULL,
    source        text NOT NULL,
    confidence    numeric(3, 2) NOT NULL CHECK (confidence > 0 AND confidence <= 1),
    verified_at   timestamptz NOT NULL,
    PRIMARY KEY (researcher_id, scheme, value)
);
CREATE UNIQUE INDEX IF NOT EXISTS researcher_identifiers_unique_strong
    ON researcher_identifiers (scheme, value) WHERE confidence = 1;   -- um identificador forte pertence a um só pesquisador

CREATE TABLE IF NOT EXISTS program_faculty (
    program_id         uuid NOT NULL REFERENCES graduate_programs (id) ON DELETE CASCADE,
    researcher_id      uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    capes_id_pessoa    text NOT NULL,
    base_year          integer NOT NULL,
    category           text,                 -- PERMANENTE, COLABORADOR, VISITANTE
    bond_type          text,
    work_regime        text,
    pq_category        text,                 -- categoria de bolsa de produtividade CNPq, quando houver
    is_doctor          boolean,
    degree_year        integer,
    degree_level       text,
    degree_area        text,
    degree_institution text,
    degree_country     text,
    PRIMARY KEY (program_id, researcher_id, base_year)
);

-- ------------------------------------------------------------------ Parte 5
CREATE TABLE IF NOT EXISTS topics (
    openalex_id text PRIMARY KEY,
    name        text NOT NULL,
    subfield_id text,
    subfield    text,
    field_id    text,
    field       text,
    domain      text
);
CREATE INDEX IF NOT EXISTS topics_name_trgm ON topics USING gin (lower(f_unaccent(name)) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS works (
    id                    uuid PRIMARY KEY,
    openalex_id           text NOT NULL UNIQUE,
    doi                   text,
    title                 text,
    year                  integer,
    publication_date      date,
    type                  text,
    language              text,
    venue                 text,
    venue_issn_l          text,
    venue_openalex_id     text,
    is_oa                 boolean,
    oa_status             text,
    primary_topic_id      text REFERENCES topics (openalex_id),
    primary_topic         text,
    primary_subfield      text,
    primary_field_id      text,
    primary_field         text,
    cited_by_count        integer,
    pmid                  text,
    authors_count         integer,
    ne_institutions_count integer,
    ne_ufs                text[],
    is_xpac               boolean,
    updated_at            timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS works_year_idx ON works (year);
CREATE INDEX IF NOT EXISTS works_field_idx ON works (primary_field_id);
CREATE INDEX IF NOT EXISTS works_doi_idx ON works (lower(doi));
CREATE INDEX IF NOT EXISTS works_title_trgm ON works USING gin (lower(f_unaccent(title)) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS work_topics (
    work_id           uuid NOT NULL REFERENCES works (id) ON DELETE CASCADE,
    topic_openalex_id text NOT NULL REFERENCES topics (openalex_id),
    score             real,
    is_primary        boolean,
    PRIMARY KEY (work_id, topic_openalex_id)
);

CREATE TABLE IF NOT EXISTS funders (
    openalex_id text PRIMARY KEY,
    name        text NOT NULL,
    ror         text
);

CREATE TABLE IF NOT EXISTS work_funders (
    work_id            uuid NOT NULL REFERENCES works (id) ON DELETE CASCADE,
    funder_openalex_id text NOT NULL REFERENCES funders (openalex_id),
    PRIMARY KEY (work_id, funder_openalex_id)
);

-- Todas as autorias (inclusive coautores de fora do NE, que ficam sem researcher_id).
CREATE TABLE IF NOT EXISTS work_authorships (
    work_id            uuid NOT NULL REFERENCES works (id) ON DELETE CASCADE,
    author_order       integer NOT NULL,
    researcher_id      uuid REFERENCES researchers (id),
    openalex_author_id text,
    author_name        text,
    author_position    text,
    is_corresponding   boolean,
    institution_ids    uuid[],              -- instituições do NE da autoria
    is_ne              boolean NOT NULL,
    PRIMARY KEY (work_id, author_order)
);
CREATE INDEX IF NOT EXISTS work_authorships_researcher_idx ON work_authorships (researcher_id);

-- ------------------------------------------------------------------ Parte 4
CREATE TABLE IF NOT EXISTS researcher_topics (
    researcher_id     uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    topic_openalex_id text NOT NULL,
    works_count       integer,
    PRIMARY KEY (researcher_id, topic_openalex_id)
);

CREATE TABLE IF NOT EXISTS coauthorships (
    researcher_a_id    uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    researcher_b_id    uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    shared_works_count integer NOT NULL,
    first_year         integer,
    last_year          integer,
    PRIMARY KEY (researcher_a_id, researcher_b_id),
    CHECK (researcher_a_id < researcher_b_id)
);

CREATE TABLE IF NOT EXISTS institution_collaborations (
    institution_a_id   uuid NOT NULL REFERENCES institutions (id) ON DELETE CASCADE,
    institution_b_id   uuid NOT NULL REFERENCES institutions (id) ON DELETE CASCADE,
    shared_works_count integer NOT NULL,
    PRIMARY KEY (institution_a_id, institution_b_id),
    CHECK (institution_a_id < institution_b_id)
);

-- Campos extras de pesquisador vindos do OpenAlex (métricas e resumo); a tabela researchers fica enxuta.
CREATE TABLE IF NOT EXISTS researcher_openalex_stats (
    researcher_id      uuid PRIMARY KEY REFERENCES researchers (id) ON DELETE CASCADE,
    ufs                text[],
    works_count_period integer,
    first_year         integer,
    last_year          integer,
    works_count_total  integer,
    cited_by_count     integer,
    h_index_openalex   integer,
    top_topics         text[],
    updated_at         timestamptz NOT NULL
);

-- ------------------------------------------------------------------ Parte 6
CREATE TABLE IF NOT EXISTS theses (
    id                    uuid PRIMARY KEY,
    capes_production_id   text NOT NULL UNIQUE,
    title                 text,
    degree                text,                 -- DISSERTAÇÃO, TESE, TRABALHO DE CONCLUSÃO (mestrado profissional)...
    year                  integer,
    defense_date          date,
    program_id            uuid REFERENCES graduate_programs (id),
    institution_id        uuid REFERENCES institutions (id),
    author_name           text,
    author_capes_id       text,
    advisor_name          text,
    advisor_capes_id      text,
    advisor_researcher_id uuid REFERENCES researchers (id),
    keywords              text,
    abstract              text,
    language              text,
    full_text_url         text,
    research_line         text,
    concentration_area    text,
    pages                 integer
);
CREATE INDEX IF NOT EXISTS theses_advisor_idx ON theses (advisor_researcher_id);
CREATE INDEX IF NOT EXISTS theses_program_idx ON theses (program_id);
CREATE INDEX IF NOT EXISTS theses_title_trgm ON theses USING gin (lower(f_unaccent(title)) gin_trgm_ops);

CREATE TABLE IF NOT EXISTS funders_ne (
    funder_openalex_id text PRIMARY KEY REFERENCES funders (openalex_id),
    sigla              text NOT NULL,
    uf                 char(2) NOT NULL,
    name               text NOT NULL,
    works_no_recorte   integer
);
