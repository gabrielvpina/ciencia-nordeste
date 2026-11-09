import { POR_ARQUIVO, site, totalPesquisadores, xml } from "@/lib/sitemap";

export const dynamic = "force-dynamic";

// Índice: /sitemaps/0 (páginas fixas, instituições, programas) e /sitemaps/1..N (pesquisadores).
export async function GET() {
  const n = 1 + Math.ceil((await totalPesquisadores()) / POR_ARQUIVO);
  const itens = Array.from({ length: n }, (_, i) => `<sitemap><loc>${site()}/sitemaps/${i}</loc></sitemap>`).join("\n");
  return xml(`<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${itens}\n</sitemapindex>`);
}
