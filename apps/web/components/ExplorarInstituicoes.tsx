"use client";
// Instituições (D-048): treemap agrupado (por estado ou por tipo) à esquerda e lista ordenável à direita, com destaque
// cruzado (passar o mouse numa linha realça o retângulo e vice-versa). Tudo no navegador (≈190 itens).
// Desktop: numa tela, a lista rola por dentro. Celular: o treemap fica recolhido e a lista vem em partes.
import { useEffect, useMemo, useRef, useState } from "react";
import { AREAS_ORDEM, rotuloArea } from "@/components/mapa/areas";
import { useDica } from "@/components/Dica";
import { UFS, fmt } from "@/lib/areas";
import { squarify, type Ret } from "@/lib/treemap";

export type InstItem = {
  id: string; nome: string; sigla: string | null; uf: string; tipo: string; works: number; pesquisadores: number; programas: number;
  pai: string | null; areas: { f: string; n: number }[];
};
type Metrica = "works" | "pesquisadores" | "programas";
type Agrupar = "uf" | "tipo";

// Tipos agrupados em 6 famílias, cada uma com uma cor categórica (as mesmas variáveis --area-N do mapa).
const FAMILIAS: { id: string; rotulo: string; cor: number; tipos: string[] }[] = [
  { id: "univ", rotulo: "Universidades", cor: 0, tipos: ["universidade"] },
  { id: "fac", rotulo: "Faculdades e centros universitários", cor: 2, tipos: ["centro_universitario", "faculdade", "ensino"] },
  { id: "if", rotulo: "Institutos federais", cor: 6, tipos: ["instituto_federal", "cefet"] },
  { id: "saude", rotulo: "Hospitais e saúde", cor: 3, tipos: ["hospital_saude"] },
  { id: "pesq", rotulo: "Institutos de pesquisa", cor: 4, tipos: ["instituto_pesquisa"] },
  { id: "outros", rotulo: "Governo e outros", cor: 9, tipos: [] },
];
const familia = (tipo: string) => FAMILIAS.find((f) => f.tipos.includes(tipo)) ?? FAMILIAS[FAMILIAS.length - 1];
const METRICAS: { id: Metrica; rotulo: string }[] = [
  { id: "works", rotulo: "Publicações" }, { id: "pesquisadores", rotulo: "Pesquisadores" }, { id: "programas", rotulo: "Programas de pós" },
];
const NOME_UF = Object.fromEntries(UFS);
const PASSO_CELULAR = 25;
type Ordem = Metrica | "nome";

export default function ExplorarInstituicoes({ itens, ufInicial }: { itens: InstItem[]; ufInicial?: string }) {
  const [agrupar, setAgrupar] = useState<Agrupar>("uf");
  const [metrica, setMetrica] = useState<Metrica>("works");
  const [ordem, setOrdem] = useState<Ordem>("works");
  const [uf, setUf] = useState(ufInicial && NOME_UF[ufInicial] ? ufInicial : "");
  const [fams, setFams] = useState<Set<string>>(new Set());
  const [texto, setTexto] = useState("");
  const [destaque, setDestaque] = useState<string | null>(null);
  const [visao, setVisao] = useState(true);          // no celular começa recolhida
  const [limite, setLimite] = useState(Infinity);    // no celular, a lista vem em partes
  const { props: dicaProps, dica } = useDica();
  const porId = useMemo(() => new Map(itens.map((i) => [i.id, i])), [itens]);
  useEffect(() => {
    if (window.matchMedia("(max-width: 899px)").matches) { setVisao(false); setLimite(PASSO_CELULAR); }
  }, []);
  // o tamanho dos retângulos também ordena a lista
  const escolherMetrica = (m: Metrica) => { setMetrica(m); setOrdem(m); };

  const filtrados = useMemo(() => {
    const t = texto.trim().toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
    return itens
      .filter((i) => (!uf || i.uf === uf) && (!fams.size || fams.has(familia(i.tipo).id)))
      .filter((i) => !t || `${i.nome} ${i.sigla ?? ""}`.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").includes(t));
  }, [itens, uf, fams, texto]);
  const ordenados = useMemo(() => [...filtrados].sort(ordem === "nome"
    ? (a, b) => (a.sigla ?? a.nome).localeCompare(b.sigla ?? b.nome, "pt-BR")
    : (a, b) => b[ordem] - a[ordem]), [filtrados, ordem]);
  useEffect(() => setLimite((l) => (l === Infinity ? l : PASSO_CELULAR)), [uf, fams, texto, ordem]);

  const total = (k: Metrica) => filtrados.reduce((s, i) => s + i[k], 0);
  const alternarFam = (id: string) => setFams((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const maxOrdem = Math.max(1, ...filtrados.map((i) => i[ordem === "nome" ? "works" : ordem]));
  const algumFiltro = fams.size > 0 || uf || texto;
  const limpar = () => { setFams(new Set()); setUf(""); setTexto(""); };

  return (
    <div className="lp">
      <header className="lp-topo">
        <div className="lp-titulo">
          <h1>Instituições</h1>
          <p className="meta">{fmt(filtrados.length)} instituições · {fmt(total("works"))} publicações · {fmt(total("pesquisadores"))} pesquisadores</p>
        </div>
        <input className="campo lp-busca" type="search" placeholder="Buscar por nome ou sigla" value={texto} onChange={(e) => setTexto(e.target.value)} aria-label="Buscar instituição por nome ou sigla" />
        <div className="lp-filtros">
          <div className="chips chips-linha" role="group" aria-label="Estado">
            <button className={`chip${!uf ? " chip-ativo" : ""}`} aria-pressed={!uf} onClick={() => setUf("")}>Todos</button>
            {UFS.map(([s, n]) => <button key={s} title={n} className={`chip${uf === s ? " chip-ativo" : ""}`} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)}>{s}</button>)}
          </div>
          <div className="chips chips-linha legenda-familias" role="group" aria-label="Tipo de instituição">
            {FAMILIAS.map((f) => (
              <button key={f.id} className={`chip${fams.has(f.id) ? " chip-ativo" : ""}${fams.size && !fams.has(f.id) ? " chip-apagado" : ""}`} aria-pressed={fams.has(f.id)} onClick={() => alternarFam(f.id)}>
                <i className="ponto" style={{ background: `var(--area-${f.cor})` }} />{f.rotulo}
              </button>
            ))}
          </div>
          {algumFiltro && <button className="chip chip-limpar" onClick={limpar}>limpar filtros</button>}
        </div>
      </header>

      <div className="lp-corpo">
        <section className="painel-card lp-visao li-visao" aria-labelledby="li-visao-titulo">
          <div className="li-visao-topo">
            <button type="button" className="lp-visao-botao" aria-expanded={visao} onClick={() => setVisao(!visao)}>
              <span id="li-visao-titulo">Visão geral</span>
              <span className="lp-visao-seta" aria-hidden>{visao ? "−" : "+"}</span>
            </button>
            {visao && (
              <div className="li-seletores">
                <div className="seg" role="group" aria-label="Agrupar">{([["uf", "Estado"], ["tipo", "Tipo"]] as const).map(([k, r]) => (
                  <button key={k} className={agrupar === k ? "ativo" : ""} aria-pressed={agrupar === k} onClick={() => setAgrupar(k)}>{r}</button>
                ))}</div>
                <div className="seg" role="group" aria-label="Tamanho dos retângulos">{METRICAS.map((m) => (
                  <button key={m.id} className={metrica === m.id ? "ativo" : ""} aria-pressed={metrica === m.id} onClick={() => escolherMetrica(m.id)}>{m.id === "programas" ? "Programas" : m.rotulo}</button>
                ))}</div>
              </div>
            )}
          </div>
          {visao && <Treemap itens={filtrados} metrica={metrica} agrupar={agrupar} dicaProps={dicaProps} destaque={destaque} onDestaque={setDestaque}
            onGrupo={(g) => (agrupar === "uf" ? setUf(uf === g ? "" : g) : alternarFam(g))} />}
        </section>

        <section className="painel-card lp-lista" aria-label="Lista de instituições">
          <div className="lp-lista-topo">
            <h2>{filtrados.length ? `${fmt(filtrados.length)} instituições` : "Nenhuma instituição com esses filtros"}</h2>
            <label className="lp-sel">Ordenar
              <select value={ordem} onChange={(e) => setOrdem(e.target.value as Ordem)}>
                {METRICAS.map((m) => <option key={m.id} value={m.id}>{m.rotulo}</option>)}<option value="nome">Sigla</option>
              </select>
            </label>
          </div>
          <div className="li-cab" aria-hidden>
            <span>Instituição</span><span className="num">Publicações</span><span className="num">Pesquis.</span><span className="num">Progr.</span><span>Áreas</span>
          </div>
          <div className="lp-rolagem">
            <ul className="lp-linhas">
              {ordenados.slice(0, limite).map((i, k) => {
                const f = familia(i.tipo);
                const somaA = i.areas.reduce((s, a) => s + a.n, 0);
                const pai = i.pai ? porId.get(i.pai) : undefined;
                const v = i[ordem === "nome" ? "works" : ordem];
                return (
                  <li key={i.id} onPointerEnter={() => setDestaque(i.id)} onPointerLeave={() => setDestaque(null)}>
                    <a className={`lp-linha inst${destaque === i.id ? " on" : ""}`} href={`/instituicao/${i.id}`} onFocus={() => setDestaque(i.id)} onBlur={() => setDestaque(null)}>
                      <span className="li-pos">{ordem === "nome" ? "" : k + 1}</span>
                      <span className="lp-nome"><b><i className="ponto" style={{ background: `var(--area-${f.cor})` }} title={f.rotulo} />{(i.sigla ?? i.nome).split(",")[0]}<em>{i.uf}</em></b>
                        <small>{i.nome}{pai ? ` · subunidade de ${pai.sigla ?? pai.nome}` : ""}</small></span>
                      <span className="lp-num li-pub"><b>{fmt(i.works)}</b><small className="li-rot"> publ.</small>
                        {ordem !== "nome" && <i className="li-barra"><b style={{ width: `${(100 * v) / maxOrdem}%` }} /></i>}</span>
                      <span className="lp-num">{fmt(i.pesquisadores)}<small className="li-rot"> pesq.</small></span>
                      <span className="lp-num">{fmt(i.programas)}<small className="li-rot"> progr.</small></span>
                      <span className="li-areas" title={i.areas.slice(0, 4).map((a) => `${rotuloArea(a.f)} ${Math.round((100 * a.n) / Math.max(1, somaA))}%`).join(" · ")}>
                        {somaA > 0 && i.areas.map((a) => <i key={a.f} style={{ width: `${(100 * a.n) / somaA}%`, background: `var(--area-${Math.max(0, AREAS_ORDEM.indexOf(a.f))})` }} />)}
                      </span>
                    </a>
                  </li>
                );
              })}
            </ul>
            {ordenados.length > limite && (
              <p className="centro-botao"><button className="botao-sec" onClick={() => setLimite((n) => n + PASSO_CELULAR)}>Mostrar mais ({fmt(ordenados.length - limite)} restantes)</button></p>
            )}
            {!ordenados.length && algumFiltro && <p className="res3-vazio">Tente outra sigla ou <button type="button" className="chip" onClick={limpar}>limpe os filtros</button></p>}
          </div>
        </section>
      </div>
      {dica}
    </div>
  );
}

function Treemap({ itens, metrica, agrupar, dicaProps, onGrupo, destaque, onDestaque }: {
  itens: InstItem[]; metrica: Metrica; agrupar: Agrupar;
  dicaProps: ReturnType<typeof useDica>["props"]; onGrupo: (g: string) => void;
  destaque: string | null; onDestaque: (id: string | null) => void;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const [tam, setTam] = useState({ w: 900, h: 480 });
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    // a altura vem do CSS (preenche o card no desktop; fixa no celular)
    const ro = new ResizeObserver(() => setTam({ w: el.clientWidth, h: Math.max(240, el.clientHeight) }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const grupos = useMemo(() => {
    const m = new Map<string, InstItem[]>();
    for (const i of itens) {
      if (i[metrica] <= 0) continue;
      const k = agrupar === "uf" ? i.uf : familia(i.tipo).id;
      m.set(k, [...(m.get(k) ?? []), i]);
    }
    const lista = [...m.entries()].map(([k, is]) => ({
      k, rotulo: agrupar === "uf" ? NOME_UF[k] ?? k : FAMILIAS.find((f) => f.id === k)!.rotulo, itens: is, soma: is.reduce((s, i) => s + i[metrica], 0),
    }));
    const rets = squarify(lista.map((g) => g.soma), { x: 0, y: 0, w: tam.w, h: tam.h });
    return lista.map((g, n) => {
      const r = rets[n];
      const dentro: Ret = { x: r.x + 3, y: r.y + 24, w: Math.max(0, r.w - 6), h: Math.max(0, r.h - 27) };
      const filhos = squarify(g.itens.map((i) => i[metrica]), dentro);
      return { ...g, r, filhos };
    });
  }, [itens, metrica, agrupar, tam]);
  const unidade = METRICAS.find((m) => m.id === metrica)!.rotulo.toLowerCase();

  return (
    <div className="treemap" ref={caixa}>
      {grupos.length === 0 && <p className="meta centro">Nada a mostrar.</p>}
      {grupos.map((g) => (
        <div key={g.k} className="tm-grupo" style={{ left: g.r.x, top: g.r.y, width: g.r.w, height: g.r.h }}>
          <button className="tm-rotulo" onClick={() => onGrupo(g.k)} title={`Filtrar: ${g.rotulo}`}>
            {g.r.w > 90 ? g.rotulo : g.k} <span>{fmt(g.soma)}</span>
          </button>
          {g.itens.map((i, n) => {
            const r = g.filhos[n];
            if (!r || r.w < 1 || r.h < 1) return null;
            const f = familia(i.tipo);
            const rotulo = (i.sigla ?? i.nome).split(",")[0];
            const dp = dicaProps(() => ({ titulo: i.nome, sub: [i.sigla, i.uf, f.rotulo].filter(Boolean).join(" · "),
              linhas: [["Publicações", fmt(i.works)], ["Pesquisadores", fmt(i.pesquisadores)], ["Programas de pós", fmt(i.programas)]], nota: "Clique para abrir o perfil" }));
            return (
              <a key={i.id} href={`/instituicao/${i.id}`} className={`tm-item${destaque === i.id ? " on" : ""}`}
                {...dp}
                onPointerEnter={(e) => { dp.onPointerEnter(e); onDestaque(i.id); }} onPointerLeave={(e) => { dp.onPointerLeave(e); onDestaque(null); }}
                style={{ left: r.x - g.r.x, top: r.y - g.r.y, width: r.w, height: r.h, "--cor": `var(--area-${f.cor})` } as React.CSSProperties}
                aria-label={`${i.nome}: ${fmt(i[metrica])} ${unidade}`}>
                {r.w > 34 && r.h > 18 && <span className="tm-sigla">{rotulo.length * 7 > r.w ? rotulo.slice(0, Math.max(2, Math.floor(r.w / 8))) : rotulo}</span>}
                {r.w > 50 && r.h > 36 && <span className="tm-val">{fmt(i[metrica])}</span>}
              </a>
            );
          })}
        </div>
      ))}
    </div>
  );
}
