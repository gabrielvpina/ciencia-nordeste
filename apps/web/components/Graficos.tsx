// Gráficos simples em HTML/CSS para os perfis (renderizados no servidor, sem JavaScript no navegador).
import { fmt } from "@/lib/areas";

type ItemBarra = { id: string; rotulo: string; valor: number; href?: string; cor?: string; sub?: string };

/** Barras horizontais: rótulo, valor e barra proporcional ao maior. A dica nativa (title) mostra o rótulo completo. */
export function BarrasH({ itens, unidade }: { itens: ItemBarra[]; unidade?: string }) {
  const max = Math.max(1, ...itens.map((i) => i.valor));
  return (
    <ul className="barras-h">
      {itens.map((i) => {
        const corpo = (
          <>
            <span className="bh-rotulo">{i.cor && <i style={{ background: i.cor }} />}{i.rotulo}{i.sub && <small>{i.sub}</small>}</span>
            <span className="bh-valor">{fmt(i.valor)}</span>
            <span className="bh-barra"><i style={{ width: `${(100 * i.valor) / max}%`, ...(i.cor ? { background: i.cor } : {}) }} /></span>
          </>
        );
        const title = `${i.rotulo}: ${fmt(i.valor)}${unidade ? ` ${unidade}` : ""}`;
        return <li key={i.id}>{i.href ? <a href={i.href} title={title}>{corpo}</a> : <span title={title}>{corpo}</span>}</li>;
      })}
    </ul>
  );
}

type ItemNuvem = { id: string; rotulo: string; peso: number; href?: string; detalhe?: string };

/** Nuvem: tamanho da fonte e intensidade proporcionais ao peso (raiz, para não exagerar diferenças). */
export function Nuvem({ itens }: { itens: ItemNuvem[] }) {
  const max = Math.max(1, ...itens.map((i) => i.peso));
  return (
    <p className="nuvem">
      {itens.map((i) => {
        const t = Math.sqrt(i.peso / max);
        const estilo = { fontSize: `${0.78 + 0.62 * t}rem`, "--t": t.toFixed(2) } as React.CSSProperties;
        const title = i.detalhe ?? `${i.rotulo}: ${fmt(i.peso)}`;
        return i.href
          ? <a key={i.id} href={i.href} className="nv-item" style={estilo} title={title}>{i.rotulo}</a>
          : <span key={i.id} className="nv-item" style={estilo} title={title}>{i.rotulo}</span>;
      })}
    </p>
  );
}
