"use client";
// Dica (tooltip) que acompanha o mouse; no toque, aparece por 3,5 s. Mesmo visual da dica do mapa.
import { useEffect, useRef, useState } from "react";

export type ConteudoDica = { titulo: string; sub?: string; linhas?: [string, string][]; nota?: string };

export function useDica() {
  const [d, setD] = useState<(ConteudoDica & { x: number; y: number }) | null>(null);
  const t = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(t.current), []);
  const props = (c: () => ConteudoDica) => ({
    onPointerEnter: (e: React.PointerEvent) => { setD({ ...c(), x: e.clientX, y: e.clientY }); clearTimeout(t.current); if (e.pointerType === "touch") t.current = setTimeout(() => setD(null), 3500); },
    onPointerMove: (e: React.PointerEvent) => { if (e.pointerType !== "touch") setD({ ...c(), x: e.clientX, y: e.clientY }); },
    onPointerLeave: (e: React.PointerEvent) => { if (e.pointerType !== "touch") setD(null); },
  });
  const dica = d && (
    <div className="mn-dica dica-fixa" role="tooltip"
      style={{ left: d.x, top: d.y, transform: `translate(${d.x > window.innerWidth - 300 ? "calc(-100% - 14px)" : "14px"}, ${d.y > window.innerHeight - 160 ? "calc(-100% - 14px)" : "14px"})` }}>
      <b>{d.titulo}</b>
      {d.sub && <span className="mn-dica-sub">{d.sub}</span>}
      {d.linhas?.map(([k, v]) => <div key={k} className="mn-dica-linha">{k}<em>{v}</em></div>)}
      {d.nota && <span className="mn-dica-nota">{d.nota}</span>}
    </div>
  );
  return { props, dica };
}
