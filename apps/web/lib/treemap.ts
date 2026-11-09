// Treemap "squarified" (Bruls, Huizing e van Wijk, 2000), sem dependências.
export type Ret = { x: number; y: number; w: number; h: number };

/** Distribui `valores` (qualquer ordem) no retângulo; devolve um retângulo por valor, na mesma ordem. */
export function squarify(valores: number[], r: Ret): Ret[] {
  const total = valores.reduce((s, v) => s + Math.max(0, v), 0);
  const saida: Ret[] = valores.map(() => ({ x: r.x, y: r.y, w: 0, h: 0 }));
  if (total <= 0 || r.w <= 0 || r.h <= 0) return saida;
  const escala = (r.w * r.h) / total;
  const itens = valores.map((v, i) => ({ i, a: Math.max(0, v) * escala })).filter((x) => x.a > 0).sort((a, b) => b.a - a.a);
  let { x, y, w, h } = r;
  let linha: typeof itens = [];
  const pior = (l: typeof itens, lado: number) => {
    const s = l.reduce((t, it) => t + it.a, 0);
    const max = Math.max(...l.map((it) => it.a)), min = Math.min(...l.map((it) => it.a));
    return Math.max((lado * lado * max) / (s * s), (s * s) / (lado * lado * min));
  };
  const fechar = () => {
    const s = linha.reduce((t, it) => t + it.a, 0);
    if (w >= h) {          // coluna à esquerda
      const lw = s / h;
      let yy = y;
      for (const it of linha) { const hh = it.a / lw; saida[it.i] = { x, y: yy, w: lw, h: hh }; yy += hh; }
      x += lw; w -= lw;
    } else {               // faixa no topo
      const lh = s / w;
      let xx = x;
      for (const it of linha) { const ww = it.a / lh; saida[it.i] = { x: xx, y, w: ww, h: lh }; xx += ww; }
      y += lh; h -= lh;
    }
    linha = [];
  };
  for (const it of itens) {
    const lado = Math.min(w, h);
    if (!linha.length || pior([...linha, it], lado) <= pior(linha, lado)) linha.push(it);
    else { fechar(); linha.push(it); }
  }
  if (linha.length) fechar();
  return saida;
}
