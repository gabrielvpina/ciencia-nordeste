export default function Paginacao({ pagina, temMais, params }: { pagina: number; temMais: boolean; params: Record<string, string | undefined> }) {
  const link = (p: number) => "?" + new URLSearchParams({ ...Object.fromEntries(Object.entries(params).filter(([, v]) => v)), p: String(p) } as Record<string, string>).toString();
  if (pagina <= 1 && !temMais) return null;
  return (
    <nav className="paginacao" aria-label="Paginação">
      {pagina > 1 ? <a href={link(pagina - 1)}>← anterior</a> : <span />}
      <span className="meta">página {pagina}</span>
      {temMais ? <a href={link(pagina + 1)}>próxima →</a> : <span />}
    </nav>
  );
}
