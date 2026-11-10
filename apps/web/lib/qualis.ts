// Produção por ano e estrato Qualis Periódicos 2021-2024 (D-033), para pesquisadores e programas.
import { q } from "@/lib/db";
import { sqlPessoas } from "@/lib/mapa-dados";
import { juntaQualis } from "@/lib/qualis-filtro";

export const ESTRATOS = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"] as const;
export const EVENTO_QUALIS = "2021–2024";

/** Faixas do gráfico: pares de estratos (rampa ordinal de um só tom) + "sem Qualis" em cinza. A cor vem de --qualis-<i>. */
export const FAIXAS = [
  { rotulo: "A1–A2", estratos: ["A1", "A2"] },
  { rotulo: "A3–A4", estratos: ["A3", "A4"] },
  { rotulo: "B1–B2", estratos: ["B1", "B2"] },
  { rotulo: "B3–B4", estratos: ["B3", "B4"] },
  { rotulo: "C", estratos: ["C"] },
  { rotulo: "Sem Qualis", estratos: [] as string[] },
] as const;
export const FAIXA_SEM = FAIXAS.length - 1;

export const corFaixa = (i: number) => (i === FAIXA_SEM ? "var(--qualis-sem)" : `var(--qualis-${i})`);
export function faixaDe(estrato: string | null): number {
  const i = FAIXAS.findIndex((f) => (f.estratos as readonly string[]).includes(estrato ?? ""));
  return i < 0 ? FAIXA_SEM : i;
}

export type AnoProducao = { ano: number; porFaixa: number[]; total: number };
export type Producao = {
  total: number;
  anos: AnoProducao[];
  porEstrato: { estrato: string; n: number }[];   // A1…C e "Sem Qualis", nessa ordem
  revistas: { venue: string; estrato: string | null; n: number }[];
};

/** `sq` = só publicações em revistas com Qualis (filtro do site, D-035). */
export async function dadosProducao(tipo: "pesquisador" | "programa", id: string, sq: boolean): Promise<Producao> {
  const base = `WITH p AS (${sqlPessoas(tipo)}), w AS (SELECT DISTINCT a.work_id FROM work_authorships a JOIN p ON p.rid = a.researcher_id${juntaQualis(sq, "a.work_id")})`;
  const [linhas, revistas] = await Promise.all([
    q<{ ano: number; estrato: string | null; n: number }>(
      `${base} SELECT wk.year AS ano, mq.estrato, count(*)::int AS n
         FROM w JOIN works wk ON wk.id = w.work_id LEFT JOIN mv_work_qualis mq ON mq.work_id = w.work_id
        WHERE wk.year IS NOT NULL GROUP BY 1, 2`, [id]),
    q<{ venue: string; estrato: string | null; n: number }>(
      `${base} SELECT max(wk.venue) AS venue, mq.estrato, count(*)::int AS n
         FROM w JOIN works wk ON wk.id = w.work_id LEFT JOIN mv_work_qualis mq ON mq.work_id = w.work_id
        WHERE COALESCE(wk.venue, '') <> '' GROUP BY wk.venue_openalex_id, mq.estrato ORDER BY n DESC, venue LIMIT 10`, [id]),
  ]);
  const anosVistos = linhas.map((l) => l.ano);
  const anos: AnoProducao[] = [];
  if (anosVistos.length) {
    for (let a = Math.min(...anosVistos); a <= Math.max(...anosVistos); a++) anos.push({ ano: a, porFaixa: FAIXAS.map(() => 0), total: 0 });
  }
  const contagem = new Map<string, number>();
  for (const l of linhas) {
    const ano = anos.find((x) => x.ano === l.ano)!;
    ano.porFaixa[faixaDe(l.estrato)] += l.n;
    ano.total += l.n;
    const chave = l.estrato ?? "Sem Qualis";
    contagem.set(chave, (contagem.get(chave) ?? 0) + l.n);
  }
  return {
    total: anos.reduce((s, a) => s + a.total, 0),
    anos,
    porEstrato: [...ESTRATOS, "Sem Qualis"].map((estrato) => ({ estrato, n: contagem.get(estrato) ?? 0 })),
    revistas,
  };
}
