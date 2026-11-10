// Visão "Produção" de um pesquisador ou programa: volume por ano × estrato Qualis Periódicos 2021-2024 (D-033).
import type { ReactNode } from "react";
import { BarrasH } from "@/components/Graficos";
import GraficoQualis from "@/components/GraficoQualis";
import { fmt } from "@/lib/areas";
import { EVENTO_QUALIS, FAIXA_SEM, corFaixa, dadosProducao, faixaDe } from "@/lib/qualis";

const pct = (a: number, b: number) => `${b ? Math.round((100 * a) / b) : 0}%`;

export default async function ProducaoEntidade({ tipo, id, nome, abas }: { tipo: "pesquisador" | "programa"; id: string; nome: string; abas: ReactNode }) {
  const d = await dadosProducao(tipo, id);
  const somaFaixa = (i: number) => d.anos.reduce((s, a) => s + a.porFaixa[i], 0);
  const comQualis = d.total - somaFaixa(FAIXA_SEM);
  const quem = tipo === "programa" ? "dos docentes do programa (último ano-base)" : "do pesquisador";

  return (
    <section className="mapa-col">
      <div className="mapa-cabecalho">
        <a href="/" className="voltar">← mapa geral</a>
        {abas}
      </div>
      <div className="producao-area">
        {d.total === 0 ? <p className="meta">Sem publicações do recorte ligadas a {tipo === "programa" ? "este programa" : "este perfil"}.</p> : (
          <>
            <div className="kpis-tres">
              <div className="kpi"><b>{fmt(d.total)}</b><span>publicações {quem}</span></div>
              <div className="kpi"><b>{pct(somaFaixa(0), d.total)}</b><span>em revistas A1–A2 ({fmt(somaFaixa(0))})</span></div>
              <div className="kpi"><b>{pct(comQualis, d.total)}</b><span>em revistas com Qualis ({fmt(comQualis)})</span></div>
            </div>

            <h2>Publicações por ano e estrato Qualis</h2>
            <p className="meta">Altura da coluna = publicações no ano; cores = estrato da revista no Qualis Periódicos {EVENTO_QUALIS}. Passe o mouse para ver os números.</p>
            <GraficoQualis anos={d.anos} titulo={`Publicações por ano e estrato Qualis de ${nome}`} />

            <div className="producao-colunas">
              <div>
                <h2>Distribuição por estrato</h2>
                <BarrasH unidade="publicações" itens={d.porEstrato.map((e) => ({
                  id: e.estrato, rotulo: e.estrato, valor: e.n, cor: corFaixa(faixaDe(e.estrato === "Sem Qualis" ? null : e.estrato)), sub: pct(e.n, d.total),
                }))} />
              </div>
              {d.revistas.length > 0 && (
                <div>
                  <h2>Revistas mais usadas</h2>
                  <BarrasH unidade="publicações" itens={d.revistas.map((r, i) => ({
                    id: `${i}`, rotulo: r.venue, valor: r.n, cor: corFaixa(faixaDe(r.estrato)), sub: r.estrato ? `Qualis ${r.estrato}` : "sem Qualis",
                  }))} />
                </div>
              )}
            </div>

            <p className="meta nota-qualis">
              O Qualis classifica <b>revistas</b>, não artigos nem pessoas: foi feito para a avaliação dos programas de pós-graduação pela CAPES.
              Publicações de 2025 em diante usam a classificação {EVENTO_QUALIS}, a mais recente. &ldquo;Sem Qualis&rdquo; reúne revistas fora da lista,
              anais de eventos, livros e capítulos. Revistas casadas pelo ISSN (impresso ou eletrônico).
            </p>
          </>
        )}
      </div>
    </section>
  );
}
