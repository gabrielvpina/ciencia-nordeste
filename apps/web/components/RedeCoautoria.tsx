"use client";
// Rede de coautoria em anel (D-046). Pesquisador: a pessoa no centro e os coautores em volta, agrupados e coloridos por
// instituição. Programa: os docentes em volta, agrupados por vínculo (colaboração interna). Linhas entre nós do anel =
// publicaram juntos. Passar o mouse (ou focar com o teclado) isola as ligações de uma pessoa; clicar abre o perfil.
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { RedeCoautoria as Rede } from "@/lib/coautoria";
import { fmt } from "@/lib/areas";
import { paramQualis } from "@/lib/qualis-cookie";

const R = 300;                 // raio do anel (unidades do viewBox)
const CORES = 7;               // grupos com cor própria; os demais ficam em cinza
const MAX_LINHAS = 80;         // acima disso, só as ligações mais fortes (o anel vira um emaranhado)

/** "Maria Elieidy Gomes de Oliveira" → "Maria Oliveira": rótulos curtos cabem em volta do anel. */
function curto(nome: string) {
  const p = nome.split(/\s+/).filter((x) => !/^(de|da|do|dos|das|e)$/i.test(x));
  return p.length <= 2 ? p.join(" ") : `${p[0]} ${p[p.length - 1]}`;
}

/** "Marcelo Sobral da Silva" → "Marcelo S." (celular: o nome inteiro aparece ao tocar). */
function curtissimo(nome: string) {
  const p = curto(nome).split(" ");
  return p.length > 1 ? `${p[0]} ${p[p.length - 1][0]}.` : p[0];
}

export default function RedeCoautoria({ tipo, id, abas }: { tipo: "pesquisador" | "programa"; id: string; abas: ReactNode }) {
  const [rede, setRede] = useState<Rede | null>(null);
  const [erro, setErro] = useState(false);
  const [foco, setFoco] = useState<string | null>(null);
  // tela estreita: enquadramento mais largo e rótulos curtíssimos, para os nomes não serem cortados
  const [estreito, setEstreito] = useState(false);
  useEffect(() => {
    const m = window.matchMedia("(max-width: 860px)");
    const f = () => setEstreito(m.matches);
    f(); m.addEventListener("change", f);
    return () => m.removeEventListener("change", f);
  }, []);
  useEffect(() => {
    const ctl = new AbortController();
    fetch(`/api/coautoria?tipo=${tipo}&id=${id}&${paramQualis()}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject())).then(setRede).catch(() => setErro(true));
    return () => ctl.abort();
  }, [tipo, id]);

  const g = useMemo(() => {
    if (!rede) return null;
    // grupos ordenados pelo peso; dentro do grupo, quem tem mais publicações primeiro
    const peso = new Map<string, number>();
    for (const n of rede.nos) peso.set(n.grupo, (peso.get(n.grupo) ?? 0) + n.n);
    const grupos = [...peso.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k);
    const cor = (grupo: string) => { const i = grupos.indexOf(grupo); return i < CORES ? `var(--coaut-${i})` : "var(--coaut-outros)"; };
    const nos = [...rede.nos].sort((a, b) => grupos.indexOf(a.grupo) - grupos.indexOf(b.grupo) || b.n - a.n);
    const VAO = 0.8;  // espaço entre grupos, em "vagas"
    const vagas = nos.length + VAO * grupos.length;
    let k = 0, ant = "";
    const maxN = Math.max(1, ...nos.map((n) => n.n));
    const pos = new Map(nos.map((n) => {
      if (n.grupo !== ant) { k += VAO; ant = n.grupo; }
      const ang = (2 * Math.PI * (k + 0.5)) / vagas - Math.PI / 2;
      k += 1;
      return [n.id, { ...n, ang, x: R * Math.cos(ang), y: R * Math.sin(ang), r: 6 + 15 * Math.sqrt(n.n / maxN), cor: cor(n.grupo) }];
    }));
    const maxA = Math.max(1, ...rede.arestas.map((a) => a.n));
    const grau = new Map<string, number>();
    for (const a of rede.arestas) { grau.set(a.a, (grau.get(a.a) ?? 0) + 1); grau.set(a.b, (grau.get(a.b) ?? 0) + 1); }
    const legenda = grupos.slice(0, CORES).map((gr) => ({ gr, cor: cor(gr), n: nos.filter((x) => x.grupo === gr).length }));
    const outros = nos.filter((x) => grupos.indexOf(x.grupo) >= CORES).length;
    // corte: o menor número de publicações juntos que deixa no máximo MAX_LINHAS linhas
    let corte = 1;
    while (rede.arestas.filter((a) => a.n >= corte).length > MAX_LINHAS) corte++;
    const visiveis = rede.arestas.filter((a) => a.n >= corte);
    const ordem = new Map([...rede.nos].sort((a, b) => b.n - a.n).map((x, i) => [x.id, i]));
    return { pos, maxN, maxA, grau, legenda, outros, corte, visiveis, ordem, isolados: nos.filter((x) => !grau.get(x.id)).length };
  }, [rede]);

  const vizinhos = useMemo(() => {
    const s = new Set<string>();
    if (rede && foco) for (const a of rede.arestas) { if (a.a === foco) s.add(a.b); if (a.b === foco) s.add(a.a); }
    return s;
  }, [rede, foco]);
  const fNo = foco && g ? g.pos.get(foco) : undefined;

  return (
    <section className="mapa-col" aria-busy={!rede && !erro}>
      <div className="mapa-cabecalho">
        <a href="/painel" className="voltar">Painel</a>
        {abas}
        {rede && <span className="meta">{tipo === "pesquisador" ? `${rede.nos.length} coautores mais frequentes` : `${rede.nos.length} docentes`} · {fmt(rede.arestas.length)} ligações entre eles</span>}
      </div>
      {!rede || !g ? <p className="meta centro">{erro ? "Não foi possível carregar a rede." : "Carregando a rede…"}</p>
        : !rede.nos.length ? <p className="meta centro">Sem coautores com perfil na base.</p> : (
        <div className="coaut">
          <svg className="coaut-svg" onClick={(e) => { if ((e.target as Element).tagName === "svg") setFoco(null); }} viewBox={estreito ? "-660 -520 1320 1040" : "-560 -470 1120 940"} role="img"
            aria-label={tipo === "pesquisador" ? `Rede de coautoria de ${rede.centro?.nome}` : "Colaboração entre os docentes do programa"}>
            <g className={`coaut-grafo${foco ? " com-foco" : ""}`}>
              {rede.centro && [...g.pos.values()].map((n) => (
                <line key={`c${n.id}`} x1={0} y1={0} x2={n.x} y2={n.y} className={`coaut-raio${foco === n.id ? " on" : ""}`}
                  style={{ stroke: n.cor, strokeWidth: 0.6 + 5 * Math.sqrt(n.n / g.maxN) }} />
              ))}
              {g.visiveis.map((a) => {
                const p = g.pos.get(a.a), q = g.pos.get(a.b);
                if (!p || !q) return null;
                const on = foco === a.a || foco === a.b;
                return <path key={a.a + a.b} d={`M${p.x},${p.y} Q${(p.x + q.x) * 0.22},${(p.y + q.y) * 0.22} ${q.x},${q.y}`}
                  className={`coaut-aresta${on ? " on" : ""}`} style={{ strokeWidth: 0.8 + 6 * Math.sqrt(a.n / g.maxA) }} />;
              })}
              {rede.centro && (
                <g className="coaut-centro">
                  <circle r={30} />
                  <text y={estreito ? 66 : 52} textAnchor="middle">{estreito ? curtissimo(rede.centro.nome) : curto(rede.centro.nome)}</text>
                </g>
              )}
              {[...g.pos.values()].map((n) => {
                const principal = g.ordem.get(n.id)! < 12;   // no celular só os 12 maiores têm nome no anel
                const dir = Math.cos(n.ang) >= 0;
                const graus = (n.ang * 180) / Math.PI;
                const apagado = foco && foco !== n.id && !vizinhos.has(n.id);
                return (
                  <a key={n.id} href={`/pesquisador/${n.id}`} aria-label={`${n.nome}, ${n.detalhe || n.grupo}, ${n.n} publicações${tipo === "pesquisador" ? " em comum" : ""}`}
                    className={`coaut-no${apagado ? " apagado" : ""}${foco === n.id ? " on" : ""}`}
                    onPointerEnter={(e) => { if (e.pointerType === "mouse") setFoco(n.id); }} onPointerLeave={(e) => { if (e.pointerType === "mouse") setFoco(null); }}
                    onFocus={() => setFoco(n.id)}
                    onClick={(e) => { if (foco !== n.id) { e.preventDefault(); setFoco(n.id); } }}>
                    <circle cx={n.x} cy={n.y} r={n.r} style={{ fill: n.cor }} />
                    <text transform={`translate(${n.x},${n.y}) rotate(${dir ? graus : graus + 180}) translate(${dir ? n.r + 8 : -(n.r + 8)},0)`}
                      textAnchor={dir ? "start" : "end"} dominantBaseline="central" className={principal ? undefined : "secundario"}>{estreito ? curtissimo(n.nome) : curto(n.nome)}</text>
                  </a>
                );
              })}
            </g>
          </svg>

          <aside className="coaut-lado">
            <p className="meta">
              {tipo === "pesquisador"
                ? "Tamanho = publicações em comum. Linhas entre coautores = também publicaram juntos. Cores = instituição."
                : "Tamanho = publicações do docente. Linhas = docentes que publicaram juntos. Cores = vínculo no programa."}
              {g.corte > 1 && ` Para não embaralhar, só aparecem as ligações com ${g.corte} ou mais publicações juntos.`}
            </p>
            <div className="coaut-foco" aria-live="polite">
              {fNo ? (
                <>
                  <b>{fNo.nome}</b>
                  <span>{fNo.detalhe || fNo.grupo}</span>
                  <span>{fmt(fNo.n)} publicaç{fNo.n === 1 ? "ão" : "ões"}{tipo === "pesquisador" ? " em comum" : ""} · liga-se a {g.grau.get(fNo.id) ?? 0} {tipo === "pesquisador" ? "coautores" : "colegas"}</span>
                </>
              ) : <span className="meta">Passe o mouse ou toque num nome para ver as ligações.</span>}
            </div>
            <ul className="coaut-legenda">
              {g.legenda.map((x) => <li key={x.gr} title={x.gr}><i style={{ background: x.cor }} /><span>{x.gr}</span><em>{x.n}</em></li>)}
              {g.outros > 0 && <li><i style={{ background: "var(--coaut-outros)" }} /><span>Outras</span><em>{g.outros}</em></li>}
            </ul>
            {tipo === "programa" && g.isolados > 0 && (
              <p className="meta">{g.isolados} de {rede.nos.length} docentes não têm publicação com colegas do programa na base.</p>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
