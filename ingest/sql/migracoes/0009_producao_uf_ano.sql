-- 0009 — produção por estado × ano × área, em publicações únicas (card "Produção por ano" da tela inicial, com filtro de estado).
-- Cada publicação tem uma só área (primary_field), então somar áreas dentro de um estado e ano não conta nada duas vezes.
-- Uma publicação com instituições de dois estados conta uma vez em cada estado ("com participação do estado").
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uf_ano_area AS
SELECT i.uf, w.year, w.primary_field AS field, count(DISTINCT w.id)::int AS works
  FROM works w
  JOIN mv_work_inst wi ON wi.work_id = w.id
  JOIN institutions i ON i.id = wi.institution_id
 GROUP BY 1, 2, 3;
CREATE INDEX IF NOT EXISTS mv_uf_ano_area_idx ON mv_uf_ano_area (uf, year);
