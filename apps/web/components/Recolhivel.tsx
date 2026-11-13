// Lista longa que mostra só os primeiros itens; o resto abre num <details> (funciona sem JavaScript).
// Evita rolagem desnecessária na barra lateral e no celular.
import { Children, type ReactNode } from "react";

/** `lista`: os itens são <li> de uma <ul>/<ol>; o <details> vai dentro de um <li> (e o resto dentro de uma <ul>). */
export default function Recolhivel({ visiveis = 5, rotulo = "Mostrar mais", lista = false, children }: { visiveis?: number; rotulo?: string; lista?: boolean; children: ReactNode }) {
  const itens = Children.toArray(children);
  if (itens.length <= visiveis + 1) return <>{itens}</>;
  const resto = (
    <details className="recolhivel">
      <summary>{rotulo} {itens.length - visiveis}</summary>
      {lista ? <ul className="lista">{itens.slice(visiveis)}</ul> : itens.slice(visiveis)}
    </details>
  );
  return <>{itens.slice(0, visiveis)}{lista ? <li className="recolhivel-li">{resto}</li> : resto}</>;
}
