// Cores e formas dos banners (etapa 13). Sem ilustração: fundo pelo habitat, acento pelo ambiente, tinta e cartões do site
// (tema claro, paleta Azul, D-031 e D-034). Os valores seguem app/tokens.css, convertidos para hex (o gerador de PNG não lê CSS).
import geo from "@/components/mapa/geometria-ne.json";
import { NE } from "@/components/Logo";

export const TINTA = "#1b1e33";
export const PAINEL = "#fbfcfe";
export const MUDO = "#5a5e75";
export const DESTAQUE = "#7a9ced";      // --accent-vivo (azul)
export const LIMA = "#d4ef7a";          // --flow (marca-texto)

/** fundo por habitat (tons claros) */
export const FUNDO: Record<string, string> = {
  campo: "#e2eed4", bancada: "#dce6f6", computador: "#e5e0f5", pessoas: "#f6e2da", colecoes: "#f2e9d0", neutro: "#d9dde8",
};
/** acento por ambiente (tons fortes, para formas e barras) */
export const ACENTO: Record<string, string> = {
  caatinga: "#d39b35", mata: "#3f9d6b", mar: "#2f86c9", lavoura: "#8fb531", cidade: "#8f6ee8", neutro: "#5b8def",
};
/** círculos das iniciais (fixos, distintos entre si) */
export const INICIAIS = ["#7a9ced", "#d4ef7a", "#f2a58e", "#9fd8c3", "#f2c94c"];

export const iniciais = (nome: string) => {
  const p = nome.replace(/[^\p{L}\s-]/gu, " ").split(/\s+/).filter((x) => x.length > 1 && !/^(de|da|do|dos|das|e)$/i.test(x));
  return ((p[0]?.[0] ?? "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
};

export const corta = (s: string, n: number) => (s.length <= n ? s : s.slice(0, n - 1).trimEnd() + "…");

/** Ícone do site (contorno do Nordeste) como imagem SVG embutida. */
export function logoSvg(cor = DESTAQUE): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 4 47 59"><path d="${NE}" transform="translate(3,3)" fill="${TINTA}"/>`
    + `<path d="${NE}" fill="${cor}" stroke="${TINTA}" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

const P = geo.projecao;
const projetar = (lat: number, lon: number): [number, number] => [P.margem + (lon - P.lonMin) * P.kx, P.margem + (P.latMax - lat) * P.ky];

/** Mini mapa do NE (só os contornos, com sombra dura) e a posição exata de cada ponto em fração da imagem (0–1).
 *  Quem está no mesmo lugar é agrupado pelo banner num único marcador ("2·3·5"): nada é empurrado para fora do mapa. */
export function miniMapa(pontos: { lat: number | null; lon: number | null }[]): { src: string; pos: ({ x: number; y: number } | null)[] } {
  const [, , w, h] = geo.viewBox;
  const x0 = -20, y0 = -20, W = w + 60, H = h + 60;
  const estados = geo.estados.map((e) => `<path d="${e.path}" fill="${PAINEL}" stroke="${TINTA}" stroke-width="5" stroke-linejoin="round"/>`).join("");
  const sombra = geo.estados.map((e) => `<path d="${e.path}" fill="${TINTA}" transform="translate(14 14)"/>`).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${y0} ${W} ${H}">${sombra}${estados}</svg>`;
  const pos = pontos.map((p) => {
    if (p.lat == null || p.lon == null) return null;
    const [x, y] = projetar(p.lat, p.lon);
    return { x: (x - x0) / W, y: (y - y0) / H };
  });
  return { src: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`, pos };
}

/** Agrupa pontos (em px) mais próximos que `raio`: um marcador por grupo, no centro do grupo, com os números juntos. */
export function agruparPontos(pos: ({ x: number; y: number } | null)[], raio: number) {
  const grupos: { x: number; y: number; nums: number[] }[] = [];
  pos.forEach((p, i) => {
    if (!p) return;
    const g = grupos.find((q) => Math.hypot(q.x - p.x, q.y - p.y) < raio);
    if (g) { g.x = (g.x * g.nums.length + p.x) / (g.nums.length + 1); g.y = (g.y * g.nums.length + p.y) / (g.nums.length + 1); g.nums.push(i + 1); }
    else grupos.push({ x: p.x, y: p.y, nums: [i + 1] });
  });
  return grupos;
}

/** Contorno do logo (só a forma), para usar grande como elemento gráfico do banner. */
export function logoForma(cor: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 4 47 59"><path d="${NE}" transform="translate(2.4,2.4)" fill="${TINTA}"/>`
    + `<path d="${NE}" fill="${cor}" stroke="${TINTA}" stroke-width="1.1" stroke-linejoin="round"/></svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

export const PROPORCAO_MAPA = (geo.viewBox[3] + 60) / (geo.viewBox[2] + 60);   // altura / largura

/** Fontes do site para os banners (Lexend nos títulos, DM Sans no texto; licença OFL, em public/fontes/).
 *  O gerador de PNG (next/og) lê TTF/OTF/WOFF, não WOFF2 nem fontes variáveis: por isso os arquivos estáticos em WOFF. */
type Fonte = { name: string; data: ArrayBuffer; weight: 400 | 700; style: "normal" };
let fontes: Promise<Fonte[]> | null = null;
export function carregarFontes(): Promise<Fonte[]> {
  fontes ??= (async () => {
    const { readFile } = await import("node:fs/promises");
    const { join } = await import("node:path");
    const ler = async (arq: string) => { const b = await readFile(join(process.cwd(), "public", "fontes", arq)); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer; };
    return Promise.all([
      ["DM Sans", "DMSans-400.woff", 400], ["DM Sans", "DMSans-700.woff", 700],
      ["Lexend", "Lexend-400.woff", 400], ["Lexend", "Lexend-700.woff", 700],
    ].map(async ([name, arq, weight]) => ({ name: name as string, data: await ler(arq as string), weight: weight as 400 | 700, style: "normal" as const })));
  })().catch((e) => { fontes = null; throw e; });
  return fontes;
}
export const TITULO = "Lexend";
