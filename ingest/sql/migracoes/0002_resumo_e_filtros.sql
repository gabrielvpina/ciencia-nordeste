-- 0002 — Fase C: visões materializadas para a home (resumo), busca com filtros e páginas de instituição.
-- Atualizadas no fim de ingest/sql/carga.sql (REFRESH MATERIALIZED VIEW).

CREATE INDEX IF NOT EXISTS work_authorships_insts_gin ON work_authorships USING gin (institution_ids);
CREATE INDEX IF NOT EXISTS program_faculty_researcher_idx ON program_faculty (researcher_id);
CREATE INDEX IF NOT EXISTS graduate_programs_uf_idx ON graduate_programs (uf);

-- Totais da home (evita contar tabelas inteiras a cada visita).
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resumo AS
SELECT (SELECT count(*) FROM researchers WHERE NOT is_hidden)          AS pesquisadores,
       (SELECT count(*) FROM researchers WHERE is_capes_faculty)       AS docentes,
       (SELECT count(*) FROM works)                                    AS works,
       (SELECT count(*) FROM institutions)                             AS instituicoes,
       (SELECT count(*) FROM graduate_programs)                        AS programas,
       (SELECT count(*) FROM theses)                                   AS teses,
       (SELECT min(year) FROM works)                                   AS ano_inicio,
       (SELECT max(year) FROM works)                                   AS ano_fim,
       now()                                                           AS atualizado_em;

-- Uma linha por pesquisador com o que a busca filtra: UF, áreas (fields das suas publicações), instituição, docente.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_pesquisador_busca AS
WITH areas AS (
    SELECT a.researcher_id, array_agg(DISTINCT w.primary_field) FILTER (WHERE w.primary_field IS NOT NULL) AS fields
      FROM work_authorships a JOIN works w ON w.id = a.work_id
     WHERE a.researcher_id IS NOT NULL
     GROUP BY a.researcher_id
)
SELECT r.id, r.display_name, r.normalized_name, r.main_institution_id, i.acronym AS instituicao_sigla, i.name AS instituicao,
       COALESCE(i.uf, s.ufs[1]) AS uf, COALESCE(s.ufs, ARRAY[i.uf]::text[]) AS ufs, COALESCE(ar.fields, '{}') AS fields,
       COALESCE(s.works_count_period, 0) AS works, r.is_capes_faculty, r.pq_category_latest, r.orcid IS NOT NULL AS tem_orcid
  FROM researchers r
  LEFT JOIN institutions i ON i.id = r.main_institution_id
  LEFT JOIN researcher_openalex_stats s ON s.researcher_id = r.id
  LEFT JOIN areas ar ON ar.researcher_id = r.id
 WHERE NOT r.is_hidden;
CREATE UNIQUE INDEX IF NOT EXISTS mv_pesquisador_busca_id ON mv_pesquisador_busca (id);
CREATE INDEX IF NOT EXISTS mv_pesquisador_busca_nome ON mv_pesquisador_busca USING gin (normalized_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS mv_pesquisador_busca_fields ON mv_pesquisador_busca USING gin (fields);
CREATE INDEX IF NOT EXISTS mv_pesquisador_busca_uf ON mv_pesquisador_busca (uf);
CREATE INDEX IF NOT EXISTS mv_pesquisador_busca_works ON mv_pesquisador_busca (works DESC);

-- Números por instituição (produção no recorte, pesquisadores, programas).
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_instituicao_stats AS
WITH w AS (
    SELECT unnest(institution_ids) AS institution_id, count(DISTINCT work_id) AS works
      FROM work_authorships WHERE is_ne GROUP BY 1
), p AS (
    SELECT main_institution_id AS institution_id, count(*) AS pesquisadores FROM researchers GROUP BY 1
), g AS (
    SELECT institution_id, count(*) AS programas FROM graduate_programs GROUP BY 1
)
SELECT i.id AS institution_id, COALESCE(w.works, 0) AS works, COALESCE(p.pesquisadores, 0) AS pesquisadores, COALESCE(g.programas, 0) AS programas
  FROM institutions i LEFT JOIN w ON w.institution_id = i.id LEFT JOIN p ON p.institution_id = i.id LEFT JOIN g ON g.institution_id = i.id;
CREATE UNIQUE INDEX IF NOT EXISTS mv_instituicao_stats_id ON mv_instituicao_stats (institution_id);
