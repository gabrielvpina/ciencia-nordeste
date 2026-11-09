"""Parte 6 — Complementos: teses e orientações (CAPES), FAPs do Nordeste, situação do BDTD/Oasisbr.

Depende das Partes 2 (programas), 4/5 (financiadores) e da consolidação da revisão (aliases).

Saídas (ingest/dados/processados/): theses.csv, funders_ne.csv; relatório ingest/relatorios/parte6_complementos.md.

Uso:
    python -m ingest.carga.parte6_complementos [-v]
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp
from ..diagnostico.recorte import UFS_NORDESTE
from .comum import AGORA, DIR_BRUTOS, DIR_IDS, DIR_PROCESSADOS, DIR_RELATORIOS, RegistroIds, escrever_csv, ler_csv
from .parte2_capes import _arquivos

log = logging.getLogger("ingest.parte6")
csv.field_size_limit(10**8)

SLUG_TESES = "2021-a-2024-catalogo-de-teses-e-dissertacoes-brasil"
FAPS_NE = {
    "MA": ("FAPEMA", r"\bFAPEMA\b|Maranh"), "PI": ("FAPEPI", r"\bFAPEPI\b|Piau"), "CE": ("FUNCAP", r"\bFUNCAP\b|Cearense"),
    "RN": ("FAPERN", r"\bFAPERN\b|Rio Grande do Norte"), "PB": ("FAPESQ", r"\bFAPESQ\b|Para[ií]ba"), "PE": ("FACEPE", r"\bFACEPE\b|Pernambuco"),
    "AL": ("FAPEAL", r"\bFAPEAL\b|Alagoas"), "SE": ("FAPITEC", r"\bFAPITEC\b|Sergipe"), "BA": ("FAPESB", r"\bFAPESB\b|Bahia"),
}
# Colunas do catálogo: nomes possíveis (o leiaute muda entre anos); a primeira que existir é usada.
COLUNAS = {
    "production_id": ["ID_PRODUCAO_INTELECTUAL", "ID_ADD_PRODUCAO_INTELECTUAL"],
    "program_code": ["CD_PROGRAMA", "CD_PROGRAMA_IES"],
    "title": ["NM_PRODUCAO", "NM_TITULO"],
    "degree": ["NM_SUBTIPO_PRODUCAO", "NM_GRAU_ACADEMICO"],
    "year": ["AN_BASE"],
    "defense_date": ["DT_TITULACAO", "DH_TITULACAO"],
    "author_name": ["NM_DISCENTE", "NM_AUTOR"],
    "author_capes_id": ["ID_PESSOA_DISCENTE"],
    "advisor_name": ["NM_ORIENTADOR", "NM_ORIENTADOR_PRINCIPAL"],
    "advisor_capes_id": ["ID_PESSOA_ORIENTADOR"],
    "keywords": ["DS_PALAVRA_CHAVE", "DS_PALAVRAS_CHAVE"],
    "abstract": ["DS_RESUMO"],
    "language": ["NM_IDIOMA", "DS_IDIOMA"],
    "full_text_url": ["DS_URL_TEXTO_COMPLETO", "NM_URL_TEXTO_COMPLETO"],
    "research_line": ["NM_LINHA_PESQUISA"],
    "concentration_area": ["NM_AREA_CONCENTRACAO"],
    "pages": ["NR_PAGINAS"],
}


def _abrir_csv(caminho: Path) -> tuple[csv.DictReader, Any]:
    """Abre o CSV em streaming, detectando codificação (utf-8 ou latin-1) e separador."""
    amostra = caminho.open("rb").read(200_000)
    try:
        amostra.decode("utf-8")
        enc = "utf-8-sig"
    except UnicodeDecodeError:
        enc = "latin-1"
    primeira = amostra.split(b"\n", 1)[0].decode(enc, errors="replace")
    sep = ";" if primeira.count(";") >= primeira.count(",") else ","
    f = caminho.open(newline="", encoding=enc, errors="replace")
    return csv.DictReader(f, delimiter=sep), f


def teses(http: ClienteHttp, ano_ini: int, ano_fim: int) -> dict[str, Any]:
    programas = {p["capes_code"]: p for p in ler_csv(DIR_PROCESSADOS / "graduate_programs.csv")}
    capes_para_uuid = {}
    if (DIR_IDS / "researcher.csv").exists():
        for lin in ler_csv(DIR_IDS / "researcher.csv"):
            if lin["chave"].startswith("capes_id_pessoa:"):
                capes_para_uuid[lin["chave"].split(":", 1)[1]] = lin["uuid"]
    alias = {a["alias_id"]: a["researcher_id"] for a in ler_csv(DIR_PROCESSADOS / "researcher_aliases.csv")} if (DIR_PROCESSADOS / "researcher_aliases.csv").exists() else {}

    arquivos = _arquivos(http, SLUG_TESES, ano_ini, ano_fim)
    locais = [(ano, http.baixar(u, DIR_BRUTOS / "capes" / u.rsplit("/", 1)[-1])) for ano, u in arquivos]

    ids = RegistroIds("thesis")
    saida: list[dict[str, Any]] = []
    lidas = 0
    colunas_usadas: dict[str, str | None] = {}
    c: dict[str, collections.Counter[Any]] = collections.defaultdict(collections.Counter)
    for ano, caminho in locais:
        leitor, f = _abrir_csv(caminho)
        with f:
            cab = leitor.fieldnames or []
            colunas_usadas = {k: next((x for x in v if x in cab), None) for k, v in COLUNAS.items()}
            pega = lambda lin, k: (lin.get(colunas_usadas[k]) or "").strip() if colunas_usadas[k] else ""  # noqa: E731
            for lin in leitor:
                lidas += 1
                p = programas.get(pega(lin, "program_code"))
                if not p:
                    continue
                pid_prod = pega(lin, "production_id")
                if not pid_prod:
                    continue
                orient = pega(lin, "advisor_capes_id")
                uuid_or = capes_para_uuid.get(orient, "")
                uuid_or = alias.get(uuid_or, uuid_or)
                tid = ids.obter([f"capes_producao:{pid_prod}"])
                saida.append(
                    {
                        "id": tid, "capes_production_id": pid_prod, "title": pega(lin, "title"), "degree": pega(lin, "degree"),
                        "year": pega(lin, "year") or ano, "defense_date": pega(lin, "defense_date")[:10], "program_id": p["id"],
                        "institution_id": p["institution_id"], "author_name": pega(lin, "author_name"), "author_capes_id": pega(lin, "author_capes_id"),
                        "advisor_name": pega(lin, "advisor_name"), "advisor_capes_id": orient, "advisor_researcher_id": uuid_or,
                        "keywords": pega(lin, "keywords"), "abstract": pega(lin, "abstract")[:4000], "language": pega(lin, "language"),
                        "full_text_url": pega(lin, "full_text_url"), "research_line": pega(lin, "research_line"),
                        "concentration_area": pega(lin, "concentration_area"), "pages": pega(lin, "pages"),
                    }
                )
                c["grau"][pega(lin, "degree")] += 1
                c["ano"][str(pega(lin, "year") or ano)] += 1
                c["uf"][p["uf"]] += 1
                c["area"][p["evaluation_area"]] += 1
                c["orientador"]["com_orientador_ligado" if uuid_or else "sem_orientador_ligado"] += 1
    ids.salvar()
    escrever_csv(DIR_PROCESSADOS / "theses.csv", saida, list(saida[0].keys()) if saida else ["id"])
    return {
        "anos": [a for a, _ in locais],
        "linhas_lidas_brasil": lidas,
        "teses_dissertacoes_recorte": len(saida),
        "por_grau": dict(c["grau"].most_common()),
        "por_ano": dict(sorted(c["ano"].items())),
        "por_uf": dict(c["uf"].most_common()),
        "por_area": dict(c["area"].most_common(10)),
        "orientador": dict(c["orientador"]),
        "orientadores_distintos": len({t["advisor_capes_id"] for t in saida if t["advisor_capes_id"]}),
        "colunas_usadas": colunas_usadas,
        "colunas_ausentes": [k for k, v in colunas_usadas.items() if not v],
    }


def faps_ne() -> dict[str, Any]:
    funders = ler_csv(DIR_PROCESSADOS / "funders.csv")
    work_f = ler_csv(DIR_PROCESSADOS / "work_funders.csv")
    por_funder = collections.Counter(w["funder_openalex_id"] for w in work_f)
    linhas: list[dict[str, Any]] = []
    for f in funders:
        nome = f["name"] or ""
        if not re.search(r"funda[cç][aã]o|amparo|apoio|fapes|facepe|funcap|fapitec|fapeal|fapern|fapesq|fapepi|fapema", nome, re.I):
            continue
        for uf, (sigla, padrao) in FAPS_NE.items():
            sigla_no_nome = re.search(rf"\b{sigla}\b", nome, re.I)
            fundacao_estadual = re.search(padrao, nome, re.I) and re.search(r"amparo|apoio", nome, re.I)
            if sigla_no_nome or fundacao_estadual:
                linhas.append({"funder_openalex_id": f["openalex_id"], "sigla": sigla, "uf": uf, "name": nome, "works_no_recorte": por_funder.get(f["openalex_id"], 0)})
                break
    escrever_csv(DIR_PROCESSADOS / "funders_ne.csv", linhas, ["funder_openalex_id", "sigla", "uf", "name", "works_no_recorte"])
    por_sigla: collections.Counter[str] = collections.Counter()
    for lin in linhas:
        por_sigla[lin["sigla"]] += int(lin["works_no_recorte"])
    nomes_uf = {u.sigla: u.nome for u in UFS_NORDESTE}
    return {
        "faps_identificadas": len(linhas),
        "faps_sem_correspondencia": [s for _, (s, _) in FAPS_NE.items() if s not in por_sigla],
        "works_por_fap": dict(por_sigla.most_common()),
        "detalhe": [{"sigla": x["sigla"], "uf": nomes_uf[x["uf"]], "openalex": x["funder_openalex_id"], "nome": x["name"], "works": x["works_no_recorte"]} for x in linhas],
        "works_com_alguma_fap_ne": len({w["work_id"] for w in work_f if w["funder_openalex_id"] in {x["funder_openalex_id"] for x in linhas}}),
    }


def sondar_ibict(cfg: Any) -> dict[str, Any]:
    """Uma única requisição leve por host, SEM retry, para saber se o bloqueio do firewall (D-011) expirou."""
    http = ClienteHttp(cfg, tentativas=1, timeout=20.0)
    out = {}
    for host in ("bdtd.ibict.br", "oasisbr.ibict.br"):
        try:
            r = http.get(f"https://{host}/vufind/api/v1/search", params={"lookfor": "*", "limit": 0}, cache=False)
            out[host] = {"status": r.status, "resultCount": (r.json().get("resultCount") if r.ok else None)}
        except Exception as e:  # noqa: BLE001
            out[host] = {"erro": f"{type(e).__name__}: {str(e)[:150]}"}
    http.fechar()
    return out


def executar() -> dict[str, Any]:
    cfg = carregar_config()
    http = ClienteHttp(cfg)
    try:
        s: dict[str, Any] = {"gerado_em": AGORA, "periodo": f"{cfg.year_start}-{cfg.year_end}"}
        s["teses"] = teses(http, cfg.year_start, cfg.year_end)
        s["faps"] = faps_ne()
        s["ibict"] = sondar_ibict(cfg)
    finally:
        http.fechar()
    _relatorio(s)
    return s


def _relatorio(s: dict[str, Any]) -> None:
    j = lambda x: json.dumps(x, ensure_ascii=False)  # noqa: E731
    t, f = s["teses"], s["faps"]
    L = [
        "# Parte 6 — Complementos (teses e orientações, FAPs do NE, BDTD/Oasisbr)", "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte6_complementos`. Período {s['periodo']}.", "",
        "## Teses e dissertações (CAPES, programas do recorte)", "",
        "| Item | Valor |", "|---|---|",
        f"| Anos-base | {t['anos']} |",
        f"| **Teses e dissertações do recorte** | **{t['teses_dissertacoes_recorte']}** (de {t['linhas_lidas_brasil']} no Brasil) |",
        f"| Orientadores distintos | {t['orientadores_distintos']} |",
        f"| Orientador ligado a um pesquisador | {j(t['orientador'])} |",
        f"| Colunas não encontradas no leiaute | {', '.join(t['colunas_ausentes']) or 'nenhuma'} |", "",
        f"Por grau: {j(t['por_grau'])}", "", f"Por ano: {j(t['por_ano'])}", "", f"Por UF: {j(t['por_uf'])}", "",
        f"Por área de avaliação (top 10): {j(t['por_area'])}", "",
        "## FAPs do Nordeste (financiadores declarados nos works do recorte)", "",
        f"FAPs identificadas: {f['faps_identificadas']} registros no OpenAlex; sem correspondência: {', '.join(f['faps_sem_correspondencia']) or 'nenhuma'}.", "",
        f"Works do recorte com alguma FAP do NE: {f['works_com_alguma_fap_ne']}", "",
        "| FAP | UF | Works no recorte | Registro OpenAlex |", "|---|---|---|---|",
    ]
    L += [f"| {d['sigla']} | {d['uf']} | {d['works']} | {d['nome']} ({d['openalex']}) |" for d in sorted(f["detalhe"], key=lambda d: -int(d["works"]))]
    L += ["", "## BDTD / Oasisbr (IBICT)", "", f"Sondagem única (D-011): {j(s['ibict'])}", ""]
    (DIR_RELATORIOS / "parte6_complementos.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte6_complementos.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar()
    print(json.dumps({"teses": s["teses"]["teses_dissertacoes_recorte"], "orientador": s["teses"]["orientador"], "faps": s["faps"]["works_por_fap"], "ibict": s["ibict"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
