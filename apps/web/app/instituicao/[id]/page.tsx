import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { TIPOS_INSTITUICAO, area, fmt } from "@/lib/areas";
import RedeEntidade from "@/components/RedeEntidade";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;

type Inst = {
  id: string; name: string; acronym: string | null; kind: string; legal_nature: string | null; academic_org: string | null; uf: string;
  municipio: string | null; latitude: number | null; longitude: number | null; website: string | null; established: number | null;
  works: number; pesquisadores: number; programas: number; ror: string | null; emec: string | null;
};

async function carregar(id: string) {
  if (!UUID.test(id)) return null;
  const [i] = await q<Inst>(
    `SELECT i.id, i.name, i.acronym, i.kind, i.legal_nature, i.academic_org, i.uf, m.name AS municipio, i.latitude, i.longitude, i.website,
            i.established, s.works, s.pesquisadores, s.programas,
            (SELECT value FROM institution_identifiers WHERE institution_id = i.id AND scheme = 'ror' LIMIT 1) AS ror,
            (SELECT value FROM institution_identifiers WHERE institution_id = i.id AND scheme = 'emec' LIMIT 1) AS emec
       FROM institutions i LEFT JOIN municipalities m ON m.ibge_code = i.municipality_ibge
       LEFT JOIN mv_instituicao_stats s ON s.institution_id = i.id WHERE i.id = $1`, [id]);
  return i ?? null;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const i = await carregar(params.id);
  return i ? { title: `${i.name} — Ciência Nordeste`, description: `Pesquisa em ciências da vida na ${i.name} (${i.uf}): pesquisadores, programas de pós e publicações.` } : {};
}

export default async function Instituicao({ params }: { params: { id: string } }) {
  const i = await carregar(params.id);
  if (!i) notFound();
  const [areas, pesquisadores, programas, parceiras] = await Promise.all([
    q<{ primary_field: string; n: string }>(
      `SELECT primary_field, works AS n FROM mv_instituicao_areas WHERE institution_id = $1 ORDER BY works DESC`, [i.id]),
    q<{ id: string; display_name: string; works: number; is_capes_faculty: boolean }>(
      `SELECT id, display_name, works, is_capes_faculty FROM mv_pesquisador_busca WHERE main_institution_id = $1 ORDER BY works DESC LIMIT 20`, [i.id]),
    q<{ id: string; name: string; grade: string; degree: string; evaluation_area: string }>(
      `SELECT id, name, grade, degree, evaluation_area FROM graduate_programs WHERE institution_id = $1 ORDER BY evaluation_area, name`, [i.id]),
    q<{ id: string; name: string; uf: string; n: number }>(
      `SELECT o.id, o.name, o.uf, c.shared_works_count AS n FROM institution_collaborations c
         JOIN institutions o ON o.id = CASE WHEN c.institution_a_id = $1 THEN c.institution_b_id ELSE c.institution_a_id END
        WHERE c.institution_a_id = $1 OR c.institution_b_id = $1 ORDER BY c.shared_works_count DESC LIMIT 15`, [i.id]),
  ]);
  return (
    <div className="explorar invertido">
      <RedeEntidade tipo="instituicao" id={i.id} nome={i.name} />
      <aside className="painel painel-perfil">
      <h1>{i.name} {i.acronym && <span className="meta">({i.acronym})</span>}</h1>
      <p className="meta">
        {[i.municipio, i.uf].filter(Boolean).join(" · ")} · {TIPOS_INSTITUICAO[i.kind] ?? i.kind}
        {i.legal_nature ? ` · ${i.legal_nature}` : ""}{i.established ? ` · fundada em ${i.established}` : ""}
      </p>
      <p>
        {i.website && <a className="tag" href={i.website} rel="noopener">site</a>}
        {i.ror && <a className="tag" href={`https://ror.org/${i.ror}`} rel="noopener">ROR {i.ror}</a>}
        {i.emec && <span className="tag">e-MEC {i.emec}</span>}
      </p>
      <div className="cards">
        <div className="card"><b>{fmt(i.works)}</b><span>publicações no recorte</span></div>
        <div className="card"><b>{fmt(i.pesquisadores)}</b><span>pesquisadores (vínculo principal)</span></div>
        <div className="card"><b>{fmt(i.programas)}</b><span>programas de pós</span></div>
      </div>
      {areas.length > 0 && (<><h2>Publicações por área</h2><p>{areas.map((a) => <span key={a.primary_field} className="tag">{area(a.primary_field)} · {fmt(a.n)}</span>)}</p></>)}
      {programas.length > 0 && (
        <><h2>Programas de pós-graduação</h2>
          <ul className="lista">{programas.map((p) => <li key={p.id}><a href={`/programa/${p.id}`}>{p.name}</a><div className="meta">{p.degree?.toLowerCase()} · conceito {p.grade} · {p.evaluation_area?.toLowerCase()}</div></li>)}</ul></>
      )}
      {pesquisadores.length > 0 && (
        <><h2>Pesquisadores com mais publicações</h2>
          <p>{pesquisadores.map((p) => <a key={p.id} className="tag" href={`/pesquisador/${p.id}`}>{p.display_name} ({p.works})</a>)}</p>
          <p className="meta"><a href={`/?uf=${i.uf}`}>Buscar mais pesquisadores em {i.uf}</a></p></>
      )}
      {parceiras.length > 0 && (
        <><h2>Rede: instituições do Nordeste que mais publicam com esta</h2>
          <ul className="lista">{parceiras.map((p) => <li key={p.id}><a href={`/instituicao/${p.id}`}>{p.name}</a> <span className="meta">· {p.uf} · {fmt(p.n)} publicações em comum</span></li>)}</ul></>
      )}
      </aside>
    </div>
  );
}
