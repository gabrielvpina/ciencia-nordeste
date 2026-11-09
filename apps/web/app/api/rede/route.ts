import { dadosRede } from "@/lib/mapa-dados";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;
const TIPOS = ["pesquisador", "instituicao", "programa"] as const;

export async function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const tipo = p.get("tipo") as (typeof TIPOS)[number] | null;
  const id = p.get("id") ?? "";
  if (!tipo || !TIPOS.includes(tipo) || !UUID.test(id)) return Response.json({ erro: "parâmetros inválidos" }, { status: 400 });
  return Response.json(await dadosRede(tipo, id), { headers: { "cache-control": "public, max-age=300" } });
}
