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

// Canal dos pedidos de privacidade (D-041): issue no GitHub com modelo próprio, que pede para não escrever dados pessoais.
const ISSUE_PRIVACIDADE = "https://github.com/gabrielvpina/ciencia-nordeste/issues/new?template=privacidade.md";

export default async function Sobre() {
  const [r] = await q<{ atualizado_em: string }>(`SELECT atualizado_em FROM mv_resumo`);
  const canal = process.env.CONTATO_PRIVACIDADE
    ? <b>{process.env.CONTATO_PRIVACIDADE}</b>
    : <>uma <a href={ISSUE_PRIVACIDADE} target="_blank" rel="noopener">issue no repositório do projeto</a> (pública)</>;
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
      <p><b>Responsável pelo tratamento (controlador):</b> <a href="#autor">Gabriel Pina</a>, autor do projeto, que é pessoal e sem fins lucrativos. Pedidos sobre dados pessoais: {canal}.</p>

      <h3 id="privacidade-pesquisadores">Dados dos pesquisadores</h3>
      <ul>
        <li><b>O que mostramos:</b> só informações públicas sobre atividade científica: nome como aparece nas publicações, vínculos institucionais, publicações, orientações e participação em programas de pós (OpenAlex, ROR, CAPES Dados Abertos) e, em poucos perfis, uma foto com licença livre (Wikimedia Commons). Não exibimos CPF, data de nascimento, endereço nem contatos.</li>
        <li><b>Por quê:</b> divulgação e mapeamento da ciência produzida no Nordeste, com dados que os próprios pesquisadores tornaram públicos ao publicar (LGPD, art. 7º, §§ 3º, 4º e 7º; interesse legítimo, art. 7º, IX).</li>
        <li><b>No quiz:</b> os cartões e a lista mostram pesquisadores com publicações próximas às respostas, com um índice de compatibilidade calculado <i>só</i> a partir dessas publicações. Não é avaliação de mérito nem de pessoas.</li>
        <li><b>Correção, ocultação ou remoção:</b> se um perfil seu tem erro, ou se você não quer aparecer no site nem no quiz, peça por {canal}. Perfis ocultados saem das páginas, das buscas e do quiz.</li>
      </ul>

      <h3 id="termos">Termos de uso e compartilhamento de dados</h3>
      <p className="meta">Versão de 11 de novembro de 2026 (revisão &ldquo;f&rdquo;). Aplicam-se ao cadastro e às respostas do quiz &ldquo;Que cientista é você?&rdquo;.</p>
      <ol className="termos">
        <li><b>Objeto.</b> Estes termos regem a coleta e o tratamento dos dados pessoais informados pelo usuário no cadastro do quiz, nos termos da Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais, LGPD).</li>
        <li><b>Controlador.</b> O tratamento é realizado pelo responsável pelo projeto Ciência Nordeste, identificado nesta página.</li>
        <li><b>Dados coletados.</b> (a) Do cadastro: nome, instituição de vínculo, tipo de filiação e curso ou programa, além da data e da versão destes termos. (b) Do quiz concluído: as alternativas escolhidas, um resumo numérico do tema da descrição livre, quando informada, e os pesquisadores indicados no resultado, com a posição e o índice de compatibilidade de cada um. O texto da descrição livre não é armazenado.</li>
        <li><b>Finalidade.</b> Os dados são utilizados exclusivamente para (i) a produção de estatísticas agregadas sobre o perfil dos usuários do quiz e (ii) estudos sobre redes de afinidade científica entre usuários e pesquisadores, cujos resultados serão divulgados apenas de forma agregada ou sem identificação dos usuários. Não são utilizados para contato, para publicidade nem para qualquer outra finalidade.</li>
        <li><b>Base legal.</b> O tratamento fundamenta-se no consentimento do titular (art. 7º, I, da LGPD), manifestado de forma livre, informada e inequívoca no momento do cadastro.</li>
        <li><b>Compartilhamento.</b> Os dados não são vendidos, cedidos nem compartilhados com terceiros, ressalvados os prestadores de infraestrutura estritamente necessários ao funcionamento do serviço, que atuam como operadores e não podem utilizá-los para fins próprios, e as hipóteses de requisição por autoridade competente, na forma da lei.</li>
        <li><b>Armazenamento e eliminação.</b> Os dados são armazenados pelo prazo máximo de 24 (vinte e quatro) meses, contados do cadastro, e eliminados automaticamente ao fim desse prazo, ou antes, a pedido do titular.</li>
        <li><b>Segurança.</b> São adotadas medidas técnicas para proteger os dados contra acessos não autorizados, entre elas acesso restrito ao responsável pelo projeto e conexão criptografada.</li>
        <li><b>Direitos do titular.</b> O titular pode, a qualquer tempo, requerer a confirmação do tratamento, o acesso, a correção ou a eliminação dos dados e revogar o consentimento (art. 18 da LGPD), pelo canal indicado nesta página.</li>
        <li><b>Idade mínima.</b> O cadastro é restrito a maiores de 18 (dezoito) anos.</li>
        <li><b>Alterações.</b> Estes termos podem ser atualizados. A versão aceita é registrada com o cadastro, e alterações relevantes de finalidade dependerão de novo consentimento.</li>
      </ol>

      <h3 id="privacidade-quiz">Quiz &ldquo;Que cientista é você?&rdquo;</h3>
      <ul>
        <li><b>O que guardamos:</b> o nome, a instituição, o tipo de filiação e o curso ou programa, informados no início do quiz, além da data e da versão do texto aceito. Ao concluir o quiz, guardamos também as alternativas escolhidas e os pesquisadores indicados no seu resultado, com posição e índice, para estudos de redes de afinidade. <b>Não guardamos</b> o texto da descrição livre, o seu IP nem dados do navegador. Quem abre um link de resultado compartilhado não gera registro.</li>
        <li><b>Base legal:</b> o seu consentimento (LGPD, art. 7º, I), que você pode revogar a qualquer momento pedindo a remoção. O quiz é para maiores de 18 anos.</li>
        <li><b>Para quê:</b> estatísticas agregadas sobre quem usa o quiz e estudos de redes de afinidade entre participantes e pesquisadores, divulgados só de forma agregada ou sem identificar os participantes. Não pedimos e-mail nem outro contato, e não vendemos nem compartilhamos os dados. O cadastro não entra no cálculo das afinidades.</li>
        <li><b>Descrição da pesquisa (opcional):</b> o texto que você escreve depois de &ldquo;especificamente?&rdquo; é enviado uma vez ao site, no fim do quiz, para virar um vetor numérico. Ele <b>não é gravado</b> nem registrado. Guardamos, e o link do resultado leva, só um resumo numérico do tema (128 números de baixa precisão), do qual não dá para recuperar as suas palavras.</li>
        <li><b>Quem acessa:</b> o site só consegue gravar esses dados, não lê-los. A leitura é restrita ao responsável pelo projeto. Os backups do banco ficam em arquivos acessíveis só a ele.</li>
        <li><b>Por quanto tempo:</b> até 24 meses; depois, são apagados automaticamente. Remover o cadastro apaga também as respostas e os pesquisadores indicados.</li>
        <li><b>Seus direitos (LGPD, art. 18):</b> confirmação, acesso, correção, remoção e revogação do consentimento. Peça por {canal}. <b>Não escreva o seu nome nem outros dados pessoais lá:</b> as issues do GitHub são públicas. Basta dizer o que você quer, e combinamos um jeito de identificar o seu cadastro sem expor você.</li>
        <li><b>Autoridade:</b> você também pode reclamar à Autoridade Nacional de Proteção de Dados (<a href="https://www.gov.br/anpd" target="_blank" rel="noopener">ANPD</a>).</li>
      </ul>
    </>
  );
}
