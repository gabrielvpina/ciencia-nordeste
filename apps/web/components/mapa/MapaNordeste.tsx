"use client";
// Mapa próprio do Nordeste em SVG puro: sem tiles, sem bibliotecas, sem chamadas externas (D-025).
// Só desenha o que recebe em `dados`. Estilo 100% via variáveis CSS em ./mapa.css (classes .mn-*).
// Interação: dica (tooltip) ao passar o mouse ou tocar; clique seleciona (onSelecionar) ou abre o perfil.
// Subunidades (ponto.pai) ficam ocultas até a instituição principal ser selecionada (D-030).
import { useEffect, useMemo, useRef, useState } from "react";
import "./mapa.css";
import { AREAS_ORDEM, rotuloArea } from "./areas";
import { ESTADOS, VIEWBOX, arco, espalhar, fatia, projetar, unidadesPorKm } from "./projecao";
import type { DadosMapa, ModoMapa, PontoInst } from "./tipos";

type Props = {
  modo: ModoMapa;
  dados: DadosMapa;
  ufAtiva?: string;          // destaca um estado (filtro)
  areaAtiva?: string;        // no modo áreas: pinta os estados pela área escolhida
  titulo?: string;           // rótulo acessível
  hrefInstituicao?: (id: string) => string;
  selecionado?: string | null;                   // instituição selecionada (mostra subunidades e destaca)
  onSelecionar?: (id: string | null) => void;    // sem isto, o clique abre o perfil
  destaque?: string | null;                      // realce vindo de fora (ex.: mouse sobre um nome no ranking)
};

type Ponto = PontoInst & { x: number; y: number };
type Dica = { titulo: string; sub?: string; linhas?: [string, string][]; nota?: string };

const fmt = (n: number) => n.toLocaleString("pt-BR");
const VISIVEIS_POR_CIDADE = 4;   // por cidade, as N maiores ficam sempre à mostra
// Siglas de estados pequenos saem para o oceano com linha-guia (deslocamento em unidades do viewBox).
const ROTULO_FORA: Record<string, [number, number]> = { AL: [78, 18], SE: [74, 40] };
const ALTURA_MAX = 150;       // altura do cone mais alto (unidades do viewBox), além da altura mínima
const ALTURA_MIN = 14;
const [VX, VY, VW, VH] = VIEWBOX;
const ESCALA = 200 * unidadesPorKm(-9);   // comprimento de 200 km no viewBox
// Anéis de fundo (centro e raio no viewBox) e linhas do gride geográfico.
const ANEL = { cx: VW / 2, cy: VH / 2 + 10, r: 600 };
const GRADE_LAT = [-5, -10, -15];
const GRADE_LON = [-45, -40, -35];
// Margens extras: topo para as barras do litoral norte; direita, no modo rede, para as âncoras externas.
const topoExtra = (modo: ModoMapa) => (modo === "densidade" ? 75 : 30);
const viewBox = (modo: ModoMapa) => [VX - 20, VY - topoExtra(modo), VW + (modo === "rede" ? 250 : 40), VH + topoExtra(modo) + 60];
const ANCORA_BRASIL: [number, number] = [70, VH - 60];
const ancoraExterior = (i: number): [number, number] => [VW + 150, 230 + i * 110];
const TIPOS: Record<string, string> = {
  universidade: "Universidade", centro_universitario: "Centro universitário", faculdade: "Faculdade", instituto_federal: "Instituto federal",
  ensino: "Ensino", hospital_saude: "Hospital / saúde", instituto_pesquisa: "Instituto de pesquisa", governo: "Governo", empresa: "Empresa",
  organizacao_sem_fins_lucrativos: "Organização sem fins lucrativos", financiador: "Financiador", outro: "Outro",
};

export default function MapaNordeste({ modo, dados, ufAtiva, areaAtiva, titulo, hrefInstituicao = (id) => `/instituicao/${id}`, selecionado, onSelecionar, destaque }: Props) {
  const caixa = useRef<HTMLDivElement>(null);
  const [dica, setDica] = useState<(Dica & { x: number; y: number }) | null>(null);
  const [foco, setFoco] = useState<string | null>(null);     // instituição sob o mouse
  const svgRef = useRef<SVGSVGElement>(null);
  const [tam, setTam] = useState({ w: 0, h: 0 });            // tamanho do SVG (para os callouts em HTML)
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setTam({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const tempo = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(tempo.current), []);

  const mostrar = (e: React.PointerEvent, d: Dica) => {
    const r = caixa.current?.getBoundingClientRect();
    if (!r) return;
    setDica({ ...d, x: e.clientX - r.left, y: e.clientY - r.top });
    clearTimeout(tempo.current);
    if (e.pointerType === "touch") tempo.current = setTimeout(() => setDica(null), 3500);
  };
  const comDica = (d: () => Dica, id?: string) => ({
    onPointerEnter: (e: React.PointerEvent) => { mostrar(e, d()); if (id) setFoco(id); },
    onPointerMove: (e: React.PointerEvent) => { if (e.pointerType !== "touch") mostrar(e, d()); },
    onPointerLeave: (e: React.PointerEvent) => { if (e.pointerType !== "touch") setDica(null); if (id) setFoco(null); },
  });
  const abrir = (id: string) => {
    setDica(null);
    // subunidade à mostra: vai direto ao perfil (selecioná-la esconderia a própria subunidade)
    if (onSelecionar && !subsAtuais.current.has(id)) onSelecionar(id === selecionado ? null : id);
    else window.location.assign(hrefInstituicao(id));   // link interno: mesma aba
  };
  const acionavel = (id: string, rotulo: string) => ({
    role: "button", tabIndex: 0, "aria-label": rotulo,
    onClick: (e: React.MouseEvent) => { e.stopPropagation(); abrir(id); },
    onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(id); } },
  });

  // ---- pontos: principais (espalhados quando caem na mesma cidade) + subunidades da instituição selecionada ----
  const { principais, porId, filhos, menores, subs, rank, maxWorks, dono } = useMemo(() => {
    const ids = new Set(dados.pontos.map((p) => p.id));
    const filhos = new Map<string, PontoInst[]>();
    for (const p of dados.pontos) if (p.pai && ids.has(p.pai)) filhos.set(p.pai, [...(filhos.get(p.pai) ?? []), p]);
    // Na mesma cidade, só as maiores ficam à mostra; as menores entram no leque da maior da cidade (como subunidades).
    const topo = dados.pontos.filter((p) => !(p.pai && ids.has(p.pai))).sort((a, b) => b.works - a.works).map((p) => ({ ...p, ...xy(p) }));
    const cidades = new Map<string, Ponto[]>();
    for (const p of topo) { const k = `${Math.round(p.x / 14)}:${Math.round(p.y / 14)}`; cidades.set(k, [...(cidades.get(k) ?? []), p]); }
    const menores = new Map<string, PontoInst[]>();
    const visiveis: Ponto[] = [];
    for (const g of cidades.values()) {
      const lider = g[0];
      g.forEach((p, i) => {
        if (i < VISIVEIS_POR_CIDADE || p.works >= 0.2 * lider.works) visiveis.push(p);
        else menores.set(lider.id, [...(menores.get(lider.id) ?? []), p]);
      });
    }
    const principais: Ponto[] = espalhar(visiveis.sort((a, b) => b.works - a.works)).sort((a, b) => b.works - a.works);
    const porId = new Map<string, Ponto>(principais.map((p) => [p.id, p]));
    const rank = new Map(topo.map((p, i) => [p.id, i + 1]));   // posição entre todas as principais (inclui as menores ocultas)
    const maxWorks = Math.max(1, ...principais.map((p) => p.works));
    let subs: Ponto[] = [];
    const o = selecionado ? porId.get(selecionado) : undefined;
    const leque = o ? [...(filhos.get(o.id) ?? []), ...(menores.get(o.id) ?? [])] : [];
    if (o && leque.length) {
      const fs = leque.sort((a, b) => b.works - a.works);
      const raio = Math.min(150, 48 + 7 * fs.length);
      subs = fs.map((f, i) => {
        const a = Math.PI * (0.08 + (0.84 * (i + 0.5)) / fs.length);   // leque abaixo do ponto
        return { ...f, x: o.x - raio * Math.cos(a) * 1.5, y: o.y + raio * Math.sin(a) * 0.9 };
      });
      for (const s of subs) porId.set(s.id, s);
    }
    const dono = new Map<string, string>();   // oculto → ponto à mostra que o representa
    for (const [pai, fs] of [...filhos, ...menores]) for (const f of fs) dono.set(f.id, dono.get(pai) ?? pai);
    for (const [pai] of filhos) if (dono.has(pai)) for (const f of filhos.get(pai)!) dono.set(f.id, dono.get(pai)!);
    return { principais, porId, filhos, menores, subs, rank, maxWorks, dono };
  }, [dados.pontos, selecionado]);

  const subsAtuais = useRef(new Set<string>());
  subsAtuais.current = new Set(subs.map((p) => p.id));
  // Alturas comprimidas (expoente 0,45) e com mínimo: as diferenças continuam visíveis sem picos discrepantes.
  const altura = (w: number) => ALTURA_MIN + ALTURA_MAX * Math.pow(w / maxWorks, 0.45);
  const ativo = foco ?? destaque ?? null;
  const dicaInst = (p: Ponto): Dica => {
    const n = filhos.get(p.id)?.length ?? 0;
    const k = menores.get(p.id)?.length ?? 0;
    const pai = p.pai ? porId.get(p.pai) : undefined;
    const partes = [n ? `${n} subunidade${n > 1 ? "s" : ""}` : "", k ? `${k} instituiç${k > 1 ? "ões menores" : "ão menor"} na cidade` : ""].filter(Boolean);
    return {
      titulo: p.nome, sub: [p.sigla, p.uf, p.tipo ? TIPOS[p.tipo] ?? p.tipo : null].filter(Boolean).join(" · "),
      linhas: [["Publicações", fmt(p.works)], ...(rank.has(p.id) ? [["Posição", `${rank.get(p.id)}ª de ${rank.size}`] as [string, string]] : [])],
      nota: pai ? `Subunidade de ${pai.sigla ?? pai.nome}` : subs.some((x) => x.id === p.id) ? "Clique para abrir o perfil"
        : partes.length && onSelecionar ? `${partes.join(" e ")}: clique para ver` : onSelecionar ? "Clique para selecionar" : "Clique para abrir o perfil",
    };
  };

  // ---- áreas por UF ----
  const porUf = new Map<string, { total: number; fatias: Map<string, number> }>();
  for (const a of dados.areas ?? []) {
    const u = porUf.get(a.uf) ?? { total: 0, fatias: new Map() };
    u.total += a.works;
    u.fatias.set(a.field, (u.fatias.get(a.field) ?? 0) + a.works);
    porUf.set(a.uf, u);
  }
  const maxUf = Math.max(1, ...[...porUf.values()].map((u) => u.total));
  const maxAreaUf = Math.max(1, ...[...porUf.values()].map((u) => (areaAtiva ? u.fatias.get(areaAtiva) ?? 0 : 0)));
  const totalUf = (uf: string) => principais.filter((p) => p.uf === uf);

  const dicaEstado = (e: (typeof ESTADOS)[number]): Dica => {
    if (modo === "areas") {
      const u = porUf.get(e.uf);
      const top = u ? [...u.fatias.entries()].sort((a, b) => b[1] - a[1])[0] : undefined;
      return { titulo: e.nome, linhas: u ? [["Publicações", fmt(u.total)], ...(top ? [["Maior área", rotuloArea(top[0])] as [string, string]] : [])] : [] };
    }
    const ps = totalUf(e.uf);
    return { titulo: e.nome, linhas: [["Instituições", fmt(ps.length)], ["Publicações (soma)", fmt(ps.reduce((s, p) => s + p.works, 0))]] };
  };

  return (
    <div className="mn-caixa" ref={caixa}>
      <svg ref={svgRef} className={`mn mn-modo-${modo}${selecionado ? " mn-com-selecao" : ""}`} viewBox={viewBox(modo).join(" ")} role="img"
        aria-label={titulo ?? "Mapa do Nordeste"} preserveAspectRatio="xMidYMid meet" onClick={() => onSelecionar?.(null)}>
        {/* fundo: anéis concêntricos (estáticos) e gride de latitude/longitude com rótulos */}
        <g className="mn-fundo" aria-hidden>
          <circle className="mn-anel-cheio" cx={ANEL.cx} cy={ANEL.cy} r={ANEL.r * 0.72} />
          <circle className="mn-anel-marcas" cx={ANEL.cx} cy={ANEL.cy} r={ANEL.r * 0.86} />
          <circle className="mn-anel" cx={ANEL.cx} cy={ANEL.cy} r={ANEL.r} />
          <circle className="mn-anel mn-anel-tracejado" cx={ANEL.cx} cy={ANEL.cy} r={ANEL.r * 1.1} />
          {[0, 90, 180, 270].map((g) => {
            const a = (g * Math.PI) / 180, r0 = ANEL.r * 0.97, r1 = ANEL.r * 1.04;
            return <line key={g} className="mn-anel-cardeal" x1={ANEL.cx + r0 * Math.sin(a)} y1={ANEL.cy - r0 * Math.cos(a)} x2={ANEL.cx + r1 * Math.sin(a)} y2={ANEL.cy - r1 * Math.cos(a)} />;
          })}
          {GRADE_LAT.map((lat) => {
            const y = projetar(lat, -40)[1];
            return <g key={lat}><line className="mn-grade" x1={VX - 20} x2={VX + VW + 20} y1={y} y2={y} /><text className="mn-grade-txt" x={VX - 14} y={y - 6}>{-lat}° S</text></g>;
          })}
          {GRADE_LON.map((lon) => {
            const x = projetar(-5, lon)[0];
            return <g key={lon}><line className="mn-grade" x1={x} x2={x} y1={VY - topoExtra(modo)} y2={VH + 60} /><text className="mn-grade-txt" x={x + 6} y={VH + 52}>{-lon}° O</text></g>;
          })}
        </g>
        {/* sombra dura: uma cópia do mapa deslocada, em tinta sólida */}
        <g className="mn-placa" aria-hidden>
          {[9].map((d) => (
            <g key={d} transform={`translate(${d} ${d})`}>{ESTADOS.map((e) => <path key={e.uf} d={e.path} />)}</g>
          ))}
        </g>
        <g className="mn-estados">
          {ESTADOS.map((e) => {
            const intens = modo === "areas" && areaAtiva ? (porUf.get(e.uf)?.fatias.get(areaAtiva) ?? 0) / maxAreaUf : 0;
            return (
              <path key={e.uf} d={e.path} className={`mn-estado${ufAtiva === e.uf ? " mn-estado-ativo" : ""}${ufAtiva && ufAtiva !== e.uf ? " mn-estado-apagado" : ""}`}
                style={intens ? ({ "--mn-intensidade": intens.toFixed(3) } as React.CSSProperties) : undefined}
                {...(modo === "rede" ? {} : comDica(() => dicaEstado(e)))} />
            );
          })}
        </g>
        <g className="mn-siglas" aria-hidden>
          {ESTADOS.map((e) => {
            const [dx, dy] = ROTULO_FORA[e.uf] ?? [0, 0];
            const [x, y] = [e.centro[0] + dx, e.centro[1] + dy];
            return (
              <g key={e.uf}>
                {(dx || dy) ? <><path className="mn-guia" d={`M${e.centro[0]},${e.centro[1]} L${x - 18},${y - 7}`} /><circle className="mn-guia-ponto" cx={e.centro[0]} cy={e.centro[1]} r={3} /></> : null}
                <text x={x} y={y} className="mn-sigla">{e.uf}</text>
              </g>
            );
          })}
        </g>

        {/* convenção cartográfica: escala gráfica (200 km, a 9° S) e seta do norte */}
        <g className="mn-escala" aria-hidden transform={`translate(${VX + 20} ${VH + 22})`}>
          <rect width={ESCALA / 2} height={11} className="mn-escala-a" />
          <rect x={ESCALA / 2} width={ESCALA / 2} height={11} className="mn-escala-b" />
          <text x={0} y={-8}>200 km</text>
        </g>
        <g className="mn-norte" aria-hidden transform={`translate(${VX} ${VY - topoExtra(modo) + 12})`}>
          <rect width={56} height={72} rx={7} />
          <path d="M28,10 L41,36 L28,29 L15,36 Z" />
          <text x={28} y={62} textAnchor="middle">N</text>
        </g>

        {modo === "densidade" && (
          <g className="mn-barras">
            {[...principais, ...subs].sort((a, b) => a.y - b.y).map((p) => {
              const h = altura(p.works);
              const w = 6 + 10 * Math.sqrt(p.works / maxWorks);     // base larga: legível, sem fidelidade de escala
              const ehSub = subs.includes(p);
              const n = (filhos.get(p.id)?.length ?? 0) + (menores.get(p.id)?.length ?? 0);
              const cls = ["mn-barra",
                rank.get(p.id)! <= 3 && "mn-barra-top",
                p.id === selecionado && "mn-barra-sel", ehSub && "mn-barra-sub",
                ativo === p.id && "mn-barra-foco",
                selecionado && p.id !== selecionado && !ehSub && "mn-barra-apagada"].filter(Boolean).join(" ");
              return (
                <g key={p.id} className={cls} {...acionavel(p.id, `${p.nome}: ${fmt(p.works)} publicações`)} {...comDica(() => dicaInst(p), p.id)}>
                  {ehSub && <line x1={porId.get(selecionado!)!.x} y1={porId.get(selecionado!)!.y} x2={p.x} y2={p.y} className="mn-sub-linha" />}
                  {n > 0 && !ehSub && <circle cx={p.x} cy={p.y} r={7 + w} className="mn-sub-anel" />}
                  <path d={cone(p.x, p.y, w, h)} />
                  <path d={`M${p.x},${p.y - h} L${p.x + w},${p.y} A${w},${w * 0.38} 0 0 1 ${p.x},${p.y + w * 0.38} Z`} className="mn-cone-sombra" />
                  <rect x={p.x - w - 4} y={p.y - h - 4} width={2 * w + 8} height={h + 8} className="mn-alvo" />
                </g>
              );
            })}
            {rotulosBarras(principais, subs, altura, selecionado).map(({ p, x, y, r }) => (
              <g key={p.id} className={`mn-etiqueta${r && r <= 3 ? " mn-etiqueta-top" : ""}`} transform={`translate(${x} ${y})`} aria-hidden>
                {r ? (<><circle r={19} className="mn-badge" /><text className="mn-badge-num" dy="0.35em">{r}</text></>) : null}
                <text x={r ? 25 : 0} dy="0.35em" className={`mn-rotulo${r ? " mn-rotulo-lado" : " mn-rotulo-sub"}`}>{p.sigla ?? p.nome.slice(0, 14)}</text>
              </g>
            ))}
          </g>
        )}

        {modo === "ligacoes" && (() => {
          // subunidade oculta: a ligação vai para a instituição principal
          const visivel = (id: string) => (porId.has(id) ? id : dono.get(id) ?? id);
          const soma = new Map<string, { a: string; b: string; works: number }>();
          for (const l of dados.ligacoes ?? []) {
            const a = visivel(l.a), b = visivel(l.b);
            if (a === b || !porId.has(a) || !porId.has(b)) continue;
            const k = a < b ? `${a}|${b}` : `${b}|${a}`;
            const s = soma.get(k) ?? { a, b, works: 0 };
            s.works += l.works;
            soma.set(k, s);
          }
          const lig = [...soma.values()].sort((x, y) => x.works - y.works);
          const maxL = Math.max(1, ...lig.map((l) => l.works));
          const centro = ativo ?? selecionado ?? null;
          const grau = new Map<string, number>();
          for (const l of lig) { grau.set(l.a, (grau.get(l.a) ?? 0) + 1); grau.set(l.b, (grau.get(l.b) ?? 0) + 1); }
          const vizinhos = new Set(lig.filter((l) => l.a === centro || l.b === centro).flatMap((l) => [l.a, l.b]));
          const nos = [...porId.values()].filter((p) => grau.has(p.id));
          return (
            <g className={`mn-ligacoes${centro ? " mn-com-foco" : ""}`}>
              {lig.map((l) => {
                const a = porId.get(l.a)!, b = porId.get(l.b)!;
                const t = l.works / maxL;
                const ligado = centro && (l.a === centro || l.b === centro);
                return (
                  <path key={l.a + l.b} d={arco([a.x, a.y], [b.x, b.y])} className={`mn-arco${ligado ? " mn-arco-foco" : ""}`}
                    style={{ strokeWidth: 0.6 + 7 * Math.sqrt(t), opacity: centro ? undefined : 0.18 + 0.7 * t }}
                    {...comDica(() => ({ titulo: `${a.sigla ?? a.nome} ↔ ${b.sigla ?? b.nome}`, linhas: [["Publicações em comum", fmt(l.works)]] }))} />
                );
              })}
              {nos.map((p) => (
                <circle key={p.id} cx={p.x} cy={p.y} r={5 + 15 * Math.sqrt(p.works / maxWorks)}
                  className={`mn-no${p.id === centro ? " mn-no-foco" : ""}${centro && !vizinhos.has(p.id) && p.id !== centro ? " mn-no-apagado" : ""}`}
                  {...acionavel(p.id, p.nome)}
                  {...comDica(() => ({ ...dicaInst(p), linhas: [...(dicaInst(p).linhas ?? []), ["Ligações no mapa", fmt(grau.get(p.id) ?? 0)]] }), p.id)} />
              ))}
              {semColisao(
                (centro ? nos.filter((p) => vizinhos.has(p.id)) : nos.slice(0, 12)).sort((a, b) => b.works - a.works).map((p) => ({ p, x: p.x, y: p.y - 14 })),
                centro ? 10 : 8,
              ).map(({ p, x, y }) => <text key={p.id} x={x} y={y} className="mn-rotulo">{p.sigla ?? p.nome.slice(0, 14)}</text>)}
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
                        className={`mn-fatia mn-area-${AREAS_ORDEM.indexOf(f)}${areaAtiva && areaAtiva !== f ? " mn-fatia-apagada" : ""}`}
                        {...comDica(() => ({ titulo: rotuloArea(f), sub: e.nome, linhas: [["Publicações", fmt(v)], ["Parte do estado", `${((100 * v) / u.total).toFixed(0)}%`]] }))} />
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
          const origem = rede.origem.map((id) => porId.get(id)).filter((p): p is Ponto => !!p);
          const o = origem[0];
          const parceiros = rede.parceiros.map((x) => ({ ...x, p: porId.get(x.id) })).filter((x): x is typeof x & { p: Ponto } => !!x.p);
          const maxP = Math.max(1, ...parceiros.map((x) => x.works), ...rede.externos.map((x) => x.works));
          const externosExt = rede.externos.filter((x) => x.tipo === "exterior");
          const brasil = rede.externos.find((x) => x.tipo === "brasil");
          const dicaParceiro = (p: Ponto, works: number): Dica => ({ titulo: p.nome, sub: [p.sigla, p.uf].filter(Boolean).join(" · "), linhas: [["Publicações em comum", fmt(works)]], nota: "Clique para abrir o perfil" });
          return (
            <g className={`mn-rede${foco ? " mn-com-foco" : ""}`}>
              {o && parceiros.map(({ id, works, p }) => (
                <path key={id} d={arco([o.x, o.y], [p.x, p.y], 0.3)} className={`mn-arco${foco === id ? " mn-arco-foco" : ""}`}
                  style={{ strokeWidth: 0.8 + 7 * Math.sqrt(works / maxP), opacity: foco ? undefined : 0.3 + 0.6 * (works / maxP) }}
                  {...comDica(() => dicaParceiro(p, works), id)} />
              ))}
              {o && brasil && brasil.works > 0 && (
                <g className="mn-externo mn-externo-brasil" {...comDica(() => ({ titulo: brasil.rotulo, linhas: [["Publicações com coautoria", fmt(brasil.works)]], nota: "Posição ilustrativa" }))}>
                  <path d={arco([o.x, o.y], ANCORA_BRASIL, 0.2)} className="mn-arco mn-arco-externo" style={{ strokeWidth: 0.8 + 7 * Math.sqrt(brasil.works / maxP) }} />
                  <circle cx={ANCORA_BRASIL[0]} cy={ANCORA_BRASIL[1]} r={7} className="mn-ancora" />
                  <text x={ANCORA_BRASIL[0]} y={ANCORA_BRASIL[1] + 26} className="mn-rotulo mn-rotulo-ancora">{brasil.rotulo}</text>
                </g>
              )}
              {o && externosExt.map((x, i) => {
                const alvo = ancoraExterior(i);
                return (
                  <g key={x.rotulo} className="mn-externo" {...comDica(() => ({ titulo: x.rotulo, linhas: [["Publicações com coautoria", fmt(x.works)]], nota: "Posição ilustrativa" }))}>
                    <path d={arco([o.x, o.y], alvo, 0.15)} className="mn-arco mn-arco-externo" style={{ strokeWidth: 0.8 + 7 * Math.sqrt(x.works / maxP) }} />
                    <circle cx={alvo[0]} cy={alvo[1]} r={7} className="mn-ancora" />
                    <text x={alvo[0] + 12} y={alvo[1] + 5} className="mn-rotulo mn-rotulo-ancora" textAnchor="start">{x.rotulo}</text>
                  </g>
                );
              })}
              {parceiros.map(({ id, works, p }) => (
                <circle key={id} cx={p.x} cy={p.y} r={5 + 14 * Math.sqrt(works / maxP)} className={`mn-no${foco === id ? " mn-no-foco" : ""}`}
                  {...acionavel(id, p.nome)} {...comDica(() => dicaParceiro(p, works), id)} />
              ))}
              {semColisao(parceiros.slice(0, 10).map(({ p }) => ({ p, x: p.x, y: p.y - 14 })), 6).map(({ p, x, y }) => <text key={p.id} x={x} y={y} className="mn-rotulo">{p.sigla ?? p.nome.slice(0, 16)}</text>)}
              {origem.map((p) => (
                <g key={p.id}>
                  <circle cx={p.x} cy={p.y} r={15} className="mn-pulso" />
                  <circle cx={p.x} cy={p.y} r={15} className="mn-origem" {...acionavel(p.id, p.nome)} {...comDica(() => ({ titulo: p.nome, sub: "origem da rede" }))} />
                </g>
              ))}
              {o && <text x={o.x} y={o.y + 32} className="mn-rotulo mn-rotulo-origem">{o.sigla ?? o.nome}</text>}
            </g>
          );
        })()}
        {/* pulsos nas 3 maiores (destaques com callout) */}
        {modo === "densidade" && !selecionado && principais.slice(0, 3).map((p) => (
          <circle key={p.id} cx={p.x} cy={p.y} r={7} className="mn-pulso" aria-hidden />
        ))}
      </svg>

      {modo === "densidade" && !selecionado && tam.w >= 640 && (
        <Callouts pontos={principais.slice(0, 3)} altura={altura} vb={viewBox(modo)} tam={tam} />
      )}
      <Legenda modo={modo} altura={altura} maxWorks={maxWorks} escala={tam.w ? Math.min(tam.w / viewBox(modo)[2], tam.h / viewBox(modo)[3]) : 0.5} />

      {dica && (
        <div className="mn-dica" role="tooltip"
          style={{ left: dica.x, top: dica.y, transform: `translate(${dica.x > (caixa.current?.clientWidth ?? 0) - 260 ? "calc(-100% - 14px)" : "14px"}, ${dica.y > (caixa.current?.clientHeight ?? 0) - 140 ? "calc(-100% - 14px)" : "14px"})` }}>
          <b>{dica.titulo}</b>
          {dica.sub && <span className="mn-dica-sub">{dica.sub}</span>}
          {dica.linhas?.map(([k, v]) => <div key={k} className="mn-dica-linha">{k}<em>{v}</em></div>)}
          {dica.nota && <span className="mn-dica-nota">{dica.nota}</span>}
        </div>
      )}
    </div>
  );
}

/** Rótulos das barras: top 8 com a posição no ranking; com seleção, a selecionada e as subunidades. */
function rotulosBarras(principais: Ponto[], subs: Ponto[], altura: (w: number) => number, selecionado?: string | null) {
  const topo = (p: Ponto) => p.y - altura(p.works) - 26;
  const base = principais.slice(0, 8).map((p) => ({ p, x: p.x, y: topo(p), r: principais.indexOf(p) + 1 as number | null }));
  const sel = principais.find((p) => p.id === selecionado);
  const extra = [
    ...(sel && !base.some((b) => b.p.id === sel.id) ? [{ p: sel, x: sel.x, y: topo(sel), r: principais.indexOf(sel) + 1 }] : []),
    ...subs.filter((p) => p.pai === selecionado).map((p) => ({ p, x: p.x, y: p.y + 22, r: null })),
    ...subs.filter((p) => p.pai !== selecionado).slice(0, 5).map((p) => ({ p, x: p.x, y: p.y + 22, r: null })),
  ];
  return semColisao([...extra, ...base], 8 + extra.length, 150, 42);
}

/** Mantém só rótulos que não se sobrepõem (caixa aproximada), na ordem de importância; no máximo `limite`. */
function semColisao<T extends { x: number; y: number }>(itens: T[], limite: number, larg = 140, alt = 28): T[] {
  const ok: T[] = [];
  for (const i of itens) {
    if (ok.length >= limite) break;
    if (ok.every((o) => Math.abs(o.x - i.x) > larg || Math.abs(o.y - i.y) > alt)) ok.push(i);
  }
  return ok;
}

function xy(p: { lat: number; lon: number }) {
  const [x, y] = projetar(p.lat, p.lon);
  return { x, y };
}

/** Cartões HTML para as 3 maiores, ligados à ponta da barra por linha pontilhada (como na inspiração). */
function Callouts({ pontos, altura, vb, tam }: { pontos: Ponto[]; altura: (w: number) => number; vb: number[]; tam: { w: number; h: number } }) {
  const esc = Math.min(tam.w / vb[2], tam.h / vb[3]);
  const ox = (tam.w - vb[2] * esc) / 2 - vb[0] * esc, oy = (tam.h - vb[3] * esc) / 2 - vb[1] * esc;
  const L = 168, A = 52, GAP = 10;
  const itens = pontos.map((p, i) => {
    const ax = ox + p.x * esc, ay = oy + (p.y - altura(p.works)) * esc;
    const direita = ax > tam.w * 0.5;
    const x = Math.max(8, Math.min(tam.w - L - 8, direita ? ax + 70 : ax - 70 - L));
    return { p, i, ax, ay, x, y: ay - A / 2, direita };
  });
  // empilha sem sobrepor (ordem vertical), dentro da caixa
  [...itens].sort((a, b) => a.y - b.y).reduce((ultimo, it) => { it.y = Math.max(it.y, ultimo + GAP, 8); return it.y + A; }, -Infinity);
  for (const it of itens) it.y = Math.min(it.y, tam.h - A - 8);
  return (
    <>
      <svg className="mn-callout-linhas" width={tam.w} height={tam.h} aria-hidden>
        {itens.map((it) => <path key={it.p.id} d={`M${it.ax},${it.ay} L${it.direita ? it.x : it.x + L},${it.y + A / 2}`} />)}
      </svg>
      {itens.map((it) => (
        <div key={it.p.id} className="mn-callout" style={{ left: it.x, top: it.y, width: L }} aria-hidden>
          <span className="mn-callout-ico"><svg viewBox="0 0 24 24"><path d="M5 20V10M12 20V4M19 20v-7" /></svg></span>
          <span><b>{fmt(it.p.works)}</b><span>{String(it.i + 1).padStart(2, "0")} · {(it.p.sigla ?? it.p.nome).split(",")[0]}<br />publicações</span></span>
        </div>
      ))}
    </>
  );
}

/** Legenda em caixa no canto do mapa, por modo. */
function Legenda({ modo, altura, maxWorks, escala }: { modo: ModoMapa; altura: (w: number) => number; maxWorks: number; escala: number }) {
  if (modo === "densidade") {
    const refs = [100, 1000, 10000].filter((v) => v <= maxWorks * 1.05);
    const k = Math.min(1, 24 / Math.max(1, ...refs.map((v) => altura(v) * escala)));   // a legenda não passa de 24 px
    const hMax = Math.max(...refs.map((v) => altura(v) * escala * k), 10);
    return (
      <div className="mn-legenda-caixa">
        <div>
          <div className="ttl">Publicações (altura do cone, escala comprimida)</div>
          <svg className="lg-svg" width={refs.length * 58} height={hMax + 6} aria-hidden>
            {refs.map((v, i) => {
              const h = Math.max(3, altura(v) * escala * k), x = 8 + i * 58;
              return <g key={v}><path className="lg-pico" d={cone(x, hMax + 1, 5, h)} /><text x={x + 9} y={hMax - 2}>{fmt(v)}</text></g>;
            })}
          </svg>
        </div>
        <div className="chave">
          <span><i className="bola" style={{ background: "var(--mn-barra-hover)" }} />Top 3</span>
          <span><i className="bola" style={{ background: "var(--mn-barra)" }} />Posição no ranking</span>
          <span><i className="anel" />Tem subunidades</span>
        </div>
      </div>
    );
  }
  if (modo === "ligacoes") return (
    <div className="mn-legenda-caixa">
      <div className="ttl">Coautoria entre instituições</div>
      <div className="chave"><span><i className="traco" />Espessura = publicações em comum</span><span><i className="tracejado" />Rede em foco</span></div>
    </div>
  );
  if (modo === "areas") return (
    <div className="mn-legenda-caixa">
      <div className="ttl">Produção do estado por área</div>
      <div className="chave"><span><i className="rosca" />Tamanho = publicações do estado; cores = áreas</span></div>
    </div>
  );
  return (
    <div className="mn-legenda-caixa">
      <div className="chave">
        <span><i className="bola" style={{ background: "var(--mn-origem)" }} />Origem</span>
        <span><i className="bola" style={{ background: "var(--mn-no)" }} />Parceiras no NE</span>
        <span><i className="tracejado" />Coautoria fora do NE (posição ilustrativa)</span>
      </div>
    </div>
  );
}

/** Cone: triângulo com base elíptica (visto levemente de cima). */
function cone(x: number, y: number, w: number, h: number) {
  return `M${x - w},${y} L${x},${y - h} L${x + w},${y} A${w},${w * 0.38} 0 0 1 ${x - w},${y} Z`;
}
