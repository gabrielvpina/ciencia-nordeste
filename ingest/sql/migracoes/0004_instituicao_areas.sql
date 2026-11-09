-- 0004 — publicações por área (field) de cada instituição, pré-calculadas (página de instituição).
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_instituicao_areas AS
SELECT x.institution_id, w.primary_field, count(DISTINCT w.id) AS works
  FROM (SELECT DISTINCT work_id, unnest(institution_ids) AS institution_id FROM work_authorships WHERE is_ne) x
  JOIN works w ON w.id = x.work_id
 WHERE w.primary_field IS NOT NULL
 GROUP BY 1, 2;
CREATE UNIQUE INDEX IF NOT EXISTS mv_instituicao_areas_pk ON mv_instituicao_areas (institution_id, primary_field);
