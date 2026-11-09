import type { Metadata } from "next";
import Paginacao from "@/components/Paginacao";
import { TIPOS_INSTITUICAO, UFS, fmt, ufValida } from "@/lib/areas";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Instituições — Ciência Nordeste" };

type Inst = { id: string; name: string; acronym: string | null; uf: string; kind: string; works: number; pesquisadores: number; programas: number };
const POR_PAGINA = 50;

export default async function Instituicoes({ searchParams }: { searchParams: Record<string, string | undefined> }) {
  const uf = ufValida(searchParams.uf);
  const tipo = searchParams.tipo && TIPOS_INSTITUICAO[searchParams.tipo] ? searchParams.tipo : undefined;
  const pagina = Math.max(1, Number(searchParams.p) || 1);
  const args: unknown[] = [];
  const cond = ["true"];
  if (uf) { args.push(uf); cond.push(`i.uf = $${args.length}`); }
  if (tipo) { args.push(tipo); cond.push(`i.kind = $${args.length}`); }
  args.push(POR_PAGINA + 1, (pagina - 1) * POR_PAGINA);
  const lista = await q<Inst>(
    `SELECT i.id, i.name, i.acronym, i.uf, i.kind, s.works, s.pesquisadores, s.programas
       FROM institutions i JOIN mv_instituicao_stats s ON s.institution_id = i.id
      WHERE ${cond.join(" AND ")} ORDER BY s.works DESC, s.programas DESC, i.name
      LIMIT $${args.length - 1} OFFSET $${args.length}`, args);
  return (
    <>
      <h1>Instituições</h1>
      <form className="busca filtros" action="/instituicoes">
        <select name="uf" defaultValue={uf ?? ""} aria-label="Estado"><option value="">Todos os estados</option>{UFS.map(([s, n]) => <option key={s} value={s}>{n}</option>)}</select>
        <select name="tipo" defaultValue={tipo ?? ""} aria-label="Tipo"><option value="">Todos os tipos</option>{Object.entries(TIPOS_INSTITUICAO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <button type="submit">Filtrar</button>
      </form>
      <ul className="lista">
        {lista.slice(0, POR_PAGINA).map((i) => (
          <li key={i.id}>
            <a href={`/instituicao/${i.id}`}>{i.name}</a> {i.acronym && <span className="meta">({i.acronym})</span>}
            <div className="meta">{i.uf} · {TIPOS_INSTITUICAO[i.kind] ?? i.kind} · {fmt(i.works)} publicações · {fmt(i.pesquisadores)} pesquisadores · {fmt(i.programas)} programas</div>
          </li>
        ))}
      </ul>
      <Paginacao pagina={pagina} temMais={lista.length > POR_PAGINA} params={{ uf, tipo }} />
    </>
  );
}
