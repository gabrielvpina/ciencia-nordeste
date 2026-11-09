import { q } from "@/lib/db";

export const dynamic = "force-dynamic";

export type ResultadoBusca = {
  pesquisadores: { id: string; nome: string; detalhe: string }[];
  instituicoes: { id: string; nome: string; detalhe: string }[];
  programas: { id: string; nome: string; detalhe: string }[];
};

// Busca unificada da barra lateral: pesquisador, instituição (nome ou sigla) e programa de pós.
export async function GET(req: Request) {
  const termo = (new URL(req.url).searchParams.get("q") ?? "").trim().slice(0, 100);
  if (termo.length < 2) return Response.json({ pesquisadores: [], instituicoes: [], programas: [] } satisfies ResultadoBusca);
  const [pesquisadores, instituicoes, programas] = await Promise.all([
    termo.length >= 3
      ? q<ResultadoBusca["pesquisadores"][number]>(
          `SELECT id, display_name AS nome, concat_ws(' · ', instituicao_sigla, uf, CASE WHEN works > 0 THEN works || ' publicações' END) AS detalhe
             FROM mv_pesquisador_busca WHERE normalized_name % upper(f_unaccent($1))
            ORDER BY similarity(normalized_name, upper(f_unaccent($1))) DESC, works DESC LIMIT 8`, [termo])
      : Promise.resolve([]),
    q<ResultadoBusca["instituicoes"][number]>(
      `SELECT i.id, i.name AS nome, concat_ws(' · ', i.acronym, i.uf, s.works || ' publicações') AS detalhe
         FROM institutions i JOIN mv_instituicao_stats s ON s.institution_id = i.id
        WHERE (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1)) OR lower(f_unaccent(i.name)) LIKE '%' || lower(f_unaccent($1)) || '%'
               OR lower(f_unaccent(i.name)) % lower(f_unaccent($1)))
          AND (s.works > 0 OR s.programas > 0)
        ORDER BY (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1))) DESC, s.works DESC LIMIT 6`, [termo]),
    q<ResultadoBusca["programas"][number]>(
      `SELECT id, name AS nome, concat_ws(' · ', entity_acronym, uf, 'conceito ' || grade) AS detalhe FROM graduate_programs
        WHERE lower(f_unaccent(name)) LIKE '%' || lower(f_unaccent($1)) || '%' OR upper(entity_acronym) = upper($1)
        ORDER BY grade DESC, name LIMIT 6`, [termo]),
  ]);
  return Response.json({ pesquisadores, instituicoes, programas } satisfies ResultadoBusca);
}
