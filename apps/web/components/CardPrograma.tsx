// Card de programa de pós: conceito CAPES em destaque, nome, instituição e níveis.
import { COR_CONCEITO, TITULO_NIVEL, colunaDe, niveis, nomePrograma } from "@/lib/programas";

export default function CardPrograma({ id, nome, conceito, nivel, meta, docentes }: {
  id: string; nome: string; conceito: string; nivel: string | null; meta?: string; docentes?: number | null;
}) {
  return (
    <a href={`/programa/${id}`} className="card-prog">
      <span className="cp-conceito" style={{ background: COR_CONCEITO[colunaDe(conceito)] }} title={`Conceito CAPES ${conceito}`}>{conceito}</span>
      <span className="cp-corpo">
        <span className="cp-nome">{nomePrograma(nome)}</span>
        {meta && <span className="cp-meta">{meta}</span>}
        <span className="cp-tags">
          {niveis(nivel).map((n) => <span key={n} className="cp-nivel" title={TITULO_NIVEL[n]}>{n}</span>)}
          {docentes ? <span className="cp-doc">{docentes} docentes</span> : null}
        </span>
      </span>
    </a>
  );
}
