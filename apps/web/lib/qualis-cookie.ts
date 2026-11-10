// Filtro "só revistas com Qualis" (D-035): vale para o site inteiro e fica num cookie, para o servidor e o navegador lerem.
// Sem cookie, o filtro está LIGADO (padrão); "0" desliga. Este arquivo não importa nada: serve aos dois lados.
export const COOKIE_QUALIS = "cn-qualis";

/** No navegador: o filtro está ligado? */
export function lerSoQualis(): boolean {
  if (typeof document === "undefined") return true;
  return !document.cookie.split(/;\s*/).includes(`${COOKIE_QUALIS}=0`);
}

/** No navegador: grava a escolha por um ano. */
export function gravarSoQualis(ligado: boolean): void {
  document.cookie = `${COOKIE_QUALIS}=${ligado ? 1 : 0}; path=/; max-age=31536000; samesite=lax`;
}

/** Parâmetro das chamadas às APIs: entra na URL para o cache do navegador separar as duas versões da resposta. */
export const paramQualis = (ligado = lerSoQualis()) => `ql=${ligado ? 1 : 0}`;
