-- 0006 — índices para a página de perfil (coautores pelos dois lados da aresta; orientações).
CREATE INDEX IF NOT EXISTS coauthorships_b_idx ON coauthorships (researcher_b_id);
CREATE INDEX IF NOT EXISTS institution_collaborations_b_idx ON institution_collaborations (institution_b_id);
