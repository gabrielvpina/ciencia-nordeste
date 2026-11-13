"use client";
// Menu do topo (D-047). No celular fica recolhido atrás de um botão; abre como lista em largura total.
// No desktop, os links ficam sempre visíveis (o botão some pelo CSS).
import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

const LINKS: [string, string][] = [["/painel", "Painel"], ["/quiz", "Quiz"], ["/instituicoes", "Instituições"], ["/programas", "Programas"], ["/sobre", "Sobre"]];

export default function MenuTopo({ acoes }: { acoes: ReactNode }) {
  const [aberto, setAberto] = useState(false);
  const caminho = usePathname();
  useEffect(() => setAberto(false), [caminho]);
  useEffect(() => {
    if (!aberto) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setAberto(false); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto]);
  return (
    <>
      <div className="topo-acoes">
        {acoes}
        <button type="button" className="botao-icone menu-botao" aria-expanded={aberto} aria-controls="menu-principal" aria-label={aberto ? "Fechar menu" : "Abrir menu"} onClick={() => setAberto(!aberto)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">{aberto ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}</svg>
        </button>
      </div>
      <nav id="menu-principal" className={`nav${aberto ? " aberto" : ""}`} aria-label="Principal">
        {LINKS.map(([href, rotulo]) => (
          <a key={href} href={href} aria-current={caminho === href || caminho.startsWith(`${href}/`) ? "page" : undefined}>{rotulo}</a>
        ))}
      </nav>
    </>
  );
}
