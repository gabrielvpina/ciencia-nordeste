"""Prepara o banco para o match do quiz (etapa 13): copia os sinais das opções de nicho de apps/web/lib/quiz/arvore.json
para `quiz_sinal` e pré-calcula `quiz_opcao_work` (quanto cada publicação casa cada opção), migração 0012.

Só biblioteca padrão + psql no container `db`: roda também no servidor com o Python do sistema.

  python3 -m ingest.carga.quiz_preparar

Rodar depois de scripts/carregar_banco.sh (ele já chama) e sempre que o arvore.json mudar (scripts/publicar.sh chama).
Idempotente: refaz as duas tabelas e grava a versão da estrutura em `quiz_meta`.
"""

from __future__ import annotations

import sys
import time

from .validar_arvore_quiz import _lit, carregar, estatico, opcoes, psql

PESO_TIPO = {"topic": None, "subfield": 0.5, "field": 0.25, "termo": 0.7}   # topic: 1,0 principal / 0,5 secundário


def main() -> int:
    arv = carregar()
    erros = estatico(arv)
    if erros:
        print("estrutura do quiz com erros; rode: python -m ingest.carga.validar_arvore_quiz estatico", file=sys.stderr)
        return 1
    linhas = []
    for q in arv["perguntas"].values():
        if q.get("bloco") != "nicho":
            continue
        for o in opcoes(q):
            s = o.get("sinais", {})
            for tipo, chave in (("topic", "topics"), ("subfield", "subfields"), ("field", "fields"), ("termo", "termos")):
                linhas += [(o["id"], tipo, str(v)) for v in dict.fromkeys(s.get(chave, []))]
    valores = ",\n".join(f"({_lit(a)},{_lit(b)},{_lit(c)})" for a, b, c in linhas)
    t0 = time.monotonic()
    r = psql(f"""
BEGIN;
DELETE FROM quiz_sinal;
INSERT INTO quiz_sinal (opcao_id, tipo, valor) VALUES {valores};
CREATE TEMP TABLE termo ON COMMIT DROP AS
  SELECT DISTINCT valor AS termo, '\\m' || lower(f_unaccent(valor)) || CASE WHEN char_length(valor) <= 4 THEN '(s|es)?\\M' ELSE '' END AS re
    FROM quiz_sinal WHERE tipo = 'termo';   -- termo curto (≤ 4 letras) é palavra inteira: "mel" não casa "mellitus" (D-051)
CREATE TEMP TABLE termo_work ON COMMIT DROP AS
  SELECT t.termo, w.id AS work_id FROM works w JOIN termo t ON lower(f_unaccent(w.title)) ~ t.re
  UNION
  SELECT t.termo, k.work_id FROM termo t
    JOIN work_keywords k ON lower(f_unaccent(k.keyword)) LIKE '%' || lower(f_unaccent(t.termo)) || '%' AND lower(f_unaccent(k.keyword)) ~ t.re;
CREATE INDEX ON termo_work (termo);
CREATE TEMP TABLE work_sub ON COMMIT DROP AS
  SELECT w.id AS work_id, tp.subfield_id, w.primary_field_id AS field_id FROM works w JOIN topics tp ON tp.openalex_id = w.primary_topic_id;
DELETE FROM quiz_opcao_work;
INSERT INTO quiz_opcao_work (opcao_id, work_id, v)
SELECT opcao_id, work_id, max(v) FROM (
  SELECT s.opcao_id, wt.work_id, CASE WHEN wt.is_primary THEN 1.0 ELSE 0.5 END AS v
    FROM quiz_sinal s JOIN work_topics wt ON wt.topic_openalex_id = s.valor WHERE s.tipo = 'topic'
  UNION ALL SELECT s.opcao_id, ws.work_id, {PESO_TIPO['subfield']} FROM quiz_sinal s JOIN work_sub ws ON ws.subfield_id = s.valor WHERE s.tipo = 'subfield'
  UNION ALL SELECT s.opcao_id, ws.work_id, {PESO_TIPO['field']} FROM quiz_sinal s JOIN work_sub ws ON ws.field_id = s.valor WHERE s.tipo = 'field'
  UNION ALL SELECT s.opcao_id, tw.work_id, {PESO_TIPO['termo']} FROM quiz_sinal s JOIN termo_work tw ON tw.termo = s.valor WHERE s.tipo = 'termo'
) x GROUP BY 1, 2;
INSERT INTO quiz_meta (chave, valor) VALUES ('versao_arvore', {_lit(str(arv['versao']))}), ('preparado_em', now()::text)
ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor;
COMMIT;
ANALYZE quiz_opcao_work;
SELECT (SELECT count(*) FROM quiz_sinal) AS sinais, (SELECT count(DISTINCT opcao_id) FROM quiz_opcao_work) AS opcoes,
       (SELECT count(*) FROM quiz_opcao_work) AS pares_opcao_publicacao;
""")
    print(f"quiz preparado (estrutura versão {arv['versao']}) em {time.monotonic() - t0:.0f} s: {r[0] if r else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
