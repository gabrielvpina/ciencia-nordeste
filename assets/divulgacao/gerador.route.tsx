// Peças de divulgação (docs/divulgacao): o que é o Ciência Nordeste, o quiz e por que fazer, nos formatos das redes.
// GET /api/divulgacao/o-que-e|quiz|por-que?f=instagram-post|instagram-story|tiktok|linkedin-quadrado|linkedin-paisagem
// Mesmo estilo dos cartões do quiz ("Registro de campo", D-049/D-050): fundo claro, painéis com borda e sombra dura,
// títulos em Lexend, selo verde-limão e a chamada em barra escura. Sem ilustração; só o logo e o contorno do Nordeste.
import { ImageResponse } from "next/og";
import { q } from "@/lib/db";
import { ACENTO, FUNDO, LIMA, MUDO, PAINEL, PROPORCAO_MAPA, TINTA, TITULO, carregarFontes, logoForma, logoSvg, miniMapa } from "@/lib/quiz/visual";

export const dynamic = "force-dynamic";

type Formato = { w: number; h: number; k: number; topo: number; base: number; esq: number; dir: number; deitado?: boolean };
// zonas seguras: story (perfil em cima, resposta embaixo); TikTok (botões à direita, legenda e música embaixo)
const FORMATOS: Record<string, Formato> = {
  "instagram-post": { w: 1080, h: 1350, k: 0.84, topo: 72, base: 64, esq: 64, dir: 64 },
  "instagram-story": { w: 1080, h: 1920, k: 1, topo: 230, base: 210, esq: 80, dir: 80 },
  tiktok: { w: 1080, h: 1920, k: 0.94, topo: 190, base: 430, esq: 72, dir: 168 },
  "linkedin-quadrado": { w: 1200, h: 1200, k: 0.84, topo: 72, base: 64, esq: 72, dir: 72 },
  "linkedin-paisagem": { w: 1200, h: 627, k: 0.64, topo: 44, base: 40, esq: 52, dir: 52, deitado: true },
};
const fmt = (n: number) => n.toLocaleString("pt-BR");

export async function GET(req: Request, { params }: { params: { peca: string } }) {
  const F = FORMATOS[new URL(req.url).searchParams.get("f") ?? ""] ?? FORMATOS["instagram-post"];
  const peca = params.peca;
  if (!["o-que-e", "quiz", "por-que"].includes(peca)) return Response.json({ erro: "peça inválida" }, { status: 404 });
  const z = (n: number) => Math.round(n * F.k);
  const sombra = (n: number) => `${z(n)}px ${z(n)}px 0 ${TINTA}`;
  const [r] = await q<{ pesquisadores: string; works: string; instituicoes: string; programas: string; ano_inicio: number; ano_fim: number }>(
    "SELECT pesquisadores, works, instituicoes, programas, ano_inicio, ano_fim FROM mv_resumo");
  const fontes = await carregarFontes();
  const fundo = { "o-que-e": FUNDO.bancada, quiz: FUNDO.computador, "por-que": FUNDO.campo }[peca]!;
  const acento = { "o-que-e": ACENTO.neutro, quiz: ACENTO.cidade, "por-que": ACENTO.mata }[peca]!;

  const Selo = ({ texto }: { texto: string }) => (
    <div style={{ display: "flex", alignSelf: "flex-start", fontSize: z(44), fontWeight: 700, fontFamily: TITULO, color: TINTA, background: LIMA,
      border: `${z(5)}px solid ${TINTA}`, borderRadius: 999, padding: `${z(14)}px ${z(34)}px`, boxShadow: sombra(6), transform: "rotate(-3deg)" }}>{texto}</div>
  );
  const Titulo = ({ linhas, tam = 104 }: { linhas: string[]; tam?: number }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: z(18) }}>
      <div style={{ display: "flex", flexDirection: "column", fontSize: z(tam), fontWeight: 700, fontFamily: TITULO, lineHeight: 1, letterSpacing: -2 }}>
        {linhas.map((l) => <span key={l}>{l}</span>)}
      </div>
      <div style={{ display: "flex", width: z(300), height: z(18), background: LIMA, border: `${z(4)}px solid ${TINTA}`, borderRadius: 999, boxShadow: sombra(4) }} />
    </div>
  );
  const Texto = ({ children, tam = 38 }: { children: string; tam?: number }) => (
    <div style={{ display: "flex", fontSize: z(tam), lineHeight: 1.3, color: TINTA }}>{children}</div>
  );
  const Painel = ({ children }: { children: React.ReactNode }) => (
    <div style={{ display: "flex", flexDirection: "column", background: PAINEL, border: `${z(5)}px solid ${TINTA}`, borderRadius: z(28), boxShadow: sombra(12),
      padding: `${z(10)}px ${z(36)}px` }}>{children}</div>
  );
  const Marca = ({ n }: { n: string }) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: z(62), height: z(62), flexShrink: 0, background: acento,
      border: `${z(4)}px solid ${TINTA}`, borderRadius: 999, fontSize: z(32), fontWeight: 700, fontFamily: TITULO, color: TINTA }}>{n}</div>
  );
  const Itens = ({ itens }: { itens: [string, string][] }) => (
    <Painel>
      {itens.map(([forte, resto], i) => (
        <div key={forte} style={{ display: "flex", alignItems: "center", gap: z(26), padding: `${z(24)}px 0`, borderTop: i ? `${z(4)}px solid ${TINTA}` : "none" }}>
          <Marca n={String(i + 1)} />
          <div style={{ display: "flex", flexDirection: "column", gap: z(4), flex: 1 }}>
            <span style={{ fontSize: z(40), fontWeight: 700, fontFamily: TITULO, lineHeight: 1.12 }}>{forte}</span>
            <span style={{ fontSize: z(32), color: MUDO, lineHeight: 1.25 }}>{resto}</span>
          </div>
        </div>
      ))}
    </Painel>
  );
  const Chamada = ({ convite, url }: { convite: string; url: string }) => (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: TINTA, color: PAINEL, borderRadius: z(22),
      padding: `${z(22)}px ${z(30)}px`, boxShadow: `${z(8)}px ${z(8)}px 0 ${LIMA}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: z(12) }}>
        <img src={logoSvg()} width={z(46)} height={z(57)} alt="" />
        <div style={{ display: "flex", gap: z(8), fontSize: z(32) }}><span>Ciência</span><span style={{ fontWeight: 700, fontFamily: TITULO }}>Nordeste</span></div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
        <span style={{ fontSize: z(28), color: "#c9cde0" }}>{convite}</span>
        <span style={{ fontSize: z(34), fontWeight: 700, fontFamily: TITULO, color: LIMA }}>{url}</span>
      </div>
    </div>
  );
  const Figurinha = () => (
    <img src={logoForma(acento)} width={z(150)} height={Math.round(z(150) * 59 / 47)} alt=""
      style={{ position: "absolute", top: F.deitado ? z(60) : Math.max(z(40), F.topo - z(190)), right: F.dir + z(4), transform: "rotate(8deg)" }} />
  );

  // ---- conteúdo de cada peça ----
  const numeros: [string, string][] = [
    [fmt(Number(r.pesquisadores)), "pesquisadores"], [fmt(Number(r.works)), `publicações (${r.ano_inicio}–${r.ano_fim})`],
    [fmt(Number(r.instituicoes)), "instituições"], [fmt(Number(r.programas)), "programas de pós"],
  ];
  const Numeros = () => (
    <Painel>
      {[numeros.slice(0, 2), numeros.slice(2)].map((par, i) => (
        <div key={i} style={{ display: "flex", borderTop: i ? `${z(4)}px solid ${TINTA}` : "none" }}>
          {par.map(([n, rot], j) => (
            <div key={rot} style={{ display: "flex", flexDirection: "column", flex: 1, padding: `${z(24)}px 0 ${z(24)}px ${j ? z(30) : 0}px`, borderLeft: j ? `${z(4)}px solid ${TINTA}` : "none" }}>
              <span style={{ fontSize: z(64), fontWeight: 700, fontFamily: TITULO, lineHeight: 1, letterSpacing: -1 }}>{n}</span>
              <span style={{ fontSize: z(30), color: MUDO, marginTop: z(8) }}>{rot}</span>
            </div>
          ))}
        </div>
      ))}
    </Painel>
  );
  const mapaW = z(260);
  const Mapa = () => <img src={miniMapa([]).src} width={mapaW} height={Math.round(mapaW * PROPORCAO_MAPA)} alt="" style={{ flexShrink: 0 }} />;

  const pecas = {
    "o-que-e": {
      selo: "Você conhece?",
      titulo: ["A pesquisa do", "Nordeste num", "só lugar"],
      texto: "Quem pesquisa o quê, onde e com quem em saúde, ciências biológicas e agrárias. Gratuito, com dados públicos e abertos.",
      corpo: <Numeros />,
      chamada: { convite: "explore", url: "ciencianordeste.com.br" },
      mapa: true,
    },
    quiz: {
      selo: "Que cientista é você?",
      titulo: ["Descubra o seu", "perfil de", "cientista"],
      texto: "Para estudantes de graduação, pós-graduandos e docentes. Leva uns 2 minutos.",
      corpo: <Itens itens={[
        ["Responda perguntas rápidas", "sobre como e o que você gosta de pesquisar"],
        ["Ganhe seu título e seu nicho", "em cartões prontos para stories e status"],
        ["Veja quem pesquisa como você", "pesquisadores, instituições e programas de pós no Nordeste"],
      ]} />,
      chamada: { convite: "faça o seu", url: "ciencianordeste.com.br/quiz" },
      mapa: false,
    },
    "por-que": {
      selo: "Por que fazer o quiz?",
      titulo: ["Ciência se", "faz em rede"],
      texto: "O Nordeste tem muita gente pesquisando o mesmo que você. O difícil é se encontrar.",
      corpo: <Itens itens={[
        ["Ache orientação perto de você", "quem publica no seu tema, na sua região"],
        ["Escolha sua pós com dados", "programas e instituições alinhados ao seu interesse"],
        ["Dê visibilidade à pesquisa daqui", "compartilhe o seu cartão e chame mais gente"],
      ]} />,
      chamada: { convite: "faça o seu", url: "ciencianordeste.com.br/quiz" },
      mapa: true,
    },
  }[peca]!;

  const raiz = { display: "flex", width: F.w, height: F.h, position: "relative" as const, overflow: "hidden", background: fundo, fontFamily: "DM Sans", color: TINTA,
    padding: `${F.topo}px ${F.dir}px ${F.base}px ${F.esq}px` };

  const conteudo = F.deitado ? (
    // paisagem (link do LinkedIn): título à esquerda, painel à direita, chamada embaixo
    <div style={{ ...raiz, flexDirection: "column", justifyContent: "space-between" }}>
      <div style={{ display: "flex", gap: z(56), alignItems: "center", flex: 1 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: z(30), width: "46%" }}>
          <Selo texto={pecas.selo} />
          <Titulo linhas={pecas.titulo} tam={92} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>{pecas.corpo}</div>
      </div>
      <Chamada {...pecas.chamada} />
    </div>
  ) : (
    <div style={{ ...raiz, flexDirection: "column", justifyContent: "space-between" }}>
      <Figurinha />
      <Selo texto={pecas.selo} />
      <Titulo linhas={pecas.titulo} />
      {/* o mapa fica ao lado do texto (não do título, que precisa da largura toda) e só nos formatos altos */}
      <div style={{ display: "flex", alignItems: "center", gap: z(36) }}>
        <div style={{ display: "flex", flex: 1 }}><Texto tam={F.h / F.w > 1.5 ? 42 : 38}>{pecas.texto}</Texto></div>
        {pecas.mapa && F.h / F.w > 1.5 && <Mapa />}
      </div>
      {pecas.corpo}
      <Chamada {...pecas.chamada} />
    </div>
  );
  return new ImageResponse(conteudo, { width: F.w, height: F.h, fonts: fontes, headers: { "cache-control": "no-store" } });
}
