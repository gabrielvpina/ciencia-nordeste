-- Atualiza todas as visões materializadas, na ordem das dependências. Incluído no fim de carga.sql; também rodado pelo
-- scripts/publicar.sh quando chega uma migração que altera dados (ex.: 0013).
REFRESH MATERIALIZED VIEW mv_work_qualis;      -- primeiro: as demais contam works_qualis a partir dela (0010, 0011)
REFRESH MATERIALIZED VIEW mv_resumo;
REFRESH MATERIALIZED VIEW mv_pesquisador_busca;
REFRESH MATERIALIZED VIEW mv_instituicao_stats;
REFRESH MATERIALIZED VIEW mv_instituicao_areas;
REFRESH MATERIALIZED VIEW mv_work_inst;
REFRESH MATERIALIZED VIEW mv_mapa_producao;
REFRESH MATERIALIZED VIEW mv_mapa_colaboracao;
REFRESH MATERIALIZED VIEW mv_inst_externo;
REFRESH MATERIALIZED VIEW mv_uf_ano_area;      -- depende de mv_work_inst
