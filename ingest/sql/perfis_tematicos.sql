-- Perfil temático de cada pesquisador (etapa 13, D-036): média ponderada dos vetores das suas publicações no recorte,
-- normalizada (cosseno). Idempotente: recalcula tudo. Roda no fim de scripts/carregar_banco.sh e depois da etapa "vetores".
--
-- Quem entra: pesquisadores não ocultos com >= 3 publicações no período que têm vetor.
-- Peso de cada publicação = recência × autoria × equipe:
--   recência: 1,0 no ano mais recente da base, -0,1 por ano antes (mínimo 0,5) — o interesse atual pesa mais;
--   autoria: 1,0 como primeiro, último ou correspondente; 0,6 no meio da lista — quem conduz o trabalho;
--   equipe: 1,0 até 10 autores; acima, sqrt(10 / autores) — artigos de consórcio dizem pouco do tema de cada um.
-- O pgvector 0.8.6 soma halfvec, mas não multiplica por escalar: a conta é feita em vector (float4) com um vetor de pesos.

\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _pw ON COMMIT DROP AS
WITH ano AS (SELECT max(year) AS fim FROM works),
autor AS (
    SELECT a.researcher_id AS rid, a.work_id,
           max(CASE WHEN a.author_position IN ('first', 'last') OR a.is_corresponding THEN 1.0 ELSE 0.6 END) AS w_autoria
      FROM work_authorships a JOIN researchers r ON r.id = a.researcher_id AND NOT r.is_hidden
     GROUP BY 1, 2
),
ativos AS (SELECT rid FROM autor GROUP BY rid HAVING count(*) >= 3)
SELECT au.rid, au.work_id,
       (greatest(0.5, 1.0 - 0.1 * (ano.fim - w.year))
        * au.w_autoria
        * CASE WHEN coalesce(w.authors_count, 1) <= 10 THEN 1.0 ELSE sqrt(10.0 / w.authors_count) END)::real AS peso
  FROM autor au JOIN ativos USING (rid) JOIN works w ON w.id = au.work_id CROSS JOIN ano
 WHERE w.year IS NOT NULL;

DELETE FROM researcher_embeddings;
INSERT INTO researcher_embeddings (researcher_id, model, n_works, embedding, updated_at)
SELECT p.rid, min(e.model), count(*)::int,
       l2_normalize(sum(e.embedding::vector * array_fill(p.peso, ARRAY[768])::vector))::halfvec(768), now()
  FROM _pw p JOIN work_embeddings e ON e.work_id = p.work_id
 GROUP BY p.rid;
COMMIT;
ANALYZE researcher_embeddings;
SELECT count(*) AS pesquisadores_com_perfil, round(avg(n_works), 1) AS media_publicacoes FROM researcher_embeddings;
