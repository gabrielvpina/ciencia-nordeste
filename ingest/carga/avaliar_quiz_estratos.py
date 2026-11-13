"""Avaliação da pergunta "Onde, exatamente?" (estratos de ambiente, D-054).

Para cada estrato, um caminho típico do grupo, com o ambiente e sem/com o estrato; aderência = fração do banner (5) e da lista (15)
com >= 2 publicações que casam o estrato (quiz_opcao_work).

  python -m ingest.carga.avaliar_quiz_estratos [--url http://localhost:3000]   -> ingest/relatorios/quiz_estratos_avaliacao.md
"""
from __future__ import annotations

import argparse
import statistics
import sys

import httpx

from .avaliar_quiz_tecnicas import aderentes
from .validar_arvore_quiz import DIR_RELATORIOS, carregar

CAMINHO = {"ambiente.caatinga": ["metodo.campo", "objeto.plantas", "sub.nativas"], "ambiente.mata": ["metodo.campo", "objeto.fauna", "sub.ecossistemas"],
           "ambiente.mar": ["metodo.campo", "objeto.fauna", "sub.marinha"], "ambiente.aguas": ["metodo.campo", "objeto.ambiente", "sub.agua"],
           "ambiente.lavouras": ["metodo.campo", "objeto.plantas", "sub.graos"], "ambiente.cidades": ["metodo.epidemio", "objeto.humanos", "sub.infeccoes"],
           "ambiente.comunidades": ["metodo.epidemio", "objeto.humanos", "sub.materno"]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:3000")
    a = p.parse_args(argv)
    arv = carregar()
    linhas, gb, gl, cheios, n = [], [], [], 0, 0
    with httpx.Client(timeout=120) as cli:
        for grupo, ests in arv["perguntas"]["estrato"]["opcoes_por"].items():
            base = CAMINHO[grupo] + [grupo]
            for e in ests:
                res = {k: cli.post(f"{a.url}/api/quiz/resultado", json={"instituicao_id": None, "respostas": r}).json()
                       for k, r in (("sem", base), ("com", base + [e["id"]]))}
                ad = aderentes(list({x["id"] for k in res for x in res[k]["lista"]}), e["id"])
                f = lambda xs: (sum(x["id"] in ad for x in xs) / len(xs)) if xs else 0.0
                bs, bc, ls, lc = f(res["sem"]["banner"]), f(res["com"]["banner"]), f(res["sem"]["lista"]), f(res["com"]["lista"])
                gb.append(bc - bs); gl.append(lc - ls); n += 1; cheios += len(res["com"]["banner"]) == 5
                linhas.append(f"| {e['rotulo']} ({grupo.removeprefix('ambiente.')}) | {bs:.0%} → **{bc:.0%}** | {ls:.0%} → **{lc:.0%}** | {len(res['com']['banner'])} |")
                print(linhas[-1])
    resumo = f"{n} estratos. Ganho médio de aderência: banner {statistics.mean(gb):+.0%}, lista de 15 {statistics.mean(gl):+.0%}. Banner com 5 pessoas em {cheios} de {n}."
    (DIR_RELATORIOS / "quiz_estratos_avaliacao.md").write_text("\n".join(["# Quiz: efeito da pergunta de estrato (D-054)", "", resumo, "",
        "| estrato | aderência no banner (sem → com) | na lista de 15 | banner |", "|---|---|---|---|", *linhas, ""]), encoding="utf-8")
    print("\n" + resumo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
