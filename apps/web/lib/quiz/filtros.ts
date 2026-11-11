// Que opções cada pergunta oferece, dadas as respostas anteriores (filtros por método e por objeto, D-036).
// Funções puras, sem o arvore.json: usadas no servidor (estrutura.ts) e no navegador (QuizApp).
export type OpcaoFiltravel = { id: string; objetos?: string[]; metodos?: string[]; sem_metodos?: string[] };
export type PerguntaFiltravel<O extends OpcaoFiltravel> = { opcoes?: O[]; opcoes_por?: Record<string, O[]> };

export function filtrarOpcoes<O extends OpcaoFiltravel>(q: PerguntaFiltravel<O>, metodo?: string, objeto?: string): O[] {
  const ops = q.opcoes_por ? (objeto ? q.opcoes_por[objeto] ?? [] : []) : q.opcoes ?? [];
  return ops.filter((o) =>
    (!metodo || !o.metodos || o.metodos.includes(metodo))
    && (!metodo || !o.sem_metodos?.includes(metodo))
    && (!o.objetos || !objeto || o.objetos.includes(objeto)));
}
