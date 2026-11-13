// Tipos e limites da busca (D-044), sem dependências do servidor: usados também pelos componentes do navegador.
import type { ResultadoTema } from "@/lib/vetorial";

export const TERMO_MIN = 2;
export const TERMO_MAX = 200;

export type ItemNome = { id: string; nome: string; detalhe: string };
export type ResultadoNomes = { pesquisadores: ItemNome[]; instituicoes: ItemNome[]; programas: ItemNome[] };
export type Tese = { id: string; titulo: string; grau: string; ano: number | null; detalhe: string; url: string | null; programa: string | null };
export type ResultadoPesquisa = {
  termo: string;
  nomes: ResultadoNomes;
  /** null quando a busca por tema foi pulada (consulta parece nome) ou é curta demais */
  tema: ResultadoTema | null;
  pareceNome: boolean;
  teses: Tese[];
  ms: number;
};
