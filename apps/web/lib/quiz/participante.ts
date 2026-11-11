// Cadastro dos participantes do quiz (D-037). Grava com o papel quiz_escrita (só INSERT) — uma pool separada da do site,
// que só lê. O app nunca lê a tabela quiz_participantes.
import { randomUUID } from "node:crypto";
import { Pool } from "pg";
import { ARVORE } from "./estrutura";

export const CONSENTIMENTO_VERSAO = "2026-11-11";
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
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const texto = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, max) : "");

export type Cadastro = {
  nome: string; instituicao_id: string | null; instituicao_texto: string; filiacao: Filiacao;
  email: string | null; programa_id: string | null; curso_texto: string;
};

/** Valida o corpo vindo do navegador. Erros em português, por campo. */
export function validar(c: Record<string, unknown>): { cadastro?: Cadastro; erros: Record<string, string> } {
  const erros: Record<string, string> = {};
  const nome = texto(c.nome, 120), inst = texto(c.instituicao_texto, 200), curso = texto(c.curso_texto, 200), email = texto(c.email, 200).toLowerCase();
  if (nome.length < 2 || !/\p{L}/u.test(nome)) erros.nome = "Informe o seu nome completo.";
  if (inst.length < 2) erros.instituicao_texto = "Informe a sua instituição.";
  if (!(typeof c.filiacao === "string" && c.filiacao in FILIACOES)) erros.filiacao = "Escolha o tipo de filiação.";
  if (email && !EMAIL.test(email)) erros.email = "E-mail inválido (ou deixe em branco).";
  if (curso.length < 2) erros.curso_texto = "Informe o seu curso ou programa.";
  if (c.consentimento !== true) erros.consentimento = "É preciso concordar para continuar.";
  if (Object.keys(erros).length) return { erros };
  return {
    erros,
    cadastro: {
      nome, instituicao_texto: inst, filiacao: c.filiacao as Filiacao, email: email || null, curso_texto: curso,
      instituicao_id: typeof c.instituicao_id === "string" && UUID.test(c.instituicao_id) ? c.instituicao_id : null,
      programa_id: typeof c.programa_id === "string" && UUID.test(c.programa_id) ? c.programa_id : null,
    },
  };
}

export async function gravar(c: Cadastro): Promise<"ok" | "indisponivel"> {
  const p = pool();
  if (!p) return "indisponivel";
  await p.query(
    `INSERT INTO quiz_participantes (id, nome, instituicao_id, instituicao_texto, filiacao, email, programa_id, curso_texto, consentimento_versao, versao_quiz)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
    [randomUUID(), c.nome, c.instituicao_id, c.instituicao_texto, c.filiacao, c.email, c.programa_id, c.curso_texto, CONSENTIMENTO_VERSAO, ARVORE.versao]);
  return "ok";
}
