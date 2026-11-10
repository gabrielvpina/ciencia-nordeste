import type { Metadata } from "next";
import { DM_Sans, Lexend } from "next/font/google";
import "./tokens.css";
import "./globals.css";
import Logo from "@/components/Logo";
import SeletorTema from "@/components/SeletorTema";
import { RECURSOS } from "@/lib/recursos";

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
    <html lang="pt-BR" className={`${dmsans.variable} ${lexend.variable}`} suppressHydrationWarning>
      <head>
        {/* aplica o tema salvo antes da primeira pintura */}
        <script dangerouslySetInnerHTML={{ __html: `try{var t=localStorage.getItem("cn-tema");if(t==="claro"||t==="escuro")document.documentElement.setAttribute("data-theme",t==="claro"?"light":"dark")}catch(e){}` }} />
      </head>
      <body>
        <header className="topo">
          <a href="/" className="marca">
            <Logo />
            <span className="marca-nome">Ciência <b>Nordeste</b></span>
          </a>
          <nav className="nav">
            <a href="/">Mapa</a><a href="/instituicoes">Instituições</a><a href="/programas">Programas</a><a href="/sobre">Sobre</a>
          </nav>
          <SeletorTema />
        </header>
        <main>{children}</main>
        <footer>
          Dados obtidos de fontes abertas: OpenAlex (CC0), ROR (CC0), CAPES Dados Abertos (CC-BY), INEP e IBGE.{" "}
          {RECURSOS.login ? "Este é você? Entre com seu ORCID para reivindicar o perfil." : "Encontrou um erro sobre você?"} <a href="/sobre">Saiba mais</a>. Criado por <a href="/sobre#autor">Gabriel Pina</a>.
        </footer>
      </body>
    </html>
  );
}
