// Banner (etapa 13): título descontraído e nicho escrito, a partir das respostas.
// Processo só de apresentação: não lê nem altera o match (lib/quiz/alinhamento.ts). Títulos sempre neutros (D-036).
import { ARVORE, type Opcao, type Respostas } from "./estrutura";

const CONTRACAO = { o: "do", a: "da", os: "dos", as: "das" } as const;
/** "Não, minha pesquisa não depende de um lugar": o título e o nicho ficam gerais (sem ambiente). */
const AMBIENTE_GERAL = "ambiente.qualquer";
const de = (o?: Opcao) => (o?.sintagma ? `${CONTRACAO[o.sintagma.artigo]} ${o.sintagma.nome}` : null);

export type Titulo = {
  principal: string;          // ex.: "Fã nº 1 dos vírus" ou "Magia dos dados"
  secundario: string | null;  // o arquétipo, quando o principal veio do vínculo
  nicho: string;              // ex.: "Bioinformática de vírus da caatinga"
  trilha: string[];           // rótulos das facetas de nicho respondidas, na ordem das telas
  cor: string;                // chave de cor de fundo (habitat)
  acento: string;             // chave de cor de acento (ambiente)
};

export function montarTitulo({ nicho, perfil }: Respostas): Titulo {
  const T = ARVORE.titulos;
  const habitat = perfil.get("habitat"), estilo = perfil.get("estilo"), vinculo = perfil.get("vinculo");
  const arquetipo = (habitat && estilo && T.arquetipos[habitat.id]?.[estilo.id]) || T.padrao;

  // o ambiente só entra no título e no nicho quando a pessoa disse que um lugar é essencial na pesquisa (pergunta 9)
  // o tema (D-051), quando respondido, é o recorte mais específico: vale para o título e para o nicho escrito
  const metodo = nicho.get("metodo"), sub = nicho.get("tema") ?? nicho.get("sub_objeto"), objeto = nicho.get("objeto");
  const ambiente = nicho.get("ambiente")?.id === AMBIENTE_GERAL ? undefined : nicho.get("ambiente");

  let doVinculo: string | null = null;
  const v = vinculo ? T.vinculos[vinculo.id] : undefined;
  if (v?.modelo) {
    // "Sentinela da caatinga" só com ambiente essencial; senão, do objeto ("Sentinela dos anfíbios e répteis")
    const alvo = v.usa === "ambiente" && ambiente?.sintagma ? ambiente : sub ?? objeto;
    const frase = de(alvo);
    if (frase) doVinculo = v.modelo.replace("{de}", frase);
  }

  const partes = [metodo?.nicho ?? "Ciência", sub?.nicho ?? (objeto ? `de ${objeto.rotulo.toLowerCase()}` : ""), ambiente?.nicho ?? ""];
  const nichoEscrito = partes.filter(Boolean).join(" ").replace(/\s+/g, " ").trim();

  return {
    principal: doVinculo ?? arquetipo,
    secundario: doVinculo ? arquetipo : null,
    nicho: nichoEscrito,
    trilha: ARVORE.telas.map((pid) => ARVORE.perguntas[pid]).filter((q) => q.bloco === "nicho")
      .map((q) => nicho.get(q.faceta)).filter((o): o is Opcao => !!o && o.id !== AMBIENTE_GERAL).map((o) => o.rotulo),
    cor: habitat?.visual?.cor ?? "neutro",
    acento: nicho.get("ambiente")?.visual?.cor ?? "neutro",
  };
}
