// Texto livre do quiz (D-040): o vetor do texto vira um código curto (129 caracteres) que vai no link do resultado.
// O texto nunca é gravado nem volta ao navegador: só o código, que guarda o tema aproximado, não as palavras.
// Código = versão da base (1 caractere) + 128 coeficientes PCA de 6 bits, um caractere base64url cada.
// Só no servidor: a base (lib/quiz/base-texto-v*.json, ~260 KB) não entra no JavaScript do navegador.
import base1 from "./base-texto-v1.json";

type BaseJson = { versao: number; k: number; bits: number; limite: number; dimensoes: number; media: string; sigma: string; componentes: string };
type Base = { versao: number; k: number; d: number; max: number; passo: Float64Array; media: Float64Array; comp: Float64Array };

/** float16 little-endian (base64) → números. Node 20 não tem Float16Array. */
function f16(b64: string): Float64Array {
  const b = Buffer.from(b64, "base64");
  const out = new Float64Array(b.length / 2);
  for (let i = 0; i < out.length; i++) {
    const h = b[2 * i] | (b[2 * i + 1] << 8);
    const s = h & 0x8000 ? -1 : 1, e = (h >> 10) & 0x1f, m = h & 0x3ff;
    out[i] = e === 0 ? s * m * 2 ** -24 : e === 31 ? (m ? NaN : s * Infinity) : s * (1 + m / 1024) * 2 ** (e - 15);
  }
  return out;
}

function carregar(j: BaseJson): Base {
  const max = 2 ** (j.bits - 1) - 1;   // 6 bits: -31…31
  const sigma = f16(j.sigma);
  return { versao: j.versao, k: j.k, d: j.dimensoes, max, media: f16(j.media), comp: f16(j.componentes),
    passo: sigma.map((s) => (j.limite * s) / max) };
}

const BASES = new Map<string, Base>([["1", carregar(base1 as BaseJson)]]);
const ATUAL = "1";
const ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
export const TEXTO_MAX = 160;   // caracteres aceitos na descrição

/** vetor do e5 (768, normalizado) → código para a URL */
export function codificar(vetor: number[]): string {
  const b = BASES.get(ATUAL)!;
  let cod = ATUAL;
  for (let i = 0; i < b.k; i++) {
    let c = 0;
    for (let j = 0; j < b.d; j++) c += (vetor[j] - b.media[j]) * b.comp[i * b.d + j];
    const q = Math.max(-b.max, Math.min(b.max, Math.round(c / b.passo[i])));
    cod += ALFABETO[q + b.max];
  }
  return cod;
}

/** código da URL → vetor aproximado (literal do pgvector) ou null se for inválido */
export function decodificar(cod: string | null | undefined): string | null {
  if (!cod) return null;
  const b = BASES.get(cod[0]);
  if (!b || cod.length !== b.k + 1) return null;
  const v = Float64Array.from(b.media);
  for (let i = 0; i < b.k; i++) {
    const n = ALFABETO.indexOf(cod[i + 1]);
    if (n < 0 || n > 2 * b.max) return null;
    const c = (n - b.max) * b.passo[i];
    if (c) for (let j = 0; j < b.d; j++) v[j] += c * b.comp[i * b.d + j];
  }
  const norma = Math.hypot(...v);
  return norma ? `[${Array.from(v, (x) => (x / norma).toFixed(6)).join(",")}]` : null;
}

/** Aceita só códigos bem formados (para repassar em links sem decodificar). */
export const codigoValido = (cod: string | null | undefined): cod is string => decodificar(cod) !== null;
