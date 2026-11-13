"use client";
// Coautores em lista ordenada (D-046), no lugar da nuvem de nomes: dá para comparar os números e ver a instituição.
// Passar o mouse (ou focar) num coautor realça a instituição dele no mapa da rede (evento "cn:destaque").
import { useState } from "react";
import { fmt } from "@/lib/areas";

export type ItemCoautor = { id: string; nome: string; n: number; instituicao_id: string | null; detalhe: string };

const VISIVEIS = 6;
const realcar = (id: string | null) => window.dispatchEvent(new CustomEvent("cn:destaque", { detail: id }));

export default function ListaCoautores({ itens }: { itens: ItemCoautor[] }) {
  const [todos, setTodos] = useState(false);
  const max = Math.max(1, ...itens.map((c) => c.n));
  const lista = todos ? itens : itens.slice(0, VISIVEIS);
  return (
    <>
      <ol className="lista-coautores">
        {lista.map((c) => (
          <li key={c.id} onPointerEnter={() => realcar(c.instituicao_id)} onPointerLeave={() => realcar(null)}>
            <a href={`/pesquisador/${c.id}`} onFocus={() => realcar(c.instituicao_id)} onBlur={() => realcar(null)}>{c.nome}</a>
            <span className="meta">{c.detalhe}</span>
            <em title="publicações em comum">{fmt(c.n)}</em>
            <i><b style={{ width: `${(100 * c.n) / max}%` }} /></i>
          </li>
        ))}
      </ol>
      {itens.length > VISIVEIS && (
        <button type="button" className="mais-itens" onClick={() => setTodos(!todos)}>{todos ? "Mostrar menos" : `Mostrar mais ${itens.length - VISIVEIS}`}</button>
      )}
    </>
  );
}
