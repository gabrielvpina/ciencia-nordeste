// Resultado do quiz (etapa 13): os dois banners, a lista estendida, o filtro de distância e as instituições e programas
// mais alinhados. Tudo recalculado no servidor a partir dos ids na URL; nada é gravado (D-037).
import type { Metadata } from "next";
import Avatar from "@/components/Avatar";
import { CompartilharBanner, CopiarLink } from "@/components/quiz/Compartilhar";
import { nomePrograma } from "@/lib/programas";
import { alinhar, type Filtro } from "@/lib/quiz/alinhamento";
import { interpretar } from "@/lib/quiz/estrutura";
import { montarTitulo } from "@/lib/quiz/titulo";
import { soQualis } from "@/lib/qualis-filtro";

export const dynamic = "force-dynamic";
const UUID = /^[0-9a-f-]{36}$/i;
type SP = { r?: string; i?: string; f?: string; km?: string };

function ler(sp: SP) {
  const ids = (sp.r ?? "").split(",").filter(Boolean).slice(0, 12);
  const inst = UUID.test(sp.i ?? "") ? sp.i! : null;
  const filtro: Filtro = inst && sp.f === "uf" ? { tipo: "uf" } : inst && sp.f === "raio" && Number(sp.km) > 0 ? { tipo: "raio", km: Math.min(Number(sp.km), 3000) } : { tipo: "ne" };
  return { ids, inst, filtro, ...interpretar(ids) };
}
const qsBanner = (ids: string[], inst: string | null, extra: Record<string, string> = {}) =>
  new URLSearchParams({ r: ids.join(","), ...(inst ? { i: inst } : {}), ...extra }).toString();

export async function generateMetadata({ searchParams }: { searchParams: SP }): Promise<Metadata> {
  const { ids, inst, respostas, erros } = ler(searchParams);
  if (erros.length || !ids.length) return { title: "Que cientista é você? — Ciência Nordeste" };
  const t = montarTitulo(respostas);
  const img = `/api/quiz/banner/perfil?${qsBanner(ids, inst, { f: "feed" })}`;
  return {
    title: `${t.principal} — Que cientista é você? · Ciência Nordeste`,
    description: `${t.nicho}. Descubra o seu perfil de cientista e quem no Nordeste pesquisa como você.`,
    openGraph: { images: [{ url: img, width: 1080, height: 1350 }] },
    twitter: { card: "summary_large_image", images: [img] },
  };
}

export default async function Resultado({ searchParams }: { searchParams: SP }) {
  const { ids, inst, filtro, respostas, erros } = ler(searchParams);
  if (erros.length || !ids.length) {
    return <div className="quiz"><section className="quiz-abertura"><h1>Resultado inválido</h1><p>Este link não corresponde a um quiz respondido.</p>
      <a className="quiz-comecar" href="/quiz">Fazer o quiz</a></section></div>;
  }
  const sq = soQualis();
  const [t, r] = [montarTitulo(respostas), await alinhar(respostas.nicho, { instituicao: inst, soQualis: sq, filtro })];
  const extra = { ql: sq ? "1" : "0" };
  const bPerfil = `/api/quiz/banner/perfil?${qsBanner(ids, inst, extra)}`;
  const bAfin = `/api/quiz/banner/afinidades?${qsBanner(ids, inst, extra)}`;
  const base = qsBanner(ids, inst);

  return (
    <div className="quiz quiz-resultado">
      <section className="qr-cabeca">
        <span className="quiz-tag">seu resultado</span>
        <h1>{t.principal}</h1>
        {t.secundario && <p className="qr-sec">{t.secundario}</p>}
        <p className="qr-nicho">{t.nicho}</p>
      </section>

      <div className="qr-banners">
        <figure className="qr-banner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={bPerfil} alt={`Cartão: ${t.principal}. ${t.nicho}.`} width={1080} height={1920} />
          <CompartilharBanner src={bPerfil} nome="meu-perfil-de-cientista" texto={`Sou "${t.principal}" no Ciência Nordeste. E você?`} />
        </figure>
        <figure className="qr-banner">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={bAfin} alt={`Cartão: pesquisadores de afinidade no Nordeste — ${r.banner.map((x) => x.nome).join(", ") || "nenhum ainda"}.`} width={1080} height={1920} />
          <CompartilharBanner src={bAfin} nome="minhas-afinidades-no-nordeste" texto="Meus pesquisadores de afinidade no Nordeste, pelo Ciência Nordeste." />
        </figure>
      </div>
      <div className="qr-acoes centro"><CopiarLink /><a className="botao-sec" href="/quiz">Refazer o quiz</a></div>

      <section className="painel-card qr-lista">
        <h2>Quem pesquisa como você <small>{r.lista.length ? `${r.lista.length} pesquisadores · índice de compatibilidade 0–100` : ""}</small></h2>
        {inst && (
          <form className="qr-filtro" method="get" action="/quiz/resultado">
            <input type="hidden" name="r" value={ids.join(",")} /><input type="hidden" name="i" value={inst} />
            <label><input type="radio" name="f" value="ne" defaultChecked={filtro.tipo === "ne"} /> Todo o Nordeste</label>
            <label><input type="radio" name="f" value="uf" defaultChecked={filtro.tipo === "uf"} /> Só o meu estado</label>
            <label><input type="radio" name="f" value="raio" defaultChecked={filtro.tipo === "raio"} /> Até
              <input type="number" name="km" min={10} max={3000} step={10} defaultValue={filtro.tipo === "raio" ? filtro.km : 300} aria-label="Raio em km" /> km</label>
            <button type="submit" className="chip">aplicar</button>
          </form>
        )}
        {!r.lista.length && <p className="meta">Ninguém no Nordeste combina com todas as suas respostas{filtro.tipo !== "ne" ? " nesse filtro de distância" : ""}. Tente pular uma das perguntas mais específicas, como escala ou ambiente.</p>}
        <ol className="qr-pessoas">
          {r.lista.map((x, k) => (
            <li key={x.id}>
              <span className="qr-pos">{k + 1}</span>
              <Avatar id={x.id} nome={x.nome} tamanho={52} />
              <div className="qr-corpo">
                <a href={`/pesquisador/${x.id}`} className="qr-nome">{x.nome}</a>
                <span className="meta">{[x.sigla ?? x.instituicao, x.municipio && `${x.municipio}/${x.uf}`, x.distancia_km != null ? `${x.distancia_km} km` : null].filter(Boolean).join(" · ")}</span>
                {x.programa && <span className="meta">Pós: {x.programa_id ? <a href={`/programa/${x.programa_id}`}>{nomePrograma(x.programa)}</a> : nomePrograma(x.programa)}</span>}
                <span className="qr-porque">{x.n_nicho} publicaç{x.n_nicho === 1 ? "ão" : "ões"} no seu nicho{x.desde ? ` desde ${x.desde}` : ""} · {x.facetas.slice(0, 3).join(", ").toLowerCase()}</span>
                {x.exemplos.map((e) => (
                  <span key={e.titulo} className="qr-ex">{e.doi ? <a href={`https://doi.org/${e.doi}`} target="_blank" rel="noopener noreferrer">{e.titulo}</a> : e.titulo} <small>({e.ano})</small></span>
                ))}
              </div>
              <span className="qr-indice" title="índice de compatibilidade (0–100)">{x.indice}</span>
            </li>
          ))}
        </ol>
      </section>

      {(r.instituicoes.length > 0 || r.programas.length > 0) && (
        <div className="qr-duas">
          {r.instituicoes.length > 0 && (
            <section className="painel-card"><h2>Instituições mais alinhadas</h2>
              <ul className="qr-simples">{r.instituicoes.map((x) => <li key={x.id}><a href={`/instituicao/${x.id}`}>{x.sigla ?? x.nome}</a> <span className="meta">{x.uf} · {x.n} pesquisador{x.n > 1 ? "es" : ""}</span></li>)}</ul>
            </section>
          )}
          {r.programas.length > 0 && (
            <section className="painel-card"><h2>Programas de pós mais alinhados</h2>
              <ul className="qr-simples">{r.programas.map((x) => <li key={x.id}><a href={`/programa/${x.id}`}>{nomePrograma(x.nome)}</a> <span className="meta">{x.sigla} · {x.uf}</span></li>)}</ul>
            </section>
          )}
        </div>
      )}

      <p className="meta qr-aviso">
        O alinhamento vem de dados públicos de produção científica (OpenAlex, CAPES) e pode ter lacunas: quem publica pouco
        ou em veículos fora dessas bases aparece menos. {inst ? "Pesquisadores da sua instituição e das ligadas a ela ficam de fora. " : ""}
        Suas respostas não são gravadas. <a href={`/quiz/resultado?${base}`}>Link deste resultado</a>.
      </p>
    </div>
  );
}
