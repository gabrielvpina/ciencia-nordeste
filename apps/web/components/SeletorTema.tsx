"use client";
// Tema claro/escuro. Sem escolha salva, vale o tema do sistema (padrão); clicar num ícone fixa a escolha neste navegador.
// O script em app/layout.tsx aplica a escolha salva antes da primeira pintura (sem piscar).
import { useEffect, useState } from "react";

type Tema = "claro" | "escuro";
const CHAVE_TEMA = "cn-tema";
const REPOSITORIO = "https://github.com/gabrielvpina/ciencia-nordeste";

export default function SeletorTema() {
  const [tema, setTema] = useState<Tema | null>(null);   // tema em vigor (escolhido ou do sistema)
  useEffect(() => {
    let salvo: string | null = null;
    try { salvo = localStorage.getItem(CHAVE_TEMA); } catch { /* sem armazenamento */ }
    if (salvo === "claro" || salvo === "escuro") { setTema(salvo); return; }
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const seguir = () => setTema(mq.matches ? "escuro" : "claro");
    seguir();
    mq.addEventListener("change", seguir);
    return () => mq.removeEventListener("change", seguir);
  }, []);
  const escolher = (t: Tema) => {
    setTema(t);
    document.documentElement.setAttribute("data-theme", t === "claro" ? "light" : "dark");
    try { localStorage.setItem(CHAVE_TEMA, t); } catch { /* sem armazenamento */ }
  };
  return (
    <div className="topo-acoes">
      <div className="seg seg-tema" role="radiogroup" aria-label="Tema">
        <button type="button" role="radio" aria-checked={tema === "claro"} className={tema === "claro" ? "ativo" : ""} onClick={() => escolher("claro")} title="Tema claro" aria-label="Tema claro">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
        </button>
        <button type="button" role="radio" aria-checked={tema === "escuro"} className={tema === "escuro" ? "ativo" : ""} onClick={() => escolher("escuro")} title="Tema escuro" aria-label="Tema escuro">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" /></svg>
        </button>
      </div>
      <a className="botao-icone" href={REPOSITORIO} target="_blank" rel="noopener" title="Código no GitHub" aria-label="Repositório no GitHub">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.08 0 4.41-2.69 5.38-5.26 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" /></svg>
      </a>
    </div>
  );
}
