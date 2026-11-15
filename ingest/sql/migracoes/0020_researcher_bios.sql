-- 0020: biografias públicas do ORCID (D-055). Texto escrito pelo próprio pesquisador e publicado no ORCID (dados públicos, CC0).
-- Uma linha por pesquisador consultado: status guarda o resultado (200 = tem biografia; 404 = sem biografia pública), para a
-- coleta incremental não repetir quem já foi consultado recentemente.
CREATE TABLE IF NOT EXISTS researcher_bios (
  researcher_id     uuid PRIMARY KEY REFERENCES researchers(id) ON DELETE CASCADE,
  orcid             text NOT NULL,
  status            smallint NOT NULL,
  texto             text,
  idioma            text,
  atualizado_orcid  timestamptz,
  coletado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS researcher_bios_coletado ON researcher_bios (coletado_em);
