import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

export type ResumoInstituicao = {
  id: string; nome: string; sigla: string | null; uf: string; tipo: string; municipio: string | null;
  works: number; pesquisadores: number; programas: number; areas: { f: string; n: number }[];
};

// Resumo de uma instituição para o card "Detalhe da seleção" da tela inicial.
export async function GET(req: Request) {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  if (!UUID.test(id)) return Response.json({ erro: "id inválido" }, { status: 400 });
  const [r] = await q<ResumoInstituicao>(
    `SELECT i.id, i.name AS nome, i.acronym AS sigla, i.uf, i.kind AS tipo, m.name AS municipio,
            COALESCE(s.works, 0)::int AS works, COALESCE(s.pesquisadores, 0)::int AS pesquisadores, COALESCE(s.programas, 0)::int AS programas,
            COALESCE((SELECT json_agg(json_build_object('f', a.primary_field, 'n', a.works) ORDER BY a.works DESC)
                        FROM (SELECT * FROM mv_instituicao_areas WHERE institution_id = i.id ORDER BY works DESC LIMIT 3) a), '[]') AS areas
       FROM institutions i
       LEFT JOIN municipalities m ON m.ibge_code = i.municipality_ibge
       LEFT JOIN mv_instituicao_stats s ON s.institution_id = i.id
      WHERE i.id = $1`, [id]);
  return r ? Response.json(r) : Response.json({ erro: "não encontrada" }, { status: 404 });
}
