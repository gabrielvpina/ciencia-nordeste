// Colunas empilhadas: altura = publicações no ano (volume), segmentos = faixa Qualis (rampa ordinal de um tom; "sem Qualis" em cinza).
// SVG renderizado no servidor; a dica de cada segmento é o <title> nativo e a tabela abaixo traz todos os números.
import { fmt } from "@/lib/areas";
import { FAIXAS, corFaixa, type AnoProducao } from "@/lib/qualis";

const L = 44, R = 12, T = 24, B = 30, W = 640, H = 300, GAP = 2, RAIO = 4;

function passoBonito(max: number): number {
  const bruto = max / 4;
  const p = 10 ** Math.floor(Math.log10(Math.max(1, bruto)));
  return [1, 2, 5, 10].map((m) => m * p).find((s) => s >= bruto) ?? p * 10;
}

/** Retângulo com só os cantos de cima arredondados (a ponta de dados; a base fica reta, presa ao eixo). */
function topoArredondado(x: number, y: number, w: number, h: number, r: number): string {
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + rr}Q${x},${y} ${x + rr},${y}H${x + w - rr}Q${x + w},${y} ${x + w},${y + rr}V${y + h}Z`;
}

export default function GraficoQualis({ anos, titulo }: { anos: AnoProducao[]; titulo: string }) {
  const max = Math.max(1, ...anos.map((a) => a.total));
  const passo = passoBonito(max);
  const topo = Math.ceil(max / passo) * passo;
  const ph = H - T - B, pw = W - L - R;
  const y = (v: number) => T + ph - (v / topo) * ph;
  const banda = pw / Math.max(1, anos.length);
  const lb = Math.min(64, banda * 0.58);
  const ticks = Array.from({ length: Math.round(topo / passo) + 1 }, (_, i) => i * passo);

  return (
    <figure className="grafico-qualis">
      <ul className="gq-legenda" aria-label="Legenda: faixas Qualis">
        {FAIXAS.map((f, i) => <li key={f.rotulo}><i style={{ background: corFaixa(i) }} />{f.rotulo}</li>)}
      </ul>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={titulo}>
        {ticks.map((t) => (
          <g key={t} className="gq-grade">
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} />
            <text x={L - 8} y={y(t)} dy="0.32em" textAnchor="end">{fmt(t)}</text>
          </g>
        ))}
        {anos.map((a, k) => {
          const x = L + k * banda + (banda - lb) / 2;
          let acumulado = 0;
          const segs = FAIXAS.map((f, i) => ({ i, rotulo: f.rotulo, v: a.porFaixa[i] })).filter((s) => s.v > 0);
          return (
            <g key={a.ano}>
              {segs.map((s, j) => {
                const y0 = y(acumulado), y1 = y(acumulado + s.v);
                acumulado += s.v;
                const ultimo = j === segs.length - 1;
                const alto = Math.max(0.75, y0 - y1 - (ultimo ? 0 : GAP));
                const dica = `${a.ano} · ${s.rotulo}: ${fmt(s.v)} publicaç${s.v === 1 ? "ão" : "ões"} (${Math.round((100 * s.v) / a.total)}% do ano)`;
                return (
                  <g key={s.i} className="gq-seg">
                    <title>{dica}</title>
                    {ultimo
                      ? <path d={topoArredondado(x, y1, lb, y0 - y1, RAIO)} fill={corFaixa(s.i)} />
                      : <rect x={x} y={y0 - alto} width={lb} height={alto} fill={corFaixa(s.i)} />}
                  </g>
                );
              })}
              {a.total > 0 && <text className="gq-total" x={x + lb / 2} y={y(a.total) - 7} textAnchor="middle">{fmt(a.total)}</text>}
              <text className="gq-ano" x={x + lb / 2} y={H - B + 18} textAnchor="middle">{a.ano}</text>
            </g>
          );
        })}
        <line className="gq-base" x1={L} x2={W - R} y1={y(0)} y2={y(0)} />
      </svg>
      <details className="gq-tabela">
        <summary>Ver os números em tabela</summary>
        <div className="tabela-rolagem">
          <table>
            <thead><tr><th>Ano</th>{FAIXAS.map((f) => <th key={f.rotulo}>{f.rotulo}</th>)}<th>Total</th></tr></thead>
            <tbody>
              {anos.map((a) => (
                <tr key={a.ano}><th>{a.ano}</th>{a.porFaixa.map((v, i) => <td key={i}>{fmt(v)}</td>)}<td><b>{fmt(a.total)}</b></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
