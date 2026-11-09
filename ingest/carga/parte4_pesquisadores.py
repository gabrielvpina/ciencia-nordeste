"""Parte 4 — Pesquisadores do recorte: autores OpenAlex + docentes CAPES, com resolução de identidade.

Depende das Partes 1, 2 e 5 (works e autorias). Exige OPENALEX_API_KEY.

Modelo de identidade (SCHEME.md §8, docs/decisoes.md D-015):
- cada pesquisador tem um UUID estável (registro ingest/dados/ids/researcher.csv, compartilhado com a Parte 2);
- perfis OpenAlex com o mesmo ORCID viram o mesmo pesquisador (identificador comum, confiança 1);
- docente CAPES × autor OpenAlex não têm identificador comum: o par (nome + instituição em comum) vai para a fila
  de revisão com score < 1 e NUNCA é mesclado automaticamente;
- ORCID não é consultado em massa: a API pública fica para a reivindicação de perfil (sob demanda).

Saídas (ingest/dados/processados/):
    researchers_openalex.csv, researcher_identifiers_openalex.csv, researcher_topics.csv, researcher_review_queue.csv,
    work_authorships.csv, coauthorships.csv, institution_collaborations.csv
e o relatório ingest/relatorios/parte4_pesquisadores.md.

Uso:
    python -m ingest.carga.parte4_pesquisadores [--recoletar] [-v]
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import itertools
import json
import logging
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp
from ..diagnostico.openalex import OpenAlex
from ..diagnostico.recorte import normalizar
from .comum import AGORA, DIR_BRUTOS, DIR_PROCESSADOS, DIR_RELATORIOS, RegistroIds, escrever_csv, ler_csv

log = logging.getLogger("ingest.parte4")

MAX_AUTORES_COAUTORIA = 50  # works com mais autores (consórcios) não geram arestas de coautoria
SCORE_MIN_REVISAO = 0.8
DIR_OA = DIR_BRUTOS / "openalex"
csv.field_size_limit(10**8)


@dataclass
class AutorNE:
    oa_id: str
    nome: str = ""
    orcids: collections.Counter[str] = field(default_factory=collections.Counter)
    works: set[str] = field(default_factory=set)
    insts: collections.Counter[str] = field(default_factory=collections.Counter)
    anos: set[int] = field(default_factory=set)


# ------------------------------------------------------------------ nomes


def partes_nome(nome: str) -> list[str]:
    return [p for p in normalizar(nome).replace("-", " ").replace(".", " ").split() if p not in {"DE", "DA", "DO", "DAS", "DOS", "E"}]


def score_nome(a: str, b: str) -> float:
    """1.0 nome completo igual; 0.9 primeiro e último iguais e intermediários compatíveis (iniciais); 0.8 só primeiro e último."""
    pa, pb = partes_nome(a), partes_nome(b)
    if not pa or not pb:
        return 0.0
    if pa == pb:
        return 1.0
    if pa[-1] != pb[-1] or not (pa[0] == pb[0] or (len(pa[0]) == 1 and pb[0].startswith(pa[0])) or (len(pb[0]) == 1 and pa[0].startswith(pb[0]))):
        return 0.0
    meio_a, meio_b = pa[1:-1], pb[1:-1]
    curto, longo = sorted((meio_a, meio_b), key=len)
    it = iter(longo)
    compativel = all(any(x == y or (len(x) == 1 and y.startswith(x)) or (len(y) == 1 and x.startswith(y)) for y in it) for x in curto)
    if compativel and pa[0] == pb[0]:
        return 0.9
    return 0.8 if compativel else 0.0


def eh_latino(nome: str) -> bool:
    """True se o nome usa só alfabeto latino (com acentos)."""
    return bool(nome) and all(not ch.isalpha() or "LATIN" in unicodedata.name(ch, "") for ch in nome)


def nome_latino(candidatos: list[str]) -> str:
    """Primeiro nome em alfabeto latino; o OpenAlex às vezes escolhe uma transliteração (cirílico, CJK) como display_name."""
    validos = [c for c in candidatos if c]
    return next((c for c in validos if eh_latino(c)), validos[0] if validos else "")


# ------------------------------------------------------------------ etapas


def agregar_autorias() -> tuple[dict[str, AutorNE], dict[str, list[str]], dict[str, list[str]]]:
    """Autores com autoria NE; por work, os autores NE (para coautoria) e as instituições NE."""
    anos = {w["id"]: int(w["year"]) for w in ler_csv(DIR_PROCESSADOS / "works.csv") if w["year"]}
    n_autores = {w["id"]: int(w["authors_count"] or 0) for w in ler_csv(DIR_PROCESSADOS / "works.csv")}
    autores: dict[str, AutorNE] = {}
    work_autores: dict[str, list[str]] = collections.defaultdict(list)
    work_insts: dict[str, list[str]] = collections.defaultdict(list)
    with (DIR_PROCESSADOS / "work_authorships_openalex.csv").open(newline="", encoding="utf-8") as f:
        for lin in csv.DictReader(f):
            if lin["is_ne"] != "True":
                continue
            wid = lin["work_id"]
            insts = [i for i in lin["ne_institution_ids"].split("|") if i]
            work_insts[wid].extend(insts)
            aid = lin["openalex_author_id"]
            if not aid:
                continue
            a = autores.get(aid) or autores.setdefault(aid, AutorNE(aid))
            a.nome = a.nome or lin["author_name"]
            if lin["orcid"]:
                a.orcids[lin["orcid"]] += 1
            a.works.add(wid)
            a.insts.update(insts)
            if wid in anos:
                a.anos.add(anos[wid])
            if n_autores.get(wid, 0) <= MAX_AUTORES_COAUTORIA:
                work_autores[wid].append(aid)
    return autores, work_autores, work_insts


def coletar_perfis(oa: OpenAlex, ids: list[str], recoletar: bool) -> dict[str, dict[str, Any]]:
    destino = DIR_OA / "authors_ne.jsonl.gz"
    perfis: dict[str, dict[str, Any]] = {}
    if destino.exists() and not recoletar:
        with gzip.open(destino, "rt", encoding="utf-8") as f:
            for linha in f:
                p = json.loads(linha)
                perfis[p["id"].rsplit("/", 1)[-1]] = p
    faltando = [i for i in ids if i not in perfis]
    if faltando:
        log.info("Buscando %d perfis de autor no OpenAlex (%d chamadas)", len(faltando), -(-len(faltando) // 100))
        DIR_OA.mkdir(parents=True, exist_ok=True)
        with gzip.open(destino, "at", encoding="utf-8") as f:
            for n, i in enumerate(range(0, len(faltando), 100)):
                lote = faltando[i : i + 100]
                d = oa.http.get(
                    "https://api.openalex.org/authors",
                    params=oa._params({
                        "filter": "openalex:" + "|".join(lote), "per_page": 100,
                        "select": "id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,summary_stats,last_known_institutions,topics",
                    }),
                    cache=False,
                ).json()
                for p in d.get("results", []):
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
                    perfis[p["id"].rsplit("/", 1)[-1]] = p
                if n % 100 == 0:
                    log.info("  perfis: %d/%d", min(i + 100, len(faltando)), len(faltando))
    return perfis


def executar(recoletar: bool = False) -> dict[str, Any]:
    cfg = carregar_config()
    for arq in ("works.csv", "work_authorships_openalex.csv", "researchers_capes.csv", "institutions.csv"):
        if not (DIR_PROCESSADOS / arq).exists():
            raise SystemExit(f"Falta {arq}: rode as Partes 1, 2 e 5 antes")
    autores, work_autores, work_insts = agregar_autorias()
    log.info("Autores com autoria no NE: %d", len(autores))

    http = ClienteHttp(cfg)
    try:
        perfis = coletar_perfis(OpenAlex(http), sorted(autores), recoletar)
        creditos, custo = http.creditos_openalex, http.custo_openalex_usd
    finally:
        http.fechar()

    # ---------------------------------------------------- OpenAlex -> pesquisadores (ORCID une perfis)
    ids = RegistroIds("researcher")
    oa_para_uuid: dict[str, str] = {}
    por_uuid: dict[str, list[str]] = collections.defaultdict(list)
    orcid_de: dict[str, str] = {}
    for aid, a in autores.items():
        p = perfis.get(aid, {})
        orcid = (p.get("orcid") or "").rsplit("/", 1)[-1] or (a.orcids.most_common(1)[0][0] if a.orcids else "")
        orcid_de[aid] = orcid
        u = ids.obter([f"openalex:{aid}", f"orcid:{orcid}" if orcid else ""])
        oa_para_uuid[aid] = u
        por_uuid[u].append(aid)
    ids.salvar()

    inst_nome = {i["id"]: (i["acronym"] or i["name"]) for i in ler_csv(DIR_PROCESSADOS / "institutions.csv")}
    inst_uf = {i["id"]: i["uf"] for i in ler_csv(DIR_PROCESSADOS / "institutions.csv")}
    pesquisadores, identificadores, topicos_pesq = [], [], []
    for u, aids in por_uuid.items():
        works = set().union(*(autores[x].works for x in aids))
        insts: collections.Counter[str] = sum((autores[x].insts for x in aids), collections.Counter())
        anos = set().union(*(autores[x].anos for x in aids))
        principal = max(aids, key=lambda x: len(autores[x].works))
        p = perfis.get(principal, {})
        nome = nome_latino([p.get("display_name") or "", autores[principal].nome] + (p.get("display_name_alternatives") or []))
        orcid = next((orcid_de[x] for x in aids if orcid_de[x]), "")
        stats = p.get("summary_stats") or {}
        top_inst = insts.most_common(1)[0][0] if insts else ""
        pesquisadores.append(
            {
                "id": u,
                "display_name": nome,
                "normalized_name": normalizar(nome),
                "main_institution_id": top_inst,
                "main_institution": inst_nome.get(top_inst, ""),
                "ufs": sorted({inst_uf[i] for i in insts if i in inst_uf}),
                "works_count_period": len(works),
                "first_year": min(anos) if anos else "",
                "last_year": max(anos) if anos else "",
                "orcid": orcid,
                "openalex_ids": aids,
                "works_count_total": sum((perfis.get(x, {}).get("works_count") or 0) for x in aids),
                "cited_by_count": sum((perfis.get(x, {}).get("cited_by_count") or 0) for x in aids),
                "h_index_openalex": stats.get("h_index", ""),
                "top_topics": [t.get("display_name") for t in (p.get("topics") or [])[:5]],
                "source": "openalex",
                "updated_at": AGORA,
            }
        )
        for x in aids:
            identificadores.append({"researcher_id": u, "scheme": "openalex", "value": x, "source": "openalex", "confidence": 1.0, "verified_at": AGORA})
        if orcid:
            identificadores.append({"researcher_id": u, "scheme": "orcid", "value": orcid, "source": "openalex", "confidence": 1.0, "verified_at": AGORA})
        for t in (p.get("topics") or [])[:10]:
            topicos_pesq.append({"researcher_id": u, "topic_openalex_id": (t.get("id") or "").rsplit("/", 1)[-1], "works_count": t.get("count")})

    # ---------------------------------------------------- CAPES × OpenAlex -> fila de revisão (sem mescla)
    capes = ler_csv(DIR_PROCESSADOS / "researchers_capes.csv")
    indice: dict[str, list[str]] = collections.defaultdict(list)  # último sobrenome -> autores
    nomes_autor: dict[str, list[str]] = {}
    for aid, a in autores.items():
        p = perfis.get(aid, {})
        nomes = list(dict.fromkeys([p.get("display_name") or a.nome] + (p.get("display_name_alternatives") or [])[:15]))
        nomes_autor[aid] = nomes
        for n in nomes:
            partes = partes_nome(n)
            if partes:
                indice[partes[-1]].append(aid)
    revisao: list[dict[str, Any]] = []
    cobertura: collections.Counter[str] = collections.Counter()
    for doc in capes:
        insts_doc = set(filter(None, doc["institution_ids"].split("|")))
        partes = partes_nome(doc["display_name"])
        if not partes:
            continue
        cands: dict[str, tuple[float, float, str]] = {}
        for aid in set(indice.get(partes[-1], [])):
            if not (insts_doc & set(autores[aid].insts)):
                continue
            sn, nome_ok = max(((score_nome(doc["display_name"], n), n) for n in nomes_autor[aid]), key=lambda x: x[0])
            if sn < 0.8:
                continue
            score = round(0.75 * sn + 0.2, 3)  # 0.2 pela instituição em comum; teto 0.95 (nunca 1 sem identificador)
            cands[aid] = (score, sn, nome_ok)
        if not cands:
            cobertura["sem_candidato"] += 1
            continue
        melhores = sorted(cands.items(), key=lambda x: -x[1][0])[:3]
        cobertura["com_candidato"] += 1
        if len(melhores) == 1 and melhores[0][1][1] == 1.0:
            cobertura["candidato_unico_nome_identico"] += 1
        for aid, (score, sn, nome_ok) in melhores:
            if score < SCORE_MIN_REVISAO:
                continue
            uuid_oa = oa_para_uuid[aid]
            revisao.append(
                {
                    "entity": "researcher",
                    "candidate_a": f"researcher:{doc['id']}",
                    "candidate_b": f"researcher:{uuid_oa}",
                    "score": score,
                    "evidence": json.dumps(
                        {
                            "capes_id_pessoa": doc["capes_id_pessoa"], "capes_nome": doc["display_name"], "openalex_author": aid,
                            "openalex_nome": nome_ok, "score_nome": sn, "orcid": orcid_de.get(aid) or None,
                            "instituicoes_em_comum": sorted(inst_nome.get(i, i) for i in insts_doc & set(autores[aid].insts)),
                            "works_no_periodo": len(autores[aid].works), "candidatos": len(melhores),
                        },
                        ensure_ascii=False,
                    ),
                    "status": "pendente",
                    "created_at": AGORA,
                }
            )

    # ---------------------------------------------------- autorias finais, coautorias e colaboração entre instituições
    n_aut = 0
    with (DIR_PROCESSADOS / "work_authorships_openalex.csv").open(newline="", encoding="utf-8") as fin, (DIR_PROCESSADOS / "work_authorships.csv").open("w", newline="", encoding="utf-8") as fout:
        campos = ["work_id", "researcher_id", "openalex_author_id", "author_name", "author_order", "author_position", "is_corresponding", "institution_ids", "is_ne", "countries"]
        w = csv.DictWriter(fout, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for lin in csv.DictReader(fin):
            lin["researcher_id"] = oa_para_uuid.get(lin["openalex_author_id"], "") if lin["is_ne"] == "True" else ""
            lin["institution_ids"] = lin["ne_institution_ids"]
            w.writerow(lin)
            n_aut += 1
    ano_work = {x["id"]: int(x["year"]) for x in ler_csv(DIR_PROCESSADOS / "works.csv") if x["year"]}
    pares: dict[tuple[str, str], list[int]] = {}
    for wid, lista_aids in work_autores.items():
        us = sorted({oa_para_uuid[x] for x in lista_aids})
        ano = ano_work.get(wid, 0)
        for ua, ub in itertools.combinations(us, 2):
            v = pares.get((ua, ub))
            if v is None:
                pares[(ua, ub)] = [1, ano, ano]
            else:
                v[0] += 1
                v[1] = min(v[1], ano)
                v[2] = max(v[2], ano)
    pares_inst: collections.Counter[tuple[str, str]] = collections.Counter()
    for lista_insts in work_insts.values():
        for ia, ib in itertools.combinations(sorted(set(lista_insts)), 2):
            pares_inst[(ia, ib)] += 1

    # -------------------------------------------------------------------- saídas
    escrever_csv(
        DIR_PROCESSADOS / "researchers_openalex.csv",
        pesquisadores,
        ["id", "display_name", "normalized_name", "main_institution_id", "main_institution", "ufs", "works_count_period", "first_year", "last_year",
         "orcid", "openalex_ids", "works_count_total", "cited_by_count", "h_index_openalex", "top_topics", "source", "updated_at"],
    )
    escrever_csv(DIR_PROCESSADOS / "researcher_identifiers_openalex.csv", identificadores, ["researcher_id", "scheme", "value", "source", "confidence", "verified_at"])
    escrever_csv(DIR_PROCESSADOS / "researcher_topics.csv", topicos_pesq, ["researcher_id", "topic_openalex_id", "works_count"])
    escrever_csv(DIR_PROCESSADOS / "researcher_review_queue.csv", revisao, ["entity", "candidate_a", "candidate_b", "score", "evidence", "status", "created_at"])
    escrever_csv(
        DIR_PROCESSADOS / "coauthorships.csv",
        ({"researcher_a_id": a, "researcher_b_id": b, "shared_works_count": v[0], "first_year": v[1], "last_year": v[2]} for (a, b), v in pares.items()),
        ["researcher_a_id", "researcher_b_id", "shared_works_count", "first_year", "last_year"],
    )
    escrever_csv(
        DIR_PROCESSADOS / "institution_collaborations.csv",
        ({"institution_a_id": a, "institution_b_id": b, "shared_works_count": n} for (a, b), n in pares_inst.items()),
        ["institution_a_id", "institution_b_id", "shared_works_count"],
    )

    wp = collections.Counter(min(p["works_count_period"], 10) for p in pesquisadores)
    uf_count: collections.Counter[str] = collections.Counter()
    for p in pesquisadores:
        uf_count.update(p["ufs"])
    s = {
        "gerado_em": AGORA,
        "autores_openalex_ne": len(autores),
        "perfis_obtidos": sum(1 for a in autores if a in perfis),
        "pesquisadores_openalex": len(pesquisadores),
        "perfis_unidos_por_orcid": len(autores) - len(pesquisadores),
        "com_orcid": sum(1 for p in pesquisadores if p["orcid"]),
        "por_works_no_periodo": {("10+" if k == 10 else str(k)): v for k, v in sorted(wp.items())},
        "com_3_ou_mais_works": sum(1 for p in pesquisadores if p["works_count_period"] >= 3),
        "por_uf": dict(uf_count.most_common()),
        "docentes_capes": len(capes),
        "docentes_com_candidato": cobertura["com_candidato"],
        "docentes_candidato_unico_nome_identico": cobertura["candidato_unico_nome_identico"],
        "docentes_sem_candidato": cobertura["sem_candidato"],
        "fila_revisao_pesquisadores": len(revisao),
        "autorias_gravadas": n_aut,
        "coautorias_pares": len(pares),
        "colaboracoes_instituicoes_pares": len(pares_inst),
        "conflitos_ids": ids.conflitos[:50],
        "n_conflitos_ids": len(ids.conflitos),
        "creditos_openalex": creditos,
        "custo_openalex_usd": round(custo, 4),
        "top_colaboracoes_instituicoes": [(inst_nome.get(a, a), inst_nome.get(b, b), n) for (a, b), n in pares_inst.most_common(15)],
        "top_pesquisadores": [
            {"nome": p["display_name"], "instituicao": p["main_institution"], "works": p["works_count_period"], "orcid": bool(p["orcid"])}
            for p in sorted(pesquisadores, key=lambda p: -p["works_count_period"])[:15]
        ],
    }
    _relatorio(s)
    return s


def _relatorio(s: dict[str, Any]) -> None:
    j = lambda x: json.dumps(x, ensure_ascii=False)  # noqa: E731
    pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "—"  # noqa: E731
    L = [
        "# Parte 4 — Pesquisadores do recorte (OpenAlex + CAPES)",
        "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte4_pesquisadores`.",
        "",
        "## Resumo",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Autores OpenAlex com autoria em instituição do NE no recorte | {s['autores_openalex_ne']} (perfis obtidos: {s['perfis_obtidos']}) |",
        f"| **Pesquisadores (após unir perfis com o mesmo ORCID)** | **{s['pesquisadores_openalex']}** ({s['perfis_unidos_por_orcid']} perfis unidos) |",
        f"| Com ORCID | {s['com_orcid']} ({pct(s['com_orcid'], s['pesquisadores_openalex'])}) |",
        f"| Com 3+ works no período | {s['com_3_ou_mais_works']} |",
        f"| Docentes CAPES do recorte | {s['docentes_capes']} |",
        f"| ...com candidato OpenAlex (nome + instituição) | {s['docentes_com_candidato']} ({pct(s['docentes_com_candidato'], s['docentes_capes'])}) |",
        f"| ...com candidato único e nome idêntico | {s['docentes_candidato_unico_nome_identico']} |",
        f"| ...sem candidato | {s['docentes_sem_candidato']} |",
        f"| Pares na fila de revisão (docente × autor) | {s['fila_revisao_pesquisadores']} |",
        f"| Arestas de coautoria (works com até {MAX_AUTORES_COAUTORIA} autores) | {s['coautorias_pares']} |",
        f"| Pares de instituições do NE que publicam juntas | {s['colaboracoes_instituicoes_pares']} |",
        f"| Conflitos no registro de IDs | {s['n_conflitos_ids']} |",
        f"| Créditos OpenAlex | {s['creditos_openalex']} (US$ {s['custo_openalex_usd']}) |",
        "",
        f"Distribuição de works no período por pesquisador: {j(s['por_works_no_periodo'])}",
        "",
        f"Pesquisadores por UF (um pesquisador pode ter vínculo em mais de uma): {j(s['por_uf'])}",
        "",
        "Nenhum docente CAPES foi mesclado a um autor OpenAlex: os pares vão para `researcher_review_queue.csv` (score ≤ 0,95).",
        "",
        "## Pesquisadores com mais works no período",
        "",
        "| Pesquisador | Instituição principal | Works | ORCID |",
        "|---|---|---|---|",
    ]
    L += [f"| {t['nome']} | {t['instituicao']} | {t['works']} | {'sim' if t['orcid'] else 'não'} |" for t in s["top_pesquisadores"]]
    L += ["", "## Instituições do NE que mais publicam juntas", "", "| Instituição A | Instituição B | Works |", "|---|---|---|"]
    L += [f"| {a} | {b} | {n} |" for a, b, n in s["top_colaboracoes_instituicoes"]]
    if s["conflitos_ids"]:
        L += ["", "## Conflitos no registro de IDs (amostra)", "", f"```\n{json.dumps(s['conflitos_ids'][:10], ensure_ascii=False)}\n```"]
    L += ["", "## Arquivos", "", "researchers_openalex.csv, researcher_identifiers_openalex.csv, researcher_topics.csv, researcher_review_queue.csv, "
          "work_authorships.csv, coauthorships.csv, institution_collaborations.csv. Perfis brutos: `ingest/dados/brutos/openalex/authors_ne.jsonl.gz`."]
    (DIR_RELATORIOS / "parte4_pesquisadores.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte4_pesquisadores.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recoletar", action="store_true", help="Busca de novo todos os perfis de autor.")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar(recoletar=a.recoletar)
    print(json.dumps({k: s[k] for k in ("pesquisadores_openalex", "com_orcid", "docentes_com_candidato", "fila_revisao_pesquisadores", "coautorias_pares")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
