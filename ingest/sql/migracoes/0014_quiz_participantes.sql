-- 0014 — cadastro dos participantes do quiz (etapa 13, D-037). Primeira escrita do app.
-- Dados pessoais informados pela própria pessoa, com consentimento. O app grava com o papel quiz_escrita (só INSERT)
-- e nunca lê esta tabela; leitura e exportação só pelo responsável (psql). Retenção: 24 meses (expurgo em
-- scripts/publicar.sh e scripts/carregar_banco.sh). Não se grava IP, navegador, respostas nem resultado.
CREATE TABLE IF NOT EXISTS quiz_participantes (
    id                   uuid PRIMARY KEY,
    criado_em            timestamptz NOT NULL DEFAULT now(),
    nome                 text NOT NULL CHECK (char_length(nome) BETWEEN 2 AND 120),
    instituicao_id       uuid REFERENCES institutions (id) ON DELETE SET NULL,   -- quando a pessoa escolheu uma sugestão da base
    instituicao_texto    text NOT NULL CHECK (char_length(instituicao_texto) BETWEEN 2 AND 200),
    filiacao             text NOT NULL CHECK (filiacao IN ('graduacao', 'mestrado', 'doutorado', 'docente', 'pesquisador', 'mercado')),
    email                text CHECK (email IS NULL OR (char_length(email) <= 200 AND email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')),
    programa_id          uuid REFERENCES graduate_programs (id) ON DELETE SET NULL, -- quando escolheu um programa da base
    curso_texto          text NOT NULL CHECK (char_length(curso_texto) BETWEEN 2 AND 200),
    consentimento_versao text NOT NULL,                                             -- versão do texto de consentimento aceito
    versao_quiz          integer NOT NULL                                           -- versão do arvore.json
);
CREATE INDEX IF NOT EXISTS quiz_participantes_criado ON quiz_participantes (criado_em);

-- Papel só de escrita. Nasce sem login; scripts/migrar.sh habilita o login com QUIZ_DB_PASSWORD do .env.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'quiz_escrita') THEN
        CREATE ROLE quiz_escrita NOLOGIN;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO quiz_escrita', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO quiz_escrita;
REVOKE ALL ON quiz_participantes FROM quiz_escrita;
GRANT INSERT ON quiz_participantes TO quiz_escrita;
