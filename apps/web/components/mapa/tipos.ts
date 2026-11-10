// Contratos de dados do mapa (o componente só desenha; quem chama busca os dados).
export type ModoMapa = "densidade" | "ligacoes" | "areas" | "rede";

export type PontoInst = {
  id: string; nome: string; sigla: string | null; uf: string; lat: number; lon: number; works: number;
  tipo?: string;               // kind da instituição (rótulo no tooltip)
  pai?: string | null;         // subunidade de outra instituição (v_instituicao_vinculo): fica oculta até o pai ser selecionado
};
export type Ligacao = { a: string; b: string; works: number };
export type AreaUf = { uf: string; field: string; works: number };
export type Externo = { rotulo: string; works: number; tipo: "brasil" | "exterior" };

export type DadosMapa = {
  pontos: PontoInst[];
  ligacoes?: Ligacao[];
  areas?: AreaUf[];
  rede?: { origem: string[]; parceiros: { id: string; works: number }[]; externos: Externo[] };
  anos?: { ano: number; works: number }[];       // publicações únicas por ano (filtro de estado e área; todos os anos)
};
