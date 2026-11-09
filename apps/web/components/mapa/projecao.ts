// Projeção e utilidades do mapa próprio do Nordeste. Mesma fórmula do gerador (ingest/carga/gerar_mapa_ne.py).
import geo from "./geometria-ne.json";

export type Estado = { uf: string; nome: string; codigo: number; path: string; centro: [number, number] };
export const ESTADOS = geo.estados as Estado[];
export const VIEWBOX = geo.viewBox as [number, number, number, number];
const P = geo.projecao;

export function projetar(lat: number, lon: number): [number, number] {
  return [P.margem + (lon - P.lonMin) * P.kx, P.margem + (P.latMax - lat) * P.ky];
}

export const centroUf = (uf: string): [number, number] | undefined => ESTADOS.find((e) => e.uf === uf)?.centro;

/** Espalha pontos sobrepostos (várias instituições na mesma cidade) num pequeno anel: posições são representativas. */
export function espalhar<T extends { x: number; y: number }>(pontos: T[], celula = 14): T[] {
  const grupos = new Map<string, T[]>();
  for (const p of pontos) {
    const k = `${Math.round(p.x / celula)}:${Math.round(p.y / celula)}`;
    grupos.set(k, [...(grupos.get(k) ?? []), p]);
  }
  const saida: T[] = [];
  for (const g of grupos.values()) {
    if (g.length === 1) { saida.push(g[0]); continue; }
    const cx = g.reduce((s, p) => s + p.x, 0) / g.length;
    const cy = g.reduce((s, p) => s + p.y, 0) / g.length;
    const raio = 8 + 2.2 * Math.sqrt(g.length) * 3;
    g.forEach((p, i) => {
      if (i === 0) { saida.push({ ...p, x: cx, y: cy }); return; }   // o maior fica no centro (vem ordenado)
      const a = (2 * Math.PI * (i - 1)) / (g.length - 1);
      saida.push({ ...p, x: cx + raio * Math.cos(a), y: cy + raio * Math.sin(a) });
    });
  }
  return saida;
}

/** Arco quadrático de a até b, curvado para "cima" (perpendicular ao segmento). */
export function arco(a: [number, number], b: [number, number], curva = 0.25): string {
  const [x1, y1] = a, [x2, y2] = b;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const dx = x2 - x1, dy = y2 - y1;
  const sinal = dx >= 0 ? -1 : 1;
  const cx = mx + sinal * dy * curva, cy = my - Math.abs(dx) * curva - Math.abs(dy) * 0.05;
  return `M${x1.toFixed(1)},${y1.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
}

/** Fatia de rosca (donut) em SVG. */
export function fatia(cx: number, cy: number, r: number, r0: number, a0: number, a1: number): string {
  const p = (r_: number, a: number) => [cx + r_ * Math.sin(a), cy - r_ * Math.cos(a)].map((v) => v.toFixed(1)).join(",");
  const grande = a1 - a0 > Math.PI ? 1 : 0;
  return `M${p(r, a0)} A${r},${r} 0 ${grande} 1 ${p(r, a1)} L${p(r0, a1)} A${r0},${r0} 0 ${grande} 0 ${p(r0, a0)} Z`;
}
