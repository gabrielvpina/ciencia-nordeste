// GET /api/quiz/banner/perfil|afinidades?r=<ids das opções, separados por vírgula>&i=<instituição>&ql=0|1&f=story|feed
// Gera o banner em PNG no próprio servidor (next/og). A URL leva só ids: o servidor recalcula tudo e não grava nada.
// Visual provisório (etapa 13): só cores e formas simples, sem ilustração.
import { ImageResponse } from "next/og";
import { alinhar } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { montarTitulo } from "@/lib/quiz/titulo";
import { ACENTO, DESTAQUE, FUNDO, INICIAIS, LIMA, MUDO, PAINEL, PROPORCAO_MAPA, TINTA, corta, iniciais, logoSvg, miniMapa } from "@/lib/quiz/visual";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;
const TAMANHOS = { story: [1080, 1920], feed: [1080, 1350] } as const;

const cartao = (extra: Record<string, unknown> = {}) => ({
  display: "flex", flexDirection: "column" as const, background: PAINEL, border: `6px solid ${TINTA}`, borderRadius: 36,
  boxShadow: `14px 14px 0 ${TINTA}`, ...extra,
});

function Cabecalho({ texto }: { texto: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <img src={logoSvg()} width={78} height={98} alt="" />
        <div style={{ display: "flex", gap: 12, fontSize: 44, color: TINTA }}><span>Ciência</span><span style={{ fontWeight: 700 }}>Nordeste</span></div>
      </div>
      <div style={{ display: "flex", fontSize: 28, color: TINTA, background: LIMA, border: `4px solid ${TINTA}`, borderRadius: 999, padding: "8px 22px" }}>{texto}</div>
    </div>
  );
}

function Rodape() {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", fontSize: 30, color: TINTA }}>
      <div style={{ display: "flex" }}>ciencianordeste.com.br</div>
      <div style={{ display: "flex", color: MUDO }}>descubra o seu perfil de cientista</div>
    </div>
  );
}

export async function GET(req: Request, { params }: { params: { tipo: string } }) {
  const u = new URL(req.url);
  const tipo = params.tipo === "afinidades" ? "afinidades" : params.tipo === "perfil" ? "perfil" : null;
  if (!tipo) return Response.json({ erro: "tipo inválido" }, { status: 404 });
  const { respostas, erros } = interpretar((u.searchParams.get("r") ?? "").split(",").filter(Boolean));
  if (erros.length) return Response.json({ erro: "respostas inválidas", detalhes: erros.slice(0, 5) }, { status: 400 });
  const inst = UUID.test(u.searchParams.get("i") ?? "") ? u.searchParams.get("i") : null;
  const [W, H] = TAMANHOS[u.searchParams.get("f") === "feed" ? "feed" : "story"];
  const story = H === 1920;
  const t = montarTitulo(respostas);
  const fundo = FUNDO[t.cor] ?? FUNDO.neutro, acento = ACENTO[t.acento] ?? ACENTO.neutro;

  // formas de fundo (só geometria): dois círculos e uma faixa no acento do ambiente
  const formas = (
    <>
      <div style={{ position: "absolute", top: -160, right: -160, width: 560, height: 560, borderRadius: 999, background: acento, border: `6px solid ${TINTA}` }} />
      <div style={{ position: "absolute", bottom: story ? 260 : 200, left: -120, width: 300, height: 300, borderRadius: 999, background: DESTAQUE, border: `6px solid ${TINTA}` }} />
      <div style={{ position: "absolute", bottom: story ? 520 : 380, right: -40, width: 520, height: 46, background: LIMA, border: `6px solid ${TINTA}`, transform: "rotate(-8deg)" }} />
    </>
  );

  if (tipo === "perfil") {
    const tam = t.principal.length > 26 ? 96 : t.principal.length > 18 ? 112 : 128;
    return new ImageResponse(
      (
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: W, height: H, padding: 72, background: fundo, position: "relative", fontFamily: "sans-serif" }}>
          {formas}
          <Cabecalho texto="Que cientista você é" />
          <div style={cartao({ padding: "64px 56px", gap: 28 })}>
            <div style={{ display: "flex", fontSize: 30, letterSpacing: 4, color: MUDO }}>SEU TÍTULO</div>
            <div style={{ display: "flex", fontSize: tam, fontWeight: 700, lineHeight: 1.02, color: TINTA }}>{t.principal}</div>
            {t.secundario && <div style={{ display: "flex", fontSize: 48, color: TINTA }}>{t.secundario}</div>}
            <div style={{ display: "flex", height: 6, width: "100%", background: TINTA, borderRadius: 3, margin: "12px 0" }} />
            <div style={{ display: "flex", fontSize: 30, letterSpacing: 4, color: MUDO }}>SEU NICHO</div>
            <div style={{ display: "flex", fontSize: 54, fontWeight: 700, lineHeight: 1.1, color: TINTA }}>{corta(t.nicho, 70)}</div>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 18 }}>
            {t.trilha.slice(0, 6).map((x, i) => (
              <div key={x} style={{ display: "flex", alignItems: "center", gap: 18 }}>
                <div style={{ display: "flex", fontSize: 34, color: TINTA, background: i === 0 ? LIMA : PAINEL, border: `5px solid ${TINTA}`, borderRadius: 999, padding: "12px 28px" }}>{corta(x, 34)}</div>
                {i < Math.min(t.trilha.length, 6) - 1 && <div style={{ display: "flex", fontSize: 40, color: TINTA }}>→</div>}
              </div>
            ))}
          </div>
          <Rodape />
        </div>
      ),
      { width: W, height: H, headers: { "cache-control": "public, max-age=3600" } },
    );
  }

  // afinidades: o match (só facetas de nicho), desenhado
  const ql = u.searchParams.get("ql");
  const r = await alinhar(respostas.nicho, { instituicao: inst, soQualis: ql !== "0" });
  const lista = r.banner;
  const mapa = miniMapa(lista.map((x) => ({ lat: x.lat, lon: x.lon })));
  const mapaW = story ? 330 : 250, mapaH = mapaW * PROPORCAO_MAPA;
  return new ImageResponse(
    (
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: W, height: H, padding: 72, background: fundo, position: "relative", fontFamily: "sans-serif" }}>
        <div style={{ position: "absolute", top: story ? 820 : 600, right: -230, width: 520, height: 520, borderRadius: 999, background: acento, border: `6px solid ${TINTA}` }} />
        <Cabecalho texto="Afinidades no Nordeste" />
        <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, flex: 1 }}>
            <div style={{ display: "flex", fontSize: story ? 66 : 56, fontWeight: 700, color: TINTA, lineHeight: 1.05 }}>
              {lista.length ? `${lista.length === 5 ? "Seus 5" : `${lista.length}`} pesquisador${lista.length > 1 ? "es" : ""} de afinidade no Nordeste` : "Ninguém no seu nicho, ainda"}
            </div>
            <div style={{ display: "flex", fontSize: 34, color: TINTA, background: PAINEL, border: `5px solid ${TINTA}`, borderRadius: 999, padding: "10px 26px", alignSelf: "flex-start" }}>{corta(t.nicho, 46)}</div>
          </div>
          {lista.length > 0 && (
            <div style={{ display: "flex", position: "relative", width: mapaW, height: mapaH }}>
              <img src={mapa.src} width={mapaW} height={mapaH} alt="" />
              {mapa.pos.map((p, i) => p && (
                <div key={i} style={{ position: "absolute", left: p.x * mapaW - 22, top: p.y * mapaH - 22, width: 44, height: 44, borderRadius: 999, background: acento, border: `5px solid ${TINTA}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 700, color: TINTA }}>{i + 1}</div>
              ))}
            </div>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: story ? 26 : 16 }}>
          {lista.map((x, i) => (
            <div key={x.id} style={cartao({ flexDirection: "row", alignItems: "center", gap: 26, padding: story ? "24px 30px" : "16px 26px", borderRadius: 28, boxShadow: `8px 8px 0 ${TINTA}`, border: `5px solid ${TINTA}` })}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 96, height: 96, borderRadius: 999, background: INICIAIS[i % INICIAIS.length], border: `5px solid ${TINTA}`, fontSize: 38, fontWeight: 700, color: TINTA }}>{iniciais(x.nome)}</div>
              <div style={{ display: "flex", flexDirection: "column", flex: 1, gap: 8 }}>
                <div style={{ display: "flex", fontSize: 38, fontWeight: 700, color: TINTA }}>{`${i + 1}. ${corta(x.nome, 34)}`}</div>
                <div style={{ display: "flex", fontSize: 28, color: MUDO }}>{corta([x.sigla ?? x.instituicao, x.municipio && `${x.municipio}/${x.uf}`].filter(Boolean).join(" · "), 46)}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, width: 210 }}>
                <div style={{ display: "flex", fontSize: 52, fontWeight: 700, color: TINTA, lineHeight: 1 }}>{x.indice}</div>
                <div style={{ display: "flex", width: 200, height: 22, background: "#e7eaf2", border: `4px solid ${TINTA}`, borderRadius: 999 }}>
                  <div style={{ display: "flex", width: `${x.indice}%`, background: acento, borderRadius: 999 }} />
                </div>
              </div>
            </div>
          ))}
          {!lista.length && <div style={cartao({ padding: 40, fontSize: 36, color: TINTA })}>Tente pular uma das perguntas mais específicas e refazer.</div>}
        </div>
        <div style={{ display: "flex", fontSize: 26, color: MUDO }}>Índice de compatibilidade (0–100) calculado a partir de publicações abertas (OpenAlex, CAPES).</div>
        <Rodape />
      </div>
    ),
    { width: W, height: H, headers: { "cache-control": "public, max-age=3600" } },
  );
}
