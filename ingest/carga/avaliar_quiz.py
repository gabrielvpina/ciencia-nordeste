"""Avaliação do match do quiz (etapa 13): 15 caminhos fictícios × instituição contra POST /api/quiz/resultado do app local.

Verifica, para cada caminho:
  - exclusão: nenhum resultado da instituição informada nem das ligadas a ela (institution_relations parent/child e
    v_instituicao_vinculo);
  - diversidade: no banner, instituições diferentes (até 2 da mesma só se faltar gente);
  - coerência temática: fração dos pesquisadores do banner cuja publicação de exemplo traz algum termo esperado (PT/EN);
  - índice de compatibilidade do 1º e do último do banner (calibração: não pode ficar 99 para todo mundo);
  - latência no servidor;
  - separação: trocar só as respostas de perfil (habitat, estilo, vínculo) não muda nomes, ordem nem índices.

  python -m ingest.carga.avaliar_quiz [--url http://localhost:3000]

Relatório: ingest/relatorios/avaliacao_quiz.md (+ .json). Usa o filtro Qualis do jeito que o site abre (ligado).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import unicodedata
from typing import Any

import httpx

from .validar_arvore_quiz import DIR_RELATORIOS, RAIZ, _lit, psql

PERFIL_A = ["habitat.computador", "estilo.modelo", "vinculo.paixao"]
PERFIL_B = ["habitat.campo", "estilo.gente", "vinculo.ferramenta"]

# (nome, instituição (sigla) ou None, respostas de nicho, termos esperados nos títulos de exemplo)
CAMINHOS: list[tuple[str, str | None, list[str], list[str]]] = [
    ("Bioinformática × vírus × caatinga", "UESC", ["metodo.bioinfo", "objeto.micro", "sub.virus", "escala.moleculas", "ambiente.caatinga"],
     ["virus", "viral", "genom", "sequenc", "sars", "arbovir", "zika", "dengue"]),
    ("Genética × caprinos e ovinos", "UFPI", ["metodo.genetica", "objeto.producao", "sub.caprinos", "foco.melhoramento"],
     ["goat", "sheep", "caprin", "ovin", "lamb", "cordeir", "santa ines", "santa inês"]),
    ("Campo × abelhas", "UFRB", ["metodo.campo", "objeto.insetos", "sub.abelhas", "ambiente.caatinga"],
     ["bee", "abelha", "honey", "mel", "pollin", "polin", "propolis", "própolis", "melipon", "apis"]),
    ("Epidemiologia × infecções", "UFC", ["metodo.epidemio", "objeto.humanos", "sub.infeccoes", "foco.prevencao"],
     ["hiv", "tubercul", "lepros", "hansen", "syphil", "sífilis", "covid", "sars", "infect", "infecç", "dengue", "leishman"]),
    ("Química × plantas medicinais", "UFPB", ["metodo.quimica", "objeto.plantas", "sub.medicinais", "foco.produtos"],
     ["extract", "extrato", "essential oil", "óleo", "phyto", "fito", "medicinal", "compound", "compost", "chemical"]),
    ("Clínica × boca e dentes", "UFPE", ["metodo.clinica", "objeto.humanos", "sub.boca", "foco.diagnostico"],
     ["dental", "oral", "tooth", "teeth", "dente", "bucal", "periodon", "caries", "cárie", "endodon", "orthodon", "implant"]),
    ("Dados × cérebro e mente", "UFRN", ["metodo.dados", "objeto.humanos", "sub.mente"],
     ["brain", "cérebro", "neuro", "depress", "autism", "autis", "stroke", "eeg", "cogniti", "dementia", "mental", "parkinson", "epilep"]),
    ("Bancada × fungos", "UFBA", ["metodo.bancada", "objeto.micro", "sub.fungos", "foco.diagnostico"],
     ["fung", "candida", "antifung", "yeast", "levedura", "cryptococ", "aspergil", "sporothri"]),
    ("Campo × anfíbios e répteis", None, ["metodo.campo", "objeto.fauna", "sub.herpeto", "foco.diversidade", "ambiente.mata"],
     ["frog", "anura", "anuro", "lizard", "lagart", "snake", "serpent", "reptil", "réptil", "amphib", "anfíb", "tropidurus", "turtle", "toad"]),
    ("Bancada × laticínios e fermentados", "UFPB", ["metodo.bancada", "objeto.alimentos", "sub.laticinios", "foco.produtos"],
     ["cheese", "queijo", "milk", "leite", "ferment", "probio", "yogurt", "iogurte", "dairy", "kefir", "lactic"]),
    ("Dados × clima e secas", "UFCG", ["metodo.dados", "objeto.ambiente", "sub.clima", "escala.paisagens", "ambiente.caatinga"],
     ["drought", "seca", "climat", "clima", "rain", "chuva", "precipit", "remote sensing", "sensoriamento", "evapotrans", "ndvi", "land"]),
    ("Epidemiologia × mosquitos e vetores", "UFPE", ["metodo.epidemio", "objeto.insetos", "sub.vetores", "foco.prevencao", "ambiente.cidades"],
     ["aedes", "dengue", "mosquito", "vector", "vetor", "arbovir", "zika", "chikungunya", "sandfl", "flebot", "triatom", "chagas", "leishman"]),
    ("Genética × frutíferas e hortaliças", "UFRPE", ["metodo.genetica", "objeto.plantas", "sub.frutiferas", "foco.melhoramento"],
     ["genetic", "genét", "breeding", "melhoramento", "cultivar", "genotyp", "genótip", "fruit", "melon", "melão", "mango", "pepper", "tomato", "cashew", "banana", "passion"]),
    ("Clínica × movimento e reabilitação", "UFRN", ["metodo.clinica", "objeto.humanos", "sub.movimento", "impacto.saude"],
     ["rehabil", "reabil", "exercis", "exercí", "pain", "dor", "physio", "fisio", "balance", "equilíbr", "stroke", "gait", "muscul", "training"]),
    ("Bioinformática × bactérias", None, ["metodo.bioinfo", "objeto.micro", "sub.bacterias", "foco.diagnostico"],
     ["genom", "sequenc", "bacteri", "resist", "strain", "klebsiella", "staphyloc", "escherichia", "plasmid", "phylogen"]),
]


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def instituicoes(siglas: set[str]) -> dict[str, dict[str, Any]]:
    """sigla -> {id, excluidas: set de ids} (a própria + ligadas por relação ou vínculo)."""
    if not siglas:
        return {}
    linhas = psql(f"""
      WITH i AS (SELECT DISTINCT ON (acronym) id, acronym FROM institutions WHERE acronym IN ({','.join(map(_lit, siglas))})
                  ORDER BY acronym, (SELECT works FROM mv_instituicao_stats s WHERE s.institution_id = institutions.id) DESC NULLS LAST)
      SELECT i.acronym, i.id::text AS id, (SELECT string_agg(x::text, ',') FROM (
          SELECT i.id AS x
          UNION SELECT related_institution_id FROM institution_relations WHERE institution_id = i.id AND relation IN ('parent','child') AND related_institution_id IS NOT NULL
          UNION SELECT institution_id FROM institution_relations WHERE related_institution_id = i.id AND relation IN ('parent','child')
          UNION SELECT institution_id FROM v_instituicao_vinculo WHERE parent_id = i.id
          UNION SELECT parent_id FROM v_instituicao_vinculo WHERE institution_id = i.id) e) AS excl
        FROM i;""")
    return {r["acronym"]: {"id": r["id"], "excl": set((r["excl"] or "").split(","))} for r in linhas}


def chamar(cli: httpx.Client, url: str, inst: str | None, respostas: list[str]) -> dict[str, Any]:
    r = cli.post(f"{url}/api/quiz/resultado", json={"instituicao_id": inst, "respostas": respostas})
    r.raise_for_status()
    return dict(r.json())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:3000")
    a = p.parse_args(argv)
    insts = instituicoes({s for _, s, _, _ in CAMINHOS if s})
    resultados = []
    with httpx.Client(timeout=60) as cli:
        chamar(cli, a.url, None, CAMINHOS[0][2])                     # aquece o serviço de embedding
        for nome, sigla, nicho, termos in CAMINHOS:
            inst = insts.get(sigla) if sigla else None
            r = chamar(cli, a.url, inst["id"] if inst else None, PERFIL_A + nicho)
            r_b = chamar(cli, a.url, inst["id"] if inst else None, PERFIL_B + nicho)
            banner = r["banner"]
            excl = inst["excl"] if inst else set()
            violacoes = [x["nome"] for x in r["lista"] if x["instituicao_id"] in excl]
            por_inst: dict[str, int] = {}
            for x in banner:
                por_inst[x["instituicao_id"] or x["id"]] = por_inst.get(x["instituicao_id"] or x["id"], 0) + 1
            coerentes = [x for x in banner if any(any(t in norm(e["titulo"]) for t in map(norm, termos)) for e in x["exemplos"])]
            assinatura = lambda res: [(x["id"], x["indice"]) for x in res["lista"]]  # noqa: E731
            resultados.append({
                "caminho": nome, "instituicao": sigla or "sem vínculo", "n_banner": len(banner), "candidatos": r["candidatos"],
                "exclusao_ok": not violacoes, "violacoes": violacoes, "max_por_inst": max(por_inst.values(), default=0),
                "coerencia": len(coerentes) / len(banner) if banner else None,
                "indice_1": banner[0]["indice"] if banner else None, "indice_ultimo": banner[-1]["indice"] if banner else None,
                "ms": r.get("ms"), "tempos": r.get("tempos"), "vetorial": r["vetorial"],
                "separacao_ok": assinatura(r) == assinatura(r_b),
                "banner": [f"{x['indice']} {x['nome']} ({x['sigla'] or '—'}, {x['uf'] or '—'})" for x in banner],
            })
    ok = all(x["exclusao_ok"] and x["max_por_inst"] <= 2 and x["separacao_ok"] for x in resultados)
    coer = [x["coerencia"] for x in resultados if x["coerencia"] is not None]
    lat = [x["ms"] for x in resultados if x["ms"] is not None]
    i1 = [x["indice_1"] for x in resultados if x["indice_1"] is not None]
    iu = [x["indice_ultimo"] for x in resultados if x["indice_ultimo"] is not None]
    L = ["# Quiz — avaliação do match", "",
         f"{len(resultados)} caminhos fictícios contra `/api/quiz/resultado` ({a.url}); filtro Qualis ligado (padrão do site).", "",
         "| Item | Resultado |", "|---|---|",
         f"| Exclusão da instituição e das ligadas | {'ok em todos' if all(x['exclusao_ok'] for x in resultados) else 'FALHOU'} |",
         f"| Diversidade (máx. por instituição no banner) | {max((x['max_por_inst'] for x in resultados), default=0)} |",
         f"| Separação perfil × match (mesmos nomes, ordem e índices) | {'ok em todos' if all(x['separacao_ok'] for x in resultados) else 'FALHOU'} |",
         f"| Coerência temática (exemplo com termo esperado) | média {statistics.mean(coer):.0%}, mínima {min(coer):.0%} |" if coer else "| Coerência | — |",
         f"| Índice do 1º do banner | mediana {statistics.median(i1)}, de {min(i1)} a {max(i1)} |" if i1 else "| Índice | — |",
         f"| Índice do último do banner | mediana {statistics.median(iu)}, de {min(iu)} a {max(iu)} |" if iu else "",
         f"| Pesquisadores no banner | {', '.join(str(x['n_banner']) for x in resultados)} |",
         f"| Latência no servidor | mediana {statistics.median(lat):.0f} ms, máxima {max(lat):.0f} ms |" if lat else "",
         f"| Resultado | **{'OK' if ok else 'há falhas'}** |", "",
         "| caminho | instituição | candidatos | coerência | índices (1º–último) | ms | banner |", "|---|---|---|---|---|---|---|"]
    for x in resultados:
        c = "—" if x["coerencia"] is None else f"{x['coerencia']:.0%}"
        L.append(f"| {x['caminho']} | {x['instituicao']} | {x['candidatos']} | {c} | {x['indice_1']}–{x['indice_ultimo']} | {x['ms']} | "
                 + "<br>".join(x["banner"]) + " |")
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    arq = DIR_RELATORIOS / "avaliacao_quiz.md"
    arq.write_text("\n".join(x for x in L if x is not None) + "\n", encoding="utf-8")
    (DIR_RELATORIOS / "avaliacao_quiz.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"gravado {arq.relative_to(RAIZ)}: {'OK' if ok else 'há falhas'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
