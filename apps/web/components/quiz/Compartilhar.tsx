"use client";
// Compartilhar um banner: no celular, envia a imagem pela Web Share API (WhatsApp, Instagram…); sem suporte, baixa o PNG.
import { useState } from "react";

// ícones simples (traço), herdam a cor do botão
const Icone = {
  compartilhar: <svg viewBox="0 0 24 24" aria-hidden><circle cx="18" cy="5" r="2.6" /><circle cx="6" cy="12" r="2.6" /><circle cx="18" cy="19" r="2.6" /><path d="m8.3 10.8 7.4-4.4M8.3 13.2l7.4 4.4" /></svg>,
  baixar: <svg viewBox="0 0 24 24" aria-hidden><path d="M12 4v11M7 10.5l5 5 5-5M5 20h14" /></svg>,
  link: <svg viewBox="0 0 24 24" aria-hidden><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2" /><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2" /></svg>,
  ok: <svg viewBox="0 0 24 24" aria-hidden><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>,
  refazer: <svg viewBox="0 0 24 24" aria-hidden><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" /></svg>,
};

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
      <button type="button" className="qr-icone principal" onClick={compartilhar} aria-label="Compartilhar imagem" title="Compartilhar">{Icone.compartilhar}</button>
      <a className="qr-icone" href={src} download={`${nome}.png`} aria-label="Baixar imagem (PNG)" title="Baixar">{Icone.baixar}</a>
      {estado && <small className="meta" role="status">{estado}</small>}
    </div>
  );
}

export function CopiarLink() {
  const [ok, setOk] = useState(false);
  return (
    <button type="button" className={`qr-icone${ok ? " feito" : ""}`} aria-label={ok ? "Link copiado" : "Copiar link do resultado"} title={ok ? "Link copiado" : "Copiar link do resultado"} onClick={async () => {
      try { await navigator.clipboard.writeText(window.location.href); setOk(true); window.setTimeout(() => setOk(false), 2000); } catch { /* sem permissão */ }
    }}>{ok ? Icone.ok : Icone.link}</button>
  );
}

export function Refazer() {
  return <a className="qr-icone" href="/quiz" aria-label="Refazer o quiz" title="Refazer o quiz">{Icone.refazer}</a>;
}
