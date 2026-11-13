"use client";
// Resultados da busca em três colunas (D-044): nomes (busca por texto) | pesquisadores do tema (busca vetorial) |
// trabalhos (artigos do tema e teses/dissertações). Usado na página /busca e no painel, no lugar dos cards de filtro.
import { useState } from "react";
import { rotuloArea } from "@/components/mapa/areas";
import type { ItemNome, ResultadoPesquisa } from "@/lib/busca-tipos";

type Props = {
  r: ResultadoPesquisa | null;
  carregando?: boolean;
  /** destaca no mapa a instituição sob o mouse (só no painel) */
  onFoco?: (id: string | null) => void;
  /** roda a busca por tema mesmo quando a consulta parece um nome; sem ele, vira link para /busca?…&tema=1 */
  onForcarTema?: () => void;
};

export default function ResultadosBusca({ r, carregando, onFoco, onForcarTema }: Props) {
  if (!r) return <div className="res3" aria-busy="true"><p className="meta res3-aviso">Buscando…</p></div>;
  const { nomes, tema, teses } = r;
  const nNomes = nomes.pesquisadores.length + nomes.instituicoes.length + nomes.programas.length;
  const forcar = onForcarTema
    ? <button type="button" className="chip" onClick={onForcarTema}>buscar “{r.termo}” como tema</button>
    : <a className="chip" href={`/busca?q=${encodeURIComponent(r.termo)}&tema=1`}>buscar “{r.termo}” como tema</a>;
  const pulado = !tema && (
    <p className="res3-vazio">{r.pareceNome ? "A busca parece um nome, então a busca por tema não foi feita." : "Busca curta demais para tema."} {r.pareceNome && forcar}</p>
  );

  return (
    <div className="res3" aria-live="polite" aria-busy={carregando}>
      <section className="res3-col">
        <h3>Nomes <span className="meta">{nNomes ? `${nNomes} encontrados` : "nada encontrado"}</span></h3>
        <Bloco titulo="Pesquisadores" itens={nomes.pesquisadores} href={(id) => `/pesquisador/${id}`} />
        <Bloco titulo="Instituições" itens={nomes.instituicoes} href={(id) => `/instituicao/${id}`} onFoco={onFoco} />
        <Bloco titulo="Programas de pós" itens={nomes.programas} href={(id) => `/programa/${id}`} />
        {!nNomes && <p className="res3-vazio">Nenhum pesquisador, instituição ou programa com esse nome.</p>}
      </section>

      <section className="res3-col res3-tema">
        <h3>Pesquisadores no tema <span className="meta">{tema ? (tema.vetorial ? "busca semântica PT/EN" : "só texto") : ""}</span></h3>
        {pulado}
        {tema && !tema.pesquisadores.length && <p className="res3-vazio">Ninguém encontrado nesse tema.</p>}
        {tema && tema.pesquisadores.length > 0 && (
          <ul className="res3-lista">{tema.pesquisadores.map((p) => (
            <li key={p.id}><a href={`/pesquisador/${p.id}`}>{p.nome}</a>
              <span className="meta">{[p.detalhe, `${p.n} publicaç${p.n > 1 ? "ões" : "ão"} no tema`].filter(Boolean).join(" · ")}</span>
              {p.exemplo && <span className="res3-exemplo">“{p.exemplo}”</span>}
            </li>
          ))}</ul>
        )}
        {tema && tema.instituicoes.length > 0 && (
          <>
            <h4>Instituições no tema</h4>
            <p className="nuvem-mini">{tema.instituicoes.map((i) => (
              <a key={i.id} href={`/instituicao/${i.id}`} className="chip" onPointerEnter={() => onFoco?.(i.id)} onPointerLeave={() => onFoco?.(null)}>{i.detalhe.split(" · ")[0] || i.nome} · {i.n}</a>
            ))}</p>
          </>
        )}
      </section>

      <section className="res3-col">
        <h3>Trabalhos <span className="meta">{tema ? `${tema.publicacoes.length + teses.length}` : ""}</span></h3>
        {pulado}
        {tema && tema.publicacoes.length > 0 && (
          <>
            <h4>Artigos</h4>
            <ul className="res3-lista res3-pubs">{tema.publicacoes.map((w) => (
              <li key={w.id}>{w.doi ? <a href={`https://doi.org/${w.doi}`} target="_blank" rel="noopener noreferrer">{w.titulo}</a> : <span>{w.titulo}</span>}
                <span className="meta">{w.ano}{w.area ? ` · ${rotuloArea(w.area)}` : ""}</span></li>
            ))}</ul>
          </>
        )}
        {teses.length > 0 && (
          <>
            <h4>Teses e dissertações</h4>
            <ul className="res3-lista res3-pubs">{teses.map((t) => (
              <li key={t.id}>{t.url ? <a href={t.url} target="_blank" rel="noopener noreferrer">{t.titulo}</a> : <span>{t.titulo}</span>}
                <span className="meta">{[t.grau, t.ano, t.detalhe].filter(Boolean).join(" · ")}{t.programa && <> · <a href={`/programa/${t.programa}`}>programa</a></>}</span></li>
            ))}</ul>
          </>
        )}
        {tema && !tema.publicacoes.length && !teses.length && <p className="res3-vazio">Nenhum trabalho encontrado nesse tema.</p>}
      </section>
    </div>
  );
}

/** Bloco de nomes: até LIMITE itens; o resto fica atrás de "mais N". */
const LIMITE = 5;
function Bloco({ titulo, itens, href, onFoco }: { titulo: string; itens: ItemNome[]; href: (id: string) => string; onFoco?: (id: string | null) => void }) {
  const [aberto, setAberto] = useState(false);
  if (!itens.length) return null;
  const visiveis = aberto ? itens : itens.slice(0, LIMITE);
  return (
    <>
      <h4>{titulo} <span className="meta">{itens.length}</span></h4>
      <ul className="res3-lista">{visiveis.map((i) => (
        <li key={i.id} onPointerEnter={() => onFoco?.(i.id)} onPointerLeave={() => onFoco?.(null)}>
          <a href={href(i.id)}>{i.nome}</a><span className="meta">{i.detalhe}</span>
        </li>
      ))}</ul>
      {itens.length > LIMITE && (
        <button type="button" className="mais-itens" onClick={() => setAberto(!aberto)}>{aberto ? "mostrar menos" : `mais ${itens.length - LIMITE}`}</button>
      )}
    </>
  );
}
