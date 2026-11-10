"use client";
// Mapa de rede (modo "rede") para pesquisador, instituição ou programa: arcos para parceiros do NE e âncoras externas.
import { useEffect, useState, type ReactNode } from "react";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import type { DadosMapa } from "@/components/mapa/tipos";

type Rede = DadosMapa & { resumo: { works: number; parceiros: number; externos: number } };

export default function RedeEntidade({ tipo, id, nome, abas }: { tipo: "pesquisador" | "instituicao" | "programa"; id: string; nome: string; abas?: ReactNode }) {
  const [rede, setRede] = useState<Rede | null>(null);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    const ctl = new AbortController();
    fetch(`/api/rede?tipo=${tipo}&id=${id}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject())).then(setRede).catch(() => setErro(true));
    return () => ctl.abort();
  }, [tipo, id]);
  return (
    <section className="mapa-col" aria-busy={!rede && !erro}>
      <div className="mapa-cabecalho">
        <a href="/" className="voltar">← mapa geral</a>
        {abas ?? <b>Rede de colaboração</b>}
        {rede && (
          <span className="meta">
            {rede.resumo.parceiros} parceiras no Nordeste · {rede.resumo.externos} destinos externos · passe o mouse para ver os números
          </span>
        )}
      </div>
      <div className="mapa-area">
        {rede ? <MapaNordeste modo="rede" dados={rede} titulo={`Rede de colaboração de ${nome}`} />
          : <p className="meta centro">{erro ? "Não foi possível carregar a rede." : "Carregando rede…"}</p>}
      </div>
    </section>
  );
}
