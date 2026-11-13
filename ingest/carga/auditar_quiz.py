"""Auditoria das opções do quiz contra os dados reais (D-051): o quanto cada nicho corresponde às publicações do Nordeste.

  python -m ingest.carga.auditar_quiz            # relatório em ingest/relatorios/quiz_auditoria.md + candidatos em quiz_auditoria.json

Mede, só lendo o banco (precisa de quiz_opcao_work preparado, python -m ingest.carga.quiz_preparar):
  1. por opção de nicho: publicações, pesquisadores ativos (>= 2 publicações casadas) e os tópicos principais (OpenAlex) que
     ela cobre, com a pureza (fração das publicações casadas no tópico mais comum e nos 5 mais comuns);
  2. temas por sub-objeto: tópicos OpenAlex mais comuns entre as publicações casadas, com o número de pesquisadores do Nordeste
     que têm >= 2 publicações no tema (candidatos à pergunta de tema);
  3. lacunas: tópicos com muitos pesquisadores cujas publicações quase não casam nenhum sub-objeto.
"""
from __future__ import annotations

import json
import sys

from .validar_arvore_quiz import DIR_RELATORIOS, carregar, opcoes, psql

MIN_PESQ_TEMA = 12      # pesquisadores com >= 2 publicações no tema (dentro do sub-objeto) para ser candidato
TEMAS_POR_SUB = 8
MIN_PESQ_LACUNA = 40
MAX_COBERTURA_LACUNA = 0.35


def main() -> int:
    arv = carregar()
    rotulo = {o["id"]: o["rotulo"] for q in arv["perguntas"].values() for o in opcoes(q)}
    faceta = {o["id"]: q["faceta"] for q in arv["perguntas"].values() for o in opcoes(q)}

    # 1. por opção
    por_opcao = psql("""
      WITH ow AS (SELECT q.opcao_id, q.work_id, w.primary_topic_id AS t FROM quiz_opcao_work q JOIN works w ON w.id = q.work_id),
           n AS (SELECT opcao_id, count(*) AS works FROM ow GROUP BY 1),
           pq AS (SELECT opcao_id, count(*) AS pesq FROM (
                    SELECT ow.opcao_id, a.researcher_id FROM ow JOIN work_authorships a ON a.work_id = ow.work_id
                     WHERE a.researcher_id IS NOT NULL GROUP BY 1, 2 HAVING count(*) >= 2) x GROUP BY 1),
           tp AS (SELECT opcao_id, t, count(*) AS c, row_number() OVER (PARTITION BY opcao_id ORDER BY count(*) DESC) AS r
                    FROM ow WHERE t IS NOT NULL GROUP BY 1, 2)
      SELECT n.opcao_id AS id, n.works, coalesce(pq.pesq, 0) AS pesq,
             round(max(tp.c) FILTER (WHERE tp.r = 1)::numeric / n.works, 3) AS pureza1,
             round(sum(tp.c) FILTER (WHERE tp.r <= 5)::numeric / n.works, 3) AS pureza5,
             string_agg(tp.t || ':' || tp.c, ',' ORDER BY tp.r) FILTER (WHERE tp.r <= 3) AS top3
        FROM n LEFT JOIN pq USING (opcao_id) LEFT JOIN tp USING (opcao_id)
       GROUP BY n.opcao_id, n.works, pq.pesq ORDER BY n.works;""")
    nomes_t = {r["id"]: r["name"] for r in psql("SELECT openalex_id AS id, name FROM topics")}

    # 2. temas por sub-objeto (tópico principal das publicações casadas pelo sub-objeto)
    temas = psql(f"""
      WITH sw AS (SELECT q.opcao_id, q.work_id, w.primary_topic_id AS t FROM quiz_opcao_work q JOIN works w ON w.id = q.work_id
                   WHERE q.opcao_id LIKE 'sub.%' AND w.primary_topic_id IS NOT NULL),
           rp AS (SELECT sw.opcao_id, sw.t, a.researcher_id FROM sw JOIN work_authorships a ON a.work_id = sw.work_id
                   WHERE a.researcher_id IS NOT NULL GROUP BY 1, 2, 3 HAVING count(*) >= 2),
           c AS (SELECT opcao_id, t, count(*) AS pesq, row_number() OVER (PARTITION BY opcao_id ORDER BY count(*) DESC) AS r FROM rp GROUP BY 1, 2)
      SELECT opcao_id AS sub, t, pesq FROM c WHERE r <= {TEMAS_POR_SUB} AND pesq >= {MIN_PESQ_TEMA} ORDER BY 1, 3 DESC;""")

    # 3. lacunas: tópicos com muitos pesquisadores e pouca cobertura pelos sub-objetos
    lacunas = psql(f"""
      WITH wt AS (SELECT w.id AS work_id, w.primary_topic_id AS t FROM works w WHERE w.primary_topic_id IS NOT NULL),
           cob AS (SELECT DISTINCT work_id FROM quiz_opcao_work WHERE opcao_id LIKE 'sub.%'),
           porT AS (SELECT wt.t, count(*) AS works, count(cob.work_id) AS cobertos FROM wt LEFT JOIN cob USING (work_id) GROUP BY 1),
           rp2 AS (SELECT t, count(*) AS pesq FROM (SELECT wt.t, a.researcher_id FROM wt JOIN work_authorships a ON a.work_id = wt.work_id
                   WHERE a.researcher_id IS NOT NULL GROUP BY 1, 2 HAVING count(*) >= 2) x GROUP BY 1)
      SELECT porT.t, porT.works, round(porT.cobertos::numeric / porT.works, 2) AS cobertura, rp2.pesq
        FROM porT JOIN rp2 USING (t)
       WHERE rp2.pesq >= {MIN_PESQ_LACUNA} AND porT.cobertos::numeric / porT.works < {MAX_COBERTURA_LACUNA}
       ORDER BY rp2.pesq DESC LIMIT 40;""")
    sub_t = {r["id"]: r for r in psql("SELECT openalex_id AS id, subfield, field FROM topics")}

    # 4. cobertura dos temas (D-053): pesquisadores ativos (>= 3 publicações) com >= 2 publicações num tema; e os tópicos
    #    principais mais comuns entre os ativos que nenhum tema cobre (candidatos a temas novos)
    cob_temas = psql("""
      WITH ativos AS (SELECT researcher_id AS rid FROM work_authorships WHERE researcher_id IS NOT NULL GROUP BY 1 HAVING count(DISTINCT work_id) >= 3),
           tw AS (SELECT DISTINCT work_id FROM quiz_opcao_work WHERE opcao_id LIKE 'tema.%'),
           sw AS (SELECT DISTINCT work_id FROM quiz_opcao_work WHERE opcao_id LIKE 'sub.%'),
           porR AS (SELECT a.researcher_id AS rid, count(DISTINCT a.work_id) FILTER (WHERE tw.work_id IS NOT NULL) AS nt,
                           count(DISTINCT a.work_id) FILTER (WHERE sw.work_id IS NOT NULL) AS ns
                      FROM work_authorships a JOIN ativos ON ativos.rid = a.researcher_id
                      LEFT JOIN tw ON tw.work_id = a.work_id LEFT JOIN sw ON sw.work_id = a.work_id GROUP BY 1)
      SELECT count(*) AS ativos, count(*) FILTER (WHERE nt >= 2) AS com_tema, count(*) FILTER (WHERE ns >= 2) AS com_sub FROM porR;""")
    fora = psql(f"""
      WITH tw AS (SELECT DISTINCT work_id FROM quiz_opcao_work WHERE opcao_id LIKE 'tema.%'),
           rp AS (SELECT w.primary_topic_id AS t, a.researcher_id FROM works w JOIN work_authorships a ON a.work_id = w.id
                   LEFT JOIN tw ON tw.work_id = w.id
                  WHERE a.researcher_id IS NOT NULL AND w.primary_topic_id IS NOT NULL AND tw.work_id IS NULL
                  GROUP BY 1, 2 HAVING count(*) >= 2)
      SELECT t, count(*) AS pesq FROM rp GROUP BY 1 ORDER BY 2 DESC LIMIT 60;""")

    # ---- relatório
    L = ["# Auditoria do quiz contra os dados (D-051)", "",
         f"Estrutura versão {arv['versao']}. Publicações e pesquisadores do Nordeste no recorte; tópicos = tópico principal do OpenAlex.", "",
         "## 1. Opções de nicho", "",
         "| opção | faceta | publicações | pesquisadores (≥ 2) | pureza (1º tópico / 5 primeiros) | tópicos mais comuns |", "|---|---|---|---|---|---|"]
    for r in por_opcao:
        top = "; ".join(f"{nomes_t.get(x.split(':')[0], x.split(':')[0])} ({x.split(':')[1]})" for x in (r["top3"] or "").split(",") if x)
        L.append(f"| {rotulo.get(r['id'], r['id'])} `{r['id']}` | {faceta.get(r['id'], '?')} | {int(r['works']):,} | {int(r['pesq']):,} | "
                 f"{float(r['pureza1'] or 0):.0%} / {float(r['pureza5'] or 0):.0%} | {top} |".replace(",", "."))
    L += ["", "## 2. Temas reais por sub-objeto (candidatos à pergunta de tema)", "",
          f"Tópicos com ≥ {MIN_PESQ_TEMA} pesquisadores do Nordeste com ≥ 2 publicações no tema, dentro do sub-objeto (até {TEMAS_POR_SUB}).", ""]
    atual = None
    for r in temas:
        if r["sub"] != atual:
            atual = r["sub"]
            L += ["", f"**{rotulo.get(atual, atual)}** `{atual}`", ""]
        L.append(f"- {nomes_t.get(r['t'], r['t'])} `{r['t']}`: {r['pesq']} pesquisadores")
    L += ["", "## 3. Lacunas (tópicos com muitos pesquisadores e pouca cobertura dos sub-objetos)", "",
          "| tópico | subárea | publicações | cobertura | pesquisadores |", "|---|---|---|---|---|"]
    for r in lacunas:
        L.append(f"| {nomes_t.get(r['t'], r['t'])} `{r['t']}` | {sub_t.get(r['t'], {}).get('subfield', '')} | {r['works']} | {float(r['cobertura']):.0%} | {r['pesq']} |")
    c = cob_temas[0]
    L += ["", "## 4. Cobertura dos temas (D-053)", "",
          f"Pesquisadores ativos (≥ 3 publicações): {int(c['ativos']):,}. Com ≥ 2 publicações em algum tema: {int(c['com_tema']):,} "
          f"({int(c['com_tema']) / int(c['ativos']):.0%}); em algum sub-objeto: {int(c['com_sub']):,} ({int(c['com_sub']) / int(c['ativos']):.0%}).".replace(",", "."),
          "", "Tópicos principais mais comuns em publicações que nenhum tema cobre (pesquisadores com ≥ 2 publicações no tópico):", "",
          "| tópico | subárea | pesquisadores |", "|---|---|---|"]
    L += [f"| {nomes_t.get(r['t'], r['t'])} `{r['t']}` | {sub_t.get(r['t'], {}).get('subfield', '')} | {r['pesq']} |" for r in fora]
    saida = DIR_RELATORIOS / "quiz_auditoria.md"
    saida.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR_RELATORIOS / "quiz_auditoria.json").write_text(json.dumps({
        "opcoes": por_opcao, "temas": [{**r, "nome": nomes_t.get(r["t"])} for r in temas],
        "lacunas": [{**r, "nome": nomes_t.get(r["t"]), "subarea": sub_t.get(r["t"], {}).get("subfield")} for r in lacunas],
        "cobertura_temas": cob_temas[0], "fora_dos_temas": [{**r, "nome": nomes_t.get(r["t"]), "subarea": sub_t.get(r["t"], {}).get("subfield")} for r in fora],
    }, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"{len(por_opcao)} opções, {len(temas)} temas candidatos, {len(lacunas)} lacunas -> {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
