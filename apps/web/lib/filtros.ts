import { AREAS_ORDEM } from "@/components/mapa/areas";
import { ufValida } from "@/lib/areas";

export const ANO_MIN = 2022;
export const ANO_MAX = 2026;

export type Filtros = { uf?: string; area?: string; de: number; ate: number };

export function lerFiltros(p: URLSearchParams | Record<string, string | undefined>): Filtros {
  const get = (k: string) => (p instanceof URLSearchParams ? p.get(k) ?? undefined : p[k]);
  const ano = (v: string | undefined, padrao: number) => {
    const n = Number(v);
    return Number.isInteger(n) && n >= ANO_MIN && n <= ANO_MAX ? n : padrao;
  };
  const de = ano(get("de"), ANO_MIN), ate = ano(get("ate"), ANO_MAX);
  const area = get("area");
  return { uf: ufValida(get("uf")), area: area && AREAS_ORDEM.includes(area) ? area : undefined, de: Math.min(de, ate), ate: Math.max(de, ate) };
}
