// GET /api/quiz/instituicoes?q= — sugestões de instituições do NE para o cadastro do quiz (nome, sigla, município/UF).
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const termo = (new URL(req.url).searchParams.get("q") ?? "").trim().slice(0, 100);
  if (termo.length < 2) return Response.json([]);
  const r = await q<{ id: string; nome: string; sigla: string | null; uf: string; municipio: string | null }>(
    `SELECT i.id, i.name AS nome, i.acronym AS sigla, i.uf, m.name AS municipio
       FROM institutions i JOIN mv_instituicao_stats s ON s.institution_id = i.id
       LEFT JOIN municipalities m ON m.ibge_code = i.municipality_ibge
      WHERE (s.works > 0 OR s.programas > 0)
        AND (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1))
             OR lower(f_unaccent(i.name)) LIKE '%' || lower(f_unaccent($1)) || '%'
             OR lower(f_unaccent(i.name)) % lower(f_unaccent($1)))
      ORDER BY (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1))) DESC,
               (lower(f_unaccent(i.name)) LIKE lower(f_unaccent($1)) || '%') DESC, s.works DESC LIMIT 8`, [termo]);
  return Response.json(r, { headers: { "cache-control": "public, max-age=600" } });
}
