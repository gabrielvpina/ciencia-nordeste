import type { Metadata } from "next";
import { DM_Sans, Lexend } from "next/font/google";
import "./tokens.css";
import "./globals.css";
import Logo from "@/components/Logo";
import { soQualis } from "@/lib/qualis-filtro";
import { RECURSOS } from "@/lib/recursos";

const REPOSITORIO = "https://github.com/gabrielvpina/ciencia-nordeste";

// Fontes baixadas no build e servidas pelo próprio site (nenhuma chamada ao Google em tempo de execução).
const dmsans = DM_Sans({ subsets: ["latin"], variable: "--fonte-dmsans", display: "swap" });
const lexend = Lexend({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--fonte-lexend", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: "Ciência Nordeste",
  description: "Repositório aberto da pesquisa em ciências da vida no Nordeste: saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${dmsans.variable} ${lexend.variable}`}>
      <body>
        <header className="topo">
          <a href="/" className="marca">
            <Logo />
            <span className="marca-nome">Ciência <b>Nordeste</b></span>
          </a>
          <nav className="nav">
            <a href="/">Mapa</a><a href="/instituicoes">Instituições</a><a href="/programas">Programas</a><a href="/sobre">Sobre</a>
          </nav>
          <div className="topo-acoes">
            <a className="botao-icone" href={REPOSITORIO} target="_blank" rel="noopener" title="Código no GitHub" aria-label="Repositório no GitHub">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.08 0 4.41-2.69 5.38-5.26 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" /></svg>
            </a>
          </div>
        </header>
        <main>{children}</main>
        <footer>
          {soQualis() && <>Contagens só com publicações em revistas com Qualis (filtro na <a href="/">tela inicial</a>).{" "}</>}
          Dados obtidos de fontes abertas: OpenAlex (CC0), ROR (CC0), CAPES Dados Abertos (CC-BY), INEP e IBGE.{" "}
          {RECURSOS.login ? "Este é você? Entre com seu ORCID para reivindicar o perfil." : "Encontrou um erro sobre você?"} <a href="/sobre">Saiba mais</a>. Criado por <a href="/sobre#autor">Gabriel Pina</a>.
        </footer>
      </body>
    </html>
  );
}
