"use client";
// Tela inicial: barra lateral de busca + filtros (esquerda) e mapa do Nordeste (direita).
import { useEffect, useMemo, useRef, useState } from "react";
import { AREAS_ORDEM, rotuloArea } from "@/components/mapa/areas";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import type { DadosMapa, ModoMapa } from "@/components/mapa/tipos";
import type { ResultadoBusca } from "@/app/api/busca/route";
import type { ResultadoTema } from "@/lib/vetorial";
import { rotuloArea as nomeArea } from "@/components/mapa/areas";
import { UFS, fmt } from "@/lib/areas";

type Resumo = { pesquisadores: string; works: string; instituicoes: string; programas: string; teses: string };
const ANOS = [2022, 2023, 2024, 2025, 2026];
const MODOS: { id: Exclude<ModoMapa, "rede">; rotulo: string; ajuda: string }[] = [
  { id: "densidade", rotulo: "Produção", ajuda: "Altura da barra = publicações da instituição no período e área escolhidos." },
  { id: "ligacoes", rotulo: "Colaboração", ajuda: "Arcos = publicações em coautoria entre instituições do Nordeste (as 160 ligações mais fortes)." },
  { id: "areas", rotulo: "Áreas", ajuda: "Cada rosca mostra como a produção do estado se divide entre as áreas. Escolha uma área para colorir os estados por ela." },
];

export default function Inicio({ resumo, inicial }: { resumo: Resumo; inicial: DadosMapa }) {
  const [modo, setModo] = useState<Exclude<ModoMapa, "rede">>("densidade");
  const [uf, setUf] = useState("");
  const [area, setArea] = useState("");
  const [de, setDe] = useState(2022);
  const [ate, setAte] = useState(2026);
  const [dados, setDados] = useState<DadosMapa>(inicial);
  const [carregando, setCarregando] = useState(false);
  const [termo, setTermo] = useState("");
  const [res, setRes] = useState<ResultadoBusca | null>(null);
  const [tema, setTema] = useState<ResultadoTema | null>(null);
  const [buscandoTema, setBuscandoTema] = useState(false);
  const primeira = useRef(true);

  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }
    const ctl = new AbortController();
    setCarregando(true);
    const qs = new URLSearchParams({ de: String(de), ate: String(ate), ...(uf && { uf }), ...(area && { area }) });
    fetch(`/api/mapa?${qs}`, { signal: ctl.signal }).then((r) => r.json()).then(setDados).catch(() => {}).finally(() => setCarregando(false));
    return () => ctl.abort();
  }, [uf, area, de, ate]);

  useEffect(() => {
    const q = termo.trim();
    if (q.length < 4) { setTema(null); return; }
    const ctl = new AbortController();
    const t = setTimeout(() => {
      setBuscandoTema(true);
      fetch(`/api/tema?q=${encodeURIComponent(q)}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : null)).then(setTema)
        .catch(() => {}).finally(() => setBuscandoTema(false));
    }, 450);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [termo]);

  useEffect(() => {
    if (termo.trim().length < 2) { setRes(null); return; }
    const ctl = new AbortController();
    const t = setTimeout(() => {
      fetch(`/api/busca?q=${encodeURIComponent(termo)}`, { signal: ctl.signal }).then((r) => r.json()).then(setRes).catch(() => {});
    }, 250);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [termo]);

  const total = useMemo(() => dados.pontos.reduce((s, p) => s + p.works, 0), [dados]);
  const ajuda = MODOS.find((m) => m.id === modo)!.ajuda;
  const vazioNome = res && !res.pesquisadores.length && !res.instituicoes.length && !res.programas.length;
  const temTema = tema && (tema.pesquisadores.length || tema.publicacoes.length);
  const vazio = vazioNome && !temTema && !buscandoTema;

  return (
    <div className="explorar">
      <aside className="painel painel-busca">
        <h1 className="painel-titulo">Ciência Nordeste</h1>
        <p className="meta">Pesquisa em ciências da vida nos nove estados do Nordeste, {resumo ? "2022–2026" : ""}.</p>
        <div className="mini-cards">
          <span><b>{fmt(resumo.pesquisadores)}</b> pesquisadores</span>
          <span><b>{fmt(resumo.works)}</b> publicações</span>
          <a href="/instituicoes"><b>{fmt(resumo.instituicoes)}</b> instituições</a>
          <a href="/programas"><b>{fmt(resumo.programas)}</b> programas</a>
        </div>

        <label className="rotulo-campo" htmlFor="busca">Buscar</label>
        <input id="busca" className="campo" value={termo} onChange={(e) => setTermo(e.target.value)}
          placeholder="Pesquisador, universidade, programa ou tema…" autoComplete="off" />
        {res && (
          <div className="resultados" aria-live="polite">
            {vazio && <p className="meta">Nada encontrado.</p>}
            <Grupo titulo="Pesquisadores" itens={res.pesquisadores} href={(id) => `/pesquisador/${id}`} />
            <Grupo titulo="Instituições" itens={res.instituicoes} href={(id) => `/instituicao/${id}`} />
            <Grupo titulo="Programas de pós-graduação" itens={res.programas} href={(id) => `/programa/${id}`} />
            {(temTema || buscandoTema) && (
              <div className="bloco-tema">
                <h3 className="titulo-tema">
                  Por tema de pesquisa
                  <span className="meta">{buscandoTema ? " · buscando…" : tema?.vetorial ? " · busca semântica (PT/EN)" : " · só texto (serviço semântico indisponível)"}</span>
                </h3>
                {tema && (
                  <>
                    <Grupo titulo="Pesquisadores" href={(id) => `/pesquisador/${id}`}
                      itens={tema.pesquisadores.map((p) => ({ id: p.id, nome: p.nome, detalhe: `${p.detalhe} · ${p.n} publicaç${p.n > 1 ? "ões" : "ão"} no tema` }))} />
                    <div className="grupo">
                      {tema.publicacoes.length > 0 && <h3>Publicações</h3>}
                      <ul>{tema.publicacoes.map((w) => (
                        <li key={w.id}>{w.doi ? <a href={`https://doi.org/${w.doi}`} rel="noopener">{w.titulo}</a> : <span>{w.titulo}</span>}
                          <span className="meta">{w.ano}{w.area ? ` · ${nomeArea(w.area)}` : ""}</span></li>
                      ))}</ul>
                    </div>
                    <Grupo titulo="Instituições" href={(id) => `/instituicao/${id}`}
                      itens={tema.instituicoes.map((i) => ({ id: i.id, nome: i.nome, detalhe: `${i.detalhe} · ${i.n} publicações no tema` }))} />
                    <Grupo titulo="Programas" href={(id) => `/programa/${id}`}
                      itens={tema.programas.map((g) => ({ id: g.id, nome: g.nome, detalhe: g.detalhe }))} />
                  </>
                )}
              </div>
            )}
          </div>
        )}

        <div className="controles">
          <div className="modos" role="tablist" aria-label="Modo do mapa">
            {MODOS.map((m) => (
              <button key={m.id} role="tab" aria-selected={modo === m.id} className={modo === m.id ? "ativo" : ""} onClick={() => setModo(m.id)}>{m.rotulo}</button>
            ))}
          </div>
          <p className="meta ajuda">{ajuda}</p>
          <label className="rotulo-campo">Área
            <select className="campo" value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">Todas as áreas</option>
              {AREAS_ORDEM.map((a) => <option key={a} value={a}>{rotuloArea(a)}</option>)}
            </select>
          </label>
          <label className="rotulo-campo">Estado
            <select className="campo" value={uf} onChange={(e) => setUf(e.target.value)}>
              <option value="">Todo o Nordeste</option>
              {UFS.map(([s, n]) => <option key={s} value={s}>{n}</option>)}
            </select>
          </label>
          <div className="linha-campos">
            <label className="rotulo-campo">De
              <select className="campo" value={de} onChange={(e) => setDe(Number(e.target.value))}>{ANOS.map((a) => <option key={a}>{a}</option>)}</select>
            </label>
            <label className="rotulo-campo">Até
              <select className="campo" value={ate} onChange={(e) => setAte(Number(e.target.value))}>{ANOS.map((a) => <option key={a}>{a}</option>)}</select>
            </label>
          </div>
          {modo === "areas" && (
            <div className="mn-legenda">{AREAS_ORDEM.map((a, i) => <span key={a}><i style={{ background: `var(--area-${i})` }} />{rotuloArea(a)}</span>)}</div>
          )}
        </div>
      </aside>

      <section className="mapa-col" aria-busy={carregando}>
        <div className="mapa-cabecalho">
          <b>{MODOS.find((m) => m.id === modo)!.rotulo}</b>
          <span className="meta">{dados.pontos.length} instituições · {fmt(total)} autorias institucionais (uma publicação conta para cada instituição envolvida){area ? ` · ${rotuloArea(area)}` : ""}{uf ? ` · ${uf}` : ""} · {de}–{ate}{carregando ? " · atualizando…" : ""}</span>
        </div>
        <div className="mapa-area">
          <MapaNordeste modo={modo} dados={dados} ufAtiva={uf || undefined} areaAtiva={area || undefined} />
        </div>
      </section>
    </div>
  );
}

function Grupo({ titulo, itens, href }: { titulo: string; itens: { id: string; nome: string; detalhe: string }[]; href: (id: string) => string }) {
  if (!itens.length) return null;
  return (
    <div className="grupo">
      <h3>{titulo}</h3>
      <ul>{itens.map((i) => <li key={i.id}><a href={href(i.id)}>{i.nome}</a><span className="meta">{i.detalhe}</span></li>)}</ul>
    </div>
  );
}
