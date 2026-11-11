// GET /api/quiz/programas?q=&inst= — sugestões de programas de pós (CAPES) para o cadastro do quiz;
// os da instituição escolhida vêm primeiro (e, sem texto, aparecem todos os dela).
import { q } from "@/lib/db";
import { nomePrograma } from "@/lib/programas";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const termo = (p.get("q") ?? "").trim().slice(0, 100);
  const inst = UUID.test(p.get("inst") ?? "") ? p.get("inst") : null;
  if (termo.length < 2 && !inst) return Response.json([]);
  const r = await q<{ id: string; name: string; sigla: string | null; uf: string; degree: string | null; da_inst: boolean }>(
    `SELECT g.id, g.name, g.entity_acronym AS sigla, g.uf, g.degree, (g.institution_id = $2::uuid) AS da_inst
       FROM graduate_programs g
      WHERE ($1 = '' AND g.institution_id = $2::uuid)
         OR ($1 <> '' AND (lower(f_unaccent(g.name)) LIKE '%' || lower(f_unaccent($1)) || '%' OR lower(f_unaccent(g.name)) % lower(f_unaccent($1))))
      ORDER BY (g.institution_id = $2::uuid) DESC NULLS LAST, similarity(lower(f_unaccent(g.name)), lower(f_unaccent($1))) DESC, g.name LIMIT 10`,
    [termo.length >= 2 ? termo : "", inst]);
  return Response.json(r.map((x) => ({ ...x, nome: nomePrograma(x.name) })), { headers: { "cache-control": "public, max-age=600" } });
}
