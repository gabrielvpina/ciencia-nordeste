"use client";
// Mapa de rede (modo "rede") para pesquisador, instituição ou programa: arcos para parceiros do NE e âncoras externas.
import { useEffect, useState } from "react";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import type { DadosMapa } from "@/components/mapa/tipos";
import { fmt } from "@/lib/areas";

type Rede = DadosMapa & { resumo: { works: number; parceiros: number; externos: number } };

export default function RedeEntidade({ tipo, id, nome }: { tipo: "pesquisador" | "instituicao" | "programa"; id: string; nome: string }) {
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
        <b>Rede de colaboração</b>
        {rede && (
          <span className="meta">
            {fmt(rede.resumo.works)} publicações · {rede.resumo.parceiros} instituições parceiras no NE · {rede.resumo.externos} destinos externos
          </span>
        )}
      </div>
      <div className="mapa-area">
        {rede ? <MapaNordeste modo="rede" dados={rede} titulo={`Rede de colaboração de ${nome}`} />
          : <p className="meta centro">{erro ? "Não foi possível carregar a rede." : "Carregando rede…"}</p>}
      </div>
      <div className="mn-legenda legenda-rede">
        <span><i style={{ background: "var(--mn-origem, #e0672b)", borderRadius: "50%" }} />origem</span>
        <span><i style={{ background: "var(--mn-no, #0f6e5a)", borderRadius: "50%" }} />parceiros no Nordeste (espessura = publicações em comum)</span>
        <span><i style={{ background: "var(--mn-arco-externo, #e0672b)" }} />coautoria fora do NE (Brasil e exterior; posições ilustrativas)</span>
      </div>
    </section>
  );
}
