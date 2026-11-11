// POST /api/quiz/resultado — { instituicao_id: uuid | null, respostas: [ids das opções], filtro?: {tipo: "ne"|"uf"|"raio", km?} }
// O servidor reconstrói tudo a partir dos ids (não aceita sinais do cliente) e não grava nada (D-022, LGPD).
import { alinhar, type Filtro } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

function lerFiltro(f: unknown, temInstituicao: boolean): Filtro {
  const x = (f ?? {}) as { tipo?: string; km?: number };
  if (x.tipo === "uf" && temInstituicao) return { tipo: "uf" };
  if (x.tipo === "raio" && temInstituicao && Number.isFinite(x.km) && Number(x.km) > 0) return { tipo: "raio", km: Math.min(Number(x.km), 3000) };
  return { tipo: "ne" };
}

export async function POST(req: Request) {
  let corpo: { instituicao_id?: unknown; respostas?: unknown; filtro?: unknown };
  try { corpo = await req.json(); } catch { return Response.json({ erro: "json inválido" }, { status: 400 }); }
  const inst = typeof corpo.instituicao_id === "string" && UUID.test(corpo.instituicao_id) ? corpo.instituicao_id : null;
  const { respostas, erros } = interpretar(corpo.respostas);
  if (erros.length) return Response.json({ erro: "respostas inválidas", detalhes: erros.slice(0, 5) }, { status: 400 });
  const t0 = Date.now();
  const r = await alinhar(respostas.nicho, { instituicao: inst, soQualis: soQualis(req), filtro: lerFiltro(corpo.filtro, !!inst) });
  return Response.json({ ...r, ms: Date.now() - t0 }, { headers: { "cache-control": "no-store" } });
}
