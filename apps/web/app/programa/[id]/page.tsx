import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fmt } from "@/lib/areas";
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
  return (
    <div className="explorar invertido">
      <RedeEntidade tipo="programa" id={p.id} nome={p.name} />
      <aside className="painel painel-perfil">
      <h1>{p.name}</h1>
      <p className="meta">
        {p.instituicao ? <a href={`/instituicao/${p.institution_id}`}>{p.instituicao}</a> : "instituição não vinculada"} · {p.municipality_name} · {p.uf}
      </p>
      <p>
        <span className="tag">{p.degree?.toLowerCase()}</span><span className="tag">{p.modality?.toLowerCase()}</span>
        <span className="tag">conceito CAPES {p.grade}</span><span className="tag">{p.evaluation_area?.toLowerCase()}</span>
        <span className="tag">código CAPES {p.capes_code}</span>{p.start_year && <span className="tag">desde {p.start_year}</span>}
      </p>
      <h2>Docentes ({ultimo}) · {fmt(docentes.length)}</h2>
      <ul className="lista">
        {docentes.map((d) => (
          <li key={d.id}><a href={`/pesquisador/${d.id}`}>{d.display_name}</a>{" "}
            <span className="meta">· {d.category?.toLowerCase()}{d.pq_category ? ` · PQ ${d.pq_category}` : ""}{d.works ? ` · ${d.works} publicações` : ""}</span></li>
        ))}
      </ul>
      {teses.length > 0 && (
        <><h2>Teses e dissertações recentes</h2>
          <ul className="lista">{teses.map((t) => (
            <li key={t.title + t.year}>{t.full_text_url ? <a href={t.full_text_url} rel="noopener">{t.title}</a> : t.title}
              <div className="meta">{t.degree?.toLowerCase()} · {t.author_name} · orientação: {t.advisor_researcher_id ? <a href={`/pesquisador/${t.advisor_researcher_id}`}>{t.advisor_name || "ver perfil"}</a> : t.advisor_name} · {t.year}</div></li>
          ))}</ul></>
      )}
      </aside>
    </div>
  );
}
