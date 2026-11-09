"""Parte 5 — Produção científica do recorte (OpenAlex).

Recorte: works com ao menos uma autoria em instituição do NE (lista de IDs OpenAlex da Parte 1, filtro por
`authorships.institutions.lineage`, em lotes de até 100 IDs), primary topic nos fields de saúde/biomédicas
(ingest/diagnostico/recorte.py) e ano de publicação no período. Exige OPENALEX_API_KEY (cursor paging).

Etapas:
  1. coleta: grava os works brutos (campos selecionados) em ingest/dados/brutos/openalex/works_<lote>.jsonl.gz;
     cada lote completo ganha um arquivo .ok e não é baixado de novo (use --recoletar para refazer);
  2. derivação: deduplica e gera em ingest/dados/processados/
        works.csv, work_authorships_openalex.csv, topics.csv, work_topics.csv, funders.csv, work_funders.csv.
     A ligação autoria → pesquisador (researcher_id) e as coautorias saem da Parte 4.

Uso:
    python -m ingest.carga.parte5_producao [--recoletar] [-v]
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import logging
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp
from ..diagnostico.openalex import OpenAlex
from ..diagnostico.recorte import CAMPOS_OPENALEX, filtro_openalex_campos
from .comum import AGORA, DIR_BRUTOS, DIR_PROCESSADOS, DIR_RELATORIOS, RegistroIds, escrever_csv, ler_csv

log = logging.getLogger("ingest.parte5")

CAMPOS_SELECT = (
    "id,doi,title,publication_year,publication_date,type,language,primary_location,open_access,"
    "primary_topic,topics,authorships,cited_by_count,funders,ids,is_xpac"
)
DIR_OA = DIR_BRUTOS / "openalex"


def _curto(url: str | None) -> str:
    return (url or "").rsplit("/", 1)[-1]


def coletar(oa: OpenAlex, ids_ne: list[str], anos: str, recoletar: bool) -> list[Path]:
    area = filtro_openalex_campos("primary_topic.field.id")
    arquivos = []
    for n, i in enumerate(range(0, len(ids_ne), 100)):
        lote = ids_ne[i : i + 100]
        destino = DIR_OA / f"works_lote{n:02d}.jsonl.gz"
        ok = destino.with_suffix(".ok")
        arquivos.append(destino)
        if ok.exists() and destino.exists() and not recoletar:
            log.info("Lote %d já coletado (%s)", n, ok.read_text().strip())
            continue
        filtro = f"authorships.institutions.lineage:{'|'.join(lote)},{area},publication_year:{anos}"
        esperado = oa.contar("works", filtro)
        log.info("Lote %d: %d works esperados (%d chamadas)", n, esperado, -(-esperado // 100))
        DIR_OA.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_suffix(".parcial")
        t0, total = time.monotonic(), 0
        with gzip.open(parcial, "wt", encoding="utf-8") as f:
            for pagina in oa.paginar("works", filter=filtro, select=CAMPOS_SELECT):
                for w in pagina:
                    f.write(json.dumps(w, ensure_ascii=False) + "\n")
                total += len(pagina)
                if total % 5000 < 100:
                    log.info("  lote %d: %d/%d (%.0f s)", n, total, esperado, time.monotonic() - t0)
        parcial.replace(destino)
        ok.write_text(f"{total} works em {AGORA}; esperado {esperado}\n")
        log.info("Lote %d concluído: %d works em %.0f s", n, total, time.monotonic() - t0)
    return arquivos


def completar_autorias(oa: OpenAlex, arquivos: list[Path]) -> Path:
    """A listagem traz só as 100 primeiras autorias de cada work. Para os works com 100 autorias, busca o registro
    completo no endpoint individual (gratuito; até 5.000 autorias) e grava em works_completos.jsonl.gz."""
    destino = DIR_OA / "works_completos.jsonl.gz"
    ja: set[str] = set()
    if destino.exists():
        with gzip.open(destino, "rt", encoding="utf-8") as f:
            ja = {json.loads(linha)["id"] for linha in f}
    alvos = []
    vistos: set[str] = set()
    for a in arquivos:
        with gzip.open(a, "rt", encoding="utf-8") as f:
            for linha in f:
                w = json.loads(linha)
                if w["id"] not in vistos and len(w.get("authorships") or []) >= 100 and w["id"] not in ja:
                    alvos.append(w["id"])
                vistos.add(w["id"])
    if alvos:
        log.info("Buscando %d works com autorias truncadas no endpoint individual (gratuito)", len(alvos))
        with gzip.open(destino, "at", encoding="utf-8") as f:
            for wid in alvos:
                r = oa.http.get(f"https://api.openalex.org/works/{_curto(wid)}", params=oa._params({"select": CAMPOS_SELECT}))
                if r.ok:
                    f.write(json.dumps(r.json(), ensure_ascii=False) + "\n")
                else:
                    log.warning("Work %s: HTTP %s", wid, r.status)
    return destino


def ler_works(arquivos: list[Path], completos: Path | None = None) -> Iterator[dict[str, Any]]:
    """Works deduplicados; quando há versão completa (todas as autorias), ela substitui a da listagem."""
    substitutos: dict[str, dict[str, Any]] = {}
    if completos and completos.exists():
        with gzip.open(completos, "rt", encoding="utf-8") as f:
            for linha in f:
                w = json.loads(linha)
                substitutos[w["id"]] = w
    vistos: set[str] = set()
    for a in arquivos:
        with gzip.open(a, "rt", encoding="utf-8") as f:
            for linha in f:
                w = json.loads(linha)
                if w["id"] in vistos:
                    continue
                vistos.add(w["id"])
                yield substitutos.get(w["id"], w)


CAMPOS_AUTORIA = [
    "work_id", "openalex_work_id", "author_order", "author_position", "openalex_author_id", "author_name", "orcid", "is_corresponding",
    "institution_openalex_ids", "ne_institution_ids", "is_ne", "countries",
]


def derivar(arquivos: list[Path], completos: Path | None = None) -> dict[str, Any]:
    oa_para_inst: dict[str, str] = {}
    uf_inst: dict[str, str] = {}
    for i in ler_csv(DIR_PROCESSADOS / "institution_identifiers.csv"):
        if i["scheme"] == "openalex":
            oa_para_inst[i["value"]] = i["institution_id"]
    for i in ler_csv(DIR_PROCESSADOS / "institutions.csv"):
        uf_inst[i["id"]] = i["uf"]

    ids_work = RegistroIds("work")
    works: list[dict[str, Any]] = []
    caminho_aut = DIR_PROCESSADOS / "work_authorships_openalex.csv"
    caminho_aut.parent.mkdir(parents=True, exist_ok=True)
    f_aut = caminho_aut.open("w", newline="", encoding="utf-8")
    w_aut = csv.DictWriter(f_aut, fieldnames=CAMPOS_AUTORIA)
    w_aut.writeheader()
    n_aut = n_aut_ne = n_sem_id = 0
    autores_ne: set[str] = set()
    autores_todos: set[str] = set()
    topicos: dict[str, dict[str, Any]] = {}
    work_topicos: list[dict[str, Any]] = []
    financiadores: dict[str, dict[str, Any]] = {}
    work_fin: list[dict[str, Any]] = []
    c: dict[str, collections.Counter[Any]] = collections.defaultdict(collections.Counter)

    for w in ler_works(arquivos, completos):
        wid_oa = _curto(w["id"])
        wid = ids_work.obter([f"openalex:{wid_oa}"])
        pt = w.get("primary_topic") or {}
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        oa_info = w.get("open_access") or {}
        ne_insts: set[str] = set()
        ufs: set[str] = set()
        n_autores = len(w.get("authorships") or [])
        for pos, a in enumerate(w.get("authorships") or []):
            insts_oa = [_curto(x.get("id")) for x in a.get("institutions") or [] if x.get("id")]
            # instituição do NE se ela ou algum ancestral (lineage) estiver na lista da Parte 1
            ne = []
            for x in a.get("institutions") or []:
                for anc in [_curto(y) for y in (x.get("lineage") or [x.get("id")])]:
                    if anc in oa_para_inst:
                        ne.append(oa_para_inst[anc])
                        break
            ne = list(dict.fromkeys(ne))
            ne_insts.update(ne)
            ufs.update(uf_inst[i] for i in ne)
            autor = a.get("author") or {}
            aid = _curto(autor.get("id"))
            n_aut += 1
            n_aut_ne += bool(ne)
            n_sem_id += not aid
            if aid:
                autores_todos.add(aid)
                if ne:
                    autores_ne.add(aid)
            w_aut.writerow(
                {
                    "work_id": wid,
                    "openalex_work_id": wid_oa,
                    "author_order": pos + 1,
                    "author_position": a.get("author_position", ""),
                    "openalex_author_id": aid,
                    "author_name": autor.get("display_name", ""),
                    "orcid": _curto(autor.get("orcid")),
                    "is_corresponding": bool(a.get("is_corresponding")),
                    "institution_openalex_ids": "|".join(insts_oa),
                    "ne_institution_ids": "|".join(ne),
                    "is_ne": bool(ne),
                    "countries": "|".join(a.get("countries") or []),
                }
            )
        for t in w.get("topics") or []:
            tid = _curto(t.get("id"))
            topicos.setdefault(
                tid,
                {
                    "openalex_id": tid, "name": t.get("display_name"), "subfield_id": _curto((t.get("subfield") or {}).get("id")),
                    "subfield": (t.get("subfield") or {}).get("display_name"), "field_id": _curto((t.get("field") or {}).get("id")),
                    "field": (t.get("field") or {}).get("display_name"), "domain": (t.get("domain") or {}).get("display_name"),
                },
            )
            work_topicos.append({"work_id": wid, "topic_openalex_id": tid, "score": t.get("score"), "is_primary": tid == _curto(pt.get("id"))})
        for fu in w.get("funders") or []:
            fid = _curto(fu.get("id"))
            financiadores.setdefault(fid, {"openalex_id": fid, "name": fu.get("display_name"), "ror": _curto(fu.get("ror"))})
            work_fin.append({"work_id": wid, "funder_openalex_id": fid})
        ano = w.get("publication_year")
        works.append(
            {
                "id": wid,
                "openalex_id": wid_oa,
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "title": (w.get("title") or "").strip(),
                "year": ano,
                "publication_date": w.get("publication_date"),
                "type": w.get("type"),
                "language": w.get("language"),
                "venue": src.get("display_name") or "",
                "venue_issn_l": src.get("issn_l") or "",
                "venue_openalex_id": _curto(src.get("id")),
                "is_oa": oa_info.get("is_oa"),
                "oa_status": oa_info.get("oa_status"),
                "primary_topic_id": _curto(pt.get("id")),
                "primary_topic": pt.get("display_name"),
                "primary_subfield": (pt.get("subfield") or {}).get("display_name"),
                "primary_field_id": _curto((pt.get("field") or {}).get("id")),
                "primary_field": (pt.get("field") or {}).get("display_name"),
                "cited_by_count": w.get("cited_by_count"),
                "pmid": _curto((w.get("ids") or {}).get("pmid")),
                "authors_count": n_autores,
                "ne_institutions_count": len(ne_insts),
                "ne_ufs": sorted(ufs),
                "is_xpac": w.get("is_xpac"),
                "updated_at": AGORA,
            }
        )
        c["ano"][ano] += 1
        c["tipo"][w.get("type")] += 1
        c["field"][(pt.get("field") or {}).get("display_name")] += 1
        c["oa"][oa_info.get("oa_status")] += 1
        c["lingua"][w.get("language")] += 1
        for uf in ufs:
            c["uf"][uf] += 1
        c["n_ufs_ne"][min(len(ufs), 3)] += 1
        if n_autores > 100:
            c["mega"]["works_com_mais_de_100_autores"] += 1
        c["inst"].update(ne_insts)
        if not ne_insts:
            c["sem_ne"]["works_sem_autoria_ne_identificada"] += 1
    ids_work.salvar()
    f_aut.close()

    escrever_csv(
        DIR_PROCESSADOS / "works.csv",
        works,
        ["id", "openalex_id", "doi", "title", "year", "publication_date", "type", "language", "venue", "venue_issn_l", "venue_openalex_id",
         "is_oa", "oa_status", "primary_topic_id", "primary_topic", "primary_subfield", "primary_field_id", "primary_field", "cited_by_count",
         "pmid", "authors_count", "ne_institutions_count", "ne_ufs", "is_xpac", "updated_at"],
    )
    escrever_csv(DIR_PROCESSADOS / "topics.csv", topicos.values(), ["openalex_id", "name", "subfield_id", "subfield", "field_id", "field", "domain"])
    escrever_csv(DIR_PROCESSADOS / "work_topics.csv", work_topicos, ["work_id", "topic_openalex_id", "score", "is_primary"])
    escrever_csv(DIR_PROCESSADOS / "funders.csv", financiadores.values(), ["openalex_id", "name", "ror"])
    escrever_csv(DIR_PROCESSADOS / "work_funders.csv", work_fin, ["work_id", "funder_openalex_id"])

    nomes_inst = {i["id"]: (i["acronym"] or i["name"]) for i in ler_csv(DIR_PROCESSADOS / "institutions.csv")}
    log.info("Gravado %s (%d linhas)", caminho_aut.name, n_aut)
    return {
        "works": len(works),
        "autorias": n_aut,
        "autorias_ne": n_aut_ne,
        "autorias_sem_author_id": n_sem_id,
        "autores_ne_distintos": len(autores_ne),
        "autores_distintos_total": len(autores_todos),
        "topicos": len(topicos),
        "financiadores": len(financiadores),
        "works_com_financiador": len({x["work_id"] for x in work_fin}),
        "por_ano": dict(sorted(c["ano"].items())),
        "por_tipo": dict(c["tipo"].most_common()),
        "por_field": dict(c["field"].most_common()),
        "por_oa": dict(c["oa"].most_common()),
        "por_lingua": dict(c["lingua"].most_common(6)),
        "por_uf": dict(c["uf"].most_common()),
        "works_por_n_ufs_ne": {("3+" if k == 3 else str(k)): v for k, v in sorted(c["n_ufs_ne"].items())},
        "works_com_mais_de_100_autores": c["mega"]["works_com_mais_de_100_autores"],
        "works_sem_autoria_ne_identificada": c["sem_ne"]["works_sem_autoria_ne_identificada"],
        "top_instituicoes": [(nomes_inst.get(k, k), v) for k, v in c["inst"].most_common(20)],
    }


def executar(recoletar: bool = False) -> dict[str, Any]:
    cfg = carregar_config()
    ids_ne = (DIR_PROCESSADOS / "openalex_institution_ids_ne.txt").read_text().split()
    if not ids_ne:
        raise SystemExit("Rode antes a Parte 1 (lista de instituições do NE)")
    http = ClienteHttp(cfg)
    try:
        oa = OpenAlex(http)
        arquivos = coletar(oa, ids_ne, f"{cfg.year_start}-{cfg.year_end}", recoletar)
        completos = completar_autorias(oa, arquivos)
        creditos, custo = http.creditos_openalex, http.custo_openalex_usd
    finally:
        http.fechar()
    s = derivar(arquivos, completos)
    s.update({"gerado_em": AGORA, "periodo": f"{cfg.year_start}-{cfg.year_end}", "instituicoes_filtro": len(ids_ne),
              "creditos_openalex": creditos, "custo_openalex_usd": round(custo, 4), "fields": CAMPOS_OPENALEX})
    _relatorio(s)
    return s


def _relatorio(s: dict[str, Any]) -> None:
    j = lambda x: json.dumps(x, ensure_ascii=False)  # noqa: E731
    L = [
        "# Parte 5 — Produção científica do recorte (OpenAlex)",
        "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte5_producao`. Período {s['periodo']}; filtro: autoria em uma das "
        f"{s['instituicoes_filtro']} instituições do NE (lineage) × primary topic nos fields {j(list(s['fields'].values()))}.",
        "",
        "## Resumo",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| **Works (deduplicados)** | **{s['works']}** |",
        f"| Autorias (total / com instituição do NE) | {s['autorias']} / {s['autorias_ne']} |",
        f"| Autores distintos (todos / com autoria no NE) | {s['autores_distintos_total']} / {s['autores_ne_distintos']} |",
        f"| Autorias sem ID de autor no OpenAlex | {s['autorias_sem_author_id']} |",
        f"| Works com mais de 100 autores (consórcios) | {s['works_com_mais_de_100_autores']} |",
        f"| Works sem autoria NE identificada na derivação | {s['works_sem_autoria_ne_identificada']} |",
        f"| Tópicos distintos | {s['topicos']} |",
        f"| Works com financiador declarado | {s['works_com_financiador']} ({s['financiadores']} financiadores) |",
        f"| Créditos OpenAlex gastos na coleta | {s['creditos_openalex']} (US$ {s['custo_openalex_usd']}) |",
        "",
        f"Por ano: {j(s['por_ano'])}",
        "",
        f"Por UF (works com autoria na UF; um work conta em várias): {j(s['por_uf'])}",
        "",
        f"Works por número de UFs do NE envolvidas: {j(s['works_por_n_ufs_ne'])}",
        "",
        f"Por field: {j(s['por_field'])}",
        "",
        f"Por tipo: {j(s['por_tipo'])}",
        "",
        f"Acesso aberto: {j(s['por_oa'])}",
        "",
        f"Idioma: {j(s['por_lingua'])}",
        "",
        "## Instituições com mais works no recorte",
        "",
        "| Instituição | Works |",
        "|---|---|",
    ]
    L += [f"| {n} | {v} |" for n, v in s["top_instituicoes"]]
    L += ["", "## Arquivos", "", "Brutos: `ingest/dados/brutos/openalex/works_lote*.jsonl.gz`. Processados: works.csv, work_authorships_openalex.csv, "
          "topics.csv, work_topics.csv, funders.csv, work_funders.csv. UUIDs: `ingest/dados/ids/work.csv`."]
    (DIR_RELATORIOS / "parte5_producao.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte5_producao.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recoletar", action="store_true", help="Ignora lotes já coletados e baixa de novo.")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar(recoletar=a.recoletar)
    print(json.dumps({k: s[k] for k in ("works", "autores_ne_distintos", "por_ano", "por_uf", "creditos_openalex")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
