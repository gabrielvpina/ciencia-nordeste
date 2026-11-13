"use client";
// Mapa de rede (modo "rede") para pesquisador, instituição ou programa: arcos para as parceiras do NE; a coautoria fora do NE
// fica numa lista na legenda. Outras partes da página realçam uma instituição com o evento "cn:destaque" (detail = id ou null).
import { useEffect, useState, type ReactNode } from "react";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import type { DadosMapa } from "@/components/mapa/tipos";
import { paramQualis } from "@/lib/qualis-cookie";

type Rede = DadosMapa & { resumo: { works: number; parceiros: number; externos: number } };

export default function RedeEntidade({ tipo, id, nome, abas }: { tipo: "pesquisador" | "instituicao" | "programa"; id: string; nome: string; abas?: ReactNode }) {
  const [rede, setRede] = useState<Rede | null>(null);
  const [erro, setErro] = useState(false);
  const [destaque, setDestaque] = useState<string | null>(null);
  useEffect(() => {
    const ouvir = (e: Event) => setDestaque((e as CustomEvent<string | null>).detail ?? null);
    window.addEventListener("cn:destaque", ouvir);
    return () => window.removeEventListener("cn:destaque", ouvir);
  }, []);
  useEffect(() => {
    const ctl = new AbortController();
    fetch(`/api/rede?tipo=${tipo}&id=${id}&${paramQualis()}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : Promise.reject())).then(setRede).catch(() => setErro(true));
    return () => ctl.abort();
  }, [tipo, id]);
  return (
    <section className="mapa-col" aria-busy={!rede && !erro}>
      <div className="mapa-cabecalho">
        <a href="/painel" className="voltar">Painel</a>
        {abas ?? <b>Mapa da colaboração</b>}
        {rede && (
          <span className="meta">
            {rede.resumo.parceiros} instituições parceiras no Nordeste · passe o mouse para ver os números
          </span>
        )}
      </div>
      <div className="mapa-area">
        {rede ? <MapaNordeste modo="rede" dados={rede} destaque={destaque} titulo={`Rede de colaboração de ${nome}`} />
          : <p className="meta centro">{erro ? "Não foi possível carregar a rede." : "Carregando rede…"}</p>}
      </div>
    </section>
  );
}
