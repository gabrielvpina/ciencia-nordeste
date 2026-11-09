import type { Metadata } from "next";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Sobre os dados — Ciência Nordeste" };

export default async function Sobre() {
  const [r] = await q<{ atualizado_em: string }>(`SELECT atualizado_em FROM mv_resumo`);
  return (
    <>
      <h1>Sobre os dados</h1>
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
    </>
  );
}
