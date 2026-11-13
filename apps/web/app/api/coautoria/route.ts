import { redePesquisador, redePrograma } from "@/lib/coautoria";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

// Rede de coautoria (D-046): ?tipo=pesquisador|programa&id=…&ql=0|1
export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const tipo = p.get("tipo"), id = p.get("id") ?? "";
  if ((tipo !== "pesquisador" && tipo !== "programa") || !UUID.test(id)) return Response.json({ erro: "parâmetros inválidos" }, { status: 400 });
  const sq = soQualis(req);
  const r = tipo === "pesquisador" ? await redePesquisador(id, sq) : await redePrograma(id, sq);
  return Response.json(r, { headers: { "cache-control": "public, max-age=600" } });
}
