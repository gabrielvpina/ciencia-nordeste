import { pesquisar } from "@/lib/busca";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";

// Busca completa (D-044), usada pelo painel ao apertar "Buscar": nomes, pesquisadores do tema e trabalhos.
// ?q=...&tema=1 força a busca por tema mesmo quando a consulta parece um nome. ?ql=0|1 = filtro Qualis.
export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const r = await pesquisar(p.get("q") ?? "", soQualis(req), p.get("tema") === "1");
  return Response.json(r, { headers: { "cache-control": "private, max-age=600" } });
}
