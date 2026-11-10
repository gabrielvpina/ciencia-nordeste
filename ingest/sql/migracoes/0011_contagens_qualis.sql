-- 0011 — filtro "só revistas com Qualis" no site inteiro (D-035).
-- Cada visão de contagem ganha uma coluna works_qualis, ao lado de works: as publicações cuja revista está no Qualis
-- (mv_work_qualis, migração 0010). O app escolhe a coluna conforme o filtro; as linhas e índices continuam os mesmos.
-- Visão materializada não aceita ADD COLUMN: as visões são recriadas. mv_work_inst (0005) não muda.
-- Depende de mv_work_qualis estar atualizada: em ingest/sql/carga.sql ela é a primeira do REFRESH.

DROP MATERIALIZED VIEW IF EXISTS mv_uf_ano_area;
DROP MATERIALIZED VIEW IF EXISTS mv_inst_externo;
DROP MATERIALIZED VIEW IF EXISTS mv_mapa_colaboracao;
DROP MATERIALIZED VIEW IF EXISTS mv_mapa_producao;
DROP MATERIALIZED VIEW IF EXISTS mv_instituicao_areas;
DROP MATERIALIZED VIEW IF EXISTS mv_instituicao_stats;
DROP MATERIALIZED VIEW IF EXISTS mv_pesquisador_busca;
DROP MATERIALIZED VIEW IF EXISTS mv_resumo;

-- Totais da home
CREATE MATERIALIZED VIEW mv_resumo AS
SELECT (SELECT count(*) FROM researchers WHERE NOT is_hidden)          AS pesquisadores,
       (SELECT count(*) FROM researchers WHERE is_capes_faculty)       AS docentes,
       (SELECT count(*) FROM works)                                    AS works,
       (SELECT count(*) FROM mv_work_qualis)                           AS works_qualis,
       (SELECT count(*) FROM institutions)                             AS instituicoes,
       (SELECT count(*) FROM graduate_programs)                        AS programas,
       (SELECT count(*) FROM theses)                                   AS teses,
       (SELECT min(year) FROM works)                                   AS ano_inicio,
       (SELECT max(year) FROM works)                                   AS ano_fim,
       now()                                                           AS atualizado_em;

-- Busca de pesquisadores (works = perfil OpenAlex no período; works_qualis = autorias do recorte em revistas com Qualis)
CREATE MATERIALIZED VIEW mv_pesquisador_busca AS
WITH areas AS (
    SELECT a.researcher_id, array_agg(DISTINCT w.primary_field) FILTER (WHERE w.primary_field IS NOT NULL) AS fields,
           count(DISTINCT a.work_id) FILTER (WHERE mq.work_id IS NOT NULL) AS works_qualis
      FROM work_authorships a JOIN works w ON w.id = a.work_id LEFT JOIN mv_work_qualis mq ON mq.work_id = a.work_id
     WHERE a.researcher_id IS NOT NULL
     GROUP BY a.researcher_id
)
SELECT r.id, r.display_name, r.normalized_name, r.main_institution_id, i.acronym AS instituicao_sigla, i.name AS instituicao,
       COALESCE(i.uf, s.ufs[1]) AS uf, COALESCE(s.ufs, ARRAY[i.uf]::text[]) AS ufs, COALESCE(ar.fields, '{}') AS fields,
       COALESCE(s.works_count_period, 0) AS works, COALESCE(ar.works_qualis, 0)::int AS works_qualis,
       r.is_capes_faculty, r.pq_category_latest, r.orcid IS NOT NULL AS tem_orcid
  FROM researchers r
  LEFT JOIN institutions i ON i.id = r.main_institution_id
  LEFT JOIN researcher_openalex_stats s ON s.researcher_id = r.id
  LEFT JOIN areas ar ON ar.researcher_id = r.id
 WHERE NOT r.is_hidden;
CREATE UNIQUE INDEX mv_pesquisador_busca_id ON mv_pesquisador_busca (id);
CREATE INDEX mv_pesquisador_busca_nome ON mv_pesquisador_busca USING gin (normalized_name gin_trgm_ops);
CREATE INDEX mv_pesquisador_busca_fields ON mv_pesquisador_busca USING gin (fields);
CREATE INDEX mv_pesquisador_busca_uf ON mv_pesquisador_busca (uf);
CREATE INDEX mv_pesquisador_busca_works ON mv_pesquisador_busca (works DESC);
CREATE INDEX mv_pesquisador_busca_inst ON mv_pesquisador_busca (main_institution_id);

-- Números por instituição
CREATE MATERIALIZED VIEW mv_instituicao_stats AS
WITH w AS (
    SELECT x.institution_id, count(*) AS works, count(mq.work_id) AS works_qualis
      FROM (SELECT DISTINCT work_id, unnest(institution_ids) AS institution_id FROM work_authorships WHERE is_ne) x
      LEFT JOIN mv_work_qualis mq ON mq.work_id = x.work_id
     GROUP BY 1
), p AS (
    SELECT main_institution_id AS institution_id, count(*) AS pesquisadores FROM researchers GROUP BY 1
), g AS (
    SELECT institution_id, count(*) AS programas FROM graduate_programs GROUP BY 1
)
SELECT i.id AS institution_id, COALESCE(w.works, 0) AS works, COALESCE(w.works_qualis, 0) AS works_qualis,
       COALESCE(p.pesquisadores, 0) AS pesquisadores, COALESCE(g.programas, 0) AS programas
  FROM institutions i LEFT JOIN w ON w.institution_id = i.id LEFT JOIN p ON p.institution_id = i.id LEFT JOIN g ON g.institution_id = i.id;
CREATE UNIQUE INDEX mv_instituicao_stats_id ON mv_instituicao_stats (institution_id);

-- Publicações por área de cada instituição
CREATE MATERIALIZED VIEW mv_instituicao_areas AS
SELECT x.institution_id, w.primary_field, count(*) AS works, count(mq.work_id) AS works_qualis
  FROM (SELECT DISTINCT work_id, unnest(institution_ids) AS institution_id FROM work_authorships WHERE is_ne) x
  JOIN works w ON w.id = x.work_id
  LEFT JOIN mv_work_qualis mq ON mq.work_id = x.work_id
 WHERE w.primary_field IS NOT NULL
 GROUP BY 1, 2;
CREATE UNIQUE INDEX mv_instituicao_areas_pk ON mv_instituicao_areas (institution_id, primary_field);

-- Mapa: instituição × área × ano
CREATE MATERIALIZED VIEW mv_mapa_producao AS
SELECT wi.institution_id, w.primary_field AS field, w.year, count(*)::int AS works, count(mq.work_id)::int AS works_qualis
  FROM mv_work_inst wi JOIN works w ON w.id = wi.work_id LEFT JOIN mv_work_qualis mq ON mq.work_id = wi.work_id
 GROUP BY 1, 2, 3;
CREATE INDEX mv_mapa_producao_inst ON mv_mapa_producao (institution_id);

-- Mapa: pares de instituições do NE × área × ano
CREATE MATERIALIZED VIEW mv_mapa_colaboracao AS
SELECT a.institution_id AS inst_a, b.institution_id AS inst_b, w.primary_field AS field, w.year,
       count(*)::int AS works, count(mq.work_id)::int AS works_qualis
  FROM mv_work_inst a
  JOIN mv_work_inst b ON b.work_id = a.work_id AND a.institution_id < b.institution_id
  JOIN works w ON w.id = a.work_id
  LEFT JOIN mv_work_qualis mq ON mq.work_id = a.work_id
 GROUP BY 1, 2, 3, 4;
CREATE INDEX mv_mapa_colaboracao_a ON mv_mapa_colaboracao (inst_a);
CREATE INDEX mv_mapa_colaboracao_b ON mv_mapa_colaboracao (inst_b);

-- Rede: colaboração externa de cada instituição
CREATE MATERIALIZED VIEW mv_inst_externo AS
WITH ext AS (
    SELECT DISTINCT a.work_id, c.pais
      FROM work_authorships a, unnest(a.countries) AS c(pais)
     WHERE NOT a.is_ne AND a.countries IS NOT NULL
)
SELECT wi.institution_id, ext.pais, count(DISTINCT wi.work_id)::int AS works,
       count(DISTINCT wi.work_id) FILTER (WHERE mq.work_id IS NOT NULL)::int AS works_qualis
  FROM mv_work_inst wi JOIN ext ON ext.work_id = wi.work_id LEFT JOIN mv_work_qualis mq ON mq.work_id = wi.work_id
 GROUP BY 1, 2;
CREATE INDEX mv_inst_externo_inst ON mv_inst_externo (institution_id);

-- Produção por estado × ano × área (publicações únicas)
CREATE MATERIALIZED VIEW mv_uf_ano_area AS
SELECT i.uf, w.year, w.primary_field AS field, count(DISTINCT w.id)::int AS works,
       count(DISTINCT w.id) FILTER (WHERE mq.work_id IS NOT NULL)::int AS works_qualis
  FROM works w
  JOIN mv_work_inst wi ON wi.work_id = w.id
  JOIN institutions i ON i.id = wi.institution_id
  LEFT JOIN mv_work_qualis mq ON mq.work_id = w.id
 GROUP BY 1, 2, 3;
CREATE INDEX mv_uf_ano_area_idx ON mv_uf_ano_area (uf, year);
