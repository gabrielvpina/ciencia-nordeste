// Lado do servidor do filtro "só revistas com Qualis" (D-035). Ver lib/qualis-cookie.ts.
import { cookies } from "next/headers";
import { COOKIE_QUALIS } from "@/lib/qualis-cookie";

/** Filtro ligado? Nas APIs vale o parâmetro ?ql=0|1 (mandado pelo navegador); sem ele, o cookie; sem cookie, ligado. */
export function soQualis(req?: Request): boolean {
  const p = req ? new URL(req.url).searchParams.get("ql") : null;
  if (p === "0" || p === "1") return p === "1";
  return cookies().get(COOKIE_QUALIS)?.value !== "0";
}

/** Coluna de contagem das visões materializadas (migração 0011): todas as publicações ou só as com Qualis. */
export const colWorks = (sq: boolean) => (sq ? "works_qualis" : "works");

/** JOIN que restringe uma consulta às publicações com Qualis (`alias` = expressão com o id da publicação). */
export const juntaQualis = (sq: boolean, alias: string) => (sq ? ` JOIN mv_work_qualis mqf ON mqf.work_id = ${alias}` : "");
