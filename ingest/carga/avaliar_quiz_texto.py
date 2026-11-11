"""Avaliação da descrição livre do quiz (D-040): o texto melhora a precisão do match?

Para cada caso (respostas de nicho amplas + uma descrição específica + termos que indicam o assunto descrito), chama
POST /api/quiz/texto e POST /api/quiz/resultado com e sem o código, e mede nos 15 da lista e nos 5 do banner:
  - aderência: fração de pessoas com pelo menos 2 publicações cujo título traz algum termo do assunto descrito
    (todas as publicações da pessoa na base, não só os exemplos, que já são escolhidos pelo texto);
  - latência e quantos nomes do banner mudaram.

Uso (app local no ar): python -m ingest.carga.avaliar_quiz_texto [--url http://localhost:3000]
Relatório: ingest/relatorios/quiz_texto.md
"""
from __future__ import annotations

import argparse
import statistics
import sys

import httpx

from .avaliar_quiz import norm
from .validar_arvore_quiz import DIR_RELATORIOS, _lit, psql

# (nome, respostas de nicho, descrição livre, termos do assunto descrito, sem acento e em minúsculas)
CASOS: list[tuple[str, list[str], str, list[str]]] = [
    ("Vírus → arboviroses", ["metodo.bioinfo", "objeto.micro", "sub.virus"],
     "vírus transmitidos por mosquitos, como dengue, zika e chikungunya", ["dengue", "zika", "chikungunya", "arbovir", "aedes", "flavivir"]),
    ("Bactérias → resistência hospitalar", ["metodo.bancada", "objeto.micro", "sub.bacterias"],
     "resistência a antibióticos em bactérias de ambiente hospitalar", ["resist", "carbapenem", "klebsiella", "acinetobacter", "mrsa", "esbl", "multidrug"]),
    ("Plantas medicinais → anti-inflamatório", ["metodo.bancada", "objeto.plantas", "sub.medicinais"],
     "atividade anti-inflamatória e analgésica de extratos de plantas", ["inflamat", "analges", "antinocicep", "nocicep", "edema"]),
    ("Infecções → tuberculose", ["metodo.epidemio", "objeto.humanos", "sub.infeccoes"],
     "tuberculose em populações vulneráveis e adesão ao tratamento", ["tubercul", "mycobacter"]),
    ("Mente → depressão em idosos", ["metodo.dados", "objeto.humanos", "sub.mente"],
     "depressão e declínio cognitivo em idosos", ["depress", "cogniti", "elderly", "idoso", "older adult", "aging", "envelhec", "dementia"]),
    ("Boca e dentes → cárie infantil", ["metodo.clinica", "objeto.humanos", "sub.boca"],
     "cárie dentária em crianças e prevenção com flúor", ["carie", "caries", "fluor", "child", "crianc", "pediatric", "preschool"]),
    ("Caprinos → nutrição com palma", ["metodo.bancada", "objeto.producao", "sub.caprinos"],
     "nutrição de cabras e ovelhas com palma forrageira e resíduos agroindustriais", ["cactus", "palma", "opuntia", "nopalea", "diet", "feed", "dieta", "suplement"]),
    ("Fungos → candidíase", ["metodo.bancada", "objeto.micro", "sub.fungos"],
     "Candida e resistência a antifúngicos", ["candida", "antifung", "fluconazol", "azole"]),
]


def chamar(cli: httpx.Client, url: str, respostas: list[str], codigo: str | None) -> dict:
    r = cli.post(f"{url}/api/quiz/resultado", json={"instituicao_id": None, "respostas": respostas, "texto": codigo})
    r.raise_for_status()
    return dict(r.json())


def aderentes(ids: list[str], termos: list[str]) -> set[str]:
    """pessoas com >= 2 publicações cujo título traz algum termo"""
    if not ids:
        return set()
    padrao = "|".join(termos)
    linhas = psql(f"""
      SELECT a.researcher_id::text AS id FROM work_authorships a JOIN works w ON w.id = a.work_id
       WHERE a.researcher_id IN ({','.join(_lit(i) + '::uuid' for i in ids)})
         AND lower(translate(w.title, 'áàâãäéêèíìóôõòúùüçÁÀÂÃÉÊÍÓÔÕÚÇ', 'aaaaaeeeiiooooouuucAAAAEEIOOOUC')) ~ {_lit(padrao)}
       GROUP BY 1 HAVING count(DISTINCT a.work_id) >= 2;""")
    return {r["id"] for r in linhas}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:3000")
    a = p.parse_args(argv)
    linhas, ganhos, lat = [], [], {"sem": [], "com": []}
    with httpx.Client(timeout=60) as cli:
        for nome, resp, texto, termos in CASOS:
            termos = [norm(t) for t in termos]
            cod = cli.post(f"{a.url}/api/quiz/texto", json={"texto": texto}).json().get("codigo")
            sem, com = chamar(cli, a.url, resp, None), chamar(cli, a.url, resp, cod)
            lat["sem"].append(sem["ms"]); lat["com"].append(com["ms"])
            ad = aderentes(list({x["id"] for r in (sem, com) for x in r["lista"]}), termos)
            f = lambda xs: (sum(x["id"] in ad for x in xs) / len(xs)) if xs else 0.0
            l_sem, l_com, b_sem, b_com = f(sem["lista"]), f(com["lista"]), f(sem["banner"]), f(com["banner"])
            trocas = len({x["id"] for x in com["banner"]} - {x["id"] for x in sem["banner"]})
            ganhos.append(l_com - l_sem)
            linhas.append(f"| {nome} | {b_sem:.0%} → **{b_com:.0%}** | {l_sem:.0%} → **{l_com:.0%}** | {trocas} | {sem['ms']} → {com['ms']} |")
            print(linhas[-1])
    rel = DIR_RELATORIOS / "quiz_texto.md"
    rel.write_text("\n".join([
        "# Quiz: efeito da descrição livre (D-040)", "",
        "Aderência = fração de pessoas com ≥ 2 publicações cujo título traz algum termo do assunto descrito.", "",
        "| caso | aderência no banner (sem → com texto) | aderência na lista de 15 | nomes trocados no banner | ms (sem → com) |",
        "|---|---|---|---|---|", *linhas, "",
        f"Ganho médio de aderência na lista: {statistics.mean(ganhos):+.0%}. "
        f"Latência mediana: {statistics.median(lat['sem'])} ms sem texto, {statistics.median(lat['com'])} ms com texto.", ""]))
    print(f"\nganho médio na lista {statistics.mean(ganhos):+.0%}; relatório em {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
