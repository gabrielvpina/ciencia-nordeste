-- 0016 — código de remoção do cadastro do quiz (revisão LGPD, D-041).
-- Os pedidos dos titulares chegam pelas issues do GitHub, que são públicas. Para pedir a remoção sem expor nome nem
-- instituição, o cadastro gera um código aleatório (ex.: K7QM-4TZP), mostrado uma vez à pessoa. O código não identifica
-- ninguém e serve só para achar o registro. Registros antigos ficam sem código (removíveis pelo nome, a pedido).
ALTER TABLE quiz_participantes ADD COLUMN IF NOT EXISTS codigo_remocao text;
CREATE UNIQUE INDEX IF NOT EXISTS quiz_participantes_codigo ON quiz_participantes (codigo_remocao);
