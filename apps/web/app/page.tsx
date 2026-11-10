import type { Metadata } from "next";
import Inicio from "@/components/Inicio";
import { q } from "@/lib/db";
import { ANO_MIN, anoMax, lerFiltros } from "@/lib/filtros";
import { dadosMapa } from "@/lib/mapa-dados";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Ciência Nordeste — pesquisa em ciências da vida no Nordeste",
  description: "Mapa e busca de pesquisadores, instituições e programas de pós-graduação em saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas no Nordeste.",
};

export default async function Home() {
  const sq = soQualis();
  const [[resumo], [periodo], inicial] = await Promise.all([
    q<{ pesquisadores: string; works: string; works_qualis: string; instituicoes: string; programas: string; teses: string }>(`SELECT * FROM mv_resumo`),
    // período real da base (muda sozinho quando uma atualização traz um ano novo)
    q<{ min: number; max: number }>(`SELECT min(year)::int AS min, max(year)::int AS max FROM works WHERE year >= $1 AND year <= $2`, [ANO_MIN, anoMax()]),
    dadosMapa(lerFiltros({}), sq),
  ]);
  return <Inicio resumo={resumo} inicial={inicial} soQualisInicial={sq} periodo={{ min: periodo?.min ?? ANO_MIN, max: periodo?.max ?? anoMax() }} />;
}
