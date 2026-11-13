// GET /api/quiz/banner/perfil|afinidades?r=<ids das opções, separados por vírgula>&i=<instituição>&ql=0|1&f=story|feed&t=<código do texto, D-040>
// Gera o banner em PNG no próprio servidor (next/og). A URL leva só ids: o servidor recalcula tudo e não grava nada.
// Arte "Registro de campo" (D-049, docs/arte-banners.md), revista com a skill ui-ux-pro-max/banner-design (D-050): zonas seguras do story,
// chamada única, contraste ≥ 4,5:1 (o acento nunca é cor de texto), selo descontraído e o logo grande como elemento gráfico.
import { ImageResponse } from "next/og";
import { alinhar } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { montarTitulo } from "@/lib/quiz/titulo";
import { ACENTO, FUNDO, LIMA, MUDO, PAINEL, PROPORCAO_MAPA, TINTA, TITULO, agruparPontos, carregarFontes, corta, logoForma, logoSvg, miniMapa } from "@/lib/quiz/visual";

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

/** Zonas seguras (skill banner-design): no story, o Instagram cobre ~220 px no topo (perfil) e embaixo (resposta). */
const ZONA = { story: { topo: 230, base: 210, lado: 80 }, feed: { topo: 72, base: 64, lado: 64 } };

/** Selo de abertura: o gancho, em tom de conversa, como figurinha colada (a única inclinação da peça). */
function Selo({ texto, story }: { texto: string; story: boolean }) {
  return (
    <div style={{ display: "flex", alignSelf: "flex-start", fontSize: story ? 44 : 34, fontWeight: 700, fontFamily: TITULO, color: TINTA, background: LIMA,
      border: `5px solid ${TINTA}`, borderRadius: 999, padding: story ? "14px 34px" : "10px 26px", boxShadow: SOMBRA(6), transform: "rotate(-3deg)" }}>{texto}</div>
  );
}

/** Logo inteiro, como figurinha no canto (na faixa do topo que a interface do story cobre; nada essencial ali). */
function LogoGrande({ acento, story }: { acento: string; story: boolean }) {
  const w = story ? 150 : 104;
  return <img src={logoForma(acento)} width={w} height={Math.round(w * 59 / 47)} alt="" style={{ position: "absolute", top: story ? 40 : 34, right: story ? 84 : 66, transform: "rotate(8deg)" }} />;
}

/** Manchete do card de afinidades: grande, em duas linhas, com um traço verde-limão por baixo. */
function Manchete({ story }: { story: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: story ? 14 : 10 }}>
      <div style={{ display: "flex", flexDirection: "column", fontSize: story ? 88 : 62, fontWeight: 700, fontFamily: TITULO, lineHeight: 0.98, letterSpacing: -2 }}>
        <span>Quem pesquisa</span><span>como eu</span>
      </div>
      <div style={{ display: "flex", width: story ? 300 : 220, height: story ? 18 : 14, background: LIMA, border: `4px solid ${TINTA}`, borderRadius: 999, boxShadow: SOMBRA(4) }} />
    </div>
  );
}

/** Chamada única, embaixo: marca + endereço do quiz. Barra escura, endereço em verde-limão (contraste alto). */
function Chamada({ story, codigo }: { story: boolean; codigo?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {codigo && <div style={{ display: "flex", justifyContent: "flex-end", fontSize: story ? 22 : 18, color: MUDO }}>{codigo}</div>}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: TINTA, color: PAINEL, borderRadius: 22, padding: story ? "20px 28px" : "14px 22px", boxShadow: `8px 8px 0 ${LIMA}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <img src={logoSvg()} width={story ? 44 : 38} height={story ? 55 : 48} alt="" />
          <div style={{ display: "flex", gap: 8, fontSize: story ? 30 : 26 }}><span>Ciência</span><span style={{ fontWeight: 700, fontFamily: TITULO }}>Nordeste</span></div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
          <span style={{ fontSize: story ? 22 : 19, color: "#c9cde0" }}>faça o seu</span>
          <span style={{ fontSize: story ? 30 : 26, fontWeight: 700, fontFamily: TITULO, color: LIMA }}>ciencianordeste.com.br/quiz</span>
        </div>
      </div>
    </div>
  );
}

/** Rótulo pequeno de catálogo. */
const Rotulo = ({ children, story }: { children: string; story: boolean }) => (
  <div style={{ display: "flex", fontSize: story ? 26 : 22, color: MUDO }}>{children}</div>
);

/** PNGs já gerados, em memória (D-052): gerar a imagem custa 2–5 s de CPU, e o mesmo banner é pedido de novo ao
 *  compartilhar e baixar, ao recarregar a página e pelas prévias de redes sociais. A chave normaliza a ordem das respostas e
 *  só leva o que muda a imagem (instituição, Qualis e texto só valem para o de afinidades). LRU por bytes; reinicia a cada publicação. */
const PNGS = new Map<string, ArrayBuffer>();
let bytesPngs = 0;
const MAX_BYTES_PNGS = 64 * 1024 * 1024;
const CABECALHOS = { "content-type": "image/png", "cache-control": "public, max-age=86400, stale-while-revalidate=604800" };

export async function GET(req: Request, ctx: { params: { tipo: string } }) {
  const u = new URL(req.url);
  const tipo = ctx.params.tipo;
  const ids = (u.searchParams.get("r") ?? "").split(",").filter(Boolean).sort().join(",");
  const extra = tipo === "afinidades" ? ["i", "ql", "t"].map((k) => `${k}=${u.searchParams.get(k) ?? ""}`).join("&") : "";
  const chave = `${tipo}|${u.searchParams.get("f") === "feed" ? "feed" : "story"}|${ids}|${extra}`;
  const guardado = PNGS.get(chave);
  if (guardado) {
    PNGS.delete(chave); PNGS.set(chave, guardado);   // mais recente no fim (LRU)
    return new Response(guardado, { headers: { ...CABECALHOS, "x-cache": "hit" } });
  }
  const res = await gerar(req, ctx);
  if (!res.ok || !res.headers.get("content-type")?.startsWith("image/")) return res;
  const buf = await res.arrayBuffer();
  PNGS.set(chave, buf);
  bytesPngs += buf.byteLength;
  while (bytesPngs > MAX_BYTES_PNGS && PNGS.size > 1) {
    const [k, v] = PNGS.entries().next().value!;
    PNGS.delete(k); bytesPngs -= v.byteLength;
  }
  return new Response(buf, { headers: { ...CABECALHOS, "x-cache": "miss" } });
}

async function gerar(req: Request, { params }: { params: { tipo: string } }) {
  const u = new URL(req.url);
  const tipo = params.tipo === "afinidades" ? "afinidades" : params.tipo === "perfil" ? "perfil" : null;
  if (!tipo) return Response.json({ erro: "tipo inválido" }, { status: 404 });
  const ids = (u.searchParams.get("r") ?? "").split(",").filter(Boolean);
  const { respostas, erros } = interpretar(ids);
  if (erros.length) return Response.json({ erro: "respostas inválidas", detalhes: erros.slice(0, 5) }, { status: 400 });
  const inst = UUID.test(u.searchParams.get("i") ?? "") ? u.searchParams.get("i") : null;
  const [W, H] = TAMANHOS[u.searchParams.get("f") === "feed" ? "feed" : "story"];
  const story = H === 1920;
  const t = montarTitulo(respostas);
  const fundo = FUNDO[t.cor] ?? FUNDO.neutro, acento = ACENTO[t.acento] ?? ACENTO.neutro;
  const semente = [...ids].sort().join(",");
  const { codigo } = sorteio(semente);
  const fontes = await carregarFontes();

  const Z = story ? ZONA.story : ZONA.feed;
  const raiz = { display: "flex", flexDirection: "column" as const, justifyContent: "space-between", width: W, height: H, position: "relative" as const, overflow: "hidden",
    padding: `${Z.topo}px ${Z.lado}px ${Z.base}px`, background: fundo, fontFamily: "DM Sans", color: TINTA };

  if (tipo === "perfil") {
    const n = t.principal.length;
    // tamanho pelo comprimento total e pela maior palavra (uma palavra longa não pode encostar na borda; Lexend bold ≈ 0,64 em por letra)
    const maiorPalavra = Math.max(...t.principal.split(/\s+/).map((w) => w.length));
    const tam = Math.min(Math.round((n > 26 ? 116 : n > 18 ? 134 : 156) * (story ? 1 : 0.8)), Math.floor((W - 2 * Z.lado - 20) / (maiorPalavra * 0.64)));
    return new ImageResponse(
      (
        <div style={raiz}>
          <LogoGrande acento={acento} story={story} />
          <Selo texto="Que cientista é você?" story={story} />

          <div style={{ display: "flex", flexDirection: "column", gap: story ? 10 : 6 }}>
            <Rotulo story={story}>meu título</Rotulo>
            <div style={{ display: "flex", fontSize: tam, fontWeight: 700, fontFamily: TITULO, lineHeight: 0.98, letterSpacing: -3 }}>{t.principal}</div>
            {t.secundario && <div style={{ display: "flex", fontSize: story ? 44 : 34, marginTop: 6 }}>{t.secundario}</div>}
          </div>

          {/* ficha: o "DNA científico" (código das respostas) e o nicho */}
          <div style={{ display: "flex", flexDirection: "column", background: PAINEL, border: `5px solid ${TINTA}`, borderRadius: RAIO, boxShadow: SOMBRA(12),
            padding: story ? "32px 40px" : "22px 30px", gap: story ? 18 : 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: story ? 24 : 20, color: MUDO }}>
              <span>meu DNA científico</span><span>{codigo}</span>
            </div>
            <CodigoBarras semente={semente} largura={W - 2 * Z.lado - (story ? 90 : 70)} altura={story ? 110 : 76} acento={acento} />
            <div style={{ display: "flex", height: 3, background: TINTA, marginTop: 4 }} />
            <Rotulo story={story}>meu nicho</Rotulo>
            <div style={{ display: "flex", fontSize: tamNicho(t.nicho.length, story ? 50 : 38), fontWeight: 700, fontFamily: TITULO, lineHeight: 1.12, marginTop: -6 }}>{t.nicho}</div>
          </div>

          {/* as escolhas, como etiquetas (a primeira marcada com o verde-limão) */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: story ? 14 : 10 }}>
            {t.trilha.slice(0, story ? 6 : 4).map((x, i) => (
              <div key={x} style={{ display: "flex", fontSize: story ? 30 : 24, background: i === 0 ? acento : PAINEL, border: `4px solid ${TINTA}`, borderRadius: 999,
                padding: story ? "8px 22px" : "6px 18px", boxShadow: SOMBRA(4) }}>{corta(x, 32)}</div>
            ))}
          </div>

          <Chamada story={story} />
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
  const mapaW = story ? 300 : 210, mapaH = mapaW * PROPORCAO_MAPA, marca = Math.round(mapaW * 0.11);
  // marcadores na posição exata; quem fica a menos de um marcador de distância vira um só ("2·3·5")
  const grupos = agruparPontos(mapa.pos.map((p) => p && { x: p.x * mapaW, y: p.y * mapaH }), marca * 0.8);
  const nome = (s: string) => s.replace(/\u00ad/g, "");
  return new ImageResponse(
    (
      <div style={raiz}>
        <Manchete story={story} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 28 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: story ? 12 : 8, flex: 1 }}>
            <Rotulo story={story}>meu nicho</Rotulo>
            <div style={{ display: "flex", fontSize: tamNicho(t.nicho.length, story ? 52 : 40), fontWeight: 700, fontFamily: TITULO, lineHeight: 1.08, letterSpacing: -1 }}>{t.nicho}</div>
            <div style={{ display: "flex", fontSize: story ? 28 : 23, color: MUDO, marginTop: 4 }}>
              {lista.length ? `${lista.length} pesquisador${lista.length > 1 ? "es" : ""} com afinidade no Nordeste` : "Ninguém no meu nicho, ainda"}
            </div>
          </div>
          {lista.length > 0 && (
            <div style={{ display: "flex", position: "relative", width: mapaW, height: mapaH, flexShrink: 0 }}>
              <img src={mapa.src} width={mapaW} height={mapaH} alt="" />
              {grupos.map((g) => {
                const larg = g.nums.length === 1 ? marca : marca * 0.62 * g.nums.length + marca * 0.5;
                const left = Math.min(Math.max(g.x - larg / 2, 0), mapaW - larg), top = Math.min(Math.max(g.y - marca / 2, 0), mapaH - marca);
                return (
                  <div key={g.nums.join()} style={{ position: "absolute", left, top, width: larg, height: marca, borderRadius: 999, background: acento, border: `${story ? 4 : 3}px solid ${TINTA}`,
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: marca * 0.5, fontWeight: 700, fontFamily: TITULO }}>{g.nums.join("·")}</div>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", background: PAINEL, border: `5px solid ${TINTA}`, borderRadius: RAIO, boxShadow: SOMBRA(12),
          padding: story ? "6px 34px" : "4px 26px" }}>
          {lista.map((x, i) => {
            const blocos = Math.round(x.indice / 10);
            return (
              <div key={x.id} style={{ display: "flex", alignItems: "center", gap: story ? 24 : 18, padding: story ? "19px 0" : "11px 0", borderTop: i ? `2px solid ${TINTA}` : "none" }}>
                {/* número em tinta sobre o acento: o acento nunca é cor de texto (contraste) */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: story ? 58 : 46, height: story ? 58 : 46, flexShrink: 0, background: acento,
                  border: `4px solid ${TINTA}`, borderRadius: 14, boxShadow: SOMBRA(4), fontSize: story ? 32 : 26, fontWeight: 700, fontFamily: TITULO }}>{i + 1}</div>
                <div style={{ display: "flex", flexDirection: "column", flex: 1, gap: story ? 6 : 3 }}>
                  <div style={{ display: "flex", fontSize: story ? 34 : 27, fontWeight: 700, fontFamily: TITULO, lineHeight: 1.12 }}>{nome(x.nome)}</div>
                  <div style={{ display: "flex", fontSize: story ? 24 : 20, color: MUDO }}>{corta([x.sigla ?? x.instituicao, x.municipio && `${x.municipio}/${x.uf}`].filter(Boolean).join(" · "), 44)}</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: story ? 8 : 5, flexShrink: 0 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                    <span style={{ fontSize: story ? 48 : 38, fontWeight: 700, fontFamily: TITULO, lineHeight: 1 }}>{x.indice}</span>
                    <span style={{ fontSize: story ? 20 : 17, color: MUDO }}>/100</span>
                  </div>
                  <div style={{ display: "flex", gap: 3 }}>
                    {Array.from({ length: 10 }, (_, k) => (
                      <div key={k} style={{ display: "flex", width: story ? 13 : 10, height: story ? 20 : 15, background: k < blocos ? acento : "transparent", border: `2.5px solid ${TINTA}` }} />
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
          {!lista.length && <div style={{ display: "flex", padding: 32, fontSize: 32 }}>Tente pular uma das perguntas mais específicas e refazer.</div>}
        </div>

        <Chamada story={story} codigo={lista.length ? "compatibilidade 0–100 · publicações abertas (OpenAlex, CAPES)" : undefined} />
      </div>
    ),
    { width: W, height: H, fonts: fontes, headers: { "cache-control": "public, max-age=3600" } },
  );
}
