import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Avatar, { type Foto } from "@/components/Avatar";
import { Nuvem } from "@/components/Graficos";
import { AREAS_ORDEM } from "@/components/mapa/areas";
import { area } from "@/lib/areas";
import { COR_CONCEITO, colunaDe, nomePrograma } from "@/lib/programas";
import AbasEntidade, { visaoDe } from "@/components/AbasEntidade";
import ProducaoEntidade from "@/components/ProducaoEntidade";
import RedeEntidade from "@/components/RedeEntidade";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";

type Perfil = {
  id: string; display_name: string; orcid: string | null; is_capes_faculty: boolean; pq_category_latest: string | null;
  instituicao: string | null; uf: string | null; main_institution_id: string | null; works: number | null; first_year: number | null; last_year: number | null; topicos: string[] | null;
};
type Programa = { id: string; name: string; entity_acronym: string; grade: string; category: string; base_year: number };
type Work = { id: string; title: string; year: number; venue: string | null; doi: string | null; primary_field: string };
type Coautor = { id: string; display_name: string; n: number };
type Orientacao = { title: string; degree: string; year: number; author_name: string; programa: string; full_text_url: string | null };

const UUID = /^[0-9a-f-]{36}$/i;

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  if (!UUID.test(params.id)) return {};
  const [p] = await q<{ display_name: string; instituicao: string | null }>(
    `SELECT r.display_name, i.name AS instituicao FROM researchers r LEFT JOIN institutions i ON i.id = r.main_institution_id WHERE r.id = $1`, [params.id]);
  return p ? { title: `${p.display_name} — Ciência Nordeste`, description: `Publicações, orientações e colaborações de ${p.display_name}${p.instituicao ? ` (${p.instituicao})` : ""}.` } : {};
}

export default async function Pesquisador({ params, searchParams }: { params: { id: string }; searchParams: { ver?: string } }) {
  const visao = visaoDe(searchParams.ver);
  if (!UUID.test(params.id)) notFound();
  // UUID antigo que virou alias: redireciona para o perfil canônico (IDs nunca quebram).
  const [alias] = await q<{ researcher_id: string }>(`SELECT researcher_id FROM researcher_aliases WHERE alias_id = $1`, [params.id]);
  if (alias) redirect(`/pesquisador/${alias.researcher_id}`);

  const [p] = await q<Perfil>(
    `SELECT r.id, r.display_name, r.orcid, r.is_capes_faculty, r.pq_category_latest, i.name AS instituicao, i.uf, r.main_institution_id,
            s.works_count_period AS works, s.first_year, s.last_year, s.top_topics AS topicos
       FROM researchers r
       LEFT JOIN institutions i ON i.id = r.main_institution_id
       LEFT JOIN researcher_openalex_stats s ON s.researcher_id = r.id
      WHERE r.id = $1 AND NOT r.is_hidden`,
    [params.id],
  );
  if (!p) notFound();

  const [programas, works, coautores, orientacoes, fotos] = await Promise.all([
    q<Programa>(
      `SELECT DISTINCT ON (g.id) g.id, g.name, g.entity_acronym, g.grade, f.category, f.base_year
         FROM program_faculty f JOIN graduate_programs g ON g.id = f.program_id
        WHERE f.researcher_id = $1 ORDER BY g.id, f.base_year DESC`, [p.id]),
    q<Work>(
      `SELECT w.id, w.title, w.year, w.venue, w.doi, w.primary_field
         FROM work_authorships a JOIN works w ON w.id = a.work_id
        WHERE a.researcher_id = $1 ORDER BY w.year DESC, w.cited_by_count DESC NULLS LAST LIMIT 50`, [p.id]),
    q<Coautor>(
      `SELECT r.id, r.display_name, c.shared_works_count AS n
         FROM coauthorships c JOIN researchers r ON r.id = CASE WHEN c.researcher_a_id = $1 THEN c.researcher_b_id ELSE c.researcher_a_id END
        WHERE c.researcher_a_id = $1 OR c.researcher_b_id = $1
        ORDER BY c.shared_works_count DESC LIMIT 12`, [p.id]),
    q<Orientacao>(
      `SELECT t.title, t.degree, t.year, t.author_name, g.name AS programa, t.full_text_url
         FROM theses t JOIN graduate_programs g ON g.id = t.program_id
        WHERE t.advisor_researcher_id = $1 ORDER BY t.year DESC, t.title LIMIT 30`, [p.id]),
    q<NonNullable<Foto>>(`SELECT license, author, source_page_url FROM researcher_photos WHERE researcher_id = $1`, [p.id]),
  ]);

  return (
    <div className="explorar invertido">
      {visao === "producao"
        ? <ProducaoEntidade tipo="pesquisador" id={p.id} nome={p.display_name} abas={<AbasEntidade base={`/pesquisador/${p.id}`} ativa={visao} />} />
        : <RedeEntidade tipo="pesquisador" id={p.id} nome={p.display_name} abas={<AbasEntidade base={`/pesquisador/${p.id}`} ativa={visao} />} />}
      <aside className="painel painel-perfil">
      <div className="perfil-topo">
        <Avatar id={p.id} nome={p.display_name} foto={fotos[0] ?? null} />
        <div>
      <h1>{p.display_name}</h1>
      <p className="meta">
        {p.main_institution_id ? <a href={`/instituicao/${p.main_institution_id}`}>{p.instituicao}</a> : p.instituicao}{p.uf ? ` · ${p.uf}` : ""}
        {p.works ? ` · ${p.works} publicações em ${p.first_year}–${p.last_year}` : ""}
      </p>
      <p>
        {p.is_capes_faculty && <span className="tag">docente de pós-graduação</span>}
        {p.pq_category_latest && <span className="tag">bolsa de produtividade {p.pq_category_latest}</span>}
        {p.orcid && <a className="tag" href={`https://orcid.org/${p.orcid}`} target="_blank" rel="noopener noreferrer">ORCID {p.orcid}</a>}
      </p>
      {p.topicos && p.topicos.length > 0 && <p>{p.topicos.map((t) => <span key={t} className="tag">{t}</span>)}</p>}
        </div>
      </div>

      {programas.length > 0 && (
        <>
          <h2>Programas de pós-graduação (CAPES)</h2>
          <div className="grade-cards grade-prog grade-estreita">
            {programas.map((g) => (
              <a key={g.id} href={`/programa/${g.id}`} className="card-prog">
                <span className="cp-conceito" style={{ background: COR_CONCEITO[colunaDe(g.grade)] }} title={`Conceito CAPES ${g.grade}`}>{g.grade}</span>
                <span className="cp-corpo"><span className="cp-nome">{nomePrograma(g.name)}</span>
                  <span className="cp-meta">{g.entity_acronym} · docente {g.category?.toLowerCase()} ({g.base_year})</span></span>
              </a>
            ))}
          </div>
        </>
      )}

      {coautores.length > 0 && (
        <>
          <h2>Principais coautores no Nordeste <small className="meta">tamanho = publicações em comum</small></h2>
          <Nuvem itens={coautores.map((c) => ({ id: c.id, rotulo: c.display_name, peso: c.n, href: `/pesquisador/${c.id}`, detalhe: `${c.display_name}: ${c.n} publicações em comum` }))} />
        </>
      )}

      {orientacoes.length > 0 && (
        <>
          <h2>Orientações concluídas (CAPES)</h2>
          <ul className="lista">
            {orientacoes.map((o) => (
              <li key={o.title + o.year}>
                {o.full_text_url ? <a href={o.full_text_url} target="_blank" rel="noopener noreferrer">{o.title}</a> : o.title}
                <div className="meta">{o.degree?.toLowerCase()} · {o.author_name} · {o.programa} · {o.year}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>Publicações recentes</h2>
      {works.length === 0 ? <p className="meta">Sem publicações do recorte ligadas a este perfil.</p> : (
        porAno(works).map(([ano, ws]) => (
          <div key={ano} className="linha-tempo">
            <span className="lt-ano">{ano} <small>{ws.length}</small></span>
            <ul className="lista">
              {ws.map((w) => (
                <li key={w.id}>
                  {w.doi ? <a href={`https://doi.org/${w.doi}`} target="_blank" rel="noopener noreferrer">{w.title}</a> : w.title}
                  <div className="meta"><i className="ponto" style={{ background: `var(--area-${Math.max(0, AREAS_ORDEM.indexOf(w.primary_field))})` }} />{area(w.primary_field)}{w.venue ? ` · ${w.venue}` : ""}</div>
                </li>
              ))}
            </ul>
          </div>
        ))
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
