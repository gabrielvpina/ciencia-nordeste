"use client";
// Tela inicial: busca em destaque no topo; abaixo, um painel em três colunas — áreas | mapa | seletores e filtros do mapa.
import { useEffect, useMemo, useRef, useState } from "react";
import { AREAS_ORDEM, rotuloArea } from "@/components/mapa/areas";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import type { DadosMapa, ModoMapa, PontoInst } from "@/components/mapa/tipos";
import type { ResultadoBusca } from "@/app/api/busca/route";
import type { ResultadoTema } from "@/lib/vetorial";
import { UFS, fmt } from "@/lib/areas";

type Resumo = { pesquisadores: string; works: string; instituicoes: string; programas: string; teses: string };
const ANOS = [2022, 2023, 2024, 2025, 2026];
const MODOS: { id: Exclude<ModoMapa, "rede">; rotulo: string; titulo: string; legenda: string }[] = [
  { id: "densidade", rotulo: "Produção", titulo: "Publicações por instituição", legenda: "Altura da barra = publicações (escala de raiz, para as menores não sumirem). Número = posição no ranking. Anel tracejado = tem subunidades: clique para ver." },
  { id: "ligacoes", rotulo: "Colaboração", titulo: "Coautoria entre instituições do Nordeste", legenda: "Espessura do arco = publicações em comum (as 160 ligações mais fortes). Passe o mouse numa instituição para isolar a rede dela." },
  { id: "areas", rotulo: "Áreas", titulo: "Produção de cada estado por área", legenda: "Cada rosca divide a produção do estado entre as áreas. Escolha uma área à esquerda para colorir os estados por ela." },
];
const EXEMPLOS = ["dengue e arboviroses", "UFPE", "melhoramento genético de caprinos", "saúde bucal", "plantas medicinais da caatinga"];

export default function Inicio({ resumo, inicial }: { resumo: Resumo; inicial: DadosMapa }) {
  const [modo, setModo] = useState<Exclude<ModoMapa, "rede">>("densidade");
  const [uf, setUf] = useState("");
  const [area, setArea] = useState("");
  const [de, setDe] = useState(2022);
  const [ate, setAte] = useState(2026);
  const [dados, setDados] = useState<DadosMapa>(inicial);
  const [carregando, setCarregando] = useState(false);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [destaque, setDestaque] = useState<string | null>(null);
  const [termo, setTermo] = useState("");
  const [res, setRes] = useState<ResultadoBusca | null>(null);
  const [tema, setTema] = useState<ResultadoTema | null>(null);
  const [buscandoTema, setBuscandoTema] = useState(false);
  const primeira = useRef(true);
  const campo = useRef<HTMLInputElement>(null);

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

  // Ranking: só instituições principais (subunidades ficam dentro da principal, como no mapa).
  const { ranking, subunidades, total } = useMemo(() => {
    const ids = new Set(dados.pontos.map((p) => p.id));
    const principais = dados.pontos.filter((p) => !(p.pai && ids.has(p.pai))).sort((a, b) => b.works - a.works);
    const subunidades = new Map<string, PontoInst[]>();
    for (const p of dados.pontos) if (p.pai && ids.has(p.pai)) subunidades.set(p.pai, [...(subunidades.get(p.pai) ?? []), p]);
    return { ranking: principais, subunidades, total: principais.length };
  }, [dados]);
  const areasUf = useMemo(() => {
    const m = new Map<string, number>();
    for (const a of dados.areas ?? []) if (!uf || a.uf === uf) m.set(a.field, (m.get(a.field) ?? 0) + a.works);
    return AREAS_ORDEM.map((f, i) => ({ f, i, n: m.get(f) ?? 0 })).sort((a, b) => b.n - a.n);
  }, [dados, uf]);

  useEffect(() => { if (selecionado && !dados.pontos.some((p) => p.id === selecionado)) setSelecionado(null); }, [dados, selecionado]);
  const sel = selecionado ? ranking.find((p) => p.id === selecionado) : undefined;
  const m = MODOS.find((x) => x.id === modo)!;
  const tudo = de === ANOS[0] && ate === ANOS[ANOS.length - 1];

    const maxArea = Math.max(1, areasUf[0]?.n ?? 1);
  const temNome = res && (res.pesquisadores.length || res.instituicoes.length || res.programas.length);
  const temTema = tema && (tema.pesquisadores.length || tema.publicacoes.length);
  const mostrarResultados = termo.trim().length >= 2;

  return (
    <div className="inicio">
      <section className="hero" aria-labelledby="hero-titulo">
        <h1 id="hero-titulo">Quem pesquisa o quê no Nordeste</h1>
        <p className="hero-sub">Pesquisadores, instituições e programas de pós em ciências da vida nos 9 estados, 2022–2026.</p>
        <div className="busca-grande">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input ref={campo} id="busca" type="search" value={termo} onChange={(e) => setTermo(e.target.value)} autoComplete="off"
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
            <Coluna titulo="Instituições" itens={res?.instituicoes ?? []} href={(id) => `/instituicao/${id}`} onFoco={setDestaque} />
            <Coluna titulo="Programas de pós" itens={res?.programas ?? []} href={(id) => `/programa/${id}`} />
            {(temTema || buscandoTema) && (
              <div className="coluna coluna-tema">
                <h3>Por tema <span className="meta">{buscandoTema ? "buscando…" : tema?.vetorial ? "busca semântica PT/EN" : "só texto"}</span></h3>
                {tema && (
                  <>
                    <ul>{tema.pesquisadores.slice(0, 5).map((p) => (
                      <li key={p.id}><a href={`/pesquisador/${p.id}`}>{p.nome}</a><span className="meta">{p.n} publicaç{p.n > 1 ? "ões" : "ão"} no tema</span></li>
                    ))}</ul>
                    <ul className="pubs">{tema.publicacoes.slice(0, 4).map((w) => (
                      <li key={w.id}>{w.doi ? <a href={`https://doi.org/${w.doi}`} rel="noopener">{w.titulo}</a> : <span>{w.titulo}</span>}
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
      </section>

      <div className="kpis">
        <div className="kpi"><b>{fmt(resumo.pesquisadores)}</b><span>pesquisadores</span></div>
        <div className="kpi"><b>{fmt(resumo.works)}</b><span>publicações</span></div>
        <a className="kpi" href="/instituicoes"><b>{fmt(resumo.instituicoes)}</b><span>instituições →</span></a>
        <a className="kpi" href="/programas"><b>{fmt(resumo.programas)}</b><span>programas de pós →</span></a>
      </div>

      <div className="cockpit">
        <div className="col col-esq">
          <section className="painel-card">
            <h2>Áreas <small>{uf || "Nordeste"} · clique para filtrar</small></h2>
            <ul className="barras-area">
              {areasUf.map(({ f, i, n }) => (
                <li key={f}>
                  <button type="button" className={area === f ? "ativa" : area ? "apagada" : ""} aria-pressed={area === f} onClick={() => setArea(area === f ? "" : f)}>
                    <span className="nome"><i style={{ background: `var(--area-${i})` }} />{rotuloArea(f)}</span>
                    <span className="val">{fmt(n)}</span>
                    <span className="barra"><i style={{ width: `${(100 * n) / maxArea}%`, background: `var(--area-${i})` }} /></span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="painel-card mapa-card" aria-busy={carregando}>
          <div className="mapa-topo">
            <div className="mapa-titulo">
              {m.titulo}
              <small>{fmt(total)} instituições{area ? ` · ${rotuloArea(area)}` : ""}{uf ? ` · ${uf}` : ""} · {de === ate ? de : `${de}–${ate}`}{carregando ? " · atualizando…" : ""}</small>
            </div>
          </div>
          <div className="mapa-palco">
            {sel && (
              <div className="selbar" aria-live="polite">
                <span className="chip-sigla">{(sel.sigla ?? sel.nome).split(",")[0].slice(0, 9)}</span>
                <span className="txt">
                  <b>{sel.nome}</b>
                  <span>{sel.uf} · {fmt(sel.works)} publicações · {ranking.indexOf(sel) + 1}ª posição</span>
                  {subunidades.get(sel.id) && (
                    <span className="subs">Subunidades: {subunidades.get(sel.id)!.map((s, k) => (
                      <a key={s.id} href={`/instituicao/${s.id}`}>{k ? ", " : ""}{s.sigla ?? s.nome} ({fmt(s.works)})</a>
                    ))}</span>
                  )}
                </span>
                <a className="botao" href={`/instituicao/${sel.id}`}>Perfil e rede →</a>
                <button type="button" className="x" onClick={() => setSelecionado(null)} aria-label="Limpar seleção">×</button>
              </div>
            )}
            <MapaNordeste modo={modo} dados={dados} ufAtiva={uf || undefined} areaAtiva={area || undefined}
              selecionado={selecionado} onSelecionar={setSelecionado} destaque={destaque} />
          </div>
        </section>

        <div className="col col-dir">
          <section className="painel-card filtros-mapa" aria-label="Seletores e filtros do mapa">
            <h2>Seletores do mapa</h2>
            <div className="filtro">
              <span className="lbl">Modo</span>
              <div className="grade-seg cols-1" role="tablist" aria-label="Modo do mapa">
                {MODOS.map((x) => (
                  <button key={x.id} role="tab" aria-selected={modo === x.id} className={modo === x.id ? "ativo" : ""} onClick={() => setModo(x.id)}>
                    <b>{x.rotulo}</b><small>{x.titulo}</small>
                  </button>
                ))}
              </div>
            </div>
            <div className="filtro">
              <span className="lbl">Estado</span>
              <div className="grade-seg cols-5" role="group" aria-label="Estado">
                <button className={!uf ? "ativo" : ""} aria-pressed={!uf} onClick={() => setUf("")} title="Todos os estados do Nordeste">Todos</button>
                {UFS.map(([s, n]) => <button key={s} className={uf === s ? "ativo" : ""} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)} title={n}>{s}</button>)}
              </div>
            </div>
            <div className="filtro">
              <span className="lbl">Período <small>{de === ate ? de : `${de}–${ate}`}</small></span>
              <div className={`faixa-anos${de === ANOS[ANOS.length - 1] ? " inicio-no-fim" : ""}`}>
                <div className="fa-trilho" aria-hidden>
                  <i style={{ left: `${(100 * (de - ANOS[0])) / (ANOS.length - 1)}%`, right: `${(100 * (ANOS[ANOS.length - 1] - ate)) / (ANOS.length - 1)}%` }} />
                </div>
                <input type="range" className="fa-inicio" min={ANOS[0]} max={ANOS[ANOS.length - 1]} step={1} value={de}
                  onChange={(e) => setDe(Math.min(Number(e.target.value), ate))} aria-label="Início do período" aria-valuetext={String(de)} />
                <input type="range" className="fa-fim" min={ANOS[0]} max={ANOS[ANOS.length - 1]} step={1} value={ate}
                  onChange={(e) => setAte(Math.max(Number(e.target.value), de))} aria-label="Fim do período" aria-valuetext={String(ate)} />
                <div className="fa-marcas" aria-hidden>{ANOS.map((a) => <span key={a} className={a >= de && a <= ate ? "dentro" : ""}>{a}</span>)}</div>
              </div>
            </div>
            {(uf || area || !tudo) && (
              <button type="button" className="chip chip-limpar" onClick={() => { setUf(""); setArea(""); setDe(ANOS[0]); setAte(ANOS[ANOS.length - 1]); }}>limpar filtros</button>
            )}
            <p className="meta mais"><a href="/instituicoes">Ver todas as instituições →</a></p>
          </section>
        </div>
      </div>
    </div>
  );
}

function Coluna({ titulo, itens, href, onFoco }: { titulo: string; itens: { id: string; nome: string; detalhe: string }[]; href: (id: string) => string; onFoco?: (id: string | null) => void }) {
  if (!itens.length) return null;
  return (
    <div className="coluna">
      <h3>{titulo}</h3>
      <ul>{itens.map((i) => (
        <li key={i.id} onPointerEnter={() => onFoco?.(i.id)} onPointerLeave={() => onFoco?.(null)}>
          <a href={href(i.id)}>{i.nome}</a><span className="meta">{i.detalhe}</span>
        </li>
      ))}</ul>
    </div>
  );
}
