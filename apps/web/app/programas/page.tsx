import type { Metadata } from "next";
import { UFS, ufValida } from "@/lib/areas";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Programas de pós-graduação — Ciência Nordeste" };

type Prog = { id: string; name: string; degree: string; evaluation_area: string; grade: string; entity_acronym: string; uf: string; faculty_count_last_year: number };

export default async function Programas({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  const uf = ufValida(searchParams.uf);
  const areas = await q<{ evaluation_area: string }>(`SELECT DISTINCT evaluation_area FROM graduate_programs ORDER BY 1`);
  const areaSel = areas.some((a) => a.evaluation_area === searchParams.area) ? searchParams.area : undefined;
  const args: unknown[] = [];
  const cond = ["true"];
  if (uf) { args.push(uf); cond.push(`uf = $${args.length}`); }
  if (areaSel) { args.push(areaSel); cond.push(`evaluation_area = $${args.length}`); }
  const lista = await q<Prog>(
    `SELECT id, name, degree, evaluation_area, grade, entity_acronym, uf, faculty_count_last_year FROM graduate_programs
      WHERE ${cond.join(" AND ")} ORDER BY evaluation_area, name`, args);
  return (
    <>
      <h1>Programas de pós-graduação</h1>
      <p className="meta">{lista.length} programas · fonte: CAPES Dados Abertos (CC-BY)</p>
      <form className="busca filtros" action="/programas">
        <select name="uf" defaultValue={uf ?? ""} aria-label="Estado"><option value="">Todos os estados</option>{UFS.map(([s, n]) => <option key={s} value={s}>{n}</option>)}</select>
        <select name="area" defaultValue={areaSel ?? ""} aria-label="Área de avaliação"><option value="">Todas as áreas de avaliação</option>{areas.map((a) => <option key={a.evaluation_area} value={a.evaluation_area}>{a.evaluation_area}</option>)}</select>
        <button type="submit">Filtrar</button>
      </form>
      <ul className="lista">
        {lista.map((p) => (
          <li key={p.id}>
            <a href={`/programa/${p.id}`}>{p.name}</a>
            <div className="meta">{p.entity_acronym} · {p.uf} · {p.degree?.toLowerCase()} · conceito {p.grade} · {p.evaluation_area?.toLowerCase()} · {p.faculty_count_last_year} docentes</div>
          </li>
        ))}
      </ul>
    </>
  );
}
