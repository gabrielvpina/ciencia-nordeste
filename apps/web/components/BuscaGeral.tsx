"use client";
// Barra de busca (tela inicial, /busca e painel). Só busca ao apertar "Buscar" ou Enter (D-044): a busca vetorial
// é a parte cara e roda uma vez por consulta. Sem `onBuscar`, leva para /busca?q=…; no painel, quem decide é o painel.
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TERMO_MIN } from "@/lib/busca-tipos";

const EXEMPLOS = ["dengue e arboviroses", "UFPE", "melhoramento genético de caprinos", "saúde bucal", "plantas medicinais da caatinga"];

type Props = {
  inicial?: string;
  onBuscar?: (termo: string) => void;
  onLimpar?: () => void;
  autoFoco?: boolean;
  exemplos?: boolean;
  compacta?: boolean;
  ocupado?: boolean;
};

export default function BuscaGeral({ inicial = "", onBuscar, onLimpar, autoFoco, exemplos = false, compacta = false, ocupado = false }: Props) {
  const [termo, setTermo] = useState(inicial);
  const campo = useRef<HTMLInputElement>(null);
  const router = useRouter();
  useEffect(() => setTermo(inicial), [inicial]);

  const buscar = (t: string) => {
    const x = t.trim();
    if (x.length < TERMO_MIN) { campo.current?.focus(); return; }
    if (onBuscar) onBuscar(x);
    else router.push(`/busca?q=${encodeURIComponent(x)}`);
  };
  const limpar = () => { setTermo(""); onLimpar?.(); campo.current?.focus(); };

  return (
    <div className={`busca-bloco${compacta ? " compacta" : ""}`}>
      <form className="busca-grande" role="search" onSubmit={(e) => { e.preventDefault(); buscar(termo); }}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input ref={campo} id="busca" name="q" autoFocus={autoFoco} type="search" value={termo} onChange={(e) => setTermo(e.target.value)} autoComplete="off"
          onKeyDown={(e) => { if (e.key === "Escape") limpar(); }} maxLength={200}
          placeholder={compacta ? "Pesquisador, instituição, programa ou tema" : "Busque um pesquisador, instituição, programa ou tema de pesquisa"} aria-label="Buscar" />
        {termo && <button type="button" className="limpar" onClick={limpar} aria-label="Limpar busca">×</button>}
        <button type="submit" className="botao-buscar" disabled={ocupado} aria-busy={ocupado}>Buscar</button>
      </form>
      {exemplos && (
        <p className="exemplos" aria-label="Exemplos de busca">{EXEMPLOS.map((x) => (
          <button key={x} type="button" className="chip" onClick={() => { setTermo(x); buscar(x); }}>{x}</button>
        ))}</p>
      )}
    </div>
  );
}
