import { q } from "@/lib/db";

export const POR_ARQUIVO = 40000;
export const site = () => process.env.SITE_URL ?? "http://localhost:3000";
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

export const xml = (corpo: string) =>
  new Response(`<?xml version="1.0" encoding="UTF-8"?>\n${corpo}`, { headers: { "content-type": "application/xml; charset=utf-8", "cache-control": "public, max-age=3600" } });

export const urlset = (urls: string[]) =>
  `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((u) => `<url><loc>${esc(u)}</loc></url>`).join("\n")}\n</urlset>`;

export async function totalPesquisadores() {
  const [{ n }] = await q<{ n: string }>(`SELECT count(*) AS n FROM mv_pesquisador_busca WHERE works > 0 OR is_capes_faculty`);
  return Number(n);
}
