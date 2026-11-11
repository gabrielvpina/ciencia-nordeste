"use client";
// Quiz "Que cientista é você?" (etapa 13): abertura → cadastro (D-037) → 10 perguntas, uma por tela, com uma descrição
// livre opcional do objeto logo depois de "especificamente?" (D-040) → resultado.
// Pensado para o celular: opções grandes na metade de baixo, toque avança, voltar desfaz (inclusive o botão do navegador).
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { filtrarOpcoes } from "@/lib/quiz/filtros";
import type { estruturaCliente } from "@/lib/quiz/estrutura";
import Cadastro, { type DadosCadastro } from "./Cadastro";
import Processando from "./Processando";

type Estrutura = ReturnType<typeof estruturaCliente>;
type Tela = Estrutura["telas"][number];
type Fase = { tipo: "abertura" } | { tipo: "cadastro" } | { tipo: "pergunta"; i: number } | { tipo: "texto" };
const TEXTO_MAX = 160;   // igual a lib/quiz/texto.ts (que é só do servidor)

export default function QuizApp({ estrutura, contato }: { estrutura: Estrutura; contato: string | null }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [respostas, setRespostas] = useState<Record<string, string | null>>({});   // tela -> opção (null = pulou)
  const [cadastro, setCadastro] = useState<DadosCadastro | null>(null);
  const [escolhida, setEscolhida] = useState<string | null>(null);
  const [processando, setProcessando] = useState(false);   // quiz concluído: espera o resultado
  const [texto, setTexto] = useState("");
  const enviado = useRef<string | null>(null);   // último alinhamento enviado (D-042)   // descrição livre: só na memória; vai ao servidor uma vez, no fim, e volta como código
  const telas = estrutura.telas;
  const total = telas.length + 2;   // cadastro + perguntas + descrição
  // a descrição vem logo depois do sub-objeto ("especificamente?"): no experimento de 20 casos, um texto sobre o objeto
  // rendeu mais que textos sobre técnica ou objetivo (ingest/carga/experimento_quiz_textos.py)
  const iSub = telas.findIndex((t) => t.id === "sub_objeto");

  // cada tela é um passo na URL (?passo=cadastro | 0…9 | texto), pelo roteador do Next: o "voltar" do navegador/celular funciona.
  // As respostas ficam só na memória; recarregar no meio do quiz volta para o começo (o cadastro não fica guardado).
  const p = sp.get("passo");
  const fase: Fase = p === "cadastro" ? { tipo: "cadastro" }
    : p === "texto" && cadastro ? { tipo: "texto" }
    : p != null && /^\d+$/.test(p) && Number(p) < telas.length && cadastro ? { tipo: "pergunta", i: Number(p) }
    : { tipo: "abertura" };
  const ir = useCallback((f: Fase) => {
    setEscolhida(null);
    const passo = f.tipo === "abertura" ? "" : f.tipo === "pergunta" ? `?passo=${f.i}` : `?passo=${f.tipo}`;
    router.push(`/quiz${passo}`, { scroll: true });
  }, [router]);
  useEffect(() => { setEscolhida(null); setProcessando(false); }, [p]);

  const opcoesDe = useCallback((t: Tela, r: Record<string, string | null>) =>
    filtrarOpcoes(t, r.metodo ?? undefined, r.objeto ?? undefined), []);

  /** resultado: a descrição (se houver) vira um código no servidor; o link leva só o código, nunca o texto */
  const concluir = async (r: Record<string, string | null>, descricao: string) => {
    setProcessando(true);
    const ids = telas.map((t) => r[t.id]).filter((x): x is string => !!x);
    const qs = new URLSearchParams({ r: ids.join(",") });
    if (cadastro?.instituicao_id) qs.set("i", cadastro.instituicao_id);
    if (descricao.trim().length >= 3) {
      // até 2 tentativas (o serviço de embedding pode estar lento); se falhar, segue só com as respostas
      for (let tentativa = 0; tentativa < 2 && !qs.has("t"); tentativa++) {
        try {
          const r = await fetch("/api/quiz/texto", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ texto: descricao }) });
          const j = r.ok ? await r.json() : null;
          if (j?.codigo) qs.set("t", j.codigo);
          else if (r.status === 400 || r.status === 429) break;   // texto inválido ou limite: não adianta repetir
        } catch { /* sem conexão: tenta de novo */ }
      }
    }
    // grava o alinhamento (D-042) uma única vez, aqui; a página de resultado só exibe (é aberta também por quem recebe o link)
    const chave = JSON.stringify([ids, qs.get("t"), cadastro?.instituicao_id]);
    if (cadastro?.participante_id && enviado.current !== chave) {
      enviado.current = chave;   // o mesmo quiz não é enviado duas vezes (ex.: toque duplo na última resposta)
      fetch("/api/quiz/alinhamento", {
        method: "POST", keepalive: true, headers: { "content-type": "application/json" },
        body: JSON.stringify({ participante_id: cadastro.participante_id, respostas: ids, instituicao_id: cadastro.instituicao_id, texto: qs.get("t") }),
      }).catch(() => { /* não impede o resultado */ });
    }
    router.push(`/quiz/resultado?${qs}`);
  };

  /** próxima tela: a descrição logo depois do sub-objeto (respondido, pulado ou sem opções); depois, a próxima pergunta
   *  com opções a oferecer (ex.: sem objeto, não há sub-objeto); ao fim, o resultado */
  const avancar = (de: number, r: Record<string, string | null>, depoisDoTexto = false) => {
    for (let j = de + 1; j <= telas.length; j++) {
      if (!depoisDoTexto && j - 1 === iSub) return ir({ tipo: "texto" });
      if (j < telas.length && opcoesDe(telas[j], r).length) return ir({ tipo: "pergunta", i: j });
    }
    concluir(r, texto);
  };

  const responder = (tela: Tela, opcao: string | null) => {
    // trocar uma resposta anterior invalida as que dependem dela (ex.: outro objeto, outro sub-objeto)
    const r: Record<string, string | null> = {};
    for (const t of telas) { if (t.id === tela.id) break; r[t.id] = respostas[t.id] ?? null; }
    r[tela.id] = opcao;
    setRespostas(r);
    setEscolhida(opcao ?? "pular");
    const i = telas.findIndex((t) => t.id === tela.id);
    const reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.setTimeout(() => avancar(i, r), reduzir ? 0 : 170);
  };

  if (processando) return <div className="quiz"><Processando /></div>;

  const passo = fase.tipo === "abertura" ? 0 : fase.tipo === "cadastro" ? 1 : fase.tipo === "texto" ? iSub + 3 : fase.i + 2 + (fase.i > iSub ? 1 : 0);
  return (
    <div className="quiz">
      {fase.tipo !== "abertura" && (
        <div className="quiz-topo">
          <button type="button" className="quiz-voltar" onClick={() => window.history.back()} aria-label="Voltar">←</button>
          <div className="quiz-progresso" role="progressbar" aria-valuemin={1} aria-valuemax={total} aria-valuenow={passo} aria-label={`Passo ${passo} de ${total}`}>
            <i style={{ width: `${(100 * passo) / total}%` }} />
          </div>
          <span className="quiz-passo">{passo}/{total}</span>
        </div>
      )}

      {fase.tipo === "abertura" && (
        <section className="quiz-abertura">
          <div className="quiz-selo" aria-hidden>?</div>
          <h1>Que cientista é você?</h1>
          <p>Responda {telas.length} perguntas rápidas e descubra o seu perfil de cientista e <b>quem no Nordeste pesquisa como você</b>.</p>
          <ul className="quiz-promessas">
            <li>leva uns 2 minutos</li><li>um toque por pergunta</li><li>dois cartões para compartilhar</li>
          </ul>
          <button type="button" className="quiz-comecar" onClick={() => ir({ tipo: "cadastro" })}>Começar</button>
        </section>
      )}

      {fase.tipo === "cadastro" && (
        <Cadastro inicial={cadastro} contato={contato} onPronto={(d) => { setCadastro(d); avancar(-1, respostas); }} />
      )}

      {fase.tipo === "pergunta" && (
        <Pergunta key={telas[fase.i].id} tela={telas[fase.i]} opcoes={opcoesDe(telas[fase.i], respostas)}
          atual={respostas[telas[fase.i].id]} escolhida={escolhida} onResponder={(o) => responder(telas[fase.i], o)} />
      )}

      {fase.tipo === "texto" && (
        <form className="quiz-pergunta quiz-texto" onSubmit={(e) => { e.preventDefault(); avancar(iSub, respostas, true); }}>
          <div className="quiz-enunciado">
            <span className="quiz-tag">sua pesquisa · opcional</span>
            <h2 id="q-texto">Qual organismo, doença ou sistema, exatamente?</h2>
            <p className="qt-ajuda">Em poucas palavras, deixa o match mais preciso. Ex.: “Klebsiella resistente a antibióticos em hospitais”, “abelhas sem ferrão”, “tuberculose”.</p>
          </div>
          <div className="qt-campo">
            <textarea aria-labelledby="q-texto" value={texto} maxLength={TEXTO_MAX} rows={3} autoFocus
              placeholder="O que você estuda (ou quer estudar)?" onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); avancar(iSub, respostas, true); } }} />
            <small className="qt-conta">{texto.length}/{TEXTO_MAX}</small>
          </div>
          <p className="qt-privacidade">O texto não é gravado. Guardamos, e o link leva, só um resumo numérico do tema, não as suas palavras.</p>
          <div className="quiz-opcoes">
            <button type="submit" className="quiz-comecar" disabled={texto.trim().length > 0 && texto.trim().length < 3}>Continuar</button>
            <button type="button" className="quiz-opcao quiz-nenhuma" onClick={() => { setTexto(""); avancar(iSub, respostas, true); }}><b>Pular</b><small>seguir só com as respostas</small></button>
          </div>
        </form>
      )}
    </div>
  );
}

function Pergunta({ tela, opcoes, atual, escolhida, onResponder }: {
  tela: Tela; opcoes: { id: string; rotulo: string; descricao?: string }[]; atual: string | null | undefined;
  escolhida: string | null; onResponder: (id: string | null) => void;
}) {
  const lista = useRef<HTMLDivElement>(null);
  useEffect(() => { lista.current?.querySelector<HTMLButtonElement>("button")?.focus({ preventScroll: true }); }, []);
  const teclas = (e: React.KeyboardEvent) => {
    const bs = [...(lista.current?.querySelectorAll<HTMLButtonElement>("button") ?? [])];
    const i = bs.indexOf(document.activeElement as HTMLButtonElement);
    const passo = { ArrowDown: 1, ArrowUp: -1, ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (passo && i >= 0) { e.preventDefault(); bs[Math.max(0, Math.min(bs.length - 1, i + passo))]?.focus(); }
  };
  return (
    <section className={`quiz-pergunta ${tela.bloco === "perfil" ? "quiz-perfil" : ""}`} aria-labelledby={`q-${tela.id}`}>
      <div className="quiz-enunciado">
        <span className="quiz-tag">{tela.bloco === "perfil" ? "sobre você" : "sua pesquisa"}</span>
        <h2 id={`q-${tela.id}`}>{tela.texto}</h2>
      </div>
      <div ref={lista} className="quiz-opcoes" role="group" aria-label={tela.texto} onKeyDown={teclas}>
        {opcoes.map((o) => (
          <button key={o.id} type="button" className={`quiz-opcao${escolhida === o.id ? " escolhida" : ""}${atual === o.id ? " anterior" : ""}`}
            onClick={() => onResponder(o.id)} aria-pressed={atual === o.id}>
            <b>{o.rotulo}</b>{o.descricao && <small>{o.descricao}</small>}
          </button>
        ))}
        <button type="button" className={`quiz-opcao quiz-nenhuma${escolhida === "pular" ? " escolhida" : ""}${atual === null ? " anterior" : ""}`}
          onClick={() => onResponder(null)} aria-pressed={atual === null}>
          <b>Nenhuma dessas</b><small>prefiro pular esta pergunta</small>
        </button>
      </div>
    </section>
  );
}
