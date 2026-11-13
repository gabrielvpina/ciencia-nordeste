import type { Metadata } from "next";
import Painel from "@/components/Painel";
import { q } from "@/lib/db";
import { ANO_MIN, anoMax, lerFiltros } from "@/lib/filtros";
import { dadosMapa } from "@/lib/mapa-dados";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Painel — Ciência Nordeste",
  description: "Mapa interativo da produção científica em ciências da vida no Nordeste: instituições, áreas, colaboração e produção por ano, com filtros por estado, área e período.",
  alternates: { canonical: "/painel" },
};

export default async function PaginaPainel({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  const filtros = lerFiltros(searchParams);   // /painel?q=…&uf=PE&area=…&de=…&ate=… (inclusive os links antigos da tela inicial)
  const sq = soQualis();
  const [[periodo], inicial] = await Promise.all([
    // período real da base (muda sozinho quando uma atualização traz um ano novo)
    q<{ min: number; max: number }>(`SELECT min(year)::int AS min, max(year)::int AS max FROM works WHERE year >= $1 AND year <= $2`, [ANO_MIN, anoMax()]),
    dadosMapa(filtros, sq),
  ]);
  return <Painel filtros={filtros} consultaInicial={(searchParams.q ?? "").trim().slice(0, 200)} inicial={inicial} soQualisInicial={sq} periodo={{ min: periodo?.min ?? ANO_MIN, max: periodo?.max ?? anoMax() }} />;
}
