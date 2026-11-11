import type { Metadata } from "next";
import { redirect } from "next/navigation";
import BuscaGeral from "@/components/BuscaGeral";
import { Estrela } from "@/components/Logo";
import { fmt } from "@/lib/areas";
import { q } from "@/lib/db";
import { soQualis } from "@/lib/qualis-filtro";

// Tela inicial (D-039): busca e dois caminhos — o painel (mapa e filtros, em /painel) e o quiz.
export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Ciência Nordeste — pesquisa em ciências da vida no Nordeste",
  description: "Busque pesquisadores, instituições, programas de pós-graduação e temas em saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas no Nordeste. Explore o painel ou descubra o seu perfil de cientista.",
  alternates: { canonical: "/" },
};

type Resumo = { pesquisadores: string; works: string; works_qualis: string; instituicoes: string; programas: string };

export default async function Inicio({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  // endereços antigos do mapa (/?uf=…, /?area=…) seguem para o painel com os mesmos parâmetros
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(searchParams)) for (const x of [v].flat()) if (x != null) qs.append(k, x);
  if (qs.toString()) redirect(`/painel?${qs}`);

  const sq = soQualis();
  const [r] = await q<Resumo>(`SELECT pesquisadores, works, works_qualis, instituicoes, programas FROM mv_resumo`);
  return (
    <div className="abertura">
      <section className="hero" aria-labelledby="hero-titulo">
        <h1 id="hero-titulo">Quem pesquisa o quê no <b>Nordeste</b> <Estrela lima tamanho={22} /></h1>
        <p className="hero-sub">Pesquisadores, instituições e programas de pós em ciências da vida nos 9 estados.</p>
        <BuscaGeral soQualis={sq} />
      </section>

      <nav className="caminhos" aria-label="Explorar">
        <a className="caminho caminho-painel" href="/painel">
          <span className="caminho-icone" aria-hidden>
            <svg viewBox="0 0 24 24"><path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" /><path d="M9 4v14M15 6v14" /></svg>
          </span>
          <b>Ver o painel</b>
          <span>Mapa das instituições, áreas, colaboração e produção por ano, com filtros por estado e período.</span>
        </a>
        <a className="caminho caminho-quiz" href="/quiz">
          <span className="caminho-icone" aria-hidden>?</span>
          <b>Descobrir meu perfil de cientista</b>
          <span>Dez perguntas rápidas: o seu título de cientista e quem no Nordeste pesquisa como você.</span>
        </a>
      </nav>

      {r && (
        <ul className="numeros" aria-label="A base em números">
          <li><b>{fmt(r.pesquisadores)}</b>pesquisadores</li>
          <li><b>{fmt(sq ? r.works_qualis : r.works)}</b>{sq ? "publicações com Qualis" : "publicações"}</li>
          <li><b>{fmt(r.instituicoes)}</b>instituições</li>
          <li><b>{fmt(r.programas)}</b>programas de pós</li>
        </ul>
      )}
    </div>
  );
}
