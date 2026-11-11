// POST /api/quiz/participante — cadastro do quiz (D-037). Só grava (papel quiz_escrita); não devolve nem lê dados.
import { gravar, validar } from "@/lib/quiz/participante";

export const dynamic = "force-dynamic";

// limite simples por origem (em memória): 10 cadastros por minuto
const janela = new Map<string, number[]>();
function excedeu(chave: string): boolean {
  const agora = Date.now(), t = (janela.get(chave) ?? []).filter((x) => agora - x < 60_000);
  t.push(agora); janela.set(chave, t);
  if (janela.size > 5000) janela.clear();
  return t.length > 10;
}

export async function POST(req: Request) {
  const origem = (req.headers.get("x-forwarded-for") ?? "local").split(",")[0].trim();   // usado só aqui, em memória; não é gravado
  if (excedeu(origem)) return Response.json({ erro: "muitas tentativas; aguarde um minuto" }, { status: 429 });
  let corpo: Record<string, unknown>;
  try { corpo = await req.json(); } catch { return Response.json({ erro: "json inválido" }, { status: 400 }); }
  if (typeof corpo.site === "string" && corpo.site) return Response.json({ ok: true });   // campo-isca preenchido: robô; finge que gravou
  const { cadastro, erros } = validar(corpo);
  if (!cadastro) return Response.json({ erro: "dados inválidos", campos: erros }, { status: 400 });
  try {
    const r = await gravar(cadastro);
    if (r === "indisponivel") return Response.json({ erro: "cadastro indisponível no momento" }, { status: 503 });
    return Response.json({ ok: true }, { headers: { "cache-control": "no-store" } });
  } catch (e) {
    console.error("quiz/participante: falha ao gravar", (e as Error).message);
    return Response.json({ erro: "não foi possível salvar agora; tente de novo" }, { status: 503 });
  }
}
