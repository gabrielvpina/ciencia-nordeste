import type { Metadata } from "next";
import Inicio from "@/components/Inicio";
import { q } from "@/lib/db";
import { lerFiltros } from "@/lib/filtros";
import { dadosMapa } from "@/lib/mapa-dados";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Ciência Nordeste — pesquisa em ciências da vida no Nordeste",
  description: "Mapa e busca de pesquisadores, instituições e programas de pós-graduação em saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas no Nordeste.",
};

export default async function Home() {
  const [[resumo], inicial] = await Promise.all([
    q<{ pesquisadores: string; works: string; instituicoes: string; programas: string; teses: string }>(`SELECT * FROM mv_resumo`),
    dadosMapa(lerFiltros({})),
  ]);
  return <Inicio resumo={resumo} inicial={inicial} />;
}
