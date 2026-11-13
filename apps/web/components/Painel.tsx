"use client";
// Painel (/painel, D-039, D-044): à esquerda, a busca compacta e, abaixo, os cards de filtro (ou os resultados da busca,
// no mesmo espaço); à direita, o mapa na altura da janela. No desktop tudo cabe numa tela, sem rolagem vertical.
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AREAS_ORDEM, rotuloArea } from "@/components/mapa/areas";
import MapaNordeste from "@/components/mapa/MapaNordeste";
import BuscaGeral from "@/components/BuscaGeral";
import ResultadosBusca from "@/components/ResultadosBusca";
import type { ResultadoPesquisa } from "@/lib/busca-tipos";
import type { DadosMapa, ModoMapa, PontoInst } from "@/components/mapa/tipos";
import type { ResumoInstituicao } from "@/app/api/instituicao-resumo/route";
import { UFS, fmt } from "@/lib/areas";
import type { Filtros } from "@/lib/filtros";
import { gravarSoQualis, paramQualis } from "@/lib/qualis-cookie";

const MODOS: { id: Exclude<ModoMapa, "rede">; rotulo: string; titulo: string; legenda: string }[] = [
  { id: "densidade", rotulo: "Produção", titulo: "Publicações por instituição", legenda: "Altura da barra = publicações (escala de raiz, para as menores não sumirem). Número = posição no ranking. Anel tracejado = tem subunidades: clique para ver." },
  { id: "ligacoes", rotulo: "Colaboração", titulo: "Coautoria entre instituições do Nordeste", legenda: "Espessura do arco = publicações em comum (as 160 ligações mais fortes). Passe o mouse numa instituição para isolar a rede dela." },
  { id: "areas", rotulo: "Áreas", titulo: "Produção de cada estado por área", legenda: "Cada rosca divide a produção do estado entre as áreas. Escolha uma área à esquerda para colorir os estados por ela." },
];

export default function Painel({ inicial, periodo, soQualisInicial, filtros, consultaInicial }: { inicial: DadosMapa; filtros: Filtros; periodo: { min: number; max: number }; soQualisInicial: boolean; consultaInicial: string }) {
  const ANOS = Array.from({ length: periodo.max - periodo.min + 1 }, (_, i) => periodo.min + i);
  const faixaCurta = `${periodo.min}–${String(periodo.max).slice(2)}`;
  // Filtro "só revistas com Qualis" (D-035): vale para o site inteiro (cookie); muda o mapa, as áreas, os anos, os totais e as buscas.
  const [soQualis, setSoQualis] = useState(soQualisInicial);
  const router = useRouter();
  // router.refresh(): o servidor relê o cookie e atualiza o que ele desenha (o aviso do rodapé); o estado desta tela continua.
  const alternarQualis = (v: boolean) => { gravarSoQualis(v); setSoQualis(v); router.refresh(); };
  const [modo, setModo] = useState<Exclude<ModoMapa, "rede">>("densidade");
  const [forma, setForma] = useState<"colunas" | "bolhas">("bolhas");
  const [uf, setUf] = useState(filtros.uf ?? "");
  const [area, setArea] = useState(filtros.area ?? "");
  const [de, setDe] = useState(Math.max(periodo.min, filtros.de));
  const [ate, setAte] = useState(Math.min(periodo.max, filtros.ate));
  const [dados, setDados] = useState<DadosMapa>(inicial);
  const [carregando, setCarregando] = useState(false);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [destaque, setDestaque] = useState<string | null>(null);
  const primeira = useRef(true);

  // Busca (D-044): só roda ao apertar "Buscar"; o resultado ocupa o lugar dos cards de filtro.
  const [consulta, setConsulta] = useState(consultaInicial);
  const [forcarTema, setForcarTema] = useState(false);
  const [res, setRes] = useState<ResultadoPesquisa | null>(null);
  const [buscando, setBuscando] = useState(false);
  const buscar = (t: string) => { setForcarTema(false); setConsulta(t); };
  useEffect(() => {
    if (!consulta) { setRes(null); return; }
    const ctl = new AbortController();
    setBuscando(true); setRes(null);
    fetch(`/api/busca?q=${encodeURIComponent(consulta)}${forcarTema ? "&tema=1" : ""}&${paramQualis(soQualis)}`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : null)).then(setRes).catch(() => {}).finally(() => setBuscando(false));
    return () => ctl.abort();
  }, [consulta, forcarTema, soQualis]);

  useEffect(() => {
    const qs = new URLSearchParams({ ...(consulta && { q: consulta }), ...(uf && { uf }), ...(area && { area }), ...(de !== periodo.min && { de: String(de) }), ...(ate !== periodo.max && { ate: String(ate) }) });
    window.history.replaceState(null, "", qs.toString() ? `/painel?${qs}` : "/painel");
  }, [consulta, uf, area, de, ate, periodo]);

  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }
    const ctl = new AbortController();
    setCarregando(true);
    const qs = new URLSearchParams({ de: String(de), ate: String(ate), ...(uf && { uf }), ...(area && { area }) });
    fetch(`/api/mapa?${qs}&${paramQualis(soQualis)}`, { signal: ctl.signal }).then((r) => r.json()).then(setDados).catch(() => {}).finally(() => setCarregando(false));
    return () => ctl.abort();
  }, [uf, area, de, ate, soQualis]);

  // Ranking: só instituições principais (subunidades ficam dentro da principal, como no mapa).
  const { ranking, subunidades, total } = useMemo(() => {
    const ids = new Set(dados.pontos.map((p) => p.id));
    const principais = dados.pontos.filter((p) => !(p.pai && ids.has(p.pai))).sort((a, b) => b.works - a.works);
    const subunidades = new Map<string, PontoInst[]>();
    for (const p of dados.pontos) if (p.pai && ids.has(p.pai)) subunidades.set(p.pai, [...(subunidades.get(p.pai) ?? []), p]);
    return { ranking: principais, subunidades, total: principais.length };
  }, [dados]);
  const areasUf = useMemo(() => {
    const m = new Map<string, number>();
    for (const a of dados.areas ?? []) if (!uf || a.uf === uf) m.set(a.field, (m.get(a.field) ?? 0) + a.works);
    return AREAS_ORDEM.map((f, i) => ({ f, i, n: m.get(f) ?? 0 })).sort((a, b) => b.n - a.n);
  }, [dados, uf]);

  useEffect(() => { if (selecionado && !dados.pontos.some((p) => p.id === selecionado)) setSelecionado(null); }, [dados, selecionado]);
  const sel = selecionado ? ranking.find((p) => p.id === selecionado) : undefined;
  const [resumoSel, setResumoSel] = useState<ResumoInstituicao | null>(null);
  useEffect(() => {
    if (!selecionado) { setResumoSel(null); return; }
    const ctl = new AbortController();
    fetch(`/api/instituicao-resumo?id=${selecionado}&${paramQualis(soQualis)}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : null)).then(setResumoSel).catch(() => {});
    return () => ctl.abort();
  }, [selecionado, soQualis]);
  const maxAno = Math.max(1, ...(dados.anos ?? []).map((a) => a.works));
  const m = MODOS.find((x) => x.id === modo)!;
  const tudo = de === ANOS[0] && ate === ANOS[ANOS.length - 1];

  const maxArea = Math.max(1, areasUf[0]?.n ?? 1);

  const cardAreas = (
    <section className="painel-card pn-areas">
      <h2>Áreas</h2>
      <p className="linha-cap">Publicações por área em {uf ? UFS.find(([s]) => s === uf)?.[1] : "todo o Nordeste"}. Clique numa área para filtrar.</p>
      <ul className="barras-area">
        {areasUf.map(({ f, i, n }) => (
          <li key={f}>
            <button type="button" className={area === f ? "ativa" : area ? "apagada" : ""} aria-pressed={area === f} title={`${rotuloArea(f)}: ${fmt(n)} publicações`} onClick={() => setArea(area === f ? "" : f)}>
              <span className="nome"><i style={{ background: `var(--area-${i})` }} />{rotuloArea(f)}</span>
              <span className="val">{fmt(n)}</span>
              <span className="barra"><i style={{ width: `${(100 * n) / maxArea}%`, background: `var(--area-${i})` }} /></span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );

  // Instituição selecionada: cartão sobre o mapa, só enquanto há seleção (o mapa já diz "clique numa bolha").
  const cardSelecionada = sel && (
    <section className="painel-card detalhe-sel pn-sel" aria-live="polite" aria-label="Instituição selecionada">
      <button type="button" className="pn-sel-fechar" onClick={() => setSelecionado(null)} aria-label="Fechar">×</button>
      <div className="detalhe-topo">
        <span className="chip-sigla">{(sel.sigla ?? sel.nome).split(",")[0].slice(0, 9)}</span>
        <div><b>{sel.nome}</b><span>{[resumoSel?.municipio, sel.uf].filter(Boolean).join(", ")} · {ranking.indexOf(sel) + 1}ª em publicações</span></div>
      </div>
      <dl className="detalhe-dl">
        <div><dt>no filtro</dt><dd>{fmt(sel.works)}<small> publ.</small></dd></div>
        <div><dt>total {faixaCurta}</dt><dd>{resumoSel ? fmt(resumoSel.works) : "…"}</dd></div>
        <div><dt>pesquisadores</dt><dd>{resumoSel ? fmt(resumoSel.pesquisadores) : "…"}</dd></div>
        <div><dt>programas de pós</dt><dd>{resumoSel ? fmt(resumoSel.programas) : "…"}</dd></div>
      </dl>
      {resumoSel && resumoSel.areas.length > 0 && (
        <ul className="detalhe-areas">
          {resumoSel.areas.slice(0, 4).map((a) => (
            <li key={a.f}><i style={{ background: `var(--area-${Math.max(0, AREAS_ORDEM.indexOf(a.f))})` }} />{rotuloArea(a.f)}<span>{fmt(a.n)}</span></li>
          ))}
        </ul>
      )}
      {subunidades.get(sel.id) && (
        <p className="detalhe-subs">Subunidades: {subunidades.get(sel.id)!.map((x, k) => (
          <a key={x.id} href={`/instituicao/${x.id}`}>{k ? ", " : ""}{x.sigla ?? x.nome}</a>
        ))}</p>
      )}
      <div className="detalhe-acoes">
        <a className="botao-primario" href={`/instituicao/${sel.id}`}>Ver perfil e rede</a>
      </div>
    </section>
  );

  const cardSeletores = (
    <section className="painel-card filtros-mapa" aria-label="Seletores e filtros do mapa">
      <h2>Filtros do mapa</h2>
      <div className="filtro">
        <span className="lbl">Modo</span>
        <div className="grade-seg cols-3" role="tablist" aria-label="Modo do mapa">
          {MODOS.map((x) => (
            <button key={x.id} role="tab" aria-selected={modo === x.id} className={modo === x.id ? "ativo" : ""} onClick={() => setModo(x.id)} title={x.legenda}>
              {x.rotulo}
            </button>
          ))}
        </div>
        {modo === "densidade" && (
          <div className="grade-seg cols-2 forma" role="group" aria-label="Forma dos marcadores">
            <button className={forma === "colunas" ? "ativo" : ""} aria-pressed={forma === "colunas"} onClick={() => setForma("colunas")} title="Relevo: altura comprimida">Cilindros</button>
            <button className={forma === "bolhas" ? "ativo" : ""} aria-pressed={forma === "bolhas"} onClick={() => setForma("bolhas")} title="Área proporcional; mais fácil de clicar">Bolhas</button>
          </div>
        )}
      </div>
      <div className="filtro">
        <span className="lbl">Estado</span>
        <div className="grade-seg cols-5" role="group" aria-label="Estado">
          <button className={!uf ? "ativo" : ""} aria-pressed={!uf} onClick={() => setUf("")} title="Todos os estados do Nordeste">Todos</button>
          {UFS.map(([s, n]) => <button key={s} className={uf === s ? "ativo" : ""} aria-pressed={uf === s} onClick={() => setUf(uf === s ? "" : s)} title={n}>{s}</button>)}
        </div>
      </div>
      <div className="filtro">
        <span className="lbl">Período <small>{de === ate ? de : `${de}–${ate}`}</small></span>
        <div className={`faixa-anos${de === ANOS[ANOS.length - 1] ? " inicio-no-fim" : ""}`}>
          <div className="fa-trilho" aria-hidden>
            <i style={{ left: `${(100 * (de - ANOS[0])) / (ANOS.length - 1)}%`, right: `${(100 * (ANOS[ANOS.length - 1] - ate)) / (ANOS.length - 1)}%` }} />
          </div>
          <input type="range" className="fa-inicio" min={ANOS[0]} max={ANOS[ANOS.length - 1]} step={1} value={de}
            onChange={(e) => setDe(Math.min(Number(e.target.value), ate))} aria-label="Início do período" aria-valuetext={String(de)} />
          <input type="range" className="fa-fim" min={ANOS[0]} max={ANOS[ANOS.length - 1]} step={1} value={ate}
            onChange={(e) => setAte(Math.max(Number(e.target.value), de))} aria-label="Fim do período" aria-valuetext={String(ate)} />
          <div className="fa-marcas" aria-hidden>{ANOS.map((a) => <span key={a} className={a >= de && a <= ate ? "dentro" : ""}>{a}</span>)}</div>
        </div>
      </div>
      <label className="check-qualis">
        <input type="checkbox" checked={soQualis} onChange={(e) => alternarQualis(e.target.checked)} />
        <span>Só publicações em revistas com Qualis <small>(vale para todo o site)</small></span>
      </label>
      {(uf || area || !tudo) && (
        <button type="button" className="chip chip-limpar" onClick={() => { setUf(""); setArea(""); setDe(ANOS[0]); setAte(ANOS[ANOS.length - 1]); }}>limpar filtros</button>
      )}
    </section>
  );

  const cardAnos = (
    <section className="painel-card pn-anos">
      <h2>Produção por ano</h2>
      <p className="linha-cap">Publicações{area ? ` em ${rotuloArea(area).toLowerCase()}` : ""}{uf ? ` (${uf})` : ""}. Clique num ano para filtrar.</p>
      <div className="anos-colunas" role="group" aria-label="Publicações por ano">
        {ANOS.map((a) => {
          const v = dados.anos?.find((x) => x.ano === a)?.works ?? 0;
          const dentro = a >= de && a <= ate;
          return (
            <button key={a} type="button" className={`ano-col${dentro ? " dentro" : ""}`} onClick={() => { setDe(a); setAte(a); }}
              title={`${a}: ${fmt(v)} publicações`} aria-pressed={de === a && ate === a}>
              <span className="ano-val">{v >= 1000 ? `${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil` : fmt(v)}</span>
              <span className="ano-barra"><i style={{ height: `${(100 * v) / maxAno}%` }} /></span>
              <span className="ano-rot">{a}</span>
            </button>
          );
        })}
      </div>
    </section>
  );

  return (
    <div className="pn">
      <h1 className="visualmente-oculto">Painel da pesquisa em ciências da vida no Nordeste</h1>
      <div className="pn-esq">
        <BuscaGeral compacta inicial={consulta} onBuscar={buscar} onLimpar={() => setConsulta("")} ocupado={buscando} />
        {consulta ? (
          <div className="pn-resultados">
            <div className="pn-res-topo">
              <button type="button" className="chip" onClick={() => setConsulta("")}>Voltar aos filtros</button>
              <span className="meta">Resultados para “{consulta}”{res ? ` · ${(res.ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s` : ""}</span>
            </div>
            <ResultadosBusca r={res} carregando={buscando} onFoco={setDestaque} onForcarTema={() => setForcarTema(true)} />
          </div>
        ) : (
          <div className="pn-cards">
            <div className="pn-coluna">{cardAreas}</div>
            <div className="pn-coluna">{cardSeletores}{cardAnos}</div>
          </div>
        )}
      </div>

      <section className="painel-card mapa-card pn-mapa" aria-busy={carregando}>
        <div className="mapa-topo">
          <div className="mapa-titulo">
            {m.titulo}
            <small>{fmt(total)} instituições{area ? ` · ${rotuloArea(area)}` : ""}{uf ? ` · ${uf}` : ""} · {de === ate ? de : `${de}–${ate}`}{carregando ? " · atualizando…" : ""}</small>
          </div>
        </div>
        <div className="mapa-palco">
          <MapaNordeste modo={modo} dados={dados} ufAtiva={uf || undefined} areaAtiva={area || undefined}
            selecionado={selecionado} onSelecionar={setSelecionado} destaque={destaque} forma={forma}
            onSelecionarUf={(x) => setUf(uf === x ? "" : x)} />
        </div>
        {cardSelecionada}
      </section>
    </div>
  );
}
