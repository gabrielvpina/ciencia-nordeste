import type { Metadata } from "next";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Sobre — Ciência Nordeste" };

// Redes do autor (as mesmas do blog gabrielvpina.github.io).
const REDES: { nome: string; titulo: string; url: string; icone: React.ReactNode }[] = [
  { nome: "Blog", titulo: "me.log — blog", url: "https://gabrielvpina.github.io", icone: <><path d="M4 20h4L19 9l-4-4L4 16v4z" /><path d="M13.5 6.5l4 4" /></> },
  { nome: "GitHub", titulo: "github.com/gabrielvpina", url: "https://github.com/gabrielvpina", icone: <path className="cheio" d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.08 0 4.41-2.69 5.38-5.26 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" /> },
  { nome: "LinkedIn", titulo: "LinkedIn", url: "https://linkedin.com/in/gabriel-rodrigues-008419210/", icone: <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M8 10v7M8 7v.01M12 17v-4a2 2 0 0 1 4 0v4M12 10v7" /></> },
  { nome: "ORCID", titulo: "ORCID 0009-0005-2294-2845", url: "https://orcid.org/0009-0005-2294-2845", icone: <><circle cx="12" cy="12" r="9" /><path d="M9 10v6M9 7.5v.01M12 16v-6h2a3 3 0 0 1 0 6h-2z" /></> },
  { nome: "Lattes", titulo: "Currículo Lattes", url: "https://lattes.cnpq.br/6691808758719803", icone: <><path d="M6 3h9l3 3v15H6z" /><path d="M9 10h6M9 14h6M9 18h4" /></> },
];

export default async function Sobre() {
  const [r] = await q<{ atualizado_em: string }>(`SELECT atualizado_em FROM mv_resumo`);
  return (
    <>
      <h1>Sobre</h1>
      <section className="autor" id="autor" aria-labelledby="autor-nome">
        <img src="/equipe/gabriel-pina.webp" alt="Foto de Gabriel Victor Pina Rodrigues" width={132} height={132} className="autor-foto" />
        <div>
          <p className="autor-rotulo">Quem faz o Ciência Nordeste</p>
          <h2 id="autor-nome">Gabriel Victor Pina Rodrigues</h2>
          <p>Cientista de Dados e Bioinformata, atua nas áreas da virologia e genômica. Doutorando em Genética e Biologia Molecular na Universidade Estadual de Santa Cruz (UESC), em Ilhéus, Bahia, onde estuda a descoberta de vírus em dados públicos de sequenciamento.</p>
          <ul className="redes">
            {REDES.map((r) => (
              <li key={r.nome}><a href={r.url} target="_blank" rel="noopener noreferrer" title={r.titulo}>
                <svg viewBox="0 0 24 24" aria-hidden="true">{r.icone}</svg>{r.nome}
              </a></li>
            ))}
          </ul>
        </div>
      </section>

      <h2>Sobre os dados</h2>
      <p>O Ciência Nordeste reúne, a partir de dados abertos, a pesquisa em ciências da vida (saúde, biomedicina, biotecnologia, genética, microbiologia, ciências agrárias e biológicas e veterinária) de instituições com sede nos nove estados do Nordeste, de 2022 em diante.</p>
      <h2>Fontes e licenças</h2>
      <ul className="lista">
        <li><b>OpenAlex</b> (CC0): publicações, autores, instituições, tópicos e financiadores.</li>
        <li><b>ROR</b> (CC0): cadastro de organizações de pesquisa e coordenadas.</li>
        <li><b>CAPES Dados Abertos</b> (CC-BY): programas de pós-graduação, docentes, teses e dissertações.</li>
        <li><b>INEP</b> (Censo da Educação Superior) e <b>IBGE</b>: instituições de ensino, municípios, coordenadas e o contorno dos estados usado no mapa (malha oficial, gravada no próprio site).</li>
        <li><b>Wikidata / Wikimedia Commons</b>: algumas fotos, sempre com licença livre e crédito ao autor.</li>
      </ul>
      <p className="meta">Não usamos dados da Plataforma Lattes nem do Google Acadêmico. Última atualização da base: {new Date(r.atualizado_em).toLocaleDateString("pt-BR")}.</p>
      <h2>Como os perfis são montados</h2>
      <p>Cada pesquisador tem um identificador interno permanente. Perfis do OpenAlex com o mesmo ORCID são unidos automaticamente. Docentes da CAPES só são unidos a um autor do OpenAlex quando há um único candidato com o mesmo nome e a mesma instituição; os demais casos passam por revisão humana. Por isso, alguns pesquisadores ainda podem aparecer em mais de um perfil.</p>
      <h2>Privacidade (LGPD)</h2>
      <p>Usamos apenas informações públicas sobre atividade científica (publicações, vínculos, pós-graduação). Não exibimos CPF, data de nascimento nem contatos. Se você encontrou um perfil seu com erro, ou quer ocultá-lo ou removê-lo, escreva para o responsável pelo projeto. A reivindicação de perfil com login pelo ORCID será habilitada quando o site entrar em produção.</p>
      <h3 id="privacidade-quiz">Quiz &ldquo;Que cientista é você?&rdquo;</h3>
      <ul>
        <li><b>O que guardamos:</b> o nome, a instituição, o tipo de filiação e o curso ou programa, informados no início do quiz, com o seu consentimento. <b>Não guardamos</b> as suas respostas, o seu resultado, o seu IP nem dados do navegador.</li>
        <li><b>Para quê:</b> apenas estatísticas sobre quem usa o quiz (filiações, instituições, programas). Não pedimos e-mail nem outro contato. Esses dados não entram no cálculo das afinidades.</li>
        <li><b>Quem acessa:</b> o site só consegue gravar esses dados, não lê-los. A leitura é restrita ao responsável pelo projeto.</li>
        <li><b>Por quanto tempo:</b> até 24 meses; depois, são apagados automaticamente.</li>
        <li><b>Seus direitos (LGPD):</b> você pode pedir acesso, correção ou remoção a qualquer momento{process.env.CONTATO_PRIVACIDADE ? <>, escrevendo para <b>{process.env.CONTATO_PRIVACIDADE}</b></> : <>, pelo <a href="https://github.com/gabrielvpina/ciencia-nordeste/issues" target="_blank" rel="noopener">repositório do projeto</a></>}.</li>
      </ul>
    </>
  );
}
