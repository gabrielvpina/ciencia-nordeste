import type { DadosMapa, Externo } from "@/components/mapa/tipos";
import { q } from "@/lib/db";
import { ANO_MIN, anoMax, type Filtros } from "@/lib/filtros";

const nomePais = (() => {
  const dn = new Intl.DisplayNames(["pt-BR"], { type: "region" });
  return (iso: string) => { try { return dn.of(iso) ?? iso; } catch { return iso; } };
})();

/** Dados do mapa geral (densidade, ligações, áreas) respeitando os filtros. */
export async function dadosMapa(f: Filtros): Promise<DadosMapa> {
  const args: unknown[] = [f.de, f.ate];
  let condArea = "";
  if (f.area) { args.push(f.area); condArea = ` AND field = $${args.length}`; }
  const pontos = await q<DadosMapa["pontos"][number]>(
    `SELECT i.id, i.name AS nome, i.acronym AS sigla, i.uf, i.latitude AS lat, i.longitude AS lon, i.kind AS tipo, v.parent_id AS pai,
            sum(m.works)::int AS works
       FROM mv_mapa_producao m JOIN institutions i ON i.id = m.institution_id
       LEFT JOIN v_instituicao_vinculo v ON v.institution_id = i.id
      WHERE m.year BETWEEN $1 AND $2${condArea} AND i.latitude IS NOT NULL
      GROUP BY i.id, v.parent_id HAVING sum(m.works) > 0`, args);
  const argsL = [...args];
  let condUf = "";
  if (f.uf) { argsL.push(f.uf); condUf = ` AND (ia.uf = $${argsL.length} OR ib.uf = $${argsL.length})`; }
  const ligacoes = await q<{ a: string; b: string; works: number }>(
    `SELECT m.inst_a AS a, m.inst_b AS b, sum(m.works)::int AS works
       FROM mv_mapa_colaboracao m JOIN institutions ia ON ia.id = m.inst_a JOIN institutions ib ON ib.id = m.inst_b
      WHERE m.year BETWEEN $1 AND $2${condArea}${condUf}
      GROUP BY 1, 2 ORDER BY works DESC LIMIT 160`, argsL);
  const areas = await q<{ uf: string; field: string; works: number }>(
    `SELECT i.uf, m.field, sum(m.works)::int AS works FROM mv_mapa_producao m JOIN institutions i ON i.id = m.institution_id
      WHERE m.year BETWEEN $1 AND $2 AND m.field IS NOT NULL GROUP BY 1, 2`, [f.de, f.ate]);
  // Produção por ano: todos os anos do recorte, para o card mostrar a série inteira.
  const anos = f.uf
    ? await q<{ ano: number; works: number }>(
        `SELECT year AS ano, sum(works)::int AS works FROM mv_uf_ano_area
          WHERE uf = $1 AND year BETWEEN $2 AND $3${f.area ? " AND field = $4" : ""} GROUP BY 1 ORDER BY 1`,
        f.area ? [f.uf, ANO_MIN, anoMax(), f.area] : [f.uf, ANO_MIN, anoMax()])
    : await q<{ ano: number; works: number }>(
        `SELECT year AS ano, count(*)::int AS works FROM works
          WHERE year BETWEEN $1 AND $2${f.area ? " AND primary_field = $3" : ""} GROUP BY 1 ORDER BY 1`,
        f.area ? [ANO_MIN, anoMax(), f.area] : [ANO_MIN, anoMax()]);
  return { pontos: f.uf ? pontos.filter((p) => p.uf === f.uf) : pontos, ligacoes, areas, anos };
}

type Tipo = "pesquisador" | "instituicao" | "programa";

/** Rede de colaboração de uma entidade: origem (instituições), parceiros do NE e coautores externos. */
export async function dadosRede(tipo: Tipo, id: string): Promise<DadosMapa & { resumo: { works: number; parceiros: number; externos: number } }> {
  let origem: string[] = [];
  let parceiros: { id: string; works: number }[] = [];
  let externosBrutos: { pais: string; works: number }[] = [];
  let works = 0;

  if (tipo === "instituicao") {
    origem = [id];
    parceiros = await q(
      `SELECT CASE WHEN inst_a = $1 THEN inst_b ELSE inst_a END AS id, sum(works)::int AS works
         FROM mv_mapa_colaboracao WHERE inst_a = $1 OR inst_b = $1 GROUP BY 1 ORDER BY 2 DESC LIMIT 40`, [id]);
    externosBrutos = await q(`SELECT pais, works FROM mv_inst_externo WHERE institution_id = $1`, [id]);
    [{ works }] = await q<{ works: number }>(`SELECT count(*)::int AS works FROM mv_work_inst WHERE institution_id = $1`, [id]);
  } else {
    // pesquisador: os próprios works; programa: works dos docentes do último ano-base
    const pessoas = tipo === "pesquisador" ? `SELECT $1::uuid AS rid`
      : `SELECT f.researcher_id AS rid FROM program_faculty f JOIN graduate_programs g ON g.id = f.program_id
          WHERE f.program_id = $1 AND f.base_year = (SELECT max(b) FROM unnest(g.base_years) b)`;
    const base = `WITH p AS (${pessoas}), w AS (SELECT DISTINCT a.work_id FROM work_authorships a JOIN p ON p.rid = a.researcher_id)`;
    origem = tipo === "programa"
      ? (await q<{ id: string }>(`SELECT institution_id AS id FROM graduate_programs WHERE id = $1 AND institution_id IS NOT NULL`, [id])).map((r) => r.id)
      : (await q<{ id: string }>(
          `${base} SELECT x AS id, count(*) FROM work_authorships a JOIN p ON p.rid = a.researcher_id, unnest(a.institution_ids) x
            GROUP BY 1 ORDER BY 2 DESC LIMIT 2`, [id])).map((r) => r.id);
    parceiros = await q(
      `${base} SELECT wi.institution_id AS id, count(*)::int AS works FROM mv_work_inst wi JOIN w ON w.work_id = wi.work_id
        WHERE NOT (wi.institution_id = ANY($2::uuid[])) GROUP BY 1 ORDER BY 2 DESC LIMIT 40`, [id, origem]);
    externosBrutos = await q(
      `${base}, e AS (SELECT DISTINCT a.work_id, c AS pais FROM work_authorships a JOIN w ON w.work_id = a.work_id, unnest(a.countries) c WHERE NOT a.is_ne)
       SELECT pais, count(*)::int AS works FROM e GROUP BY 1`, [id]);
    [{ works }] = await q<{ works: number }>(`${base} SELECT count(*)::int AS works FROM w`, [id]);
  }

  const brasil = externosBrutos.find((e) => e.pais === "BR")?.works ?? 0;
  const exterior = externosBrutos.filter((e) => e.pais !== "BR").sort((a, b) => b.works - a.works);
  const externos: Externo[] = [
    ...(brasil ? [{ rotulo: "Brasil, fora do NE", works: brasil, tipo: "brasil" as const }] : []),
    ...exterior.slice(0, 6).map((e) => ({ rotulo: nomePais(e.pais), works: e.works, tipo: "exterior" as const })),
  ];
  const ids = [...new Set([...origem, ...parceiros.map((p) => p.id)])];
  const pontos = ids.length
    ? await q<DadosMapa["pontos"][number]>(
        `SELECT i.id, i.name AS nome, i.acronym AS sigla, i.uf, i.latitude AS lat, i.longitude AS lon, i.kind AS tipo, COALESCE(s.works, 0)::int AS works
           FROM institutions i LEFT JOIN mv_instituicao_stats s ON s.institution_id = i.id
          WHERE i.id = ANY($1::uuid[]) AND i.latitude IS NOT NULL`, [ids])
    : [];
  return {
    pontos,
    rede: { origem, parceiros, externos },
    resumo: { works, parceiros: parceiros.length, externos: exterior.length + (brasil ? 1 : 0) },
  };
}
