// Rede de coautoria (D-046): quem publica com quem.
// - pesquisador: a pessoa no centro e os coautores mais frequentes em volta; as linhas entre coautores mostram
//   quem também publica junto (nas publicações da base inteira, não só nas da pessoa), revelando os grupos.
// - programa: os docentes do último ano-base e a coautoria entre eles (colaboração interna).
// Calculada direto de work_authorships (a tabela coauthorships não foi recalculada na última carga).
import { q } from "@/lib/db";
import { juntaQualis } from "@/lib/qualis-filtro";

export type NoCoautoria = { id: string; nome: string; n: number; grupo: string; detalhe: string };
export type RedeCoautoria = { centro: { id: string; nome: string; n: number } | null; nos: NoCoautoria[]; arestas: { a: string; b: string; n: number }[] };

const MAX_COAUTORES = 30;

/** Ligações entre os `ids` (pares que assinam juntos pelo menos uma publicação). */
async function arestasEntre(ids: string[], sq: boolean) {
  if (ids.length < 2) return [];
  return q<{ a: string; b: string; n: number }>(
    `SELECT x.researcher_id AS a, y.researcher_id AS b, count(DISTINCT x.work_id)::int AS n
       FROM work_authorships x${juntaQualis(sq, "x.work_id")}
       JOIN work_authorships y ON y.work_id = x.work_id AND y.researcher_id > x.researcher_id AND y.researcher_id = ANY($1::uuid[])
      WHERE x.researcher_id = ANY($1::uuid[])
      GROUP BY 1, 2`, [ids]);
}

export async function redePesquisador(id: string, sq: boolean): Promise<RedeCoautoria> {
  const [centro] = await q<{ id: string; nome: string; n: number }>(
    `SELECT r.id, r.display_name AS nome, count(DISTINCT a.work_id)::int AS n
       FROM researchers r LEFT JOIN work_authorships a ON a.researcher_id = r.id${sq ? " AND a.work_id IN (SELECT work_id FROM mv_work_qualis)" : ""}
      WHERE r.id = $1 AND NOT r.is_hidden GROUP BY r.id`, [id]);
  if (!centro) return { centro: null, nos: [], arestas: [] };
  const nos = await q<NoCoautoria>(
    `WITH w AS (SELECT DISTINCT a.work_id FROM work_authorships a${juntaQualis(sq, "a.work_id")} WHERE a.researcher_id = $1),
          c AS (SELECT b.researcher_id AS rid, count(DISTINCT b.work_id)::int AS n FROM work_authorships b JOIN w ON w.work_id = b.work_id
                 WHERE b.researcher_id IS NOT NULL AND b.researcher_id <> $1 GROUP BY 1)
     SELECT r.id, r.display_name AS nome, c.n, coalesce(i.acronym, i.name, 'sem vínculo') AS grupo, concat_ws(' · ', i.acronym, i.uf) AS detalhe
       FROM c JOIN researchers r ON r.id = c.rid AND NOT r.is_hidden LEFT JOIN institutions i ON i.id = r.main_institution_id
      ORDER BY c.n DESC, r.display_name LIMIT ${MAX_COAUTORES}`, [id]);
  const arestas = await arestasEntre(nos.map((x) => x.id), sq);
  return { centro, nos, arestas };
}

export async function redePrograma(id: string, sq: boolean): Promise<RedeCoautoria> {
  const nos = await q<NoCoautoria>(
    `WITH ult AS (SELECT max(base_year) AS ano FROM program_faculty WHERE program_id = $1)
     SELECT DISTINCT ON (r.id) r.id, r.display_name AS nome, coalesce(b.${sq ? "works_qualis" : "works"}, 0)::int AS n,
            initcap(lower(f.category)) AS grupo, concat_ws(' · ', b.instituicao_sigla, b.uf) AS detalhe
       FROM program_faculty f JOIN ult ON f.base_year = ult.ano JOIN researchers r ON r.id = f.researcher_id AND NOT r.is_hidden
       LEFT JOIN mv_pesquisador_busca b ON b.id = r.id
      WHERE f.program_id = $1 ORDER BY r.id`, [id]);
  nos.sort((x, y) => y.n - x.n || x.nome.localeCompare(y.nome));
  const arestas = await arestasEntre(nos.map((x) => x.id), sq);
  return { centro: null, nos, arestas };
}
