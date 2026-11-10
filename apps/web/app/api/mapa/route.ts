import { lerFiltros } from "@/lib/filtros";
import { dadosMapa } from "@/lib/mapa-dados";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const f = lerFiltros(new URL(req.url).searchParams);
  return Response.json(await dadosMapa(f, soQualis(req)), { headers: { "cache-control": "public, max-age=300" } });
}
