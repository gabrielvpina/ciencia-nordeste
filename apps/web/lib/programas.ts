// Utilidades de exibição dos programas de pós (CAPES), usadas no servidor e no navegador.
export const CONCEITOS = ["3", "4", "5", "6", "7", "outros"] as const;
export const colunaDe = (c: string) => ((CONCEITOS as readonly string[]).includes(c) && c !== "outros" ? c : "outros");
export const COR_CONCEITO: Record<string, string> = { "3": "var(--seq-2)", "4": "var(--seq-3)", "5": "var(--seq-4)", "6": "var(--accent-vivo)", "7": "var(--flow)", outros: "var(--line)" };

/** "CIÊNCIAS AGRÁRIAS I" → "Ciências agrárias I" */
export function nomeArea(a: string | null | undefined) {
  if (!a) return "";
  const s = a.split(" ").map((w) => (/^(I|II|III|IV)$/.test(w) ? w : w.toLowerCase())).join(" ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
/** Nome do programa em caixa normal: "BIOLOGIA ANIMAL" → "Biologia animal". */
export const nomePrograma = (n: string) => n.charAt(0) + n.slice(1).toLowerCase();

export const niveis = (d: string | null) => {
  const u = (d ?? "").toUpperCase();
  if (u.includes("PROFISSIONAL")) return u.includes("DOUTORADO") ? ["MP", "DP"] : ["MP"];
  return [...(u.includes("MESTRADO") ? ["M"] : []), ...(u.includes("DOUTORADO") ? ["D"] : [])];
};
export const TITULO_NIVEL: Record<string, string> = { M: "Mestrado", D: "Doutorado", MP: "Mestrado profissional", DP: "Doutorado profissional" };
