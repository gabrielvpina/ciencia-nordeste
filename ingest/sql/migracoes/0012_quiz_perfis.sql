-- 0012 — perfil temático por pesquisador e sinais pré-calculados do quiz (etapa 13, D-036).

-- Perfil temático: média ponderada e normalizada dos vetores das publicações do pesquisador no recorte
-- (mesmo modelo de work_embeddings, D-028). Calculado por ingest/sql/perfis_tematicos.sql.
CREATE TABLE IF NOT EXISTS researcher_embeddings (
    researcher_id uuid PRIMARY KEY REFERENCES researchers (id) ON DELETE CASCADE,
    model         text NOT NULL,
    n_works       integer NOT NULL,              -- publicações com vetor que entraram na média
    embedding     halfvec(768) NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS researcher_embeddings_hnsw ON researcher_embeddings USING hnsw (embedding halfvec_cosine_ops);

-- Quiz: sinais de cada opção de nicho (copiados de apps/web/lib/quiz/arvore.json por ingest/carga/quiz_preparar.py)
CREATE TABLE IF NOT EXISTS quiz_sinal (
    opcao_id text NOT NULL,
    tipo     text NOT NULL CHECK (tipo IN ('topic', 'subfield', 'field', 'termo')),
    valor    text NOT NULL,
    PRIMARY KEY (opcao_id, tipo, valor)
);

-- Quiz: quanto cada publicação casa cada opção (o melhor sinal: tópico principal 1,0 · secundário 0,5 · subfield 0,5 ·
-- field 0,25 · termo 0,7). O peso da faceta entra na hora do match (lib/quiz/alinhamento.ts).
CREATE TABLE IF NOT EXISTS quiz_opcao_work (
    opcao_id text NOT NULL,
    work_id  uuid NOT NULL REFERENCES works (id) ON DELETE CASCADE,
    v        real NOT NULL,
    PRIMARY KEY (opcao_id, work_id)
);
CREATE INDEX IF NOT EXISTS quiz_opcao_work_work ON quiz_opcao_work (work_id);

-- Versão da estrutura do quiz carregada (o app confere com a do arvore.json)
CREATE TABLE IF NOT EXISTS quiz_meta (
    chave text PRIMARY KEY,
    valor text NOT NULL
);
