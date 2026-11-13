"use client";
// Instituições: treemap agrupado (por estado ou por tipo) + cards filtráveis. Tudo no navegador (≈190 itens).
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
const PASSO = 24;
const PASSO_CELULAR = 8;   // no celular, menos cartões de cada vez (cada um ocupa a largura toda)

export default function ExplorarInstituicoes({ itens, ufInicial }: { itens: InstItem[]; ufInicial?: string }) {
  const [agrupar, setAgrupar] = useState<Agrupar>("uf");
  const [metrica, setMetrica] = useState<Metrica>("works");
  const [uf, setUf] = useState(ufInicial && NOME_UF[ufInicial] ? ufInicial : "");
  const [fams, setFams] = useState<Set<string>>(new Set());
  const [texto, setTexto] = useState("");
  const [mostrar, setMostrar] = useState(PASSO);
  const { props: dicaProps, dica } = useDica();
  const porId = useMemo(() => new Map(itens.map((i) => [i.id, i])), [itens]);

  const filtrados = useMemo(() => {
    const t = texto.trim().toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
    return itens
      .filter((i) => (!uf || i.uf === uf) && (!fams.size || fams.has(familia(i.tipo).id)))
      .filter((i) => !t || `${i.nome} ${i.sigla ?? ""}`.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").includes(t))
      .sort((a, b) => b[metrica] - a[metrica]);
  }, [itens, uf, fams, texto, metrica]);
  const passo = () => (typeof window !== "undefined" && window.matchMedia("(max-width: 600px)").matches ? PASSO_CELULAR : PASSO);
  useEffect(() => setMostrar(passo()), [uf, fams, texto, metrica]);

  const total = (k: Metrica) => filtrados.reduce((s, i) => s + i[k], 0);
  const alternarFam = (id: string) => setFams((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return (
    <div className="explorar-pagina">
      <header className="pagina-topo">
        <div>
          <h1>Instituições</h1>
          <p className="meta">{fmt(filtrados.length)} instituições com produção ou pós-graduação no recorte · {fmt(total("works"))} publicações · {fmt(total("pesquisadores"))} pesquisadores</p>
        </div>
        <input className="campo filtro-texto" type="search" placeholder="Filtrar por nome ou sigla" value={texto} onChange={(e) => setTexto(e.target.value)} aria-label="Filtrar por nome ou sigla" />
      </header>

      <div className="barra-controles">
        <div className="ctrl"><span className="lbl">Agrupar</span>
          <div className="seg">{([["uf", "Estado"], ["tipo", "Tipo"]] as const).map(([k, r]) => (
            <button key={k} className={agrupar === k ? "ativo" : ""} aria-pressed={agrupar === k} onClick={() => setAgrupar(k)}>{r}</button>
          ))}</div>
        </div>
        <div className="ctrl"><span className="lbl">Tamanho</span>
          <div className="seg">{METRICAS.map((m) => (
            <button key={m.id} className={metrica === m.id ? "ativo" : ""} aria-pressed={metrica === m.id} onClick={() => setMetrica(m.id)}>{m.rotulo}</button>
          ))}</div>
        </div>
        <div className="ctrl"><span className="lbl">Estado</span>
          <div className="chips chips-linha">
            <button className={`chip${!uf ? " chip-ativo" : ""}`} onClick={() => setUf("")}>Todos</button>
            {UFS.map(([s, n]) => <button key={s} title={n} className={`chip${uf === s ? " chip-ativo" : ""}`} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)}>{s}</button>)}
          </div>
        </div>
      </div>

      <div className="chips chips-linha legenda-familias" aria-label="Tipos (clique para filtrar)">
        {FAMILIAS.map((f) => (
          <button key={f.id} className={`chip${fams.has(f.id) ? " chip-ativo" : ""}${fams.size && !fams.has(f.id) ? " chip-apagado" : ""}`} aria-pressed={fams.has(f.id)} onClick={() => alternarFam(f.id)}>
            <i className="ponto" style={{ background: `var(--area-${f.cor})` }} />{f.rotulo}
          </button>
        ))}
        {(fams.size > 0 || uf || texto) && <button className="chip chip-limpar" onClick={() => { setFams(new Set()); setUf(""); setTexto(""); }}>limpar filtros</button>}
      </div>

      <section className="painel-card">
        <Treemap itens={filtrados} metrica={metrica} agrupar={agrupar} dicaProps={dicaProps}
          onGrupo={(g) => (agrupar === "uf" ? setUf(uf === g ? "" : g) : alternarFam(g))} />
      </section>

      <h2 className="secao">{filtrados.length > 0 ? `Ordenadas por ${METRICAS.find((m) => m.id === metrica)!.rotulo.toLowerCase()}` : "Nenhuma instituição com esses filtros"}</h2>
      <div className="grade-cards">
        {filtrados.slice(0, mostrar).map((i) => {
          const f = familia(i.tipo);
          const somaA = i.areas.reduce((s, a) => s + a.n, 0);
          const pai = i.pai ? porId.get(i.pai) : undefined;
          return (
            <a key={i.id} href={`/instituicao/${i.id}`} className="card-inst" style={{ "--cor": `var(--area-${f.cor})` } as React.CSSProperties}>
              <div className="ci-topo">
                <span className="ci-sigla">{(i.sigla ?? i.nome).split(",")[0]}</span>
                <span className="ci-uf" title={NOME_UF[i.uf]}>{i.uf}</span>
              </div>
              <span className="ci-nome">{i.nome}</span>
              <span className="ci-tipo"><i className="ponto" />{f.rotulo}{pai ? ` · subunidade de ${pai.sigla ?? pai.nome}` : ""}</span>
              <dl className="ci-num">
                <div><dt>publicações</dt><dd>{fmt(i.works)}</dd></div>
                <div><dt>pesquisadores</dt><dd>{fmt(i.pesquisadores)}</dd></div>
                <div><dt>programas</dt><dd>{fmt(i.programas)}</dd></div>
              </dl>
              {somaA > 0 && (
                <span className="ci-areas" {...dicaProps(() => ({ titulo: `${i.sigla ?? i.nome}: áreas`, linhas: i.areas.slice(0, 6).map((a) => [rotuloArea(a.f), `${Math.round((100 * a.n) / somaA)}%`] as [string, string]) }))}>
                  {i.areas.map((a) => <i key={a.f} style={{ width: `${(100 * a.n) / somaA}%`, background: `var(--area-${Math.max(0, AREAS_ORDEM.indexOf(a.f))})` }} />)}
                </span>
              )}
            </a>
          );
        })}
      </div>
      {filtrados.length > mostrar && (
        <p className="centro-botao"><button className="botao-sec" onClick={() => setMostrar((n) => n + passo() * 2)}>Mostrar mais ({fmt(filtrados.length - mostrar)} restantes)</button></p>
      )}
      {dica}
    </div>
  );
}

function Treemap({ itens, metrica, agrupar, dicaProps, onGrupo }: {
  itens: InstItem[]; metrica: Metrica; agrupar: Agrupar;
  dicaProps: ReturnType<typeof useDica>["props"]; onGrupo: (g: string) => void;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const [tam, setTam] = useState({ w: 900, h: 480 });
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setTam({ w: el.clientWidth, h: el.clientWidth < 600 ? 420 : 500 }));
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
    <div className="treemap" ref={caixa} style={{ height: tam.h }}>
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
            return (
              <a key={i.id} href={`/instituicao/${i.id}`} className="tm-item"
                style={{ left: r.x - g.r.x, top: r.y - g.r.y, width: r.w, height: r.h, "--cor": `var(--area-${f.cor})` } as React.CSSProperties}
                aria-label={`${i.nome}: ${fmt(i[metrica])} ${unidade}`}
                {...dicaProps(() => ({ titulo: i.nome, sub: [i.sigla, i.uf, f.rotulo].filter(Boolean).join(" · "),
                  linhas: [["Publicações", fmt(i.works)], ["Pesquisadores", fmt(i.pesquisadores)], ["Programas de pós", fmt(i.programas)]], nota: "Clique para abrir o perfil" }))}>
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
