-- 0008 — vínculo de subunidades à instituição principal (D-030).
-- Usado pelo mapa para esconder hospitais universitários, institutos e laboratórios de uma universidade
-- até que ela seja selecionada. Uma linha por subunidade, com a instituição "pai" mais confiável:
--   1. ROR parent/child entre instituições do NE;
--   2. ROR "related" entre uma universidade e um hospital ou instituto de pesquisa;
--   3. mesma UF e a sigla da universidade como palavra na sigla da subunidade (HC-UFPE → UFPE)
--      ou o nome completo da universidade dentro do nome da subunidade.
CREATE OR REPLACE VIEW v_instituicao_vinculo AS
WITH cand AS (
    SELECT r.institution_id AS filho, r.related_institution_id AS pai, 1 AS prioridade, 'ror_parent' AS regra
      FROM institution_relations r WHERE r.relation = 'parent' AND r.related_institution_id IS NOT NULL
    UNION ALL
    SELECT r.related_institution_id, r.institution_id, 1, 'ror_child'
      FROM institution_relations r WHERE r.relation = 'child' AND r.related_institution_id IS NOT NULL
    UNION ALL
    SELECT v.cid, v.pid, 2, 'ror_related'
      FROM institution_relations r
      JOIN institutions x ON x.id = r.institution_id
      JOIN institutions y ON y.id = r.related_institution_id
      CROSS JOIN LATERAL (VALUES (x.id, x.kind, y.id, y.kind), (y.id, y.kind, x.id, x.kind)) v (cid, ckind, pid, pkind)
     WHERE r.relation = 'related' AND v.pkind = 'universidade' AND v.ckind IN ('hospital_saude', 'instituto_pesquisa')
    UNION ALL
    SELECT c.id, p.id, 3, 'nome'
      FROM institutions c
      JOIN institutions p ON p.uf = c.uf AND p.kind = 'universidade' AND p.id <> c.id
     WHERE c.kind NOT IN ('universidade', 'centro_universitario', 'faculdade', 'instituto_federal')
       AND length(p.acronym) >= 3 AND p.acronym !~ '[, ]'
       AND (c.acronym ~ ('(^|[^A-Z])' || p.acronym || '($|[^A-Z])') OR c.name ILIKE '%' || p.name || '%')
)
SELECT DISTINCT ON (filho) filho AS institution_id, pai AS parent_id, regra
  FROM cand WHERE filho <> pai
 ORDER BY filho, prioridade;
