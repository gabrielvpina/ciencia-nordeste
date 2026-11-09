import type { Metadata } from "next";
import "./globals.css";
import { RECURSOS } from "@/lib/recursos";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: "Ciência Nordeste",
  description: "Repositório aberto da pesquisa em ciências da vida no Nordeste: saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="topo">
          <a href="/" className="marca">Ciência Nordeste</a>
          <span className="sub">ciências da vida · 9 estados · 2022–2026</span>
          <nav className="nav">
            <a href="/">Mapa e busca</a><a href="/instituicoes">Instituições</a><a href="/programas">Programas</a><a href="/sobre">Sobre os dados</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer>
          Dados obtidos de fontes abertas: OpenAlex (CC0), ROR (CC0), CAPES Dados Abertos (CC-BY), INEP e IBGE.
          {RECURSOS.login ? "Este é você? Entre com seu ORCID para reivindicar o perfil." : "Encontrou um erro sobre você?"} <a href="/sobre">Saiba mais</a>.
        </footer>
      </body>
    </html>
  );
}
