"""Avaliação da busca por tema: consultas em português × publicações (majoritariamente em inglês).

Para cada consulta, um resultado conta como relevante se o título ou as palavras-chave contêm algum dos termos
esperados (em português ou inglês). Mede a precisão nos k primeiros resultados (k = 8, o que a API devolve) e a fração de publicações em inglês nos modos texto, vetor e híbrido via /api/tema do app local.
É uma medida aproximada e conservadora (sinônimos fora da lista contam como erro), útil para comparar modos e versões.

Uso:
    python -m ingest.carga.avaliar_busca_tema [--url http://127.0.0.1:3000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from urllib.parse import quote

import httpx

from .comum import DIR_PROCESSADOS, DIR_RELATORIOS, ler_csv

CONSULTAS: list[tuple[str, list[str]]] = [
    ("dengue e outras arboviroses", ["dengue", "arbovir", "zika", "chikungunya", "aedes"]),
    ("resistência bacteriana a antibióticos", ["resist", "antimicrob", "antibiotic", "multidrug", "carbapenem", "esbl"]),
    ("câncer de mama", ["breast cancer", "breast neoplasm", "cancer de mama", "mama", "breast"]),
    ("doença de Chagas", ["chagas", "trypanosoma cruzi"]),
    ("leishmaniose visceral", ["leishmani"]),
    ("saúde bucal e cárie dentária", ["caries", "oral health", "dental", "carie", "saude bucal"]),
    ("diabetes tipo 2", ["diabet"]),
    ("tuberculose", ["tubercul", "mycobacterium"]),
    ("sífilis congênita", ["syphilis", "sifilis"]),
    ("hanseníase", ["leprosy", "hanseni", "mycobacterium leprae"]),
    ("esquistossomose", ["schistosom", "esquistossom"]),
    ("microcefalia associada ao zika", ["microcephal", "zika", "microcefal"]),
    ("fruticultura irrigada no semiárido", ["fruit", "irrigat", "semiarid", "semi-arid", "frut", "mango", "grape", "banana"]),
    ("melhoramento genético de caprinos e ovinos", ["goat", "sheep", "caprin", "ovin", "small ruminant"]),
    ("plantas medicinais da caatinga", ["caatinga", "medicinal plant", "plantas medicinais", "ethnobotan"]),
    ("óleos essenciais com atividade antimicrobiana", ["essential oil", "oleo essencial", "oleos essenciais"]),
    ("qualidade do solo e matéria orgânica", ["soil", "solo", "organic matter", "organic carbon"]),
    ("saúde mental de estudantes universitários", ["mental health", "depress", "anxiety", "student", "saude mental", "burnout"]),
    ("aleitamento materno", ["breastfeed", "aleitamento", "breast milk", "lactation"]),
    ("violência contra a mulher", ["violence", "violencia", "intimate partner"]),
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def avaliar(url: str) -> dict:
    kws: dict[str, str] = {}
    caminho = DIR_PROCESSADOS / "work_keywords.csv"
    if caminho.exists():
        for k in ler_csv(caminho):
            kws[k["work_id"]] = kws.get(k["work_id"], "") + " " + k["keyword"]
    ids_ingles = {w["id"] for w in ler_csv(DIR_PROCESSADOS / "works.csv") if w["language"] == "en"}
    resultado: dict[str, dict] = {}
    with httpx.Client(timeout=30) as cli:
        for consulta, termos in CONSULTAS:
            linha = {}
            for modo in ("texto", "vetor", "hibrido"):
                t0 = time.monotonic()
                r = cli.get(f"{url}/api/tema?q={quote(consulta)}&modo={modo}").json()
                ms = (time.monotonic() - t0) * 1000
                pubs = r.get("publicacoes", [])[:10]
                rel = sum(1 for p in pubs if any(_norm(t) in _norm(p["titulo"] + " " + kws.get(p["id"], "")) for t in termos))
                ingles = sum(1 for p in pubs if p["id"] in ids_ingles)
                linha[modo] = {"p@10": rel / len(pubs) if pubs else 0.0, "n": len(pubs), "ingles": ingles, "ms": round(ms), "vetorial": r.get("vetorial")}
            resultado[consulta] = linha
    medias = {m: round(sum(v[m]["p@10"] for v in resultado.values()) / len(resultado), 3) for m in ("texto", "vetor", "hibrido")}
    zeros = {m: sum(1 for v in resultado.values() if v[m]["n"] == 0) for m in ("texto", "vetor", "hibrido")}
    latencia = {m: round(sum(v[m]["ms"] for v in resultado.values()) / len(resultado)) for m in ("texto", "vetor", "hibrido")}
    frac_ingles = {m: round(sum(v[m]["ingles"] for v in resultado.values()) / max(1, sum(v[m]["n"] for v in resultado.values())), 3) for m in ("texto", "vetor", "hibrido")}
    return {"precisao_media_topk": medias, "fracao_em_ingles_topk": frac_ingles, "consultas_sem_resultado": zeros, "latencia_media_ms": latencia, "por_consulta": resultado}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://127.0.0.1:3000")
    a = p.parse_args(argv)
    s = avaliar(a.url)
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    (DIR_RELATORIOS / "avaliacao_busca_tema.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))
    print(f"{'consulta':52s} {'texto':>6s} {'vetor':>6s} {'híbr.':>6s}")
    for c, v in s["por_consulta"].items():
        print(f"{c[:52]:52s} {v['texto']['p@10']:6.1f} {v['vetor']['p@10']:6.1f} {v['hibrido']['p@10']:6.1f}")
    print(json.dumps({k: s[k] for k in ("precisao_media_topk", "fracao_em_ingles_topk", "consultas_sem_resultado", "latencia_media_ms")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
