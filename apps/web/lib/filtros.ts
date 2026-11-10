import { AREAS_ORDEM } from "@/components/mapa/areas";
import { ufValida } from "@/lib/areas";

// Início fixo do recorte (YEAR_START da ingestão); o fim é o ano corrente, para o ano novo entrar sozinho
// depois de uma atualização dos dados (scripts/atualizar_dados.sh). A tela inicial usa o período real do banco.
export const ANO_MIN = Number(process.env.ANO_INICIO) || 2022;
export const anoMax = () => new Date().getFullYear();

export type Filtros = { uf?: string; area?: string; de: number; ate: number };

export function lerFiltros(p: URLSearchParams | Record<string, string | undefined>): Filtros {
  const get = (k: string) => (p instanceof URLSearchParams ? p.get(k) ?? undefined : p[k]);
  const ano = (v: string | undefined, padrao: number) => {
    const n = Number(v);
    return Number.isInteger(n) && n >= ANO_MIN && n <= anoMax() ? n : padrao;
  };
  const de = ano(get("de"), ANO_MIN), ate = ano(get("ate"), anoMax());
  const area = get("area");
  return { uf: ufValida(get("uf")), area: area && AREAS_ORDEM.includes(area) ? area : undefined, de: Math.min(de, ate), ate: Math.max(de, ate) };
}
