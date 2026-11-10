// Alterna a coluna principal do perfil (programa ou pesquisador) entre o mapa da rede e a produção com Qualis.
// São links (?ver=producao), não estado no navegador: cada visão tem endereço próprio e funciona sem JavaScript.
export type Visao = "rede" | "producao";

export const visaoDe = (v: string | string[] | undefined): Visao => (v === "producao" ? "producao" : "rede");

export default function AbasEntidade({ base, ativa }: { base: string; ativa: Visao }) {
  const abas: [Visao, string, string][] = [["rede", "Rede de colaboração", base], ["producao", "Produção", `${base}?ver=producao`]];
  return (
    <nav className="seg abas-entidade" aria-label="Visualização">
      {abas.map(([v, rotulo, href]) => (
        <a key={v} href={href} className={v === ativa ? "ativo" : undefined} aria-current={v === ativa ? "page" : undefined}>{rotulo}</a>
      ))}
    </nav>
  );
}
