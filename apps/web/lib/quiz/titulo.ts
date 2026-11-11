// Banner (etapa 13): título descontraído e nicho escrito, a partir das respostas.
// Processo só de apresentação: não lê nem altera o match (lib/quiz/alinhamento.ts). Títulos sempre neutros (D-036).
import { ARVORE, type Opcao, type Respostas } from "./estrutura";

const CONTRACAO = { o: "do", a: "da", os: "dos", as: "das" } as const;
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

  let doVinculo: string | null = null;
  const v = vinculo ? T.vinculos[vinculo.id] : undefined;
  if (v?.modelo) {
    const ambiente = nicho.get("ambiente");
    const alvo = v.usa === "ambiente" && ambiente?.sintagma ? ambiente : nicho.get("sub_objeto") ?? nicho.get("objeto");
    const frase = de(alvo);
    if (frase) doVinculo = v.modelo.replace("{de}", frase);
  }

  const metodo = nicho.get("metodo"), sub = nicho.get("sub_objeto"), objeto = nicho.get("objeto"), ambiente = nicho.get("ambiente");
  const partes = [metodo?.nicho ?? "Ciência", sub?.nicho ?? (objeto ? `de ${objeto.rotulo.toLowerCase()}` : ""), ambiente?.nicho ?? ""];
  const nichoEscrito = partes.filter(Boolean).join(" ").replace(/\s+/g, " ").trim();

  return {
    principal: doVinculo ?? arquetipo,
    secundario: doVinculo ? arquetipo : null,
    nicho: nichoEscrito,
    trilha: ARVORE.telas.map((pid) => ARVORE.perguntas[pid]).filter((q) => q.bloco === "nicho")
      .map((q) => nicho.get(q.faceta)?.rotulo).filter((x): x is string => !!x && x !== "Tanto faz / no laboratório"),
    cor: habitat?.visual?.cor ?? "neutro",
    acento: ambiente?.visual?.cor ?? "neutro",
  };
}
