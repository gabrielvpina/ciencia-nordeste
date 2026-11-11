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

/** Mini mapa do NE (só os contornos, com sombra dura) e a posição de cada ponto em fração da imagem (0–1),
 *  para o banner desenhar os números por cima. Posições aproximadas, como no site. */
export function miniMapa(pontos: { lat: number | null; lon: number | null }[]): { src: string; pos: ({ x: number; y: number } | null)[] } {
  const [, , w, h] = geo.viewBox;
  const x0 = -20, y0 = -20, W = w + 60, H = h + 60;
  const estados = geo.estados.map((e) => `<path d="${e.path}" fill="${PAINEL}" stroke="${TINTA}" stroke-width="5" stroke-linejoin="round"/>`).join("");
  const sombra = geo.estados.map((e) => `<path d="${e.path}" fill="${TINTA}" transform="translate(14 14)"/>`).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x0} ${y0} ${W} ${H}">${sombra}${estados}</svg>`;
  const usados = new Map<string, number>();
  const pos = pontos.map((p) => {
    if (p.lat == null || p.lon == null) return null;
    const [x, y] = projetar(p.lat, p.lon);
    const k = `${Math.round(x / 40)}:${Math.round(y / 40)}`, n = usados.get(k) ?? 0;   // mesma cidade: espalha em anel
    usados.set(k, n + 1);
    const a = -Math.PI / 2 + n * 2.1, r = n ? 130 : 0;   // em unidades do mapa (~1000 de largura)
    return { x: (x + r * Math.cos(a) - x0) / W, y: (y + r * Math.sin(a) - y0) / H };
  });
  return { src: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`, pos };
}

export const PROPORCAO_MAPA = (geo.viewBox[3] + 60) / (geo.viewBox[2] + 60);   // altura / largura
