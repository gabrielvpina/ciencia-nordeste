-- 0007 — busca vetorial por tema (D-028): palavras-chave das publicações e embeddings multilíngues.
CREATE EXTENSION IF NOT EXISTS vector;

-- Palavras-chave atribuídas pelo OpenAlex a cada publicação (em inglês), com escore de relevância.
CREATE TABLE IF NOT EXISTS work_keywords (
    work_id    uuid NOT NULL REFERENCES works (id) ON DELETE CASCADE,
    keyword_id text NOT NULL,
    keyword    text NOT NULL,
    score      real,
    PRIMARY KEY (work_id, keyword_id)
);
CREATE INDEX IF NOT EXISTS work_keywords_kw_trgm ON work_keywords USING gin (lower(f_unaccent(keyword)) gin_trgm_ops);

-- Um vetor por publicação: "passage: título | palavras-chave | tópicos" no modelo multilingual-e5-base (768 dim.).
-- halfvec (meia precisão) reduz o tamanho à metade sem perda relevante de qualidade na busca.
CREATE TABLE IF NOT EXISTS work_embeddings (
    work_id    uuid PRIMARY KEY REFERENCES works (id) ON DELETE CASCADE,
    model      text NOT NULL,                 -- ex.: intfloat/multilingual-e5-base@d128750
    texto_hash text NOT NULL,                 -- sha1 do texto embutido: recalcula só o que mudou
    embedding  halfvec(768) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS work_embeddings_hnsw ON work_embeddings USING hnsw (embedding halfvec_cosine_ops);
