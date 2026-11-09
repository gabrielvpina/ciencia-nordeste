-- 0005 — dados do mapa próprio (D-025): produção e colaboração por instituição × área × ano; colaboração externa.
ALTER TABLE work_authorships ADD COLUMN IF NOT EXISTS countries text[];

-- (work, instituição do NE) distintos
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_work_inst AS
SELECT DISTINCT a.work_id, x.institution_id
  FROM work_authorships a, unnest(a.institution_ids) AS x(institution_id)
 WHERE a.is_ne;
CREATE INDEX IF NOT EXISTS mv_work_inst_work ON mv_work_inst (work_id);
CREATE INDEX IF NOT EXISTS mv_work_inst_inst ON mv_work_inst (institution_id);

-- Modo densidade/áreas: publicações por instituição × field × ano
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_mapa_producao AS
SELECT wi.institution_id, w.primary_field AS field, w.year, count(*)::int AS works
  FROM mv_work_inst wi JOIN works w ON w.id = wi.work_id
 GROUP BY 1, 2, 3;
CREATE INDEX IF NOT EXISTS mv_mapa_producao_inst ON mv_mapa_producao (institution_id);

-- Modo ligações: pares de instituições do NE × field × ano
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_mapa_colaboracao AS
SELECT a.institution_id AS inst_a, b.institution_id AS inst_b, w.primary_field AS field, w.year, count(*)::int AS works
  FROM mv_work_inst a
  JOIN mv_work_inst b ON b.work_id = a.work_id AND a.institution_id < b.institution_id
  JOIN works w ON w.id = a.work_id
 GROUP BY 1, 2, 3, 4;
CREATE INDEX IF NOT EXISTS mv_mapa_colaboracao_a ON mv_mapa_colaboracao (inst_a);
CREATE INDEX IF NOT EXISTS mv_mapa_colaboracao_b ON mv_mapa_colaboracao (inst_b);

-- Rede: colaboração externa de cada instituição (coautores do Brasil fora do NE e de outros países)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_inst_externo AS
WITH ext AS (
    SELECT DISTINCT a.work_id, c.pais
      FROM work_authorships a, unnest(a.countries) AS c(pais)
     WHERE NOT a.is_ne AND a.countries IS NOT NULL
)
SELECT wi.institution_id, ext.pais, count(DISTINCT wi.work_id)::int AS works
  FROM mv_work_inst wi JOIN ext ON ext.work_id = wi.work_id
 GROUP BY 1, 2;
CREATE INDEX IF NOT EXISTS mv_inst_externo_inst ON mv_inst_externo (institution_id);
