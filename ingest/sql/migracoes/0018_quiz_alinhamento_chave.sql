-- 0018 — alinhamentos sem duplicata (D-042): o mesmo participante com as mesmas respostas, descrição e instituição
-- grava uma vez só (ON CONFLICT DO NOTHING no app). Respostas diferentes (voltou e mudou) geram outro registro.
ALTER TABLE quiz_alinhamentos ADD COLUMN IF NOT EXISTS chave text;   -- sha256 de respostas + código do texto + instituição
CREATE UNIQUE INDEX IF NOT EXISTS quiz_alinhamentos_chave ON quiz_alinhamentos (participante_id, chave);
