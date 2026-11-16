"use client";
// Compartilhar um banner: no celular, envia a imagem pela Web Share API (WhatsApp, Instagram…), no formato do destino; sem suporte, baixa o PNG.
import { useCallback, useEffect, useRef, useState } from "react";

// ícones simples (traço), herdam a cor do botão
const Icone = {
  compartilhar: <svg viewBox="0 0 24 24" aria-hidden><circle cx="18" cy="5" r="2.6" /><circle cx="6" cy="12" r="2.6" /><circle cx="18" cy="19" r="2.6" /><path d="m8.3 10.8 7.4-4.4M8.3 13.2l7.4 4.4" /></svg>,
  baixar: <svg viewBox="0 0 24 24" aria-hidden><path d="M12 4v11M7 10.5l5 5 5-5M5 20h14" /></svg>,
  link: <svg viewBox="0 0 24 24" aria-hidden><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2" /><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2" /></svg>,
  ok: <svg viewBox="0 0 24 24" aria-hidden><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>,
  refazer: <svg viewBox="0 0 24 24" aria-hidden><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" /></svg>,
};

type Formato = "story" | "feed";
const ROTULO: Record<Formato, string> = { story: "Stories / status", feed: "Feed" };

/** Dois destinos, cada um no seu formato: 9:16 para stories e status, 4:5 para o feed. A imagem é baixada antes do toque:
 *  o navigator.share precisa vir logo depois do toque (no Safari do iOS, uma espera de 1–2 s faz o pedido ser recusado). */
export function CompartilharBanner({ src, nome, texto }: { src: Record<Formato, string>; nome: string; texto: string }) {
  const [estado, setEstado] = useState<string | null>(null);
  const blobs = useRef<Partial<Record<Formato, Promise<Blob>>>>({});
  const prontos = useRef<Partial<Record<Formato, Blob>>>({});
  const buscar = useCallback((f: Formato) => {
    blobs.current[f] ??= fetch(src[f]).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.blob(); })
      .then((b) => (prontos.current[f] = b), (e) => { delete blobs.current[f]; throw e; });
    return blobs.current[f]!;
  }, [src]);
  useEffect(() => {
    buscar("story").catch(() => {});
    // o feed é gerado sob demanda no servidor: pede depois, sem disputar com a primeira imagem
    const t = window.setTimeout(() => buscar("feed").catch(() => {}), 2500);
    return () => window.clearTimeout(t);
  }, [buscar]);

  const compartilhar = async (f: Formato) => {
    try {
      const blob = prontos.current[f] ?? (setEstado("preparando…"), await buscar(f));
      const arquivo = new File([blob], `${nome}-${f}.png`, { type: "image/png" });
      const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
      const legenda = `${texto} ${window.location.origin}/quiz`;   // o WhatsApp usa como legenda; o Instagram ignora
      if (nav.canShare?.({ files: [arquivo] })) {
        await nav.share({ files: [arquivo], text: legenda });
        setEstado(f === "story" ? "no Instagram, adicione o adesivo de link" : null);
        return;
      }
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: arquivo.name });
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      setEstado("imagem baixada");
    } catch (e) {
      setEstado((e as Error).name === "AbortError" ? null : "não foi possível compartilhar");
    }
  };
  return (
    <div className="qr-acoes">
      {(["story", "feed"] as const).map((f) => (
        <button key={f} type="button" className={`qr-destino${f === "story" ? " principal" : ""}`} onClick={() => compartilhar(f)}
          aria-label={`Compartilhar imagem para ${ROTULO[f].toLowerCase()} (${f === "story" ? "9:16" : "4:5"})`}>
          {Icone.compartilhar}<span>{ROTULO[f]}</span>
        </button>
      ))}
      <a className="qr-icone" href={src.story} download={`${nome}-story.png`} aria-label="Baixar imagem (PNG, 9:16)" title="Baixar">{Icone.baixar}</a>
      {estado && <small className="meta qr-estado" role="status">{estado}</small>}
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
