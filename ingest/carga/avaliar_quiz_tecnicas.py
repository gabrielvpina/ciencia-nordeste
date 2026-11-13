"""Avaliação da pergunta de técnica do quiz (D-053): escolher a técnica deixa o banner mais fiel a ela?

Para cada técnica, chama POST /api/quiz/resultado com um caminho típico do método (objeto e sub-objeto fixos), sem e com a
técnica, e mede a aderência: fração do banner (5) e da lista (15) com >= 2 publicações que casam a técnica (quiz_opcao_work).

  python -m ingest.carga.avaliar_quiz_tecnicas [--url http://localhost:3000]     -> ingest/relatorios/quiz_tecnicas_avaliacao.md
"""
from __future__ import annotations

import argparse
import statistics
import sys

import httpx

from .validar_arvore_quiz import DIR_RELATORIOS, _lit, carregar, psql

CAMINHO = {"metodo.bioinfo": ["objeto.micro", "sub.virus"], "metodo.genetica": ["objeto.plantas", "sub.graos"],
           "metodo.bancada": ["objeto.micro", "sub.bacterias"], "metodo.quimica": ["objeto.plantas", "sub.medicinais"],
           "metodo.dados": ["objeto.humanos", "sub.cardio"], "metodo.epidemio": ["objeto.humanos", "sub.infeccoes"],
           "metodo.clinica": ["objeto.humanos", "sub.boca"], "metodo.campo": ["objeto.fauna", "sub.ecossistemas"]}


def aderentes(ids: list[str], opcao: str) -> set[str]:
    if not ids:
        return set()
    return {r["id"] for r in psql(f"""
      SELECT a.researcher_id::text AS id FROM work_authorships a JOIN quiz_opcao_work q ON q.work_id = a.work_id AND q.opcao_id = {_lit(opcao)}
       WHERE a.researcher_id IN ({','.join(_lit(i) + '::uuid' for i in ids)}) GROUP BY 1 HAVING count(DISTINCT a.work_id) >= 2;""")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:3000")
    a = p.parse_args(argv)
    arv = carregar()
    linhas, gb, gl, cheios, n = [], [], [], 0, 0
    with httpx.Client(timeout=120) as cli:
        for metodo, tecs in arv["perguntas"]["tecnica"]["opcoes_por"].items():
            base = [metodo] + CAMINHO[metodo]
            for t in tecs:
                res = {k: cli.post(f"{a.url}/api/quiz/resultado", json={"instituicao_id": None, "respostas": r}).json()
                       for k, r in (("sem", base), ("com", [metodo, t["id"]] + CAMINHO[metodo]))}
                ad = aderentes(list({x["id"] for k in res for x in res[k]["lista"]}), t["id"])
                f = lambda xs: (sum(x["id"] in ad for x in xs) / len(xs)) if xs else 0.0
                bs, bc, ls, lc = f(res["sem"]["banner"]), f(res["com"]["banner"]), f(res["sem"]["lista"]), f(res["com"]["lista"])
                gb.append(bc - bs); gl.append(lc - ls); n += 1; cheios += len(res["com"]["banner"]) == 5
                linhas.append(f"| {t['rotulo']} ({metodo.removeprefix('metodo.')}) | {bs:.0%} → **{bc:.0%}** | {ls:.0%} → **{lc:.0%}** | {len(res['com']['banner'])} |")
                print(linhas[-1])
    resumo = f"{n} técnicas. Ganho médio de aderência: banner {statistics.mean(gb):+.0%}, lista de 15 {statistics.mean(gl):+.0%}. Banner com 5 pessoas em {cheios} de {n}."
    (DIR_RELATORIOS / "quiz_tecnicas_avaliacao.md").write_text("\n".join(["# Quiz: efeito da pergunta de técnica (D-053)", "", resumo, "",
        "| técnica | aderência no banner (sem → com) | na lista de 15 | banner |", "|---|---|---|---|", *linhas, ""]), encoding="utf-8")
    print("\n" + resumo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
