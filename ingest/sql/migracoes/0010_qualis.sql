-- 0010 — Qualis Periódicos (CAPES) por publicação (D-033).
-- qualis_periodicos: um estrato por ISSN e evento (no 2021-2024 o estrato é o mesmo em todas as áreas que listam a revista).
-- venue_issns: todos os ISSNs (impresso, eletrônico, ISSN-L) de cada revista do OpenAlex, porque o Qualis pode listar qualquer um.
CREATE TABLE IF NOT EXISTS qualis_periodicos (
    evento  text NOT NULL,                 -- quadriênio, ex.: '2021-2024'
    issn    text NOT NULL,                 -- normalizado: 1234-567X
    estrato text NOT NULL CHECK (estrato IN ('A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C')),
    titulo  text,
    areas   text[],                        -- áreas de avaliação que listam a revista
    PRIMARY KEY (evento, issn)
);
CREATE INDEX IF NOT EXISTS qualis_periodicos_issn ON qualis_periodicos (issn);

CREATE TABLE IF NOT EXISTS venue_issns (
    venue_openalex_id text NOT NULL,       -- ex.: S137905309 (mesmo formato de works.venue_openalex_id)
    issn              text NOT NULL,
    PRIMARY KEY (venue_openalex_id, issn)
);
CREATE INDEX IF NOT EXISTS venue_issns_issn ON venue_issns (issn);

-- Estrato de cada publicação no Qualis 2021-2024 (o mais recente), por qualquer ISSN da revista; havendo mais de um, o melhor
-- ('A1' < 'A2' < … < 'C' em ordem de texto). Publicações sem linha aqui ficam "sem Qualis". Ao chegar um novo quadriênio,
-- uma nova migração recria esta visão com o evento novo.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_work_qualis AS
WITH c AS (
    SELECT w.id AS work_id, q.estrato
      FROM works w
      JOIN venue_issns v ON v.venue_openalex_id = w.venue_openalex_id
      JOIN qualis_periodicos q ON q.issn = v.issn AND q.evento = '2021-2024'
    UNION ALL
    SELECT w.id, q.estrato
      FROM works w
      JOIN qualis_periodicos q ON q.issn = w.venue_issn_l AND q.evento = '2021-2024'
)
SELECT work_id, min(estrato) AS estrato FROM c GROUP BY work_id;
CREATE UNIQUE INDEX IF NOT EXISTS mv_work_qualis_work ON mv_work_qualis (work_id);
