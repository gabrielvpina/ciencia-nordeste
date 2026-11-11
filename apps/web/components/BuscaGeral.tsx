"use client";
// Busca geral (tela inicial e painel): nomes (pesquisadores, instituições, programas) e temas (busca semântica PT/EN).
// Respeita o filtro "só revistas com Qualis" (D-035). onFoco: destaca no mapa a instituição sob o mouse (só no painel).
import { useEffect, useRef, useState } from "react";
import { rotuloArea } from "@/components/mapa/areas";
import type { ResultadoBusca } from "@/app/api/busca/route";
import type { ResultadoTema } from "@/lib/vetorial";
import { paramQualis } from "@/lib/qualis-cookie";

const EXEMPLOS = ["dengue e arboviroses", "UFPE", "melhoramento genético de caprinos", "saúde bucal", "plantas medicinais da caatinga"];

export default function BuscaGeral({ soQualis, onFoco, autoFoco }: { soQualis: boolean; onFoco?: (id: string | null) => void; autoFoco?: boolean }) {
  const [termo, setTermo] = useState("");
  const [res, setRes] = useState<ResultadoBusca | null>(null);
  const [tema, setTema] = useState<ResultadoTema | null>(null);
  const [buscandoTema, setBuscandoTema] = useState(false);
  const campo = useRef<HTMLInputElement>(null);
  const setDestaque = (id: string | null) => onFoco?.(id);

  useEffect(() => {
    const q = termo.trim();
    if (q.length < 4) { setTema(null); return; }
    const ctl = new AbortController();
    const t = setTimeout(() => {
      setBuscandoTema(true);
      fetch(`/api/tema?q=${encodeURIComponent(q)}&${paramQualis(soQualis)}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : null)).then(setTema)
        .catch(() => {}).finally(() => setBuscandoTema(false));
    }, 450);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [termo, soQualis]);

  useEffect(() => {
    if (termo.trim().length < 2) { setRes(null); return; }
    const ctl = new AbortController();
    const t = setTimeout(() => {
      fetch(`/api/busca?q=${encodeURIComponent(termo)}&${paramQualis(soQualis)}`, { signal: ctl.signal }).then((r) => r.json()).then(setRes).catch(() => {});
    }, 250);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [termo, soQualis]);

  const temNome = res && (res.pesquisadores.length || res.instituicoes.length || res.programas.length);
  const temTema = tema && (tema.pesquisadores.length || tema.publicacoes.length);
  const mostrarResultados = termo.trim().length >= 2;

  return (
    <>
        <div className="busca-grande">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input ref={campo} id="busca" autoFocus={autoFoco} type="search" value={termo} onChange={(e) => setTermo(e.target.value)} autoComplete="off"
            onKeyDown={(e) => { if (e.key === "Escape") setTermo(""); }}
            placeholder="Busque um pesquisador, instituição, programa ou tema de pesquisa" aria-label="Buscar" />
          {termo && <button type="button" className="limpar" onClick={() => { setTermo(""); campo.current?.focus(); }} aria-label="Limpar busca">×</button>}
        </div>
        {!mostrarResultados && (
          <p className="exemplos"><span>Experimente:</span>{EXEMPLOS.map((x) => <button key={x} type="button" className="chip" onClick={() => setTermo(x)}>{x}</button>)}</p>
        )}
        {mostrarResultados && (
          <div className="resultados-grade" aria-live="polite">
            {res && !temNome && !temTema && !buscandoTema && <p className="meta">Nada encontrado para “{termo}”.</p>}
            <Coluna titulo="Pesquisadores" itens={res?.pesquisadores ?? []} href={(id) => `/pesquisador/${id}`} />
            <Coluna titulo="Instituições" itens={res?.instituicoes ?? []} href={(id) => `/instituicao/${id}`} onFoco={onFoco} />
            <Coluna titulo="Programas de pós" itens={res?.programas ?? []} href={(id) => `/programa/${id}`} />
            {(temTema || buscandoTema) && (
              <div className="coluna coluna-tema">
                <h3>Por tema <span className="meta">{buscandoTema ? "buscando…" : tema?.vetorial ? "busca semântica PT/EN" : "só texto"}</span></h3>
                {tema && (
                  <>
                    <ul>{tema.pesquisadores.slice(0, 3).map((p) => (
                      <li key={p.id}><a href={`/pesquisador/${p.id}`}>{p.nome}</a><span className="meta">{p.n} publicaç{p.n > 1 ? "ões" : "ão"} no tema</span></li>
                    ))}</ul>
                    <ul className="pubs">{tema.publicacoes.slice(0, 2).map((w) => (
                      <li key={w.id}>{w.doi ? <a href={`https://doi.org/${w.doi}`} target="_blank" rel="noopener noreferrer">{w.titulo}</a> : <span>{w.titulo}</span>}
                        <span className="meta">{w.ano}{w.area ? ` · ${rotuloArea(w.area)}` : ""}</span></li>
                    ))}</ul>
                    {tema.instituicoes.length > 0 && (
                      <p className="nuvem-mini">{tema.instituicoes.map((i) => (
                        <a key={i.id} href={`/instituicao/${i.id}`} className="chip" onPointerEnter={() => setDestaque(i.id)} onPointerLeave={() => setDestaque(null)}>{i.nome} · {i.n}</a>
                      ))}</p>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}
    </>
  );
}

/** Coluna de resultados: mostra até LIMITE itens; o resto fica atrás de "mais N". */
const LIMITE = 4;
function Coluna({ titulo, itens, href, onFoco }: { titulo: string; itens: { id: string; nome: string; detalhe: string }[]; href: (id: string) => string; onFoco?: (id: string | null) => void }) {
  const [aberta, setAberta] = useState(false);
  if (!itens.length) return null;
  const visiveis = aberta ? itens : itens.slice(0, LIMITE);
  return (
    <div className="coluna">
      <h3>{titulo} <span className="meta">{itens.length}</span></h3>
      <ul>{visiveis.map((i) => (
        <li key={i.id} onPointerEnter={() => onFoco?.(i.id)} onPointerLeave={() => onFoco?.(null)}>
          <a href={href(i.id)}>{i.nome}</a><span className="meta">{i.detalhe}</span>
        </li>
      ))}</ul>
      {itens.length > LIMITE && (
        <button type="button" className="mais-itens" onClick={() => setAberta(!aberta)}>{aberta ? "mostrar menos" : `mais ${itens.length - LIMITE}`}</button>
      )}
    </div>
  );
}
