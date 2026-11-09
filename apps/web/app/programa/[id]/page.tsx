import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Nuvem } from "@/components/Graficos";
import { fmt } from "@/lib/areas";
import { COR_CONCEITO, TITULO_NIVEL, colunaDe, niveis, nomeArea, nomePrograma } from "@/lib/programas";
import RedeEntidade from "@/components/RedeEntidade";
import { q } from "@/lib/db";

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
  return p ? { title: `${p.name} (${p.uf}) — Ciência Nordeste`, description: `Programa de pós-graduação em ${p.name}: docentes, orientações e área de avaliação CAPES.` } : {};
}

export default async function Programa({ params }: { params: { id: string } }) {
  const p = await carregar(params.id);
  if (!p) notFound();
  const ultimo = Math.max(...(p.base_years ?? [0]));
  const [docentes, teses] = await Promise.all([
    q<{ id: string; display_name: string; category: string; pq_category: string | null; works: number | null }>(
      `SELECT r.id, r.display_name, f.category, f.pq_category, s.works_count_period AS works
         FROM program_faculty f JOIN researchers r ON r.id = f.researcher_id LEFT JOIN researcher_openalex_stats s ON s.researcher_id = r.id
        WHERE f.program_id = $1 AND f.base_year = $2 ORDER BY f.category DESC, r.display_name`, [p.id, ultimo]),
    q<{ title: string; degree: string; year: number; author_name: string; advisor_name: string; advisor_researcher_id: string | null; full_text_url: string | null }>(
      `SELECT title, degree, year, author_name, advisor_name, advisor_researcher_id, full_text_url FROM theses
        WHERE program_id = $1 ORDER BY year DESC, defense_date DESC NULLS LAST LIMIT 40`, [p.id]),
  ]);
  const categorias = [...docentes.reduce((m, d) => m.set(d.category ?? "OUTROS", [...(m.get(d.category ?? "OUTROS") ?? []), d]), new Map<string, typeof docentes>())]
    .sort((a, b) => b[1].length - a[1].length);
  return (
    <div className="explorar invertido">
      <RedeEntidade tipo="programa" id={p.id} nome={p.name} />
      <aside className="painel painel-perfil">
      <div className="perfil-topo">
        <span className="cp-conceito cp-grande" style={{ background: COR_CONCEITO[colunaDe(p.grade)] }} title="Conceito CAPES">{p.grade}</span>
        <div><h1>{nomePrograma(p.name)}</h1>
      <p className="meta">
        {p.instituicao ? <a href={`/instituicao/${p.institution_id}`}>{p.instituicao}</a> : "instituição não vinculada"} · {p.municipality_name} · {p.uf}
      </p></div>
      </div>
      <p>
        {niveis(p.degree).map((n) => <span key={n} className="tag">{TITULO_NIVEL[n].toLowerCase()}</span>)}<span className="tag">{p.modality?.toLowerCase()}</span>
        <span className="tag">área de avaliação: {nomeArea(p.evaluation_area)}</span>
        <span className="tag">código CAPES {p.capes_code}</span>{p.start_year && <span className="tag">desde {p.start_year}</span>}
      </p>
      <h2>Docentes em {ultimo} <small className="meta">{fmt(docentes.length)} · tamanho = publicações no recorte</small></h2>
      {categorias.map(([cat, ds]) => (
        <div key={cat} className="grupo-nuvem">
          <h3>{cat.charAt(0) + cat.slice(1).toLowerCase()} <span className="contagem">{ds.length}</span></h3>
          <Nuvem itens={ds.map((d) => ({ id: d.id, rotulo: d.display_name, peso: d.works ?? 0.3, href: `/pesquisador/${d.id}`,
            detalhe: `${d.display_name}${d.pq_category ? ` · bolsa PQ ${d.pq_category}` : ""} · ${d.works ?? 0} publicações` }))} />
        </div>
      ))}
      {teses.length > 0 && (
        <><h2>Teses e dissertações recentes</h2>
          {porAno(teses).map(([ano, ts]) => (
            <div key={ano} className="linha-tempo">
              <span className="lt-ano">{ano}</span>
              <ul className="lista">{ts.map((t) => (
                <li key={t.title + t.year}>{t.full_text_url ? <a href={t.full_text_url} rel="noopener">{t.title}</a> : t.title}
                  <div className="meta">{t.degree?.toLowerCase()} · {t.author_name} · orientação: {t.advisor_researcher_id ? <a href={`/pesquisador/${t.advisor_researcher_id}`}>{t.advisor_name || "ver perfil"}</a> : t.advisor_name}</div></li>
              ))}</ul>
            </div>
          ))}</>
      )}
      </aside>
    </div>
  );
}

function porAno<T extends { year: number }>(itens: T[]): [number, T[]][] {
  const m = new Map<number, T[]>();
  for (const i of itens) m.set(i.year, [...(m.get(i.year) ?? []), i]);
  return [...m.entries()].sort((a, b) => b[0] - a[0]);
}
