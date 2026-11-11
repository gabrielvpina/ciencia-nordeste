"use client";
// Compartilhar um banner: no celular, envia a imagem pela Web Share API (WhatsApp, Instagram…); sem suporte, baixa o PNG.
import { useState } from "react";

export function CompartilharBanner({ src, nome, texto }: { src: string; nome: string; texto: string }) {
  const [estado, setEstado] = useState<string | null>(null);
  const compartilhar = async () => {
    setEstado("preparando…");
    try {
      const blob = await (await fetch(src)).blob();
      const arquivo = new File([blob], `${nome}.png`, { type: "image/png" });
      const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
      if (nav.canShare?.({ files: [arquivo] })) {
        await nav.share({ files: [arquivo], text: texto });
        setEstado(null);
        return;
      }
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: `${nome}.png` });
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      setEstado("imagem baixada");
    } catch (e) {
      setEstado((e as Error).name === "AbortError" ? null : "não foi possível compartilhar");
    }
  };
  return (
    <div className="qr-acoes">
      <button type="button" className="quiz-comecar" onClick={compartilhar}>Compartilhar</button>
      <a className="botao-sec" href={src} download={`${nome}.png`}>Baixar</a>
      {estado && <small className="meta">{estado}</small>}
    </div>
  );
}

export function CopiarLink() {
  const [ok, setOk] = useState(false);
  return (
    <button type="button" className="botao-sec" onClick={async () => {
      try { await navigator.clipboard.writeText(window.location.href); setOk(true); window.setTimeout(() => setOk(false), 2000); } catch { /* sem permissão */ }
    }}>{ok ? "Link copiado" : "Copiar link do resultado"}</button>
  );
}
