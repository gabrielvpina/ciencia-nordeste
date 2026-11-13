// POST /api/quiz/alinhamento — { participante_id, respostas: [ids], instituicao_id?, texto? } (D-042)
// Chamado pelo quiz uma única vez, ao concluir (nunca pela página de resultado, que é aberta por quem recebe o link).
// Recalcula o match como a página de resultado (só o Nordeste inteiro, filtro Qualis do site) e grava as respostas e as
// arestas participante → pesquisador. Não devolve dados.
import { alinhar } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { gravarAlinhamento } from "@/lib/quiz/participante";
import { codigoValido } from "@/lib/quiz/texto";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

// limite simples por origem (em memória): 10 por minuto
const janela = new Map<string, number[]>();
function excedeu(chave: string): boolean {
  const agora = Date.now(), t = (janela.get(chave) ?? []).filter((x) => agora - x < 60_000);
  t.push(agora); janela.set(chave, t);
  if (janela.size > 5000) janela.clear();
  return t.length > 10;
}

export async function POST(req: Request) {
  const origem = (req.headers.get("x-forwarded-for") ?? "local").split(",")[0].trim();   // só em memória
  if (excedeu(origem)) return Response.json({ erro: "muitas tentativas" }, { status: 429 });
  let corpo: { participante_id?: unknown; respostas?: unknown; instituicao_id?: unknown; texto?: unknown };
  try { corpo = await req.json(); } catch { return Response.json({ erro: "json inválido" }, { status: 400 }); }
  const pid = typeof corpo.participante_id === "string" && UUID.test(corpo.participante_id) ? corpo.participante_id : null;
  if (!pid) return Response.json({ erro: "participante inválido" }, { status: 400 });
  const { respostas, erros } = interpretar(corpo.respostas);
  if (erros.length) return Response.json({ erro: "respostas inválidas" }, { status: 400 });
  const ids = (corpo.respostas as string[]).slice(0, 12);
  const inst = typeof corpo.instituicao_id === "string" && UUID.test(corpo.instituicao_id) ? corpo.instituicao_id : null;
  const texto = typeof corpo.texto === "string" && codigoValido(corpo.texto) ? corpo.texto : null;
  const sq = soQualis(req);
  try {
    const r = await alinhar(respostas.nicho, { instituicao: inst, soQualis: sq, texto });
    const g = await gravarAlinhamento(pid, { respostas: ids, texto_codigo: texto, instituicao_id: inst, so_qualis: sq }, r);
    if (g === "indisponivel") return Response.json({ erro: "indisponível" }, { status: 503 });
    if (g === "sem_participante") return Response.json({ erro: "participante inexistente" }, { status: 404 });
    return new Response(null, { status: 204 });
  } catch (e) {
    console.error("quiz/alinhamento: falha ao gravar", (e as Error).message);
    return Response.json({ erro: "falha ao gravar" }, { status: 503 });
  }
}
