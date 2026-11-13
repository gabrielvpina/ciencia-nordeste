// Alterna a coluna principal do perfil (programa ou pesquisador): mapa da rede, rede de coautoria e produção com Qualis.
// São links (?ver=…), não estado no navegador: cada visão tem endereço próprio e funciona sem JavaScript.
export type Visao = "rede" | "coautores" | "producao";

export const visaoDe = (v: string | string[] | undefined): Visao => (v === "producao" ? "producao" : v === "coautores" ? "coautores" : "rede");

export default function AbasEntidade({ base, ativa, coautores }: { base: string; ativa: Visao; coautores?: string }) {
  const abas: [Visao, string, string][] = [
    ["rede", "Mapa", base],
    ...(coautores ? [["coautores", coautores, `${base}?ver=coautores`] as [Visao, string, string]] : []),
    ["producao", "Produção", `${base}?ver=producao`],
  ];
  return (
    <nav className="seg abas-entidade" aria-label="Visualização">
      {abas.map(([v, rotulo, href]) => (
        <a key={v} href={href} className={v === ativa ? "ativo" : undefined} aria-current={v === ativa ? "page" : undefined}>{rotulo}</a>
      ))}
    </nav>
  );
}
