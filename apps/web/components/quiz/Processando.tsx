"use client";
// Tela de espera entre a última resposta e o resultado: barra que avança e mensagens do que está sendo feito.
// O match leva de meio segundo a alguns segundos (nichos amplos); a barra nunca chega a 100% sozinha.
import { useEffect, useState } from "react";

const ETAPAS = [
  "Lendo as suas respostas…",
  "Montando o seu perfil de cientista…",
  "Comparando com os perfis de pesquisa do Nordeste…",
  "Calculando a compatibilidade…",
  "Escolhendo pesquisadores de instituições diferentes…",
  "Preparando os seus cartões…",
];

export default function Processando() {
  const [t, setT] = useState(0);   // décimos de segundo desde o início
  useEffect(() => { const id = window.setInterval(() => setT((x) => x + 1), 100); return () => window.clearInterval(id); }, []);
  const pct = Math.round(94 * (1 - Math.exp(-t / 22)));   // rápido no começo, desacelerando perto de 94%
  const etapa = ETAPAS[Math.min(ETAPAS.length - 1, Math.floor(t / 9))];
  return (
    <section className="quiz-processando" role="status" aria-live="polite" aria-busy="true">
      <div className="quiz-selo girando" aria-hidden>?</div>
      <h2>Processando o seu perfil</h2>
      <div className="quiz-progresso grande" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Processando o seu perfil">
        <i style={{ width: `${pct}%` }} />
      </div>
      <p className="qp-etapa">{etapa}</p>
    </section>
  );
}
