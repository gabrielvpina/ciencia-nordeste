"use client";
// Biografia pública do ORCID (D-055): texto do próprio pesquisador, recolhido em poucas linhas, com a fonte e a data.
import { useState } from "react";

export default function BioOrcid({ texto, orcid, atualizado, idioma }: { texto: string; orcid: string; atualizado: string | null; idioma: string | null }) {
  const [aberta, setAberta] = useState(false);
  const longa = texto.length > 360;
  const data = atualizado ? new Date(atualizado).toLocaleDateString("pt-BR", { month: "2-digit", year: "numeric" }) : null;
  return (
    <section className="bio-orcid" aria-labelledby="bio-titulo" lang={idioma === "en" ? "en" : "pt-BR"}>
      <h2 id="bio-titulo">Sobre</h2>
      <div className={`bio-texto${longa && !aberta ? " recolhida" : ""}`}>
        {texto.split(/\n{2,}/).map((p, i) => <p key={i}>{p}</p>)}
      </div>
      {longa && (
        <button type="button" className="mais-itens" aria-expanded={aberta} onClick={() => setAberta(!aberta)}>{aberta ? "Ler menos" : "Ler mais"}</button>
      )}
      <p className="bio-fonte meta" lang="pt-BR">
        Texto do próprio pesquisador no ORCID{data ? ` · atualizado em ${data}` : ""}{idioma === "en" ? " · em inglês" : ""} ·{" "}
        <a href={`https://orcid.org/${orcid}`} target="_blank" rel="noopener noreferrer">ver no ORCID</a>
      </p>
    </section>
  );
}
