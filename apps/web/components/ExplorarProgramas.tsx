"use client";
// Programas de pós: matriz área de avaliação × conceito CAPES (clicável, filtra) + cards agrupados.
import { useEffect, useMemo, useState } from "react";
import { useDica } from "@/components/Dica";
import { UFS, fmt } from "@/lib/areas";
import CardPrograma from "@/components/CardPrograma";
import { CONCEITOS, COR_CONCEITO, colunaDe, niveis, nomeArea } from "@/lib/programas";

export type ProgItem = {
  id: string; nome: string; nivel: string | null; area: string; conceito: string; sigla: string | null; uf: string;
  docentes: number | null; inst: string | null; inst_nome: string | null;
};
type Agrupar = "area" | "inst" | "uf";

const NOME_UF = Object.fromEntries(UFS);

const NIVEIS: { id: string; rotulo: string; ok: (n: string[]) => boolean }[] = [
  { id: "dout", rotulo: "Com doutorado", ok: (n) => n.includes("D") || n.includes("DP") },
  { id: "mest", rotulo: "Só mestrado acadêmico", ok: (n) => n.length === 1 && n[0] === "M" },
  { id: "prof", rotulo: "Profissional", ok: (n) => n.includes("MP") },
];

export default function ExplorarProgramas({ itens, ufInicial, areaInicial }: { itens: ProgItem[]; ufInicial?: string; areaInicial?: string }) {
  const [area, setArea] = useState(areaInicial && itens.some((p) => p.area === areaInicial) ? areaInicial : "");
  const [conceito, setConceito] = useState("");
  const [uf, setUf] = useState(ufInicial && NOME_UF[ufInicial] ? ufInicial : "");
  const [nivel, setNivel] = useState("");
  const [agrupar, setAgrupar] = useState<Agrupar>("area");
  const [texto, setTexto] = useState("");
  const [trocados, setTrocados] = useState<Set<string>>(new Set());   // grupos que a pessoa abriu ou fechou
  const { props: dicaProps, dica } = useDica();

  // A matriz respeita UF e nível; área e conceito são escolhidos nela.
  const base = useMemo(() => itens.filter((p) => (!uf || p.uf === uf) && (!nivel || NIVEIS.find((n) => n.id === nivel)!.ok(niveis(p.nivel)))), [itens, uf, nivel]);
  const sem = (x: string) => x.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
  const filtrados = useMemo(() => {
    const t = sem(texto.trim());
    return base.filter((p) => (!area || p.area === area) && (!conceito || colunaDe(p.conceito) === conceito)
      && (!t || sem(`${p.nome} ${p.sigla ?? ""} ${p.inst_nome ?? ""}`).includes(t)));
  }, [base, area, conceito, texto]);

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

  const grupos = useMemo(() => {
    const chave = (p: ProgItem) => (agrupar === "area" ? p.area : agrupar === "uf" ? p.uf : p.inst ?? `s:${p.sigla}`);
    const rotulo = (p: ProgItem) => (agrupar === "area" ? nomeArea(p.area) : agrupar === "uf" ? NOME_UF[p.uf] ?? p.uf : p.inst_nome ?? p.sigla ?? "Sem instituição vinculada");
    const m = new Map<string, { rotulo: string; sub?: string; href?: string; itens: ProgItem[] }>();
    for (const p of filtrados) {
      const k = chave(p);
      const g = m.get(k) ?? { rotulo: rotulo(p), sub: agrupar === "inst" ? `${p.sigla ?? ""} · ${p.uf}` : undefined, href: agrupar === "inst" && p.inst ? `/instituicao/${p.inst}` : undefined, itens: [] };
      g.itens.push(p);
      m.set(k, g);
    }
    for (const g of m.values()) g.itens.sort((a, b) => (Number(b.conceito) || 0) - (Number(a.conceito) || 0) || a.nome.localeCompare(b.nome));   // A (novo) e 2 por último
    return [...m.values()].sort((a, b) => b.itens.length - a.itens.length);
  }, [filtrados, agrupar]);

  const algumFiltro = area || conceito || uf || nivel || texto;
  // Grupos recolhidos: abertos só os primeiros (ou todos, com algum filtro). Evita uma página de 300 cartões.
  const [abertosIniciais, setAbertosIniciais] = useState(3);
  useEffect(() => { if (window.matchMedia("(max-width: 699px)").matches) setAbertosIniciais(1); }, []);   // no celular, só o 1º grupo aberto
  const aberto = (k: string, i: number) => (!!algumFiltro || i < abertosIniciais) !== trocados.has(k);
  const alternar = (k: string) => setTrocados((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const docentes = filtrados.reduce((s, p) => s + (p.docentes ?? 0), 0);

  return (
    <div className="explorar-pagina">
      <header className="pagina-topo">
        <div>
          <h1>Programas de pós-graduação</h1>
          <p className="meta">{fmt(filtrados.length)} programas · {fmt(docentes)} docentes no último ano-base · fonte: CAPES Dados Abertos (CC-BY)</p>
        </div>
        <input className="campo filtro-texto" type="search" placeholder="Filtrar por nome ou instituição" value={texto} onChange={(e) => setTexto(e.target.value)} aria-label="Filtrar programas por nome ou instituição" />
      </header>

      <div className="barra-controles">
        <div className="ctrl"><span className="lbl">Estado</span>
          <div className="chips chips-linha">
            <button className={`chip${!uf ? " chip-ativo" : ""}`} onClick={() => setUf("")}>Todos</button>
            {UFS.map(([s, n]) => <button key={s} title={n} className={`chip${uf === s ? " chip-ativo" : ""}`} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)}>{s}</button>)}
          </div>
        </div>
        <div className="ctrl"><span className="lbl">Nível</span>
          <div className="chips chips-linha">{NIVEIS.map((n) => (
            <button key={n.id} className={`chip${nivel === n.id ? " chip-ativo" : ""}`} aria-pressed={nivel === n.id} onClick={() => setNivel(nivel === n.id ? "" : n.id)}>{n.rotulo}</button>
          ))}</div>
        </div>
        {algumFiltro && <button className="chip chip-limpar" onClick={() => { setArea(""); setConceito(""); setUf(""); setNivel(""); setTexto(""); }}>limpar filtros</button>}
      </div>

      <section className="painel-card">
        <h2>Área de avaliação × conceito CAPES <small>tamanho = número de programas · clique numa linha, coluna ou círculo para filtrar</small></h2>
        <div className="matriz-rolagem">
          <div className="matriz" role="grid" aria-label="Programas por área de avaliação e conceito">
            <div className="mz-canto" />
            {CONCEITOS.map((c) => (
              <button key={c} className={`mz-col${conceito === c ? " ativo" : ""}`} onClick={() => setConceito(conceito === c ? "" : c)}
                {...dicaProps(() => ({ titulo: c === "outros" ? "Conceito 2 ou A (novo)" : `Conceito ${c}`, linhas: [["Programas", fmt(matriz.porConceito[c])]] }))}>
                <i style={{ background: COR_CONCEITO[c] }} />{c === "outros" ? "2 / A" : c}
              </button>
            ))}
            <div className="mz-total-cab">total</div>
            {matriz.linhas.map(({ a, l, n }) => (
              <div key={a} className={`mz-linha${area && area !== a ? " apagada" : ""}`} role="row">
                <button className={`mz-area${area === a ? " ativo" : ""}`} onClick={() => setArea(area === a ? "" : a)}>{nomeArea(a)}</button>
                {CONCEITOS.map((c) => {
                  const v = l.get(c) ?? 0;
                  const d = v ? 10 + 30 * Math.sqrt(v / matriz.max) : 0;
                  const ativo = (!area || area === a) && (!conceito || conceito === c);
                  return (
                    <button key={c} className={`mz-celula${ativo ? "" : " apagada"}`} disabled={!v} aria-label={`${nomeArea(a)}, conceito ${c}: ${v} programas`}
                      onClick={() => { const mesmo = area === a && conceito === c; setArea(mesmo ? "" : a); setConceito(mesmo ? "" : c); }}
                      {...(v ? dicaProps(() => ({ titulo: nomeArea(a), sub: c === "outros" ? "conceito 2 ou A" : `conceito ${c}`, linhas: [["Programas", fmt(v)]], nota: "Clique para filtrar" })) : {})}>
                      {v > 0 && <span className="mz-bolha" style={{ width: d, height: d, background: COR_CONCEITO[c], color: c === "5" || c === "6" ? "var(--panel)" : undefined }}>{v >= 3 ? v : ""}</span>}
                    </button>
                  );
                })}
                <span className="mz-total">{n}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="secao-topo">
        <h2 className="secao">{filtrados.length ? `${fmt(filtrados.length)} programas` : "Nenhum programa com esses filtros"}{area ? ` · ${nomeArea(area)}` : ""}{conceito ? ` · conceito ${conceito === "outros" ? "2 / A" : conceito}` : ""}</h2>
        <div className="ctrl"><span className="lbl">Agrupar</span>
          <div className="seg">{([["area", "Área"], ["inst", "Instituição"], ["uf", "Estado"]] as const).map(([k, r]) => (
            <button key={k} className={agrupar === k ? "ativo" : ""} aria-pressed={agrupar === k} onClick={() => setAgrupar(k)}>{r}</button>
          ))}</div>
        </div>
      </div>

      {grupos.map((g, i) => {
        const k = g.rotulo + (g.sub ?? "");
        const ab = aberto(k, i);
        return (
          <section key={k} className={`grupo-cards${ab ? "" : " fechado"}`}>
            <h3>
              <button type="button" className="grupo-alternar" aria-expanded={ab} onClick={() => alternar(k)}>
                <span className="grupo-seta" aria-hidden>{ab ? "−" : "+"}</span>{g.rotulo}
              </button>
              {g.href && <a className="grupo-link" href={g.href}>perfil</a>}
              {g.sub && <small> {g.sub}</small>} <span className="contagem">{g.itens.length}</span>
            </h3>
            {ab && (
              <div className="grade-cards grade-prog">
                {g.itens.map((p) => (
                  <CardPrograma key={p.id} id={p.id} nome={p.nome} conceito={p.conceito} nivel={p.nivel} docentes={p.docentes}
                    meta={`${p.sigla ?? ""} · ${p.uf}${agrupar !== "area" ? ` · ${nomeArea(p.area)}` : ""}`} />
                ))}
              </div>
            )}
          </section>
        );
      })}
      {dica}
    </div>
  );
}
