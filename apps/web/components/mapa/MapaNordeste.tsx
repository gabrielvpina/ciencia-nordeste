// Mapa próprio do Nordeste em SVG puro: sem tiles, sem bibliotecas, sem chamadas externas (D-025).
// Só desenha o que recebe em `dados`. Estilo 100% via variáveis CSS em ./mapa.css (classes .mn-*).
import "./mapa.css";
import { AREAS_ORDEM, rotuloArea } from "./areas";
import { ESTADOS, VIEWBOX, arco, espalhar, fatia, projetar } from "./projecao";
import type { DadosMapa, ModoMapa, PontoInst } from "./tipos";

type Props = {
  modo: ModoMapa;
  dados: DadosMapa;
  ufAtiva?: string;          // destaca um estado (filtro)
  areaAtiva?: string;        // no modo áreas: pinta os estados pela área escolhida
  titulo?: string;           // rótulo acessível
  hrefInstituicao?: (id: string) => string;
};

const fmt = (n: number) => n.toLocaleString("pt-BR");
const ALTURA_MAX = 360;       // altura da barra mais alta (unidades do viewBox)
const [VX, VY, VW, VH] = VIEWBOX;
// Margens extras para as âncoras de colaboração externa (posições representativas, fora do território).
// Topo extra: barras altas do litoral norte. Direita extra só no modo rede (âncoras externas).
const viewBox = (modo: ModoMapa) => [VX - 20, VY - (modo === "densidade" ? 150 : 30), VW + (modo === "rede" ? 250 : 40), VH + (modo === "densidade" ? 170 : 50)];
const ANCORA_BRASIL: [number, number] = [70, VH - 60];
const ancoraExterior = (i: number): [number, number] => [VW + 150, 230 + i * 110];

export default function MapaNordeste({ modo, dados, ufAtiva, areaAtiva, titulo, hrefInstituicao = (id) => `/instituicao/${id}` }: Props) {
  const pontos = espalhar(
    [...dados.pontos].sort((a, b) => b.works - a.works).map((p) => ({ ...p, ...xy(p) })),
  );
  const porId = new Map(pontos.map((p) => [p.id, p]));
  const maxWorks = Math.max(1, ...pontos.map((p) => p.works));

  // Áreas: totais por UF e, se houver área ativa, intensidade dessa área por UF (coroplético)
  const porUf = new Map<string, { total: number; fatias: Map<string, number> }>();
  for (const a of dados.areas ?? []) {
    const u = porUf.get(a.uf) ?? { total: 0, fatias: new Map() };
    u.total += a.works;
    u.fatias.set(a.field, (u.fatias.get(a.field) ?? 0) + a.works);
    porUf.set(a.uf, u);
  }
  const maxUf = Math.max(1, ...[...porUf.values()].map((u) => u.total));
  const maxAreaUf = Math.max(1, ...[...porUf.values()].map((u) => (areaAtiva ? u.fatias.get(areaAtiva) ?? 0 : 0)));

  return (
    <svg className={`mn mn-modo-${modo}`} viewBox={viewBox(modo).join(" ")} role="img" aria-label={titulo ?? "Mapa do Nordeste"} preserveAspectRatio="xMidYMid meet">
      <g className="mn-estados">
        {ESTADOS.map((e) => {
          const intens = modo === "areas" && areaAtiva ? (porUf.get(e.uf)?.fatias.get(areaAtiva) ?? 0) / maxAreaUf : 0;
          return (
            <path key={e.uf} d={e.path} className={`mn-estado${ufAtiva === e.uf ? " mn-estado-ativo" : ""}${ufAtiva && ufAtiva !== e.uf ? " mn-estado-apagado" : ""}`}
              style={intens ? ({ "--mn-intensidade": intens.toFixed(3) } as React.CSSProperties) : undefined}>
              <title>{e.nome}</title>
            </path>
          );
        })}
      </g>
      <g className="mn-siglas" aria-hidden>
        {ESTADOS.map((e) => <text key={e.uf} x={e.centro[0]} y={e.centro[1] + (modo === "areas" ? 0 : 0)} className="mn-sigla">{e.uf}</text>)}
      </g>

      {modo === "densidade" && (
        <g className="mn-barras">
          {[...pontos].sort((a, b) => a.y - b.y).map((p) => {
            const h = Math.max(3, (ALTURA_MAX * p.works) / maxWorks);
            const w = 4 + 6 * Math.sqrt(p.works / maxWorks);
            return (
              <a key={p.id} href={hrefInstituicao(p.id)} className="mn-barra">
                <path d={`M${p.x - w},${p.y} L${p.x},${p.y - h} L${p.x + w},${p.y} Z`} />
                <circle cx={p.x} cy={p.y} r={2.2} className="mn-base" />
                <title>{`${p.nome} (${p.uf}): ${fmt(p.works)} publicações`}</title>
              </a>
            );
          })}
          {semColisao(pontos.slice(0, 14).map((p) => ({ p, x: p.x, y: p.y - Math.max(3, (ALTURA_MAX * p.works) / maxWorks) - 8 })), 8).map(({ p, x, y }) => (
            <text key={p.id} x={x} y={y} className="mn-rotulo">{p.sigla ?? p.nome.slice(0, 14)} · {fmt(p.works)}</text>
          ))}
        </g>
      )}

      {modo === "ligacoes" && (() => {
        const lig = (dados.ligacoes ?? []).filter((l) => porId.has(l.a) && porId.has(l.b));
        const maxL = Math.max(1, ...lig.map((l) => l.works));
        return (
          <g className="mn-ligacoes">
            {[...lig].sort((a, b) => a.works - b.works).map((l) => {
              const a = porId.get(l.a)!, b = porId.get(l.b)!;
              const t = l.works / maxL;
              return (
                <path key={l.a + l.b} d={arco([a.x, a.y], [b.x, b.y])} className="mn-arco" style={{ strokeWidth: 0.6 + 7 * Math.sqrt(t), opacity: 0.18 + 0.7 * t }}>
                  <title>{`${a.sigla ?? a.nome} ↔ ${b.sigla ?? b.nome}: ${fmt(l.works)} publicações em comum`}</title>
                </path>
              );
            })}
            {pontos.filter((p) => lig.some((l) => l.a === p.id || l.b === p.id)).map((p) => (
              <a key={p.id} href={hrefInstituicao(p.id)}>
                <circle cx={p.x} cy={p.y} r={2.5 + 9 * Math.sqrt(p.works / maxWorks)} className="mn-no"><title>{`${p.nome}: ${fmt(p.works)} publicações`}</title></circle>
              </a>
            ))}
            {semColisao(pontos.slice(0, 12).map((p) => ({ p, x: p.x, y: p.y - 14 })), 8).map(({ p, x, y }) => <text key={p.id} x={x} y={y} className="mn-rotulo">{p.sigla ?? p.nome.slice(0, 14)}</text>)}
          </g>
        );
      })()}

      {modo === "areas" && (
        <g className="mn-areas">
          {ESTADOS.map((e) => {
            const u = porUf.get(e.uf);
            if (!u || u.total === 0) return null;
            const r = 20 + 46 * Math.sqrt(u.total / maxUf);
            let ang = 0;
            const ordenadas = AREAS_ORDEM.filter((f) => u.fatias.get(f));
            return (
              <g key={e.uf} className="mn-rosca">
                {ordenadas.map((f) => {
                  const v = u.fatias.get(f)!;
                  const a0 = ang, a1 = ang + (2 * Math.PI * v) / u.total;
                  ang = a1;
                  return (
                    <path key={f} d={fatia(e.centro[0], e.centro[1], r, r * 0.55, a0, Math.min(a1, a0 + 2 * Math.PI - 1e-4))}
                      className={`mn-fatia mn-area-${AREAS_ORDEM.indexOf(f)}${areaAtiva && areaAtiva !== f ? " mn-fatia-apagada" : ""}`}>
                      <title>{`${e.nome} · ${rotuloArea(f)}: ${fmt(v)} (${((100 * v) / u.total).toFixed(0)}%)`}</title>
                    </path>
                  );
                })}
                <text x={e.centro[0]} y={e.centro[1] + 5} className="mn-rosca-total">{fmt(u.total)}</text>
              </g>
            );
          })}
        </g>
      )}

      {modo === "rede" && dados.rede && (() => {
        const rede = dados.rede;
        const origem = rede.origem.map((id) => porId.get(id)).filter((p): p is PontoInst & { x: number; y: number } => !!p);
        const o = origem[0];
        const parceiros = rede.parceiros.map((x) => ({ ...x, p: porId.get(x.id) })).filter((x) => x.p);
        const maxP = Math.max(1, ...parceiros.map((x) => x.works), ...rede.externos.map((x) => x.works));
        const externosExt = rede.externos.filter((x) => x.tipo === "exterior");
        const brasil = rede.externos.find((x) => x.tipo === "brasil");
        return (
          <g className="mn-rede">
            {o && parceiros.map(({ id, works, p }) => (
              <path key={id} d={arco([o.x, o.y], [p!.x, p!.y], 0.3)} className="mn-arco" style={{ strokeWidth: 0.8 + 7 * Math.sqrt(works / maxP), opacity: 0.3 + 0.6 * (works / maxP) }}>
                <title>{`${p!.nome}: ${fmt(works)} publicações em comum`}</title>
              </path>
            ))}
            {o && brasil && brasil.works > 0 && (
              <g className="mn-externo mn-externo-brasil">
                <path d={arco([o.x, o.y], ANCORA_BRASIL, 0.2)} className="mn-arco mn-arco-externo" style={{ strokeWidth: 0.8 + 7 * Math.sqrt(brasil.works / maxP) }} />
                <circle cx={ANCORA_BRASIL[0]} cy={ANCORA_BRASIL[1]} r={7} className="mn-ancora" />
                <text x={ANCORA_BRASIL[0]} y={ANCORA_BRASIL[1] + 26} className="mn-rotulo mn-rotulo-ancora">{brasil.rotulo} · {fmt(brasil.works)}</text>
              </g>
            )}
            {o && externosExt.map((x, i) => {
              const alvo = ancoraExterior(i);
              return (
                <g key={x.rotulo} className="mn-externo">
                  <path d={arco([o.x, o.y], alvo, 0.15)} className="mn-arco mn-arco-externo" style={{ strokeWidth: 0.8 + 7 * Math.sqrt(x.works / maxP) }} />
                  <circle cx={alvo[0]} cy={alvo[1]} r={7} className="mn-ancora" />
                  <text x={alvo[0] + 12} y={alvo[1] + 5} className="mn-rotulo mn-rotulo-ancora" textAnchor="start">{x.rotulo} · {fmt(x.works)}</text>
                </g>
              );
            })}
            {parceiros.map(({ id, works, p }) => (
              <a key={id} href={hrefInstituicao(id)}>
                <circle cx={p!.x} cy={p!.y} r={3 + 9 * Math.sqrt(works / maxP)} className="mn-no"><title>{`${p!.nome} (${p!.uf}): ${fmt(works)}`}</title></circle>
              </a>
            ))}
            {semColisao(parceiros.slice(0, 10).map(({ p }) => ({ p: p!, x: p!.x, y: p!.y - 14 })), 6).map(({ p, x, y }) => <text key={p.id} x={x} y={y} className="mn-rotulo">{p.sigla ?? p.nome.slice(0, 16)}</text>)}
            {origem.map((p) => (
              <a key={p.id} href={hrefInstituicao(p.id)}>
                <circle cx={p.x} cy={p.y} r={11} className="mn-origem"><title>{p.nome}</title></circle>
              </a>
            ))}
            {o && <text x={o.x} y={o.y + 32} className="mn-rotulo mn-rotulo-origem">{o.sigla ?? o.nome}</text>}
          </g>
        );
      })()}
    </svg>
  );
}

/** Mantém só rótulos que não se sobrepõem (caixa aproximada), na ordem de importância; no máximo `limite`. */
function semColisao<T extends { x: number; y: number }>(itens: T[], limite: number): T[] {
  const ok: T[] = [];
  for (const i of itens) {
    if (ok.length >= limite) break;
    if (ok.every((o) => Math.abs(o.x - i.x) > 140 || Math.abs(o.y - i.y) > 28)) ok.push(i);
  }
  return ok;
}

function xy(p: { lat: number; lon: number }) {
  const [x, y] = projetar(p.lat, p.lon);
  return { x, y };
}
