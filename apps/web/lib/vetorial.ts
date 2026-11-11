// Busca por tema (D-028): embedding da consulta + vizinhos no pgvector (HNSW), fundidos por RRF com a
// coincidência textual em título e palavras-chave; depois agregados por pesquisador, instituição e programa.
import { pool } from "@/lib/db";

export type ModoBusca = "hibrido" | "vetor" | "texto";
const K_RRF = 60;          // constante usual da Reciprocal Rank Fusion
const CANDIDATOS = 200;    // vizinhos considerados em cada lista

export async function embedConsulta(texto: string): Promise<string | null> {
  const v = await embedVetor(texto);
  return v ? `[${v.join(",")}]` : null;
}

/** Vetor do e5 (768, normalizado) para uma consulta; null se o serviço estiver fora do ar ou passar de `limiteMs`. */
export async function embedVetor(texto: string, limiteMs = 4000): Promise<number[] | null> {
  const url = process.env.EMBED_URL;
  if (!url) return null;
  try {
    const r = await fetch(`${url}/embed`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ texto }),
      signal: AbortSignal.timeout(limiteMs), cache: "no-store",
    });
    if (!r.ok) return null;
    const { vetor } = (await r.json()) as { vetor: number[] };
    return Array.isArray(vetor) && vetor.length === 768 ? vetor : null;
  } catch {
    return null;   // serviço fora do ar: a busca continua só pelo texto
  }
}

export type ResultadoTema = {
  modo: ModoBusca;
  vetorial: boolean;
  publicacoes: { id: string; titulo: string; ano: number; area: string | null; doi: string | null; afinidade: number | null }[];
  pesquisadores: { id: string; nome: string; detalhe: string; n: number; exemplo: string }[];
  instituicoes: { id: string; nome: string; detalhe: string; n: number }[];
  programas: { id: string; nome: string; detalhe: string; n: number }[];
};

/** `sq` = só publicações em revistas com Qualis (filtro do site, D-035). */
export async function buscaPorTema(texto: string, modoPedido: ModoBusca = "hibrido", sq = false): Promise<ResultadoTema> {
  const vetor = modoPedido === "texto" ? null : await embedConsulta(texto);
  const modo: ModoBusca = vetor ? modoPedido : "texto";
  const usaVetor = modo !== "texto";
  const usaTexto = modo !== "vetor";
  const cliente = await pool.connect();
  try {
    await cliente.query("BEGIN");
    await cliente.query("SET LOCAL hnsw.ef_search = 120");
    // Busca filtrada no HNSW (pgvector >= 0.8): continua varrendo o índice até achar vizinhos que passam no filtro.
    await cliente.query("SET LOCAL hnsw.iterative_scan = relaxed_order");
    // $1 = vetor (ou null), $2 = texto, $3/$4 = usa vetor/texto, $5 = só revistas com Qualis
    await cliente.query(
      `CREATE TEMP TABLE _tema ON COMMIT DROP AS
       -- Balanceado por idioma: o modelo multilíngue ainda prefere textos no idioma da consulta, então buscamos
       -- vizinhos separadamente entre publicações em inglês e nas demais línguas e intercalamos pelos rankings.
       WITH vec AS (
         SELECT work_id, row_number() OVER (PARTITION BY ingles ORDER BY d) AS r, 1 - d AS sim FROM (
           (SELECT e.work_id, e.embedding <=> $1::halfvec AS d, true AS ingles FROM work_embeddings e
             WHERE $3 AND e.work_id IN (SELECT id FROM works WHERE language = 'en')
               AND (NOT $5 OR e.work_id IN (SELECT work_id FROM mv_work_qualis))
             ORDER BY e.embedding <=> $1::halfvec LIMIT ${CANDIDATOS / 2})
           UNION ALL
           (SELECT e.work_id, e.embedding <=> $1::halfvec AS d, false FROM work_embeddings e
             WHERE $3 AND e.work_id IN (SELECT id FROM works WHERE language IS DISTINCT FROM 'en')
               AND (NOT $5 OR e.work_id IN (SELECT work_id FROM mv_work_qualis))
             ORDER BY e.embedding <=> $1::halfvec LIMIT ${CANDIDATOS / 2})
         ) x
       ), txt AS (
         SELECT work_id, row_number() OVER (ORDER BY peso DESC, work_id) AS r FROM (
           SELECT id AS work_id, 2 AS peso FROM works WHERE $4 AND lower(f_unaccent(title)) LIKE '%' || lower(f_unaccent($2)) || '%'
           UNION
           SELECT work_id, 1 FROM work_keywords WHERE $4 AND lower(f_unaccent(keyword)) LIKE '%' || lower(f_unaccent($2)) || '%'
         ) t WHERE NOT $5 OR t.work_id IN (SELECT work_id FROM mv_work_qualis) LIMIT ${CANDIDATOS}
       )
       SELECT work_id, sum(1.0 / (${K_RRF} + r)) AS s, max(sim) AS sim
         FROM (SELECT work_id, r, sim FROM vec UNION ALL SELECT work_id, r, NULL::float FROM txt) u
        GROUP BY work_id`,
      [vetor ?? "[" + Array(768).fill(0).join(",") + "]", texto, usaVetor, usaTexto, sq],
    );
    const [pub, pesq, inst, prog] = await Promise.all([
      cliente.query(
        `SELECT w.id, w.title AS titulo, w.year AS ano, w.primary_field AS area, w.doi, round(t.sim::numeric, 3)::float AS afinidade
           FROM _tema t JOIN works w ON w.id = t.work_id ORDER BY t.s DESC LIMIT 8`),
      cliente.query(
        `WITH p AS (
           SELECT a.researcher_id, sum(t.s) AS s, count(DISTINCT t.work_id) AS n,
                  (array_agg(w.title ORDER BY t.s DESC))[1] AS exemplo
             FROM _tema t JOIN work_authorships a ON a.work_id = t.work_id AND a.researcher_id IS NOT NULL
             JOIN works w ON w.id = t.work_id
            GROUP BY 1)
         SELECT r.id, r.display_name AS nome, concat_ws(' · ', i.acronym, i.uf) AS detalhe, p.n::int, p.exemplo
           FROM p JOIN researchers r ON r.id = p.researcher_id LEFT JOIN institutions i ON i.id = r.main_institution_id
          WHERE NOT r.is_hidden ORDER BY p.s DESC, p.n DESC LIMIT 8`),
      cliente.query(
        `SELECT i.id, i.name AS nome, concat_ws(' · ', i.acronym, i.uf) AS detalhe, count(*)::int AS n
           FROM _tema t JOIN mv_work_inst wi ON wi.work_id = t.work_id JOIN institutions i ON i.id = wi.institution_id
          GROUP BY i.id ORDER BY sum(t.s) DESC LIMIT 6`),
      cliente.query(
        `SELECT g.id, g.name AS nome, concat_ws(' · ', g.entity_acronym, g.uf, 'conceito ' || g.grade) AS detalhe, count(DISTINCT t.work_id)::int AS n
           FROM _tema t JOIN work_authorships a ON a.work_id = t.work_id
           JOIN program_faculty f ON f.researcher_id = a.researcher_id JOIN graduate_programs g ON g.id = f.program_id
          GROUP BY g.id ORDER BY sum(t.s) DESC LIMIT 5`),
    ]);
    await cliente.query("COMMIT");
    return { modo, vetorial: !!vetor, publicacoes: pub.rows, pesquisadores: pesq.rows, instituicoes: inst.rows, programas: prog.rows };
  } catch (e) {
    await cliente.query("ROLLBACK").catch(() => {});
    throw e;
  } finally {
    cliente.release();
  }
}
