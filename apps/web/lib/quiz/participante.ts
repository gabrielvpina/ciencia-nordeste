// Cadastro dos participantes do quiz (D-037) e alinhamentos (D-042). Grava com o papel quiz_escrita (só INSERT) — uma
// pool separada da do site, que só lê. O app nunca lê quiz_participantes, quiz_alinhamentos nem quiz_matches.
import { createHash, randomUUID } from "node:crypto";
import { Pool } from "pg";
import type { Resultado } from "./alinhamento";
import { ARVORE } from "./estrutura";

export const CONSENTIMENTO_VERSAO = "2026-11-11f";   // b: sem e-mail; c: controlador e local do servidor; d: caixa curta + termos (D-041); e: respostas e matches gravados (D-042)
export const FILIACOES = {
  graduacao: "Graduação", mestrado: "Mestrado", doutorado: "Doutorado",
  docente: "Docente", pesquisador: "Pesquisador(a)", mercado: "Profissional do mercado",
} as const;
export type Filiacao = keyof typeof FILIACOES;

const g = globalThis as unknown as { poolQuiz?: Pool };
function pool(): Pool | null {
  if (!process.env.DATABASE_URL_QUIZ || /quiz_escrita:@/.test(process.env.DATABASE_URL_QUIZ)) return null;   // sem senha configurada
  g.poolQuiz ??= new Pool({ connectionString: process.env.DATABASE_URL_QUIZ, max: 2 });
  return g.poolQuiz;
}

const UUID = /^[0-9a-f-]{36}$/i;
const texto = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, max) : "");

export type Cadastro = {
  nome: string; instituicao_id: string | null; instituicao_texto: string; filiacao: Filiacao;
  programa_id: string | null; curso_texto: string;   // sem e-mail: o cadastro não pede contato (D-037)
};

/** Valida o corpo vindo do navegador. Erros em português, por campo. */
export function validar(c: Record<string, unknown>): { cadastro?: Cadastro; erros: Record<string, string> } {
  const erros: Record<string, string> = {};
  const nome = texto(c.nome, 120), inst = texto(c.instituicao_texto, 200), curso = texto(c.curso_texto, 200);
  if (nome.length < 2 || !/\p{L}/u.test(nome)) erros.nome = "Informe o seu nome completo.";
  if (inst.length < 2) erros.instituicao_texto = "Informe a sua instituição.";
  if (!(typeof c.filiacao === "string" && c.filiacao in FILIACOES)) erros.filiacao = "Escolha o tipo de filiação.";
  if (curso.length < 2) erros.curso_texto = "Informe o seu curso ou programa.";
  if (c.consentimento !== true) erros.consentimento = "É preciso concordar para continuar.";
  if (Object.keys(erros).length) return { erros };
  return {
    erros,
    cadastro: {
      nome, instituicao_texto: inst, filiacao: c.filiacao as Filiacao, curso_texto: curso,
      instituicao_id: typeof c.instituicao_id === "string" && UUID.test(c.instituicao_id) ? c.instituicao_id : null,
      programa_id: typeof c.programa_id === "string" && UUID.test(c.programa_id) ? c.programa_id : null,
    },
  };
}

/** Grava o cadastro e devolve o id, que fica só na memória do navegador para ligar o alinhamento (D-042).
 *  O código de remoção (D-041) foi retirado: a coluna codigo_remocao fica nula (D-043). */
export async function gravar(c: Cadastro): Promise<{ id: string } | "indisponivel"> {
  const p = pool();
  if (!p) return "indisponivel";
  const id = randomUUID();
  await p.query(
    `INSERT INTO quiz_participantes (id, nome, instituicao_id, instituicao_texto, filiacao, programa_id, curso_texto, consentimento_versao, versao_quiz)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
    [id, c.nome, c.instituicao_id, c.instituicao_texto, c.filiacao, c.programa_id, c.curso_texto, CONSENTIMENTO_VERSAO, ARVORE.versao]);
  return { id };
}

export type DadosAlinhamento = { respostas: string[]; texto_codigo: string | null; instituicao_id: string | null; so_qualis: boolean };

/** Grava o alinhamento de um quiz concluído (D-042): as respostas e as arestas participante → pesquisador (lista e banner).
 *  "sem_participante": o id não existe (cadastro removido, expirado ou inventado). */
export async function gravarAlinhamento(participanteId: string, d: DadosAlinhamento, r: Resultado): Promise<"ok" | "indisponivel" | "sem_participante"> {
  const p = pool();
  if (!p) return "indisponivel";
  const id = randomUUID();
  const chave = createHash("sha256").update(JSON.stringify([d.respostas, d.texto_codigo, d.instituicao_id])).digest("hex");
  const arestas = new Map<string, { indice: number; n_nicho: number; lista: number | null; banner: number | null }>();
  r.lista.forEach((x, i) => arestas.set(x.id, { indice: x.indice, n_nicho: x.n_nicho, lista: i + 1, banner: null }));
  r.banner.forEach((x, i) => {
    const a = arestas.get(x.id) ?? { indice: x.indice, n_nicho: x.n_nicho, lista: null, banner: null };
    a.banner = i + 1; arestas.set(x.id, a);
  });
  const cliente = await p.connect();
  try {
    await cliente.query("BEGIN");
    // repetição (mesmo participante, mesmas respostas): não grava de novo. Sem alvo no ON CONFLICT, o papel só de
    // INSERT não precisa de SELECT.
    const ins = await cliente.query(
      `INSERT INTO quiz_alinhamentos (id, participante_id, versao_quiz, respostas, texto_codigo, instituicao_id, so_qualis, nucleo, candidatos, chave)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) ON CONFLICT DO NOTHING`,
      [id, participanteId, ARVORE.versao, d.respostas, d.texto_codigo, d.instituicao_id, d.so_qualis, r.nucleo, r.candidatos, chave]);
    if (ins.rowCount && arestas.size) {
      const rs = [...arestas.entries()];
      await cliente.query(
        `INSERT INTO quiz_matches (alinhamento_id, researcher_id, indice, posicao_lista, posicao_banner, n_nicho)
         SELECT $1, * FROM unnest($2::uuid[], $3::smallint[], $4::smallint[], $5::smallint[], $6::int[])`,
        [id, rs.map(([k]) => k), rs.map(([, a]) => a.indice), rs.map(([, a]) => a.lista), rs.map(([, a]) => a.banner), rs.map(([, a]) => a.n_nicho)]);
    }
    await cliente.query("COMMIT");
    return "ok";
  } catch (e) {
    await cliente.query("ROLLBACK").catch(() => {});
    if ((e as { code?: string }).code === "23503") return "sem_participante";   // chave estrangeira: participante inexistente
    throw e;
  } finally {
    cliente.release();
  }
}
