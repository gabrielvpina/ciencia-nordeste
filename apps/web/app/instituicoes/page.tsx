import type { Metadata } from "next";
import ExplorarInstituicoes, { type InstItem } from "@/components/ExplorarInstituicoes";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Instituições — Ciência Nordeste" };

export default async function Instituicoes({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  // Só instituições com produção no recorte ou com programa de pós (as demais não têm o que mostrar).
  const itens = await q<InstItem>(
    `SELECT i.id, i.name AS nome, i.acronym AS sigla, i.uf, i.kind AS tipo, s.works::int AS works, s.pesquisadores::int AS pesquisadores,
            s.programas::int AS programas, v.parent_id AS pai,
            COALESCE((SELECT json_agg(json_build_object('f', a.primary_field, 'n', a.works) ORDER BY a.works DESC)
                        FROM mv_instituicao_areas a WHERE a.institution_id = i.id), '[]') AS areas
       FROM institutions i JOIN mv_instituicao_stats s ON s.institution_id = i.id
       LEFT JOIN v_instituicao_vinculo v ON v.institution_id = i.id
      WHERE s.works > 0 OR s.programas > 0
      ORDER BY s.works DESC`);
  return <ExplorarInstituicoes itens={itens} ufInicial={searchParams.uf} />;
}
