import type { Metadata } from "next";
import ExplorarProgramas, { type ProgItem } from "@/components/ExplorarProgramas";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Programas de pós-graduação — Ciência Nordeste" };

export default async function Programas({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  const itens = await q<ProgItem>(
    `SELECT g.id, g.name AS nome, g.degree AS nivel, g.evaluation_area AS area, g.grade AS conceito, g.entity_acronym AS sigla, g.uf,
            g.faculty_count_last_year AS docentes, g.institution_id AS inst, i.name AS inst_nome
       FROM graduate_programs g LEFT JOIN institutions i ON i.id = g.institution_id
      ORDER BY g.evaluation_area, g.name`);
  return <ExplorarProgramas itens={itens} ufInicial={searchParams.uf} areaInicial={searchParams.area} />;
}
