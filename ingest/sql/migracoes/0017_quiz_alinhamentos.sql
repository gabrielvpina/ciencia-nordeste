-- 0017 — alinhamentos do quiz (D-042): o perfil de respostas de cada participante e os pesquisadores indicados,
-- para uma futura rede (grafo) participante → pesquisador. Gravado pelo papel quiz_escrita (só INSERT); o app não lê.
-- Ligado ao cadastro com ON DELETE CASCADE: a remoção pelo código (scripts/quiz_remover.sh) e o expurgo de 24 meses
-- apagam também os alinhamentos. A descrição livre NÃO é gravada; só o código numérico do tema que já vai no link (D-040).
CREATE TABLE IF NOT EXISTS quiz_alinhamentos (
    id               uuid PRIMARY KEY,
    participante_id  uuid NOT NULL REFERENCES quiz_participantes (id) ON DELETE CASCADE,
    criado_em        timestamptz NOT NULL DEFAULT now(),
    versao_quiz      integer NOT NULL,                       -- versão do arvore.json
    respostas        text[] NOT NULL,                        -- ids das opções escolhidas (perfil e nicho), na ordem das telas
    texto_codigo     text CHECK (texto_codigo IS NULL OR char_length(texto_codigo) <= 200),   -- código PCA da descrição (D-040)
    instituicao_id   uuid REFERENCES institutions (id) ON DELETE SET NULL,   -- instituição excluída do match
    so_qualis        boolean NOT NULL,                       -- filtro do site no momento (D-035)
    nucleo           text[] NOT NULL,                        -- opções do núcleo usadas no match
    candidatos       integer NOT NULL                        -- elegíveis acima do índice mínimo
);
CREATE INDEX IF NOT EXISTS quiz_alinhamentos_participante ON quiz_alinhamentos (participante_id);

-- Arestas participante → pesquisador: a lista de 15 e o banner de 5 (com posição e índice de cada um).
CREATE TABLE IF NOT EXISTS quiz_matches (
    alinhamento_id  uuid NOT NULL REFERENCES quiz_alinhamentos (id) ON DELETE CASCADE,
    researcher_id   uuid NOT NULL REFERENCES researchers (id) ON DELETE CASCADE,
    indice          smallint NOT NULL CHECK (indice BETWEEN 0 AND 100),
    posicao_lista   smallint,                                -- 1–15, ou nulo se só aparece no banner
    posicao_banner  smallint,                                -- 1–5, ou nulo se não está no banner
    n_nicho         integer NOT NULL,                        -- publicações do pesquisador no nicho
    PRIMARY KEY (alinhamento_id, researcher_id)
);
CREATE INDEX IF NOT EXISTS quiz_matches_researcher ON quiz_matches (researcher_id);

REVOKE ALL ON quiz_alinhamentos, quiz_matches FROM quiz_escrita;
GRANT INSERT ON quiz_alinhamentos, quiz_matches TO quiz_escrita;
