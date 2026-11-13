-- 0013 — remove a Fundação Ezequiel Dias (FUNED, ROR 01qgvp179) do recorte (D-038).
-- Ela fica em Belo Horizonte (MG); o ROR a localiza em "Gameleira", casado por engano com o município de Gameleira (PE).
-- A ingestão passou a ignorá-la (ROR_EXCLUIDOS em ingest/carga/parte1_instituicoes.py). Esta migração corrige o banco já
-- carregado e é idempotente: sem a FUNED, não faz nada.
--   1. tira a FUNED das autorias (e recalcula is_ne);
--   2. apaga as publicações que ficaram sem nenhuma instituição do NE (cascata: autorias, tópicos, palavras-chave, vetores…);
--   3. desvincula os pesquisadores que a tinham como instituição principal (os que ficarem sem produção saem na próxima ingestão);
--   4. apaga a instituição (cascata: identificadores, relações, colaborações).
-- Depois (scripts/migrar.sh não faz isto): REFRESH das visões, ingest/sql/perfis_tematicos.sql e quiz_preparar.

DO $$
DECLARE
    f uuid := (SELECT institution_id FROM institution_identifiers WHERE scheme = 'ror' AND value = '01qgvp179' LIMIT 1);
    afetadas uuid[];
    n_works int;
BEGIN
    IF f IS NULL THEN
        RAISE NOTICE 'FUNED já não está na base';
        RETURN;
    END IF;
    afetadas := ARRAY(SELECT DISTINCT work_id FROM work_authorships WHERE institution_ids @> ARRAY[f]);
    UPDATE work_authorships
       SET institution_ids = array_remove(institution_ids, f),
           is_ne = cardinality(array_remove(institution_ids, f)) > 0
     WHERE institution_ids @> ARRAY[f];
    DELETE FROM works w                       -- só entre as publicações que tinham a FUNED
     WHERE w.id = ANY(afetadas) AND NOT EXISTS (SELECT 1 FROM work_authorships a WHERE a.work_id = w.id AND a.is_ne);
    GET DIAGNOSTICS n_works = ROW_COUNT;
    UPDATE researchers SET main_institution_id = NULL WHERE main_institution_id = f;
    UPDATE graduate_programs SET institution_id = NULL WHERE institution_id = f;
    UPDATE theses SET institution_id = NULL WHERE institution_id = f;
    UPDATE institution_relations SET related_institution_id = NULL WHERE related_institution_id = f;
    DELETE FROM institutions WHERE id = f;
    RAISE NOTICE 'FUNED removida (%): % publicações sem outra instituição do NE apagadas', f, n_works;
END $$;
