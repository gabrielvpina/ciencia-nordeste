import { q } from "@/lib/db";
import { POR_ARQUIVO, site, urlset, xml } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { n: string } }) {
  const n = Number(params.n);
  if (!Number.isInteger(n) || n < 0) return new Response("not found", { status: 404 });
  const s = site();
  if (n === 0) {
    const inst = await q<{ id: string }>(`SELECT institution_id AS id FROM mv_instituicao_stats WHERE works > 0 OR programas > 0`);
    const prog = await q<{ id: string }>(`SELECT id FROM graduate_programs`);
    return xml(urlset([
      ...["", "/instituicoes", "/programas", "/mapa", "/sobre"].map((p) => `${s}${p}`),
      ...inst.map((i) => `${s}/instituicao/${i.id}`),
      ...prog.map((p) => `${s}/programa/${p.id}`),
    ]));
  }
  const pesq = await q<{ id: string }>(
    `SELECT id FROM mv_pesquisador_busca WHERE works > 0 OR is_capes_faculty ORDER BY id LIMIT $1 OFFSET $2`, [POR_ARQUIVO, (n - 1) * POR_ARQUIVO]);
  if (pesq.length === 0) return new Response("not found", { status: 404 });
  return xml(urlset(pesq.map((p) => `${s}/pesquisador/${p.id}`)));
}
