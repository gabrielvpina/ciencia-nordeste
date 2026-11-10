"""Parte 9 — Qualis Periódicos (CAPES) e ISSNs das revistas do recorte (D-033).

Entradas:
  - ingest/dados/brutos/capes/qualis/qualis-<evento>.xlsx: planilha exportada da consulta pública da Plataforma Sucupira
    (colunas ISSN, Título, Área de Avaliação, Estrato). Baixada à mão: não há download em lote nem API (sem scraping, D-002).
  - ingest/dados/brutos/openalex/works_*.jsonl.gz (Parte 5): cada publicação traz a revista com todos os ISSNs
    (impresso e eletrônico), não só o ISSN-L. Nenhuma chamada nova ao OpenAlex.

Saídas (ingest/dados/processados/):
  - qualis_periodicos.csv: evento, issn, estrato, titulo, areas ('|'). No Qualis 2021-2024 cada ISSN tem um só estrato,
    repetido em todas as áreas que o listam; se um ISSN aparecer com estratos diferentes, fica o melhor e o caso vai ao relatório.
  - venue_issns.csv: venue_openalex_id, issn.
  - relatório em ingest/relatorios/parte9_qualis.md (+ .json), com a cobertura das publicações.

Uso:  python -m ingest.carga.parte9_qualis [--evento 2021-2024]
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .comum import AGORA, DIR_BRUTOS, DIR_PROCESSADOS, DIR_RELATORIOS, escrever_csv
from .parte5_producao import DIR_OA, ler_works

log = logging.getLogger("ingest.parte9")

DIR_QUALIS = DIR_BRUTOS / "capes" / "qualis"
ESTRATOS = ("A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C")
COLUNAS = ("ISSN", "Título", "Área de Avaliação", "Estrato")
RE_ISSN = re.compile(r"^\d{4}-?\d{3}[\dX]$")
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def normalizar_issn(valor: str) -> str | None:
    """'1234567x' / '1234-567X ' -> '1234-567X'; None se não for um ISSN."""
    v = (valor or "").strip().upper()
    if not RE_ISSN.match(v):
        return None
    v = v.replace("-", "")
    return f"{v[:4]}-{v[4:]}"


def _coluna(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():  # type: ignore[union-attr]
        n = n * 26 + ord(ch) - 64
    return n - 1


def ler_xlsx(caminho: Path) -> Iterator[list[str]]:
    """Linhas da primeira planilha de um .xlsx, como texto (leitor mínimo, só biblioteca padrão)."""
    with zipfile.ZipFile(caminho) as z:
        compartilhadas: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            compartilhadas = ["".join(t.text or "" for t in si.iter(f"{_NS}t")) for si in raiz.findall(f"{_NS}si")]
        for _, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml")):
            if el.tag != f"{_NS}row":
                continue
            celulas: dict[int, str] = {}
            for c in el.findall(f"{_NS}c"):
                tipo, v = c.get("t"), c.find(f"{_NS}v")
                if tipo == "inlineStr":
                    valor = "".join(t.text or "" for t in c.iter(f"{_NS}t"))
                elif v is None or v.text is None:
                    valor = ""
                elif tipo == "s":
                    valor = compartilhadas[int(v.text)]
                else:
                    valor = v.text
                celulas[_coluna(c.get("r", "A1"))] = valor
            el.clear()
            if celulas:
                yield [celulas.get(i, "") for i in range(max(celulas) + 1)]


def ler_qualis(caminho: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    linhas = ler_xlsx(caminho)
    cabecalho = [c.strip() for c in next(linhas)]
    if tuple(cabecalho[:4]) != COLUNAS:
        raise SystemExit(f"{caminho.name}: colunas inesperadas {cabecalho[:4]} (esperado {list(COLUNAS)})")
    por_issn: dict[str, dict[str, Any]] = {}
    estratos_vistos: dict[str, set[str]] = collections.defaultdict(set)
    c: collections.Counter[str] = collections.Counter()
    for lin in linhas:
        lin = (lin + [""] * 4)[:4]
        issn, titulo, area, estrato = normalizar_issn(lin[0]), lin[1].strip(), " ".join(lin[2].split()), lin[3].strip().upper()
        c["linhas"] += 1
        if not issn:
            c["issn_invalido"] += 1
            continue
        if estrato not in ESTRATOS:
            c["estrato_invalido"] += 1
            continue
        estratos_vistos[issn].add(estrato)
        r = por_issn.setdefault(issn, {"issn": issn, "estrato": estrato, "titulo": titulo, "areas": set()})
        r["estrato"] = min(r["estrato"], estrato)   # 'A1' < 'A2' < … < 'C': fica o melhor
        r["areas"].add(area)
    conflitos = {i: sorted(e) for i, e in estratos_vistos.items() if len(e) > 1}
    c["issns"] = len(por_issn)
    c["issns_com_estratos_diferentes"] = len(conflitos)
    return por_issn, {"contagens": dict(c), "conflitos_exemplo": dict(list(conflitos.items())[:20])}


def issns_das_revistas() -> tuple[dict[str, set[str]], list[tuple[str, str, int | None]]]:
    """venue_openalex_id -> ISSNs, e (work_id curto, venue, ano) de cada publicação, a partir dos brutos da Parte 5."""
    arquivos = sorted(DIR_OA.glob("works_lote*.jsonl.gz"))
    if not arquivos:
        raise SystemExit("Rode antes a Parte 5 (brutos do OpenAlex em ingest/dados/brutos/openalex/)")
    revistas: dict[str, set[str]] = collections.defaultdict(set)
    works: list[tuple[str, str, int | None]] = []
    for w in ler_works(arquivos, DIR_OA / "works_completos.jsonl.gz"):
        src = ((w.get("primary_location") or {}).get("source")) or {}
        vid = (src.get("id") or "").rsplit("/", 1)[-1]
        works.append((w["id"], vid, w.get("publication_year")))
        if not vid:
            continue
        for x in [src.get("issn_l"), *(src.get("issn") or [])]:
            n = normalizar_issn(x or "")
            if n:
                revistas[vid].add(n)
    return revistas, works


def executar(evento: str) -> dict[str, Any]:
    caminho = DIR_QUALIS / f"qualis-{evento}.xlsx"
    if not caminho.exists():
        raise SystemExit(f"Planilha não encontrada: {caminho} (exporte-a da Sucupira; veja ingest/README.md, Parte 9)")
    qualis, info = ler_qualis(caminho)
    escrever_csv(
        DIR_PROCESSADOS / "qualis_periodicos.csv",
        ({"evento": evento, "issn": r["issn"], "estrato": r["estrato"], "titulo": r["titulo"], "areas": "|".join(sorted(r["areas"]))}
         for r in sorted(qualis.values(), key=lambda r: r["issn"])),
        ["evento", "issn", "estrato", "titulo", "areas"],
    )
    revistas, works = issns_das_revistas()
    escrever_csv(
        DIR_PROCESSADOS / "venue_issns.csv",
        ({"venue_openalex_id": v, "issn": i} for v in sorted(revistas) for i in sorted(revistas[v])),
        ["venue_openalex_id", "issn"],
    )
    # Cobertura: o mesmo critério da visão mv_work_qualis (qualquer ISSN da revista; vale o melhor estrato).
    estrato_revista = {v: min((qualis[i]["estrato"] for i in iss if i in qualis), default=None) for v, iss in revistas.items()}
    por_estrato: collections.Counter[str] = collections.Counter()
    por_ano: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for _, vid, ano in works:
        e = estrato_revista.get(vid) or ("sem_qualis" if vid else "sem_revista")
        por_estrato[e] += 1
        if ano:
            por_ano[int(ano)]["com_qualis" if e in ESTRATOS else "sem"] += 1
    s = {
        "gerado_em": AGORA, "evento": evento, "planilha": caminho.name, **info,
        "revistas_no_recorte": len(revistas),
        "revistas_com_qualis": sum(1 for e in estrato_revista.values() if e),
        "works": len(works),
        "works_com_qualis": sum(por_estrato[e] for e in ESTRATOS),
        "works_por_estrato": {e: por_estrato[e] for e in (*ESTRATOS, "sem_qualis", "sem_revista")},
        "cobertura_por_ano": {a: round(100 * c["com_qualis"] / max(1, c["com_qualis"] + c["sem"]), 1) for a, c in sorted(por_ano.items())},
    }
    _relatorio(s)
    return s


def _relatorio(s: dict[str, Any]) -> None:
    pct = lambda a, b: f"{100 * a / max(1, b):.1f}%"  # noqa: E731
    L = [
        f"# Parte 9 — Qualis Periódicos {s['evento']} (CAPES)", "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte9_qualis` a partir de `{s['planilha']}`.", "",
        "| Item | Valor |", "|---|---|",
        f"| Linhas da planilha | {s['contagens'].get('linhas', 0)} |",
        f"| ISSNs distintos classificados | {s['contagens'].get('issns', 0)} |",
        f"| Linhas descartadas (ISSN ou estrato inválido) | {s['contagens'].get('issn_invalido', 0) + s['contagens'].get('estrato_invalido', 0)} |",
        f"| ISSNs com estratos diferentes entre áreas (fica o melhor) | {s['contagens'].get('issns_com_estratos_diferentes', 0)} |",
        f"| Revistas do recorte (OpenAlex) | {s['revistas_no_recorte']} |",
        f"| Revistas com Qualis | {s['revistas_com_qualis']} ({pct(s['revistas_com_qualis'], s['revistas_no_recorte'])}) |",
        f"| **Publicações com Qualis** | **{s['works_com_qualis']} de {s['works']} ({pct(s['works_com_qualis'], s['works'])})** |", "",
        "## Publicações por estrato", "", "| Estrato | Publicações |", "|---|---|",
        *[f"| {e.replace('_', ' ')} | {n} |" for e, n in s["works_por_estrato"].items()], "",
        "## Cobertura por ano de publicação", "", "| Ano | % com Qualis |", "|---|---|",
        *[f"| {a} | {p}% |" for a, p in s["cobertura_por_ano"].items()], "",
        "\"sem qualis\": a revista não está na lista (eventos, anais de iniciação científica, revistas novas ou fora das áreas);",
        "\"sem revista\": a publicação não tem fonte no OpenAlex (livros, repositórios). O Qualis classifica revistas, não artigos (D-033).",
    ]
    if s.get("conflitos_exemplo"):
        L += ["", f"Exemplos de ISSN com estratos diferentes: `{json.dumps(s['conflitos_exemplo'], ensure_ascii=False)}`"]
    (DIR_RELATORIOS / "parte9_qualis.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte9_qualis.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--evento", default="2021-2024", help="quadriênio da planilha qualis-<evento>.xlsx (padrão 2021-2024)")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    s = executar(a.evento)
    print(json.dumps({k: s[k] for k in ("contagens", "revistas_no_recorte", "revistas_com_qualis", "works", "works_com_qualis", "works_por_estrato")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
