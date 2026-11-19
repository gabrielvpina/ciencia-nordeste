"use client";
// Pedido de apoio por Pix (D-057): QR code, "copia e cola" e a chave. O código vem de lib/pix.ts (scripts/gerar_pix.py),
// gerado sem valor fixo: a pessoa escolhe quanto doar no app do banco.
import { useState } from "react";
import { PIX_CHAVE, PIX_COPIA_COLA, PIX_QR } from "@/lib/pix";

function Copiar({ valor, rotulo, principal }: { valor: string; rotulo: string; principal?: boolean }) {
  const [ok, setOk] = useState(false);
  return (
    <button type="button" className={`apoio-botao${principal ? " principal" : ""}${ok ? " feito" : ""}`} onClick={async () => {
      try { await navigator.clipboard.writeText(valor); setOk(true); window.setTimeout(() => setOk(false), 2200); } catch { /* sem permissão */ }
    }}>{ok ? "Copiado ✓" : rotulo}</button>
  );
}

export function Apoio({ id, compacto }: { id?: string; compacto?: boolean }) {
  return (
    <section className={`apoio${compacto ? " compacto" : ""}`} id={id} aria-labelledby="apoio-titulo">
      <svg className="apoio-qr" viewBox={`0 0 ${PIX_QR.lado} ${PIX_QR.lado}`} role="img" aria-label="QR code Pix para doação ao Ciência Nordeste" shapeRendering="crispEdges">
        <rect width={PIX_QR.lado} height={PIX_QR.lado} fill="#fff" /><path d={PIX_QR.d} fill="#0b1b2b" />
      </svg>
      <div className="apoio-texto">
        <p className="autor-rotulo">Pix · qualquer valor</p>
        <h2 id="apoio-titulo">Ajude a manter o Ciência Nordeste</h2>
        <p>O site é gratuito, aberto e feito de forma independente, sem patrocínio. Qualquer doação ajuda a pagar a hospedagem e a manter no ar a rede da ciência do Nordeste.</p>
        <div className="apoio-acoes">
          <Copiar valor={PIX_COPIA_COLA} rotulo="Copiar Pix copia e cola" principal />
          <Copiar valor={PIX_CHAVE} rotulo="Copiar chave" />
        </div>
        <p className="meta">Aponte a câmera do app do banco para o QR code, ou use o copia e cola. Chave Pix (aleatória): <b>{PIX_CHAVE}</b></p>
      </div>
    </section>
  );
}
