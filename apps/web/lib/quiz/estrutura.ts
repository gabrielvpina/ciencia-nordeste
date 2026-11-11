// Estrutura do quiz (etapa 13): leitura do arvore.json e interpretação das respostas.
// Usado no servidor. O navegador recebe só a versão enxuta (estruturaCliente), sem os sinais do match.
import arvore from "./arvore.json";
import { filtrarOpcoes } from "./filtros";

export type Sinais = { topics?: string[]; subfields?: string[]; fields?: string[]; termos?: string[]; frase?: string };
export type Opcao = {
  id: string; rotulo: string; descricao?: string; sinais?: Sinais;
  sintagma?: { artigo: "o" | "a" | "os" | "as"; nome: string }; nicho?: string;
  objetos?: string[]; metodos?: string[]; sem_metodos?: string[]; visual?: { cor: string };
};
export type Pergunta = {
  bloco: "nicho" | "perfil"; faceta: string; texto: string;
  opcoes?: Opcao[]; opcoes_por?: Record<string, Opcao[]>; depende_de?: string; filtra_por?: string;
};
export type Arvore = {
  versao: number; telas: string[]; nucleo: string[]; pesos_faceta: Record<string, number>;
  perguntas: Record<string, Pergunta>;
  titulos: {
    arquetipos: Record<string, Record<string, string>>; padrao: string;
    vinculos: Record<string, { modelo: string | null; usa: string | null }>; proibidos: string[];
  };
};

export const ARVORE = arvore as unknown as Arvore;

const todas = (q: Pergunta): Opcao[] => (q.opcoes_por ? Object.values(q.opcoes_por).flat() : q.opcoes ?? []);

/** id da opção -> pergunta e opção */
const INDICE = new Map<string, { pergunta: string; opcao: Opcao }>();
for (const [pid, q] of Object.entries(ARVORE.perguntas)) for (const o of todas(q)) INDICE.set(o.id, { pergunta: pid, opcao: o });

export type Respostas = {
  nicho: Map<string, Opcao>;     // faceta de nicho -> opção (só isto entra no match)
  perfil: Map<string, Opcao>;    // faceta de perfil -> opção (só o banner usa)
};

/** Opções que a pergunta oferece, dadas as respostas anteriores (filtros por objeto e por método). */
export function opcoesOferecidas(pid: string, anteriores: Map<string, Opcao>): Opcao[] {
  return filtrarOpcoes(ARVORE.perguntas[pid], anteriores.get("metodo")?.id, anteriores.get("objeto")?.id);
}

/**
 * Interpreta a lista de ids de opções. Ids desconhecidos, repetidos por pergunta ou incoerentes com as respostas
 * anteriores (ex.: sub-objeto de outro objeto) viram erro: o servidor não aceita sinais nem combinações vindos do cliente.
 */
export function interpretar(ids: unknown): { respostas: Respostas; erros: string[] } {
  const erros: string[] = [];
  const porPergunta = new Map<string, Opcao>();
  if (!Array.isArray(ids) || ids.length > ARVORE.telas.length) return { respostas: { nicho: new Map(), perfil: new Map() }, erros: ["respostas inválidas"] };
  for (const id of ids) {
    const e = typeof id === "string" ? INDICE.get(id) : undefined;
    if (!e) { erros.push(`opção desconhecida: ${String(id).slice(0, 60)}`); continue; }
    if (porPergunta.has(e.pergunta)) { erros.push(`duas respostas para ${e.pergunta}`); continue; }
    porPergunta.set(e.pergunta, e.opcao);
  }
  // coerência, na ordem das telas
  const porFaceta = new Map<string, Opcao>();
  for (const pid of ARVORE.telas) {
    const o = porPergunta.get(pid);
    if (!o) continue;
    if (!opcoesOferecidas(pid, porFaceta).some((x) => x.id === o.id)) { erros.push(`opção ${o.id} não combina com as respostas anteriores`); continue; }
    porFaceta.set(ARVORE.perguntas[pid].faceta, o);
  }
  const nicho = new Map<string, Opcao>(), perfil = new Map<string, Opcao>();
  for (const pid of ARVORE.telas) {
    const q = ARVORE.perguntas[pid], o = porFaceta.get(q.faceta);
    if (o) (q.bloco === "nicho" ? nicho : perfil).set(q.faceta, o);
  }
  return { respostas: { nicho, perfil }, erros };
}

/** Versão enxuta para o navegador: textos, rótulos e filtros; sem sinais, títulos ou frases. */
export function estruturaCliente() {
  const enxuta = (o: Opcao) => ({ id: o.id, rotulo: o.rotulo, descricao: o.descricao, objetos: o.objetos, metodos: o.metodos, sem_metodos: o.sem_metodos });
  return {
    versao: ARVORE.versao,
    telas: ARVORE.telas.map((pid) => {
      const q = ARVORE.perguntas[pid];
      return {
        id: pid, bloco: q.bloco, faceta: q.faceta, texto: q.texto, depende_de: q.depende_de,
        opcoes: q.opcoes?.map(enxuta), opcoes_por: q.opcoes_por && Object.fromEntries(Object.entries(q.opcoes_por).map(([k, v]) => [k, v.map(enxuta)])),
      };
    }),
  };
}
