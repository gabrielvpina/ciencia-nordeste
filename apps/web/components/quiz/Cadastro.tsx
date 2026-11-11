"use client";
// Cadastro do quiz (D-037): nome, instituição (com sugestões da base), filiação, e-mail opcional, curso ou programa
// (com sugestões dos programas de pós) e consentimento. Os dados vão só para /api/quiz/participante; nada fica no navegador.
import { useEffect, useRef, useState } from "react";

export type DadosCadastro = {
  nome: string; instituicao_texto: string; instituicao_id: string | null; filiacao: string;
  email: string; curso_texto: string; programa_id: string | null;
};
const FILIACOES: [string, string][] = [
  ["graduacao", "Graduação"], ["mestrado", "Mestrado"], ["doutorado", "Doutorado"],
  ["docente", "Docente"], ["pesquisador", "Pesquisador(a)"], ["mercado", "Profissional do mercado"],
];
const POS = new Set(["mestrado", "doutorado", "docente", "pesquisador"]);
const VAZIO: DadosCadastro = { nome: "", instituicao_texto: "", instituicao_id: null, filiacao: "", email: "", curso_texto: "", programa_id: null };

type Sugestao = { id: string; titulo: string; detalhe: string };

/** Campo de texto com sugestões logo abaixo (bom com o teclado do celular aberto). Escolher uma sugestão fixa o id. */
function CampoSugestoes({ id, rotulo, valor, onTexto, onEscolha, buscar, placeholder, erro, dica }: {
  id: string; rotulo: string; valor: string; onTexto: (t: string) => void; onEscolha: (s: Sugestao) => void;
  buscar: (t: string) => Promise<Sugestao[]>; placeholder: string; erro?: string; dica?: string;
}) {
  const [sug, setSug] = useState<Sugestao[]>([]);
  const [aberto, setAberto] = useState(false);
  const [ativo, setAtivo] = useState(-1);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!aberto) return;
    const t = window.setTimeout(() => { buscar(valor.trim()).then(setSug).catch(() => setSug([])); }, 220);
    return () => window.clearTimeout(t);
  }, [valor, aberto, buscar]);
  const escolher = (s: Sugestao) => { onEscolha(s); setAberto(false); setSug([]); };
  return (
    <div className="qc-campo">
      <label htmlFor={id}>{rotulo}</label>
      <input ref={ref} id={id} value={valor} placeholder={placeholder} autoComplete="off" aria-invalid={!!erro}
        role="combobox" aria-expanded={aberto && sug.length > 0} aria-controls={`${id}-lista`} aria-autocomplete="list"
        onFocus={() => { setAberto(true); window.setTimeout(() => ref.current?.scrollIntoView({ block: "start", behavior: "smooth" }), 250); }}
        onBlur={() => window.setTimeout(() => setAberto(false), 150)}
        onChange={(e) => { onTexto(e.target.value); setAberto(true); setAtivo(-1); }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setAtivo((a) => Math.min(sug.length - 1, a + 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setAtivo((a) => Math.max(-1, a - 1)); }
          else if (e.key === "Enter" && aberto && sug.length) { e.preventDefault(); escolher(sug[Math.max(0, ativo)]); }   // Enter escolhe a sugestão (não envia)
          else if (e.key === "Escape") setAberto(false);
        }} />
      {aberto && sug.length > 0 && (
        <ul id={`${id}-lista`} className="qc-sugestoes" role="listbox">
          {sug.map((s, i) => (
            <li key={s.id} role="option" aria-selected={i === ativo} className={i === ativo ? "ativo" : ""}
              onMouseDown={(e) => { e.preventDefault(); escolher(s); }}>
              <b>{s.titulo}</b><small>{s.detalhe}</small>
            </li>
          ))}
        </ul>
      )}
      {dica && !erro && <small className="qc-dica">{dica}</small>}
      {erro && <small className="qc-erro">{erro}</small>}
    </div>
  );
}

async function buscarInstituicoes(t: string): Promise<Sugestao[]> {
  if (t.length < 2) return [];
  const r: { id: string; nome: string; sigla: string | null; uf: string; municipio: string | null }[] = await (await fetch(`/api/quiz/instituicoes?q=${encodeURIComponent(t)}`)).json();
  return r.map((x) => ({ id: x.id, titulo: x.nome, detalhe: [x.sigla, x.municipio && `${x.municipio}/${x.uf}`].filter(Boolean).join(" · ") }));
}

export default function Cadastro({ inicial, contato, onPronto }: { inicial: DadosCadastro | null; contato: string | null; onPronto: (d: DadosCadastro) => void }) {
  const [d, setD] = useState<DadosCadastro>(inicial ?? VAZIO);
  const [consentimento, setConsentimento] = useState(false);
  const [isca, setIsca] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);
  const [falha, setFalha] = useState<string | null>(null);
  const pos = POS.has(d.filiacao);
  const muda = (p: Partial<DadosCadastro>) => {
    setD((x) => ({ ...x, ...p }));
    setErros((e) => { const n = { ...e }; for (const k of Object.keys(p)) delete n[k]; return n; });   // corrigiu: some o aviso do campo
  };

  const buscarProgramas = async (t: string): Promise<Sugestao[]> => {
    if (t.length < 2 && !d.instituicao_id) return [];
    const qs = new URLSearchParams({ q: t, ...(d.instituicao_id ? { inst: d.instituicao_id } : {}) });
    const r: { id: string; nome: string; sigla: string | null; uf: string; degree: string | null; da_inst: boolean }[] = await (await fetch(`/api/quiz/programas?${qs}`)).json();
    const nivel = (g: string | null) => (g ? g.toLowerCase().replace("mestrado/doutorado", "mestrado e doutorado") : null);
    return r.map((x) => ({ id: x.id, titulo: x.nome, detalhe: [x.sigla, x.uf, nivel(x.degree), x.da_inst ? "da sua instituição" : null].filter(Boolean).join(" · ") }));
  };

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setFalha(null);
    const er: Record<string, string> = {};
    if (d.nome.trim().split(/\s+/).length < 2) er.nome = "Informe o nome completo (nome e sobrenome).";
    if (d.instituicao_texto.trim().length < 2) er.instituicao_texto = "Informe a sua instituição.";
    if (!d.filiacao) er.filiacao = "Escolha uma opção.";
    if (d.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email.trim())) er.email = "E-mail inválido (ou deixe em branco).";
    if (d.curso_texto.trim().length < 2) er.curso_texto = pos ? "Informe o seu programa." : "Informe o seu curso.";
    if (!consentimento) er.consentimento = "É preciso concordar para continuar.";
    setErros(er);
    if (Object.keys(er).length) return;
    setEnviando(true);
    try {
      const r = await fetch("/api/quiz/participante", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...d, consentimento, site: isca }),
      });
      const j = await r.json().catch(() => ({}));
      if (r.ok) return onPronto(d);
      if (j.campos) setErros(j.campos);
      setFalha(j.erro ?? "Não foi possível salvar agora. Tente de novo em instantes.");
    } catch {
      setFalha("Sem conexão. Tente de novo em instantes.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="quiz-cadastro" onSubmit={enviar} noValidate>
      <div className="quiz-enunciado">
        <span className="quiz-tag">antes de começar</span>
        <h2>Quem é você?</h2>
      </div>
      <div className="qc-campo">
        <label htmlFor="qc-nome">Nome completo</label>
        <input id="qc-nome" value={d.nome} onChange={(e) => muda({ nome: e.target.value })} autoComplete="name" maxLength={120} aria-invalid={!!erros.nome} />
        {erros.nome && <small className="qc-erro">{erros.nome}</small>}
      </div>
      <CampoSugestoes id="qc-inst" rotulo="Instituição onde você está filiado(a)" valor={d.instituicao_texto} placeholder="Escreva o nome por extenso"
        onTexto={(t) => muda({ instituicao_texto: t, instituicao_id: null })}
        onEscolha={(s) => muda({ instituicao_texto: s.titulo, instituicao_id: s.id })}
        buscar={buscarInstituicoes} erro={erros.instituicao_texto}
        dica={d.instituicao_id ? "Encontrada na base do Ciência Nordeste." : "Escolha uma sugestão, se aparecer; se não, vale o nome que você escrever."} />
      <fieldset className="qc-campo qc-filiacao">
        <legend>Tipo de filiação</legend>
        <div className="qc-pilulas">
          {FILIACOES.map(([v, r]) => (
            <label key={v} className={d.filiacao === v ? "ativa" : ""}>
              <input type="radio" name="filiacao" value={v} checked={d.filiacao === v} onChange={() => muda({ filiacao: v, programa_id: null })} />{r}
            </label>
          ))}
        </div>
        {erros.filiacao && <small className="qc-erro">{erros.filiacao}</small>}
      </fieldset>
      {pos ? (
        <CampoSugestoes id="qc-curso" rotulo="Programa de pós-graduação" valor={d.curso_texto} placeholder="Ex.: Genética e Biologia Molecular"
          onTexto={(t) => muda({ curso_texto: t, programa_id: null })}
          onEscolha={(s) => muda({ curso_texto: s.titulo, programa_id: s.id })}
          buscar={buscarProgramas} erro={erros.curso_texto}
          dica={d.programa_id ? "Programa encontrado na base (CAPES)." : "Sugestões dos programas da CAPES; se o seu não aparecer, escreva o nome."} />
      ) : (
        <div className="qc-campo">
          <label htmlFor="qc-curso">{d.filiacao === "mercado" ? "Curso de formação" : "Curso de graduação"}</label>
          <input id="qc-curso" value={d.curso_texto} onChange={(e) => muda({ curso_texto: e.target.value, programa_id: null })} maxLength={200} aria-invalid={!!erros.curso_texto} placeholder="Ex.: Ciências Biológicas" />
          {erros.curso_texto && <small className="qc-erro">{erros.curso_texto}</small>}
        </div>
      )}
      <div className="qc-campo">
        <label htmlFor="qc-email">E-mail <span className="qc-opcional">(opcional)</span></label>
        <input id="qc-email" type="email" inputMode="email" autoComplete="email" value={d.email} onChange={(e) => muda({ email: e.target.value })} maxLength={200} aria-invalid={!!erros.email} />
        {erros.email && <small className="qc-erro">{erros.email}</small>}
      </div>
      <div className="qc-isca" aria-hidden>
        <label>Não preencha: <input tabIndex={-1} autoComplete="off" value={isca} onChange={(e) => setIsca(e.target.value)} name="site" /></label>
      </div>
      <label className={`qc-consentimento${erros.consentimento ? " invalido" : ""}`}>
        <input type="checkbox" checked={consentimento} onChange={(e) => { setConsentimento(e.target.checked); setErros((x) => { const n = { ...x }; delete n.consentimento; return n; }); }} />
        <span>
          Concordo que o Ciência Nordeste guarde estes dados para estatísticas sobre quem usa o quiz e, se informei o e-mail, para contato sobre o projeto.
          Minhas respostas e meu resultado não são gravados. Os dados ficam até 24 meses e posso pedir a remoção a qualquer momento
          {contato ? <> ({contato})</> : null}. <a href="/sobre#privacidade-quiz" target="_blank" rel="noopener">Saiba mais</a>
        </span>
      </label>
      {erros.consentimento && <small className="qc-erro">{erros.consentimento}</small>}
      {falha && <p className="qc-falha" role="alert">{falha}</p>}
      <button type="submit" className="quiz-comecar" disabled={enviando}>{enviando ? "Salvando…" : "Continuar"}</button>
    </form>
  );
}
