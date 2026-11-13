"use client";
// Programas de pós (D-048): visão geral (área de avaliação × conceito CAPES, clicável) à esquerda e lista ordenável à direita.
// Desktop: tudo numa tela, a lista rola por dentro. Celular: a visão geral fica recolhida e a lista vem em partes.
import { useEffect, useMemo, useState } from "react";
import { useDica } from "@/components/Dica";
import { UFS, fmt } from "@/lib/areas";
import { CONCEITOS, COR_CONCEITO, TITULO_NIVEL, colunaDe, niveis, nomeArea, nomePrograma } from "@/lib/programas";

export type ProgItem = {
  id: string; nome: string; nivel: string | null; area: string; conceito: string; sigla: string | null; uf: string;
  docentes: number | null; inst: string | null; inst_nome: string | null;
};
type Ordem = "conceito" | "nome" | "docentes" | "inst";
type Agrupar = "" | "area" | "inst" | "uf";

const NOME_UF = Object.fromEntries(UFS);
const NIVEIS: { id: string; rotulo: string; ok: (n: string[]) => boolean }[] = [
  { id: "dout", rotulo: "Com doutorado", ok: (n) => n.includes("D") || n.includes("DP") },
  { id: "mest", rotulo: "Só mestrado acadêmico", ok: (n) => n.length === 1 && n[0] === "M" },
  { id: "prof", rotulo: "Profissional", ok: (n) => n.includes("MP") },
];
const ORDENS: [Ordem, string][] = [["conceito", "Conceito"], ["nome", "Nome"], ["docentes", "Docentes"], ["inst", "Instituição"]];
const AGRUPAR: [Agrupar, string][] = [["", "Nenhum"], ["area", "Área"], ["inst", "Instituição"], ["uf", "Estado"]];
const nota = (c: string) => Number(c) || 0;   // A (novo) e "outros" por último
const sem = (x: string) => x.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
const PASSO_CELULAR = 30;

export default function ExplorarProgramas({ itens, ufInicial, areaInicial }: { itens: ProgItem[]; ufInicial?: string; areaInicial?: string }) {
  const [area, setArea] = useState(areaInicial && itens.some((p) => p.area === areaInicial) ? areaInicial : "");
  const [conceito, setConceito] = useState("");
  const [uf, setUf] = useState(ufInicial && NOME_UF[ufInicial] ? ufInicial : "");
  const [nivel, setNivel] = useState("");
  const [texto, setTexto] = useState("");
  const [ordem, setOrdem] = useState<Ordem>("conceito");
  const [agrupar, setAgrupar] = useState<Agrupar>("");
  const [visao, setVisao] = useState(true);          // no celular começa recolhida
  const [limite, setLimite] = useState(Infinity);    // no celular, a lista vem em partes
  const { props: dicaProps, dica } = useDica();
  useEffect(() => {
    if (window.matchMedia("(max-width: 899px)").matches) { setVisao(false); setLimite(PASSO_CELULAR); }
  }, []);

  // A visão geral respeita estado, nível e busca; área e conceito são escolhidos nela.
  const base = useMemo(() => {
    const t = sem(texto.trim());
    return itens.filter((p) => (!uf || p.uf === uf) && (!nivel || NIVEIS.find((n) => n.id === nivel)!.ok(niveis(p.nivel)))
      && (!t || sem(`${p.nome} ${p.sigla ?? ""} ${p.inst_nome ?? ""}`).includes(t)));
  }, [itens, uf, nivel, texto]);
  const filtrados = useMemo(() => {
    const l = base.filter((p) => (!area || p.area === area) && (!conceito || colunaDe(p.conceito) === conceito));
    const cmp: Record<Ordem, (a: ProgItem, b: ProgItem) => number> = {
      conceito: (a, b) => nota(b.conceito) - nota(a.conceito) || a.nome.localeCompare(b.nome, "pt-BR"),
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR"),
      docentes: (a, b) => (b.docentes ?? 0) - (a.docentes ?? 0),
      inst: (a, b) => (a.sigla ?? "").localeCompare(b.sigla ?? "", "pt-BR") || nota(b.conceito) - nota(a.conceito),
    };
    return l.sort(cmp[ordem]);
  }, [base, area, conceito, ordem]);
  useEffect(() => setLimite((l) => (l === Infinity ? l : PASSO_CELULAR)), [uf, nivel, texto, area, conceito, ordem, agrupar]);

  const matriz = useMemo(() => {
    const m = new Map<string, Map<string, number>>();
    for (const p of base) {
      const linha = m.get(p.area) ?? new Map();
      linha.set(colunaDe(p.conceito), (linha.get(colunaDe(p.conceito)) ?? 0) + 1);
      m.set(p.area, linha);
    }
    const linhas = [...m.entries()].map(([a, l]) => ({ a, l, n: [...l.values()].reduce((s, v) => s + v, 0) })).sort((x, y) => y.n - x.n);
    const max = Math.max(1, ...linhas.flatMap((x) => [...x.l.values()]));
    const porConceito = Object.fromEntries(CONCEITOS.map((c) => [c, linhas.reduce((s, x) => s + (x.l.get(c) ?? 0), 0)]));
    return { linhas, max, porConceito };
  }, [base]);

  // grupos (cabeçalhos dentro da lista), na ordem de tamanho
  const grupos = useMemo(() => {
    const visiveis = filtrados.slice(0, limite);
    if (!agrupar) return [{ k: "", rotulo: "", href: undefined as string | undefined, total: filtrados.length, itens: visiveis }];
    const chave = (p: ProgItem) => (agrupar === "area" ? p.area : agrupar === "uf" ? p.uf : p.inst ?? `s:${p.sigla}`);
    const tot = new Map<string, number>();
    for (const p of filtrados) tot.set(chave(p), (tot.get(chave(p)) ?? 0) + 1);
    const m = new Map<string, { k: string; rotulo: string; href?: string; total: number; itens: ProgItem[] }>();
    for (const p of [...visiveis].sort((a, b) => (tot.get(chave(b)) ?? 0) - (tot.get(chave(a)) ?? 0))) {
      const k = chave(p);
      const g = m.get(k) ?? { k, total: tot.get(k) ?? 0, itens: [],
        rotulo: agrupar === "area" ? nomeArea(p.area) : agrupar === "uf" ? NOME_UF[p.uf] ?? p.uf : p.inst_nome ?? p.sigla ?? "Sem instituição vinculada",
        href: agrupar === "inst" && p.inst ? `/instituicao/${p.inst}` : undefined };
      g.itens.push(p);
      m.set(k, g);
    }
    return [...m.values()];
  }, [filtrados, agrupar, limite]);

  const algumFiltro = area || conceito || uf || nivel || texto;
  const docentes = filtrados.reduce((s, p) => s + (p.docentes ?? 0), 0);
  const limpar = () => { setArea(""); setConceito(""); setUf(""); setNivel(""); setTexto(""); };
  const recorte = [area && nomeArea(area), conceito && `conceito ${conceito === "outros" ? "2 / A" : conceito}`].filter(Boolean).join(" · ");

  return (
    <div className="lp">
      <header className="lp-topo">
        <div className="lp-titulo">
          <h1>Programas de pós-graduação</h1>
          <p className="meta">{fmt(filtrados.length)} programas · {fmt(docentes)} docentes no último ano-base · CAPES Dados Abertos (CC-BY)</p>
        </div>
        <input className="campo lp-busca" type="search" placeholder="Buscar programa ou instituição" value={texto} onChange={(e) => setTexto(e.target.value)} aria-label="Buscar programa ou instituição" />
        <div className="lp-filtros">
          <div className="chips chips-linha" role="group" aria-label="Estado">
            <button className={`chip${!uf ? " chip-ativo" : ""}`} aria-pressed={!uf} onClick={() => setUf("")}>Todos</button>
            {UFS.map(([s, n]) => <button key={s} title={n} className={`chip${uf === s ? " chip-ativo" : ""}`} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)}>{s}</button>)}
          </div>
          <div className="chips chips-linha" role="group" aria-label="Nível">{NIVEIS.map((n) => (
            <button key={n.id} className={`chip${nivel === n.id ? " chip-ativo" : ""}`} aria-pressed={nivel === n.id} onClick={() => setNivel(nivel === n.id ? "" : n.id)}>{n.rotulo}</button>
          ))}</div>
          {algumFiltro && <button className="chip chip-limpar" onClick={limpar}>limpar filtros</button>}
        </div>
      </header>

      <div className="lp-corpo">
        <section className="painel-card lp-visao" aria-labelledby="lp-visao-titulo">
          <button type="button" className="lp-visao-botao" aria-expanded={visao} onClick={() => setVisao(!visao)}>
            <span id="lp-visao-titulo">Área de avaliação × conceito CAPES</span>
            <span className="lp-visao-seta" aria-hidden>{visao ? "−" : "+"}</span>
          </button>
          {visao && (
            <>
              <p className="meta lp-visao-nota">Tamanho = número de programas. Clique numa área, num conceito ou num círculo para filtrar a lista.</p>
              <div className="matriz lp-matriz" role="grid" aria-label="Programas por área de avaliação e conceito">
                <div className="mz-canto" />
                {CONCEITOS.map((c) => (
                  <button key={c} className={`mz-col${conceito === c ? " ativo" : ""}`} aria-pressed={conceito === c} onClick={() => setConceito(conceito === c ? "" : c)}
                    {...dicaProps(() => ({ titulo: c === "outros" ? "Conceito 2 ou A (novo)" : `Conceito ${c}`, linhas: [["Programas", fmt(matriz.porConceito[c])]] }))}>
                    <i style={{ background: COR_CONCEITO[c] }} />{c === "outros" ? "2/A" : c}
                  </button>
                ))}
                <div className="mz-total-cab">total</div>
                {matriz.linhas.map(({ a, l, n }) => (
                  <div key={a} className={`mz-linha${area && area !== a ? " apagada" : ""}`} role="row">
                    <button className={`mz-area${area === a ? " ativo" : ""}`} aria-pressed={area === a} onClick={() => setArea(area === a ? "" : a)}>{nomeArea(a)}</button>
                    {CONCEITOS.map((c) => {
                      const v = l.get(c) ?? 0;
                      const d = v ? 8 + 20 * Math.sqrt(v / matriz.max) : 0;
                      const ativo = (!area || area === a) && (!conceito || conceito === c);
                      return (
                        <button key={c} className={`mz-celula${ativo ? "" : " apagada"}`} disabled={!v} aria-label={`${nomeArea(a)}, conceito ${c}: ${v} programas`}
                          onClick={() => { const mesmo = area === a && conceito === c; setArea(mesmo ? "" : a); setConceito(mesmo ? "" : c); }}
                          {...(v ? dicaProps(() => ({ titulo: nomeArea(a), sub: c === "outros" ? "conceito 2 ou A" : `conceito ${c}`, linhas: [["Programas", fmt(v)]], nota: "Clique para filtrar" })) : {})}>
                          {v > 0 && <span className="mz-bolha" style={{ width: d, height: d, background: COR_CONCEITO[c], color: c === "5" || c === "6" ? "var(--panel)" : undefined }}>{v >= 4 ? v : ""}</span>}
                        </button>
                      );
                    })}
                    <span className="mz-total">{n}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="painel-card lp-lista" aria-label="Lista de programas">
          <div className="lp-lista-topo">
            <h2>{filtrados.length ? `${fmt(filtrados.length)} programas` : "Nenhum programa com esses filtros"}{recorte && <small> · {recorte}</small>}</h2>
            <label className="lp-sel">Ordenar
              <select value={ordem} onChange={(e) => setOrdem(e.target.value as Ordem)}>{ORDENS.map(([k, r]) => <option key={k} value={k}>{r}</option>)}</select>
            </label>
            <label className="lp-sel">Agrupar
              <select value={agrupar} onChange={(e) => setAgrupar(e.target.value as Agrupar)}>{AGRUPAR.map(([k, r]) => <option key={k} value={k}>{r}</option>)}</select>
            </label>
          </div>
          <div className="lp-rolagem">
            {grupos.map((g) => (
              <div key={g.k} className="lp-grupo">
                {g.rotulo && <h3 className="lp-grupo-cab">{g.href ? <a href={g.href}>{g.rotulo}</a> : g.rotulo} <span className="contagem">{g.total}</span></h3>}
                <ul className="lp-linhas">
                  {g.itens.map((p) => (
                    <li key={p.id}>
                      <a className="lp-linha prog" href={`/programa/${p.id}`}>
                        <span className="cp-conceito" style={{ background: COR_CONCEITO[colunaDe(p.conceito)] }} title={`Conceito CAPES ${p.conceito}`}>{p.conceito}</span>
                        <span className="lp-nome"><b>{nomePrograma(p.nome)}</b>
                          <small>{[p.sigla, p.uf, agrupar !== "area" && nomeArea(p.area)].filter(Boolean).join(" · ")}</small></span>
                        <span className="lp-niveis">{niveis(p.nivel).map((n) => <span key={n} className="cp-nivel" title={TITULO_NIVEL[n]}>{n}</span>)}</span>
                        <span className="lp-num" title="docentes no último ano-base">{p.docentes ? <>{p.docentes}<small> doc.</small></> : "–"}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {filtrados.length > limite && (
              <p className="centro-botao"><button className="botao-sec" onClick={() => setLimite((n) => n + PASSO_CELULAR)}>Mostrar mais ({fmt(filtrados.length - limite)} restantes)</button></p>
            )}
            {!filtrados.length && algumFiltro && <p className="res3-vazio">Tente outro nome ou <button type="button" className="chip" onClick={limpar}>limpe os filtros</button></p>}
          </div>
        </section>
      </div>
      {dica}
    </div>
  );
}
