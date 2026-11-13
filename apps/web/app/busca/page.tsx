import type { Metadata } from "next";
import BuscaGeral from "@/components/BuscaGeral";
import ResultadosBusca from "@/components/ResultadosBusca";
import { pesquisar } from "@/lib/busca";
import { TERMO_MIN } from "@/lib/busca-tipos";
import { soQualis } from "@/lib/qualis-filtro";

// Página de resultados da busca (D-044): /busca?q=…[&tema=1]. A consulta roda uma vez no servidor (com cache).
export const dynamic = "force-dynamic";

export function generateMetadata({ searchParams }: { searchParams: { q?: string } }): Metadata {
  const termo = (searchParams.q ?? "").trim().slice(0, 80);
  return { title: termo ? `“${termo}” — busca — Ciência Nordeste` : "Busca — Ciência Nordeste", robots: { index: false } };
}

export default async function PaginaBusca({ searchParams }: { searchParams: { q?: string; tema?: string } }) {
  const termo = (searchParams.q ?? "").trim();
  const r = termo.length >= TERMO_MIN ? await pesquisar(termo, soQualis(), searchParams.tema === "1") : null;
  return (
    <div className="pagina-busca">
      <BuscaGeral inicial={termo} exemplos={!r} autoFoco={!r} />
      {r ? <ResultadosBusca r={r} /> : <p className="meta">Digite um nome ou tema e aperte <b>Buscar</b>.</p>}
    </div>
  );
}
