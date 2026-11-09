import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import "./tokens.css";
import "./globals.css";
import { RECURSOS } from "@/lib/recursos";

// Fontes baixadas no build e servidas pelo próprio site (nenhuma chamada ao Google em tempo de execução).
const inter = Inter({ subsets: ["latin"], variable: "--fonte-inter", display: "swap" });
const sora = Sora({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--fonte-sora", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: "Ciência Nordeste",
  description: "Repositório aberto da pesquisa em ciências da vida no Nordeste: saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${sora.variable}`}>
      <body>
        <header className="topo">
          <a href="/" className="marca">
            <span className="marca-simbolo" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="17" r="2.5" /><circle cx="18" cy="7" r="2.5" /><path d="M8 15.5c3-1 4-4.5 7.5-7" /><path d="M12 21a9 9 0 1 0-9-9" /></svg>
            </span>
            Ciência Nordeste
          </a>
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
