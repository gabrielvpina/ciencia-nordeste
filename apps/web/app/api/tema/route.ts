import { soQualis } from "@/lib/qualis-filtro";
import { buscaPorTema, type ModoBusca } from "@/lib/vetorial";

export const dynamic = "force-dynamic";
const MODOS: ModoBusca[] = ["hibrido", "vetor", "texto"];

// Busca por tema de pesquisa (português ou inglês). ?q=...&modo=hibrido|vetor|texto (padrão: hibrido)
export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const q = (p.get("q") ?? "").trim().slice(0, 300);
  const modo = (MODOS.includes(p.get("modo") as ModoBusca) ? p.get("modo") : "hibrido") as ModoBusca;
  if (q.length < 3) return Response.json({ erro: "consulta curta demais" }, { status: 400 });
  return Response.json(await buscaPorTema(q, modo, soQualis(req)));
}
