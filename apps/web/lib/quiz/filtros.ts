// Que opções cada pergunta oferece, dadas as respostas anteriores (filtros por método e por objeto, D-036).
// Funções puras, sem o arvore.json: usadas no servidor (estrutura.ts) e no navegador (QuizApp).
export type OpcaoFiltravel = { id: string; objetos?: string[]; metodos?: string[]; sem_metodos?: string[] };
export type PerguntaFiltravel<O extends OpcaoFiltravel> = { opcoes?: O[]; opcoes_por?: Record<string, O[]>; depende_de?: string };

/** `dependencia`: a resposta da pergunta de que esta depende (`depende_de`), quando não é o objeto (ex.: o tema depende do sub-objeto). */
export function filtrarOpcoes<O extends OpcaoFiltravel>(q: PerguntaFiltravel<O>, metodo?: string, objeto?: string, dependencia?: string): O[] {
  const chave = q.depende_de && q.depende_de !== "objeto" ? dependencia : objeto;
  const ops = q.opcoes_por ? (chave ? q.opcoes_por[chave] ?? [] : []) : q.opcoes ?? [];
  return ops.filter((o) =>
    (!metodo || !o.metodos || o.metodos.includes(metodo))
    && (!metodo || !o.sem_metodos?.includes(metodo))
    && (!o.objetos || !objeto || o.objetos.includes(objeto)));
}
