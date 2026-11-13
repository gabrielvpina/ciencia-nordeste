"use client";
// Docentes do programa numa tabela ordenável (D-046), no lugar da nuvem de nomes.
import { useMemo, useState } from "react";
import { fmt } from "@/lib/areas";

export type Docente = { id: string; nome: string; vinculo: string; pq: string | null; works: number; a12: number; orient: number };
type Col = "nome" | "vinculo" | "works" | "a12" | "orient";
const COLS: [Col, string, string][] = [
  ["nome", "Docente", ""], ["vinculo", "Vínculo", ""], ["works", "Publ.", "publicações na base"],
  ["a12", "A1–A2", "parte das publicações em revistas A1–A2 (Qualis)"], ["orient", "Orient.", "teses e dissertações orientadas no programa"],
];

export default function TabelaDocentes({ docentes }: { docentes: Docente[] }) {
  const [ord, setOrd] = useState<{ col: Col; desc: boolean }>({ col: "works", desc: true });
  const lista = useMemo(() => {
    const v = (d: Docente) => (ord.col === "a12" ? (d.works ? d.a12 / d.works : -1) : d[ord.col]);
    return [...docentes].sort((a, b) => {
      const x = v(a), y = v(b);
      const c = typeof x === "string" ? x.localeCompare(y as string, "pt-BR") : (x as number) - (y as number);
      return ord.desc ? -c : c;
    });
  }, [docentes, ord]);
  const max = Math.max(1, ...docentes.map((d) => d.works));
  return (
    <div className="tab-docentes-caixa">
      <table className="tab-docentes">
        <thead><tr>{COLS.map(([c, rot, dica]) => (
          <th key={c} scope="col" aria-sort={ord.col === c ? (ord.desc ? "descending" : "ascending") : undefined} className={c === "nome" || c === "vinculo" ? "txt" : "num"}>
            <button type="button" title={dica || undefined} onClick={() => setOrd({ col: c, desc: ord.col === c ? !ord.desc : c !== "nome" && c !== "vinculo" })}>
              {rot}{ord.col === c ? (ord.desc ? " ▾" : " ▴") : ""}
            </button>
          </th>
        ))}</tr></thead>
        <tbody>{lista.map((d) => (
          <tr key={d.id}>
            <td className="txt"><a href={`/pesquisador/${d.id}`}>{d.nome}</a>{d.pq && <span className="tag-pq" title={`Bolsa de produtividade ${d.pq}`}>PQ {d.pq}</span>}
              <i className="barra-mini"><b style={{ width: `${(100 * d.works) / max}%` }} /></i></td>
            <td className="txt meta">{d.vinculo}</td>
            <td className="num">{fmt(d.works)}</td>
            <td className="num">{d.works ? `${Math.round((100 * d.a12) / d.works)}%` : "–"}</td>
            <td className="num">{d.orient || "–"}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
