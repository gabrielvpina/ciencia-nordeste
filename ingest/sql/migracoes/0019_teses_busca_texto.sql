-- 0019: índice de texto das teses e dissertações para a página de busca (/busca, D-044).
-- A busca casa qualquer palavra da consulta no título ou nas palavras-chave (dicionário português, sem acento).
-- A expressão precisa ser idêntica à de lib/busca.ts para o índice ser usado.
CREATE INDEX IF NOT EXISTS theses_texto_idx ON theses
  USING gin (to_tsvector('portuguese', f_unaccent(coalesce(title, '') || ' ' || coalesce(keywords, ''))));
