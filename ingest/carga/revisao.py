"""Revisão de identidade: decisões, regra de aceite em lote, planilha de revisão e consolidação.

As decisões ficam em ingest/dados/revisao/decisoes.csv (só acréscimo; a decisão mais recente de cada par vale).
Nada é apagado: aceitar um par docente CAPES × autor OpenAlex cria um ALIAS (o UUID do docente passa a apontar
para o UUID do autor OpenAlex); rejeitar depois desfaz o alias na próxima consolidação.

Comandos:
    python -m ingest.carga.revisao aplicar-regra --decidido-por "Nome (responsável)"
        Regra aprovada pelo responsável em 2026-11-09 (D-018): docente com UM único candidato, nome idêntico
        (score de nome 1,0) e instituição em comum; o autor não pode ser candidato único de outro docente.
    python -m ingest.carga.revisao exportar
        Gera ingest/dados/revisao/pendentes_pesquisadores.csv e pendentes_instituicoes.csv (coluna "decisao" em branco).
    python -m ingest.carga.revisao importar ARQUIVO.csv --decidido-por "Nome"
        Lê as linhas com decisao = aceito | rejeitado e grava em decisoes.csv.
    python -m ingest.carga.revisao consolidar
        Gera researchers.csv, researcher_identifiers.csv, researcher_aliases.csv, program_faculty_final.csv e
        review_queue.csv em ingest/dados/processados/ (é o que ingest/sql/carga.sql carrega).
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .comum import AGORA, DIR_DADOS, DIR_PROCESSADOS, DIR_RELATORIOS, escrever_csv, ler_csv

log = logging.getLogger("ingest.revisao")

DIR_REVISAO = DIR_DADOS / "revisao"
ARQ_DECISOES = DIR_REVISAO / "decisoes.csv"
CAMPOS_DECISAO = ["entity", "candidate_a", "candidate_b", "decision", "decided_by", "decided_at", "rule", "note"]
FILAS = {
    "researcher": ["researcher_review_queue.csv"],
    "institution": ["institution_review_queue.csv", "institution_review_queue_capes.csv"],
}
REGRA_095 = "regra_0.95_unico: candidato único + nome idêntico + instituição em comum (aprovada pelo responsável em 2026-11-09, D-018)"


# ------------------------------------------------------------------ decisões


def ler_decisoes() -> dict[tuple[str, str, str], dict[str, str]]:
    """Última decisão por (entity, candidate_a, candidate_b)."""
    if not ARQ_DECISOES.exists():
        return {}
    ultimas: dict[tuple[str, str, str], dict[str, str]] = {}
    for d in ler_csv(ARQ_DECISOES):
        ultimas[(d["entity"], d["candidate_a"], d["candidate_b"])] = d
    return ultimas


def gravar_decisoes(novas: list[dict[str, Any]]) -> int:
    if not novas:
        return 0
    DIR_REVISAO.mkdir(parents=True, exist_ok=True)
    novo = not ARQ_DECISOES.exists()
    with ARQ_DECISOES.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_DECISAO, extrasaction="ignore")
        if novo:
            w.writeheader()
        for d in novas:
            w.writerow(d)
    return len(novas)


def ler_fila(entidade: str) -> list[dict[str, str]]:
    linhas: list[dict[str, str]] = []
    for nome in FILAS[entidade]:
        caminho = DIR_PROCESSADOS / nome
        if caminho.exists():
            linhas.extend(ler_csv(caminho))
    return linhas


# ------------------------------------------------------------------ regra em lote


def aplicar_regra(decidido_por: str) -> dict[str, Any]:
    fila = ler_fila("researcher")
    ja = ler_decisoes()
    por_docente: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for lin in fila:
        ev = json.loads(lin["evidence"])
        por_docente[lin["candidate_a"]].append({**lin, "_ev": ev})
    # autor que é candidato único de mais de um docente: ambíguo, fica para revisão manual
    unico_de: collections.Counter[str] = collections.Counter(
        cands[0]["candidate_b"] for cands in por_docente.values() if len(cands) == 1
    )
    novas: list[dict[str, Any]] = []
    motivos: collections.Counter[str] = collections.Counter()
    for docente, cands in por_docente.items():
        if len(cands) != 1:
            motivos["mais_de_um_candidato"] += 1
            continue
        c = cands[0]
        ev = c["_ev"]
        if ev.get("candidatos") != 1:
            motivos["mais_de_um_candidato"] += 1
            continue
        if ev.get("score_nome") != 1.0:
            motivos["nome_nao_identico"] += 1
            continue
        if not ev.get("instituicoes_em_comum"):
            motivos["sem_instituicao_em_comum"] += 1
            continue
        if unico_de[c["candidate_b"]] > 1:
            motivos["autor_disputado_por_varios_docentes"] += 1
            continue
        if ("researcher", docente, c["candidate_b"]) in ja:
            motivos["ja_decidido"] += 1
            continue
        novas.append(
            {"entity": "researcher", "candidate_a": docente, "candidate_b": c["candidate_b"], "decision": "aceito",
             "decided_by": decidido_por, "decided_at": AGORA, "rule": REGRA_095, "note": ""}
        )
        motivos["aceito_pela_regra"] += 1
    n = gravar_decisoes(novas)
    log.info("Regra aplicada: %d aceites; %s", n, dict(motivos))
    return {"aceitos": n, "motivos": dict(motivos)}


# ------------------------------------------------------------------ planilha de revisão


def exportar() -> dict[str, int]:
    ja = ler_decisoes()
    DIR_REVISAO.mkdir(parents=True, exist_ok=True)
    totais = {}
    for entidade in FILAS:
        linhas = []
        for lin in ler_fila(entidade):
            if (entidade, lin["candidate_a"], lin["candidate_b"]) in ja:
                continue
            ev = json.loads(lin["evidence"])
            base = {"candidate_a": lin["candidate_a"], "candidate_b": lin["candidate_b"], "score": lin["score"], "decisao": "", "observacao": ""}
            if entidade == "researcher":
                base.update({
                    "nome_capes": ev.get("capes_nome"), "nome_openalex": ev.get("openalex_nome"), "instituicoes_em_comum": "; ".join(ev.get("instituicoes_em_comum") or []),
                    "works_no_periodo": ev.get("works_no_periodo"), "orcid": ev.get("orcid") or "", "candidatos_do_docente": ev.get("candidatos"),
                    "link_openalex": f"https://openalex.org/{ev.get('openalex_author')}",
                })
            else:
                base.update({"evidencia": json.dumps(ev, ensure_ascii=False)})
            linhas.append(base)
        linhas.sort(key=lambda x: (-float(x["score"] or 0), x["candidate_a"]))
        campos = list(linhas[0].keys()) if linhas else ["candidate_a", "candidate_b", "score", "decisao", "observacao"]
        nome = "pendentes_pesquisadores.csv" if entidade == "researcher" else "pendentes_instituicoes.csv"
        escrever_csv(DIR_REVISAO / nome, linhas, campos)
        totais[nome] = len(linhas)
    return totais


def importar(caminho: Path, decidido_por: str) -> int:
    entidade = "institution" if "institu" in caminho.name else "researcher"
    novas = []
    for lin in ler_csv(caminho):
        dec = (lin.get("decisao") or "").strip().lower()
        if dec in ("aceito", "rejeitado"):
            novas.append(
                {"entity": entidade, "candidate_a": lin["candidate_a"], "candidate_b": lin["candidate_b"], "decision": dec,
                 "decided_by": decidido_por, "decided_at": AGORA, "rule": "revisao_manual", "note": lin.get("observacao", "")}
            )
    return gravar_decisoes(novas)


# ------------------------------------------------------------------ consolidação


def consolidar() -> dict[str, Any]:
    decisoes = ler_decisoes()
    # aliases de pesquisador: docente (CAPES) -> autor OpenAlex, para pares aceitos
    alias: dict[str, tuple[str, str]] = {}
    for (ent, a, b), d in decisoes.items():
        if ent != "researcher" or d["decision"] != "aceito":
            continue
        ua, ub = a.split(":", 1)[1], b.split(":", 1)[1]
        if ua in alias and alias[ua][0] != ub:
            log.warning("Docente %s aceito para dois autores (%s, %s): mantido o primeiro", ua, alias[ua][0], ub)
            continue
        alias[ua] = (ub, d["rule"] or "revisao_manual")
    canon = lambda u: alias[u][0] if u in alias else u  # noqa: E731

    capes = {r["id"]: r for r in ler_csv(DIR_PROCESSADOS / "researchers_capes.csv")}
    oa = {r["id"]: r for r in ler_csv(DIR_PROCESSADOS / "researchers_openalex.csv")}
    pesquisadores: dict[str, dict[str, Any]] = {}
    for u, r in oa.items():
        pesquisadores[u] = {
            "id": u, "display_name": r["display_name"], "normalized_name": r["normalized_name"], "main_institution_id": r["main_institution_id"],
            "orcid": r["orcid"], "capes_id_pessoa": "", "is_capes_faculty": False, "pq_category_latest": "", "sources": ["openalex"], "updated_at": AGORA,
        }
    for u, r in capes.items():
        c = canon(u)
        if c in pesquisadores:
            p = pesquisadores[c]
            p["capes_id_pessoa"] = r["capes_id_pessoa"]
            p["is_capes_faculty"] = True
            p["pq_category_latest"] = r["pq_category_latest"]
            p["sources"] = sorted(set(p["sources"]) | {"capes"})
            if not p["main_institution_id"] and r["institution_ids"]:
                p["main_institution_id"] = r["institution_ids"].split("|")[0]
        else:
            pesquisadores[u] = {
                "id": u, "display_name": r["display_name"], "normalized_name": r["normalized_name"],
                "main_institution_id": (r["institution_ids"].split("|")[0] if r["institution_ids"] else ""), "orcid": "",
                "capes_id_pessoa": r["capes_id_pessoa"], "is_capes_faculty": True, "pq_category_latest": r["pq_category_latest"],
                "sources": ["capes"], "updated_at": AGORA,
            }

    ident: dict[tuple[str, str, str], dict[str, Any]] = {}
    for arq in ("researcher_identifiers_openalex.csv", "researcher_identifiers_capes.csv"):
        for r in ler_csv(DIR_PROCESSADOS / arq):
            u = canon(r["researcher_id"])
            linha = dict(r, researcher_id=u)
            if u != r["researcher_id"]:
                # vínculo docente↔autor sem identificador comum: confiança < 1, registra a origem
                linha["confidence"] = 0.95 if alias[r["researcher_id"]][1] != "revisao_manual" else 0.99
                linha["source"] = f"{r['source']}+alias:{alias[r['researcher_id']][1][:40]}"
            ident[(u, linha["scheme"], linha["value"])] = linha

    faculty = []
    for r in ler_csv(DIR_PROCESSADOS / "program_faculty.csv"):
        r["researcher_id"] = canon(r["researcher_id"])
        faculty.append(r)

    fila_total = []
    for ent in FILAS:
        for lin in ler_fila(ent):
            dd = decisoes.get((ent, lin["candidate_a"], lin["candidate_b"]))
            fila_total.append({**lin, "status": dd["decision"] if dd else "pendente", "decided_by": dd["decided_by"] if dd else "", "decided_at": dd["decided_at"] if dd else ""})

    escrever_csv(DIR_PROCESSADOS / "researchers.csv", pesquisadores.values(),
                 ["id", "display_name", "normalized_name", "main_institution_id", "orcid", "capes_id_pessoa", "is_capes_faculty", "pq_category_latest", "sources", "updated_at"])
    escrever_csv(DIR_PROCESSADOS / "researcher_identifiers.csv", ident.values(), ["researcher_id", "scheme", "value", "source", "confidence", "verified_at"])
    escrever_csv(DIR_PROCESSADOS / "researcher_aliases.csv",
                 ({"alias_id": a, "researcher_id": c, "reason": r, "created_at": AGORA} for a, (c, r) in alias.items()),
                 ["alias_id", "researcher_id", "reason", "created_at"])
    escrever_csv(DIR_PROCESSADOS / "program_faculty_final.csv", faculty, list(faculty[0].keys()) if faculty else ["program_id"])
    escrever_csv(DIR_PROCESSADOS / "review_queue.csv", fila_total, ["entity", "candidate_a", "candidate_b", "score", "evidence", "status", "decided_by", "decided_at", "created_at"])

    status = collections.Counter((x["entity"], x["status"]) for x in fila_total)
    s = {
        "gerado_em": AGORA,
        "pesquisadores_total": len(pesquisadores),
        "so_openalex": sum(1 for p in pesquisadores.values() if p["sources"] == ["openalex"]),
        "so_capes": sum(1 for p in pesquisadores.values() if p["sources"] == ["capes"]),
        "capes_e_openalex": sum(1 for p in pesquisadores.values() if len(p["sources"]) == 2),
        "aliases": len(alias),
        "docentes_capes": len(capes),
        "fila": {f"{e}:{st}": n for (e, st), n in sorted(status.items())},
    }
    (DIR_RELATORIOS / "revisao_consolidacao.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))
    return s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("aplicar-regra")
    r.add_argument("--decidido-por", required=True)
    sub.add_parser("exportar")
    i = sub.add_parser("importar")
    i.add_argument("arquivo", type=Path)
    i.add_argument("--decidido-por", required=True)
    sub.add_parser("consolidar")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    if a.cmd == "aplicar-regra":
        out: Any = aplicar_regra(a.decidido_por)
    elif a.cmd == "exportar":
        out = exportar()
    elif a.cmd == "importar":
        out = {"decisoes_gravadas": importar(a.arquivo, a.decidido_por)}
    else:
        out = consolidar()
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
