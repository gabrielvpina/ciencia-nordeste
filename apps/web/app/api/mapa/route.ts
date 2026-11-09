import { lerFiltros } from "@/lib/filtros";
import { dadosMapa } from "@/lib/mapa-dados";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const f = lerFiltros(new URL(req.url).searchParams);
  return Response.json(await dadosMapa(f), { headers: { "cache-control": "public, max-age=300" } });
}
