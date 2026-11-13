-- 0015 — o cadastro do quiz deixa de pedir e-mail (decisão do responsável, para reduzir riscos jurídicos; D-037).
-- A coluna sai da tabela; os registros existentes perdem o e-mail. Idempotente.
ALTER TABLE quiz_participantes DROP COLUMN IF EXISTS email;
