import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Recolhivel from "@/components/Recolhivel";
import RedeCoautoria from "@/components/RedeCoautoria";
import TabelaDocentes, { type Docente } from "@/components/TabelaDocentes";
import { fmt } from "@/lib/areas";
import { COR_CONCEITO, TITULO_NIVEL, colunaDe, niveis, nomeArea, nomePrograma } from "@/lib/programas";
import AbasEntidade, { visaoDe } from "@/components/AbasEntidade";
import ProducaoEntidade from "@/components/ProducaoEntidade";
import RedeEntidade from "@/components/RedeEntidade";
import { q } from "@/lib/db";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

type Prog = {
  id: string; name: string; capes_code: string; degree: string; modality: string; evaluation_area: string; knowledge_area: string; grade: string;
  status: string; start_year: number | null; uf: string; municipality_name: string; institution_id: string | null; instituicao: string | null; base_years: number[];
};

async function carregar(id: string) {
  if (!UUID.test(id)) return null;
  const [p] = await q<Prog>(
    `SELECT g.*, i.name AS instituicao FROM graduate_programs g LEFT JOIN institutions i ON i.id = g.institution_id WHERE g.id = $1`, [id]);
  return p ?? null;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const p = await carregar(params.id);
  return p ? { title: `${nomePrograma(p.name)} (${p.uf}) — Ciência Nordeste`, description: `Programa de pós-graduação em ${p.name}: docentes, orientações e área de avaliação CAPES.` } : {};
}

export default async function Programa({ params, searchParams }: { params: { id: string }; searchParams: { ver?: string } }) {
  const visao = visaoDe(searchParams.ver);
  const p = await carregar(params.id);
  if (!p) notFound();
  const ultimo = Math.max(...(p.base_years ?? [0]));
  const sq = soQualis();
  const [docentes, teses, tesesAno] = await Promise.all([
    // por docente: publicações (com o filtro, só em revistas com Qualis), parte em A1–A2 e orientações no programa
    q<Docente>(
      `SELECT r.id, r.display_name AS nome, initcap(lower(f.category)) AS vinculo, f.pq_category AS pq,
              count(DISTINCT a.work_id)::int AS works,
              count(DISTINCT a.work_id) FILTER (WHERE mq.estrato IN ('A1', 'A2'))::int AS a12,
              (SELECT count(*)::int FROM theses t WHERE t.program_id = f.program_id AND t.advisor_researcher_id = r.id) AS orient
         FROM program_faculty f JOIN researchers r ON r.id = f.researcher_id AND NOT r.is_hidden
         LEFT JOIN work_authorships a ON a.researcher_id = r.id${sq ? " AND a.work_id IN (SELECT work_id FROM mv_work_qualis)" : ""}
         LEFT JOIN mv_work_qualis mq ON mq.work_id = a.work_id
        WHERE f.program_id = $1 AND f.base_year = $2
        GROUP BY r.id, f.category, f.pq_category, f.program_id ORDER BY works DESC`, [p.id, ultimo]),
    q<{ title: string; degree: string; year: number; author_name: string; advisor_name: string; advisor_researcher_id: string | null; full_text_url: string | null }>(
      `SELECT title, degree, year, author_name, advisor_name, advisor_researcher_id, full_text_url FROM theses
        WHERE program_id = $1 ORDER BY year DESC, defense_date DESC NULLS LAST LIMIT 40`, [p.id]),
    q<{ ano: number; dissertacoes: number; teses: number }>(
      `SELECT year AS ano, count(*) FILTER (WHERE degree = 'DISSERTAÇÃO')::int AS dissertacoes, count(*) FILTER (WHERE degree = 'TESE')::int AS teses
         FROM theses WHERE program_id = $1 AND year IS NOT NULL GROUP BY 1 ORDER BY 1`, [p.id]),
  ]);
  const porVinculo = [...docentes.reduce((m, d) => m.set(d.vinculo, (m.get(d.vinculo) ?? 0) + 1), new Map<string, number>())].sort((a, b) => b[1] - a[1]);
  const maxAno = Math.max(1, ...tesesAno.map((t) => t.dissertacoes + t.teses));
  const abas = <AbasEntidade base={`/programa/${p.id}`} ativa={visao} coautores="Docentes" />;
  const identidade = (
    <div className="perfil-topo">
      <span className="cp-conceito cp-grande" style={{ background: COR_CONCEITO[colunaDe(p.grade)] }} title="Conceito CAPES">{p.grade}</span>
      <div><h1>{nomePrograma(p.name)}</h1>
        <p className="meta">
          {p.instituicao ? <a href={`/instituicao/${p.institution_id}`}>{p.instituicao}</a> : "instituição não vinculada"} · {nomeCidade(p.municipality_name)} · {p.uf}
        </p></div>
    </div>
  );

  return (
    <div className="explorar invertido">
      {visao === "producao" ? <ProducaoEntidade tipo="programa" id={p.id} nome={p.name} abas={abas} />
        : visao === "coautores" ? <RedeCoautoria tipo="programa" id={p.id} abas={abas} />
        : <RedeEntidade tipo="programa" id={p.id} nome={p.name} abas={abas} />}
      <aside className="painel painel-perfil">
        {identidade}
        {visao === "coautores" ? (
          <>
            <h2>Docentes em {ultimo} <small className="meta">{fmt(docentes.length)} · clique no título de uma coluna para ordenar</small></h2>
            <TabelaDocentes docentes={docentes} />
          </>
        ) : (
          <>
            <p className="tags-linha">
              {niveis(p.degree).map((n) => <span key={n} className="tag">{TITULO_NIVEL[n].toLowerCase()}</span>)}<span className="tag">{p.modality?.toLowerCase()}</span>
              <span className="tag">área de avaliação: {nomeArea(p.evaluation_area)}</span>
              <span className="tag">código CAPES {p.capes_code}</span>{p.start_year && <span className="tag">desde {p.start_year}</span>}
            </p>
            <h2>Docentes em {ultimo} <small className="meta">{fmt(docentes.length)}</small></h2>
            <p className="resumo-docentes">
              {porVinculo.map(([v, n]) => <span key={v}><b>{n}</b> {v.toLowerCase()}{n > 1 ? "s" : ""}</span>)}
            </p>
            <ol className="lista-coautores">
              {docentes.slice(0, 5).map((d) => (
                <li key={d.id}><a href={`/pesquisador/${d.id}`}>{d.nome}</a><span className="meta">{d.vinculo.toLowerCase()}{d.pq ? ` · PQ ${d.pq}` : ""}</span>
                  <em title="publicações">{fmt(d.works)}</em><i><b style={{ width: `${(100 * d.works) / Math.max(1, docentes[0]?.works ?? 1)}%` }} /></i></li>
              ))}
            </ol>
            <a className="mais-itens" href={`/programa/${p.id}?ver=coautores`}>Ver todos os docentes e quem publica com quem</a>

            {tesesAno.length > 0 && (
              <>
                <h2>Teses e dissertações por ano</h2>
                <div className="hist-teses" role="img" aria-label={`Defesas por ano: ${tesesAno.map((t) => `${t.ano}: ${t.dissertacoes} dissertações e ${t.teses} teses`).join("; ")}`}>
                  {tesesAno.map((t) => (
                    <div key={t.ano} className="ht-col" title={`${t.ano}: ${t.dissertacoes} dissertações, ${t.teses} teses`}>
                      <span className="ht-val">{t.dissertacoes + t.teses}</span>
                      <i className="ht-tese" style={{ height: `${(100 * t.teses) / maxAno}%` }} />
                      <i className="ht-diss" style={{ height: `${(100 * t.dissertacoes) / maxAno}%` }} />
                      <span className="ht-ano">{t.ano}</span>
                    </div>
                  ))}
                </div>
                <p className="ht-legenda"><span><i className="ht-diss" />dissertações</span><span><i className="ht-tese" />teses</span></p>
              </>
            )}
            {teses.length > 0 && (
              <><h2>Defesas recentes</h2>
                <Recolhivel visiveis={1} rotulo="Anos anteriores:">{porAno(teses).map(([ano, ts]) => (
                  <div key={ano} className="linha-tempo">
                    <span className="lt-ano">{ano} <small>{ts.length}</small></span>
                    <ul className="lista"><Recolhivel visiveis={4} rotulo="Mostrar mais" lista>{ts.map((t) => (
                      <li key={t.title + t.year}>{t.full_text_url ? <a href={t.full_text_url} target="_blank" rel="noopener noreferrer">{caixa(t.title)}</a> : caixa(t.title)}
                        <div className="meta">{t.degree?.toLowerCase()} · {nomeCidade(t.author_name)} · orientação: {t.advisor_researcher_id ? <a href={`/pesquisador/${t.advisor_researcher_id}`}>{t.advisor_name ? nomeCidade(t.advisor_name) : "ver perfil"}</a> : nomeCidade(t.advisor_name ?? "")}</div></li>
                    ))}</Recolhivel></ul>
                  </div>
                ))}</Recolhivel></>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

/** "FORTALEZA" → "Fortaleza"; "MARIA DA SILVA" → "Maria da Silva" (dados da CAPES vêm em maiúsculas). */
function nomeCidade(t: string) {
  if (!t || t !== t.toUpperCase()) return t;
  return t.toLowerCase().replace(/(^|[\s-])(\p{L})/gu, (_, a, b) => a + b.toUpperCase()).replace(/\b(Da|De|Do|Das|Dos|E)\b/g, (x) => x.toLowerCase());
}
/** Título todo em maiúsculas vira caixa de frase. */
function caixa(t: string) {
  if (!t || t !== t.toUpperCase()) return t;
  const m = t.toLowerCase();
  return m.charAt(0).toUpperCase() + m.slice(1);
}

function porAno<T extends { year: number }>(itens: T[]): [number, T[]][] {
  const m = new Map<number, T[]>();
  for (const i of itens) m.set(i.year, [...(m.get(i.year) ?? []), i]);
  return [...m.entries()].sort((a, b) => b[0] - a[0]);
}
