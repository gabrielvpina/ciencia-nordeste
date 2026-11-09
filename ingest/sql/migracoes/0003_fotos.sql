-- 0003 — Parte 7: fotos de pesquisadores (Wikimedia Commons com licença livre; depois, upload próprio na Fase D).
CREATE TABLE IF NOT EXISTS researcher_photos (
    researcher_id   uuid PRIMARY KEY REFERENCES researchers (id) ON DELETE CASCADE,
    source          text NOT NULL CHECK (source IN ('wikimedia_commons', 'upload_proprio')),
    file_name       text NOT NULL,          -- arquivo WebP em ingest/dados/fotos/
    source_title    text,                   -- título do arquivo no Commons
    source_page_url text,
    license         text NOT NULL,
    license_url     text,
    author          text,                   -- crédito exigido pela licença
    width           integer,
    height          integer,
    retrieved_at    timestamptz NOT NULL
);
