// GET /api/quiz/banner/perfil|afinidades?r=<ids das opções, separados por vírgula>&i=<instituição>&ql=0|1&f=story|feed&t=<código do texto, D-040>
// Gera o banner em PNG no próprio servidor (next/og). A URL leva só ids: o servidor recalcula tudo e não grava nada.
// Arte "Registro de campo" (D-049, docs/arte-banners.md): ficha de catálogo, só cores e formas retas, sem ilustração.
import { ImageResponse } from "next/og";
import { alinhar } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { montarTitulo } from "@/lib/quiz/titulo";
import { ACENTO, FUNDO, LIMA, MUDO, PAINEL, PROPORCAO_MAPA, TINTA, TITULO, carregarFontes, corta, logoSvg, miniMapa } from "@/lib/quiz/visual";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;
const TAMANHOS = { story: [1080, 1920], feed: [1080, 1350] } as const;

const RAIO = 28;
const SOMBRA = (n: number) => `${n}px ${n}px 0 ${TINTA}`;

/** Tamanho da fonte do nicho pelo comprimento: o nicho sai sempre inteiro (até ~95 caracteres), quebrando em linhas. */
function tamNicho(n: number, base: number): number {
  return Math.round(base * (n <= 36 ? 1 : n <= 52 ? 0.9 : n <= 70 ? 0.8 : 0.7));
}

/** Gerador determinístico (mulberry32) a partir das respostas: as mesmas respostas desenham sempre o mesmo código. */
function sorteio(semente: string) {
  let h = 2166136261;
  for (const c of semente) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  let a = h >>> 0;
  const prox = () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return { prox, codigo: `CN-${String((h >>> 0) % 10000).padStart(4, "0")}·${String(((h >>> 0) / 10000 | 0) % 10000).padStart(4, "0")}` };
}

/** Código de barras das respostas: barras de 1 a 4 unidades, quase todas na tinta, poucas no acento. */
function CodigoBarras({ semente, largura, altura, acento }: { semente: string; largura: number; altura: number; acento: string }) {
  const { prox } = sorteio(semente);
  const barras: { w: number; vazio: number; cor: string; h: number }[] = [];
  let usado = 0;
  const u = 6;   // unidade, em px
  while (true) {
    const w = (1 + Math.floor(prox() * 4)) * u, vazio = (1 + Math.floor(prox() * 3)) * u;
    if (usado + w > largura) break;
    barras.push({ w, vazio, cor: prox() < 0.14 ? acento : TINTA, h: prox() < 0.12 ? 0.78 : 1 });
    usado += w + vazio;
  }
  return (
    <div style={{ display: "flex", alignItems: "flex-end", width: largura, height: altura }}>
      {barras.map((b, i) => <div key={i} style={{ display: "flex", width: b.w, height: altura * b.h, background: b.cor, marginRight: i < barras.length - 1 ? b.vazio : 0 }} />)}
    </div>
  );
}

function Cabecalho({ texto, story }: { texto: string; story: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", paddingBottom: story ? 28 : 20, borderBottom: `4px solid ${TINTA}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <img src={logoSvg()} width={story ? 58 : 50} height={story ? 72 : 62} alt="" />
        <div style={{ display: "flex", gap: 10, fontSize: story ? 40 : 34, color: TINTA }}><span>Ciência</span><span style={{ fontWeight: 700, fontFamily: TITULO }}>Nordeste</span></div>
      </div>
      <div style={{ display: "flex", fontSize: story ? 28 : 24, color: MUDO }}>{texto}</div>
    </div>
  );
}

function Rodape({ story, codigo }: { story: boolean; codigo?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", paddingTop: story ? 24 : 16, borderTop: `4px solid ${TINTA}`, fontSize: story ? 30 : 26, color: TINTA }}>
      <div style={{ display: "flex", fontWeight: 700, fontFamily: TITULO }}>ciencianordeste.com.br</div>
      <div style={{ display: "flex", color: MUDO }}>{codigo ?? "descubra o seu perfil de cientista"}</div>
    </div>
  );
}

/** Rótulo pequeno de catálogo. */
const Rotulo = ({ children, story }: { children: string; story: boolean }) => (
  <div style={{ display: "flex", fontSize: story ? 26 : 22, color: MUDO }}>{children}</div>
);

export async function GET(req: Request, { params }: { params: { tipo: string } }) {
  const u = new URL(req.url);
  const tipo = params.tipo === "afinidades" ? "afinidades" : params.tipo === "perfil" ? "perfil" : null;
  if (!tipo) return Response.json({ erro: "tipo inválido" }, { status: 404 });
  const ids = (u.searchParams.get("r") ?? "").split(",").filter(Boolean);
  const { respostas, erros } = interpretar(ids);
  if (erros.length) return Response.json({ erro: "respostas inválidas", detalhes: erros.slice(0, 5) }, { status: 400 });
  const inst = UUID.test(u.searchParams.get("i") ?? "") ? u.searchParams.get("i") : null;
  const [W, H] = TAMANHOS[u.searchParams.get("f") === "feed" ? "feed" : "story"];
  const story = H === 1920;
  const M = story ? 80 : 64;   // margem
  const t = montarTitulo(respostas);
  const fundo = FUNDO[t.cor] ?? FUNDO.neutro, acento = ACENTO[t.acento] ?? ACENTO.neutro;
  const semente = [...ids].sort().join(",");
  const { codigo } = sorteio(semente);
  const fontes = await carregarFontes();

  if (tipo === "perfil") {
    const n = t.principal.length;
    const tam = Math.round((n > 26 ? 118 : n > 18 ? 138 : 160) * (story ? 1 : 0.78));
    const trilha = t.trilha.slice(0, 6);
    return new ImageResponse(
      (
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: W, height: H, padding: M, background: fundo, fontFamily: "DM Sans", color: TINTA }}>
          <Cabecalho texto="Perfil de cientista" story={story} />

          {/* o único gesto grande: o título */}
          <div style={{ display: "flex", flexDirection: "column", gap: story ? 12 : 8 }}>
            <Rotulo story={story}>seu título</Rotulo>
            <div style={{ display: "flex", fontSize: tam, fontWeight: 700, fontFamily: TITULO, lineHeight: 0.98, letterSpacing: -3 }}>{t.principal}</div>
            {t.secundario && <div style={{ display: "flex", fontSize: story ? 46 : 36, color: TINTA, marginTop: 6 }}>{t.secundario}</div>}
          </div>

          {/* ficha: código das respostas e nicho */}
          <div style={{ display: "flex", flexDirection: "column", background: PAINEL, border: `5px solid ${TINTA}`, borderRadius: RAIO, boxShadow: SOMBRA(12),
            padding: story ? "36px 44px" : "26px 34px", gap: story ? 22 : 16 }}>
            <CodigoBarras semente={semente} largura={W - 2 * M - (story ? 98 : 78)} altura={story ? 128 : 92} acento={acento} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: story ? 24 : 20, color: MUDO }}>
              <span>{codigo}</span><span>{ids.length} respostas</span>
            </div>
            <div style={{ display: "flex", height: 3, background: TINTA }} />
            <Rotulo story={story}>nicho</Rotulo>
            <div style={{ display: "flex", fontSize: tamNicho(t.nicho.length, story ? 54 : 40), fontWeight: 700, fontFamily: TITULO, lineHeight: 1.12, marginTop: -8 }}>{t.nicho}</div>
          </div>

          {/* registro numerado das escolhas */}
          <div style={{ display: "flex", flexDirection: story ? "column" : "row", flexWrap: "wrap" }}>
            {trilha.map((x, i) => (
              <div key={x} style={{ display: "flex", alignItems: "baseline", gap: 20, width: story ? "100%" : "50%", padding: story ? "13px 0" : "10px 0",
                borderTop: `2px solid ${TINTA}`, paddingRight: story ? 0 : 20 }}>
                <div style={{ display: "flex", fontSize: story ? 24 : 20, color: MUDO, width: story ? 40 : 32 }}>{String(i + 1).padStart(2, "0")}</div>
                <div style={{ display: "flex", fontSize: story ? 32 : 26, background: i === 0 ? LIMA : "transparent", padding: i === 0 ? "0 8px" : 0 }}>{corta(x, story ? 44 : 26)}</div>
              </div>
            ))}
          </div>

          <Rodape story={story} />
        </div>
      ),
      { width: W, height: H, fonts: fontes, headers: { "cache-control": "public, max-age=3600" } },
    );
  }

  // afinidades: o match (só facetas de nicho), como levantamento de campo
  const ql = u.searchParams.get("ql");
  const r = await alinhar(respostas.nicho, { instituicao: inst, soQualis: ql !== "0", texto: u.searchParams.get("t") });
  const lista = r.banner;
  const mapa = miniMapa(lista.map((x) => ({ lat: x.lat, lon: x.lon })));
  const mapaW = story ? 360 : 230, mapaH = mapaW * PROPORCAO_MAPA, marca = Math.round(mapaW * 0.105);   // marcadores proporcionais ao mapa
  const nome = (s: string) => s.replace(/\u00ad/g, "");
  return new ImageResponse(
    (
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: W, height: H, padding: M, background: fundo, fontFamily: "DM Sans", color: TINTA }}>
        <Cabecalho texto="Afinidades no Nordeste" story={story} />

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 32 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: story ? 16 : 10, flex: 1 }}>
            <Rotulo story={story}>nicho</Rotulo>
            <div style={{ display: "flex", fontSize: tamNicho(t.nicho.length, story ? 56 : 42), fontWeight: 700, fontFamily: TITULO, lineHeight: 1.08, letterSpacing: -1 }}>{t.nicho}</div>
            <div style={{ display: "flex", fontSize: story ? 30 : 24, color: MUDO, marginTop: 6 }}>
              {lista.length ? `${lista.length} pesquisador${lista.length > 1 ? "es" : ""} com afinidade` : "Ninguém no seu nicho, ainda"}
            </div>
          </div>
          {lista.length > 0 && (
            <div style={{ display: "flex", position: "relative", width: mapaW, height: mapaH, flexShrink: 0 }}>
              <img src={mapa.src} width={mapaW} height={mapaH} alt="" />
              {mapa.pos.map((p, i) => p && (
                <div key={i} style={{ position: "absolute", left: p.x * mapaW - marca / 2, top: p.y * mapaH - marca / 2, width: marca, height: marca, borderRadius: 999, background: acento, border: `${story ? 4 : 3}px solid ${TINTA}`,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: marca * 0.52, fontWeight: 700, fontFamily: TITULO }}>{i + 1}</div>
              ))}
            </div>
          )}
        </div>

        {/* a lista como prancha: uma ficha, linhas separadas por réguas */}
        <div style={{ display: "flex", flexDirection: "column", background: PAINEL, border: `5px solid ${TINTA}`, borderRadius: RAIO, boxShadow: SOMBRA(12),
          padding: story ? "8px 40px" : "4px 30px" }}>
          {lista.map((x, i) => {
            const blocos = Math.round(x.indice / 10);
            return (
              <div key={x.id} style={{ display: "flex", alignItems: "center", gap: story ? 28 : 22, padding: story ? "30px 0" : "14px 0", borderTop: i ? `2px solid ${TINTA}` : "none" }}>
                <div style={{ display: "flex", width: story ? 56 : 44, fontSize: story ? 64 : 46, fontWeight: 400, fontFamily: TITULO, color: acento, lineHeight: 1 }}>{i + 1}</div>
                <div style={{ display: "flex", flexDirection: "column", flex: 1, gap: story ? 8 : 4 }}>
                  <div style={{ display: "flex", fontSize: story ? 36 : 28, fontWeight: 700, fontFamily: TITULO, lineHeight: 1.12 }}>{nome(x.nome)}</div>
                  <div style={{ display: "flex", fontSize: story ? 25 : 21, color: MUDO }}>{corta([x.sigla ?? x.instituicao, x.municipio && `${x.municipio}/${x.uf}`].filter(Boolean).join(" · "), 46)}</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: story ? 10 : 6, flexShrink: 0 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                    <span style={{ fontSize: story ? 54 : 40, fontWeight: 700, fontFamily: TITULO, lineHeight: 1 }}>{x.indice}</span>
                    <span style={{ fontSize: story ? 22 : 18, color: MUDO }}>/100</span>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {Array.from({ length: 10 }, (_, k) => (
                      <div key={k} style={{ display: "flex", width: story ? 14 : 11, height: story ? 22 : 16, background: k < blocos ? acento : "transparent", border: `2.5px solid ${TINTA}` }} />
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
          {!lista.length && <div style={{ display: "flex", padding: 36, fontSize: 34 }}>Tente pular uma das perguntas mais específicas e refazer.</div>}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: story ? 22 : 14 }}>
          {lista.length > 0 && <div style={{ display: "flex", fontSize: story ? 24 : 20, color: MUDO }}>Índice de compatibilidade de 0 a 100, calculado só com publicações abertas (OpenAlex, CAPES).</div>}
          <Rodape story={story} codigo={codigo} />
        </div>
      </div>
    ),
    { width: W, height: H, fonts: fontes, headers: { "cache-control": "public, max-age=3600" } },
  );
}
