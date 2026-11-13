"""Avaliação da pergunta de tema do quiz (D-051): escolher um tema torna o banner mais específico?

Para cada tema (ou uma amostra), chama POST /api/quiz/resultado duas vezes, com o mesmo método, objeto e sub-objeto:
sem o tema e com o tema. Mede, nos 5 do banner e nos 15 da lista:
  - aderência ao tema: fração de pessoas com >= 2 publicações cujo tópico principal (OpenAlex) é um dos tópicos do tema;
  - quantos nomes do banner mudam; se o banner fechou com 5 pessoas; latência.

  python -m ingest.carga.avaliar_quiz_temas [--url http://localhost:3000] [--amostra 40]

Relatório: ingest/relatorios/quiz_temas.md
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys

import httpx

from .validar_arvore_quiz import DIR_RELATORIOS, _lit, carregar, psql

# método mais típico para cada objeto (o tema não depende do método, mas o núcleo sim)
METODO = {"objeto.plantas": "metodo.campo", "objeto.insetos": "metodo.campo", "objeto.producao": "metodo.bancada", "objeto.fauna": "metodo.campo",
          "objeto.micro": "metodo.bancada", "objeto.humanos": "metodo.epidemio", "objeto.alimentos": "metodo.bancada", "objeto.ambiente": "metodo.campo",
          "objeto.servicos": "metodo.epidemio"}


def aderentes(ids: list[str], topicos: list[str]) -> set[str]:
    if not ids:
        return set()
    linhas = psql(f"""
      SELECT a.researcher_id::text AS id FROM work_authorships a JOIN works w ON w.id = a.work_id
       WHERE a.researcher_id IN ({','.join(_lit(i) + '::uuid' for i in ids)}) AND w.primary_topic_id IN ({','.join(map(_lit, topicos))})
       GROUP BY 1 HAVING count(DISTINCT a.work_id) >= 2;""")
    return {r["id"] for r in linhas}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:3000")
    p.add_argument("--amostra", type=int, default=40)
    a = p.parse_args(argv)
    arv = carregar()
    obj_de = {s["id"]: obj for obj, subs in arv["perguntas"]["sub_objeto"]["opcoes_por"].items() for s in subs}
    casos = [(sub, t) for sub, ts in arv["perguntas"]["tema"]["opcoes_por"].items() for t in ts]
    random.Random(51).shuffle(casos)
    casos = casos[: a.amostra]
    linhas, ganhos_b, ganhos_l, cheios, ms = [], [], [], 0, []
    with httpx.Client(timeout=120) as cli:
        for sub, t in casos:
            base = [METODO[obj_de[sub]], obj_de[sub], sub]
            res = {}
            for nome, resp in (("sem", base), ("com", base + [t["id"]])):
                r = cli.post(f"{a.url}/api/quiz/resultado", json={"instituicao_id": None, "respostas": resp})
                r.raise_for_status()
                res[nome] = r.json()
            ad = aderentes(list({x["id"] for k in res for x in res[k]["lista"]}), t["sinais"]["topics"])
            f = lambda xs: (sum(x["id"] in ad for x in xs) / len(xs)) if xs else 0.0
            b_sem, b_com, l_sem, l_com = f(res["sem"]["banner"]), f(res["com"]["banner"]), f(res["sem"]["lista"]), f(res["com"]["lista"])
            trocas = len({x["id"] for x in res["com"]["banner"]} - {x["id"] for x in res["sem"]["banner"]})
            ganhos_b.append(b_com - b_sem); ganhos_l.append(l_com - l_sem); ms.append(res["com"]["ms"])
            cheios += len(res["com"]["banner"]) == 5
            linhas.append(f"| {t['rotulo']} ({sub.removeprefix('sub.')}) | {b_sem:.0%} → **{b_com:.0%}** | {l_sem:.0%} → **{l_com:.0%}** | {trocas} | {len(res['com']['banner'])} | {res['com']['ms']} |")
            print(linhas[-1])
    resumo = (f"{len(casos)} temas (amostra fixa). Aderência média ao tema no banner: {statistics.mean([b + 0 for b in ganhos_b]):+.0%} "
              f"(ganho); na lista de 15: {statistics.mean(ganhos_l):+.0%}. Banner com 5 pessoas em {cheios} de {len(casos)}. "
              f"Latência mediana com tema: {statistics.median(ms)} ms.")
    rel = DIR_RELATORIOS / "quiz_temas.md"
    rel.write_text("\n".join([
        "# Quiz: efeito da pergunta de tema (D-051)", "",
        "Aderência = fração de pessoas com ≥ 2 publicações cujo tópico principal (OpenAlex) é um dos tópicos do tema.",
        "Mesmo método, objeto e sub-objeto; só muda a resposta de tema.", "", resumo, "",
        "| tema | aderência no banner (sem → com tema) | na lista de 15 | nomes trocados no banner | banner | ms |",
        "|---|---|---|---|---|---|", *linhas, ""]), encoding="utf-8")
    print("\n" + resumo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
