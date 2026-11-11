// POST /api/quiz/texto — { texto } → { codigo } (D-040). A descrição livre da pesquisa vira vetor (e5) e depois um
// código curto para o link do resultado. O texto não é gravado, nem registrado em log, nem devolvido.
import { embedVetor } from "@/lib/vetorial";
import { TEXTO_MAX, codificar } from "@/lib/quiz/texto";

export const dynamic = "force-dynamic";

// limite simples por origem (em memória): 20 por minuto (cada pedido roda o modelo de embedding)
const janela = new Map<string, number[]>();
function excedeu(chave: string): boolean {
  const agora = Date.now(), t = (janela.get(chave) ?? []).filter((x) => agora - x < 60_000);
  t.push(agora); janela.set(chave, t);
  if (janela.size > 5000) janela.clear();
  return t.length > 20;
}

export async function POST(req: Request) {
  const origem = (req.headers.get("x-forwarded-for") ?? "local").split(",")[0].trim();   // só em memória
  if (excedeu(origem)) return Response.json({ erro: "muitas tentativas; aguarde um minuto" }, { status: 429 });
  let corpo: { texto?: unknown };
  try { corpo = await req.json(); } catch { return Response.json({ erro: "json inválido" }, { status: 400 }); }
  const texto = typeof corpo.texto === "string" ? corpo.texto.replace(/\s+/g, " ").trim().slice(0, TEXTO_MAX) : "";
  if (texto.length < 3) return Response.json({ erro: "texto curto demais" }, { status: 400 });
  const vetor = await embedVetor(texto);
  if (!vetor) return Response.json({ erro: "indisponível no momento" }, { status: 503 });
  return Response.json({ codigo: codificar(vetor) }, { headers: { "cache-control": "no-store" } });
}
