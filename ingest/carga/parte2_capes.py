"""Parte 2 — Programas de pós-graduação e docentes (CAPES) do recorte, ligados às instituições.

Recorte: programas com SG_UF_PROGRAMA no Nordeste e área de avaliação de saúde/ciências biológicas
(ingest/diagnostico/recorte.py), anos-base dentro do período. Depende da Parte 1 (institutions).

Saídas (ingest/dados/processados/):
    graduate_programs.csv, program_faculty.csv, researchers_capes.csv, researcher_identifiers_capes.csv,
    institution_identifiers_capes.csv, institution_review_queue_capes.csv
e o relatório ingest/relatorios/parte2_capes.md.

Dados pessoais: CPF mascarado, ano de nascimento e faixa etária NÃO são gravados (SCHEME.md §13).

Uso:
    python -m ingest.carga.parte2_capes [--sem-cache] [-v]
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

from ..diagnostico.config import carregar_config
from ..diagnostico.contexto import Contexto
from ..diagnostico.fontes.capes import _anos_do_arquivo, _ler_pagina
from ..diagnostico.http import ClienteHttp, ErroHttp
from ..diagnostico.openalex import OpenAlex
from ..diagnostico.recorte import SIGLAS_NE, eh_area_capes, normalizar
from .comum import AGORA, DIR_BRUTOS, DIR_PROCESSADOS, DIR_RELATORIOS, RegistroIds, escrever_csv, ler_csv, similaridade

log = logging.getLogger("ingest.parte2")

SLUG_PROGRAMAS = "2021-a-2024-programas-da-pos-graduacao-stricto-sensu-no-brasil"
SLUG_DOCENTES = "2021-a-2024-docentes-da-pos-graduacao-stricto-sensu-no-brasil"
LICENCA = "CC-BY (CAPES Dados Abertos)"

# Colunas de docentes que não gravamos (dados pessoais desnecessários).
COLUNAS_DESCARTADAS = {"TP_DOCUMENTO_DOCENTE", "NR_DOCUMENTO_DOCENTE", "AN_NASCIMENTO_DOCENTE", "DS_FAIXA_ETARIA"}


def _arquivos(http: ClienteHttp, slug: str, ano_ini: int, ano_fim: int) -> list[tuple[int, str]]:
    ctx_pag = _ler_pagina(Contexto(cfg=http.cfg, http=http, oa=OpenAlex(http)), slug)
    saida = []
    for u in ctx_pag["downloads"]:
        if not u.lower().endswith(".csv"):
            continue
        anos = _anos_do_arquivo(u)
        if len(anos) == 1 and ano_ini <= anos[0] <= ano_fim:
            saida.append((anos[0], u))
    if not saida:
        raise ErroHttp(f"Nenhum CSV de {slug} entre {ano_ini} e {ano_fim}")
    return sorted(saida)


def _ler(caminho: Path) -> list[dict[str, str]]:
    bruto = caminho.read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    primeira = texto.split("\n", 1)[0]
    sep = ";" if primeira.count(";") >= primeira.count(",") else ","
    return list(csv.DictReader(texto.splitlines(), delimiter=sep))


def executar(sem_cache: bool = False) -> dict[str, Any]:
    cfg = carregar_config(usar_cache=not sem_cache)
    ano_ini, ano_fim = cfg.year_start, cfg.year_end
    inst_path = DIR_PROCESSADOS / "institutions.csv"
    if not inst_path.exists():
        raise SystemExit("Rode antes a Parte 1: python -m ingest.carga.parte1_instituicoes")
    instituicoes = ler_csv(inst_path)
    idents = ler_csv(DIR_PROCESSADOS / "institution_identifiers.csv")
    emec_para_inst = {i["value"]: i["institution_id"] for i in idents if i["scheme"] == "emec"}
    inst_por_id = {i["id"]: i for i in instituicoes}

    http = ClienteHttp(cfg)
    try:
        arq_prog = _arquivos(http, SLUG_PROGRAMAS, ano_ini, ano_fim)
        arq_doc = _arquivos(http, SLUG_DOCENTES, ano_ini, ano_fim)
        locais_prog = [(ano, http.baixar(u, DIR_BRUTOS / "capes" / u.rsplit("/", 1)[-1])) for ano, u in arq_prog]
        locais_doc = [(ano, http.baixar(u, DIR_BRUTOS / "capes" / u.rsplit("/", 1)[-1])) for ano, u in arq_doc]
    finally:
        http.fechar()

    # ------------------------------------------------------------------ programas
    ids_prog = RegistroIds("graduate_program")
    programas: dict[str, dict[str, Any]] = {}
    revisao: list[dict[str, Any]] = []
    ident_inst_capes: dict[tuple[str, str], dict[str, Any]] = {}
    sem_inst: set[str] = set()
    for ano, caminho in locais_prog:
        for lin in _ler(caminho):
            if lin.get("SG_UF_PROGRAMA") not in SIGLAS_NE or not eh_area_capes(lin.get("NM_AREA_AVALIACAO", "")):
                continue
            cod = lin["CD_PROGRAMA_IES"]
            p = programas.get(cod)
            if p is None:
                p = programas[cod] = {"id": ids_prog.obter([f"capes_programa:{cod}"]), "capes_code": cod, "base_years": set()}
            p["base_years"].add(ano)
            if ano >= max(p.get("_ano", 0), ano):  # mantém os dados do ano mais recente
                p.update(
                    {
                        "_ano": ano,
                        "name": lin.get("NM_PROGRAMA_IES", "").strip(),
                        "degree": lin.get("NM_GRAU_PROGRAMA", ""),
                        "modality": lin.get("NM_MODALIDADE_PROGRAMA", ""),
                        "evaluation_area": lin.get("NM_AREA_AVALIACAO", ""),
                        "evaluation_area_code": lin.get("CD_AREA_AVALIACAO", ""),
                        "major_area": lin.get("NM_GRANDE_AREA_CONHECIMENTO", ""),
                        "knowledge_area": lin.get("NM_AREA_CONHECIMENTO", ""),
                        "basic_area": lin.get("NM_AREA_BASICA", ""),
                        "grade": lin.get("CD_CONCEITO_PROGRAMA", ""),
                        "status": lin.get("DS_SITUACAO_PROGRAMA", ""),
                        "start_year": lin.get("AN_INICIO_PROGRAMA", ""),
                        "uf": lin.get("SG_UF_PROGRAMA", ""),
                        "municipality_name": lin.get("NM_MUNICIPIO_PROGRAMA_IES", ""),
                        "capes_entity_code": lin.get("CD_ENTIDADE_CAPES", ""),
                        "emec_code": lin.get("CD_ENTIDADE_EMEC", ""),
                        "entity_acronym": lin.get("SG_ENTIDADE_ENSINO", ""),
                        "entity_name": lin.get("NM_ENTIDADE_ENSINO", ""),
                        "legal_nature_capes": lin.get("DS_DEPENDENCIA_ADMINISTRATIVA", ""),
                        "network_program": lin.get("IN_REDE", ""),
                    }
                )

    # Ligação programa -> instituição: e-MEC (identificador comum) ou nome exato na mesma UF; senão, revisão.
    nomes_por_uf: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for i in instituicoes:
        nomes_por_uf[i["uf"]].append(i)
    for p in programas.values():
        emec = str(int(p["emec_code"])) if (p.get("emec_code") or "").strip().isdigit() and int(p["emec_code"]) > 0 else ""
        iid = emec_para_inst.get(emec) if emec else None
        metodo = "emec" if iid else ""
        if not iid:
            alvo = normalizar(p["entity_name"])
            exatos = [i for i in nomes_por_uf[p["uf"]] if alvo in (normalizar(i["name"]), normalizar(i.get("name_ror", "")))]
            if len(exatos) == 1:
                iid, metodo = exatos[0]["id"], "nome_exato_uf"
            else:
                cands = sorted(
                    ((max(similaridade(p["entity_name"], i["name"]), similaridade(p["entity_name"], i.get("name_ror") or "")), i) for i in nomes_por_uf[p["uf"]]),
                    key=lambda x: -x[0],
                )
                if cands and cands[0][0] >= 0.5:
                    revisao.append(
                        {
                            "entity": "institution",
                            "candidate_a": f"capes_entidade:{p['capes_entity_code']}",
                            "candidate_b": f"institution:{cands[0][1]['id']}",
                            "score": round(cands[0][0], 3),
                            "evidence": json.dumps({"capes_nome": p["entity_name"], "capes_sigla": p["entity_acronym"], "instituicao": cands[0][1]["name"], "uf": p["uf"]}, ensure_ascii=False),
                            "status": "pendente",
                            "created_at": AGORA,
                        }
                    )
                sem_inst.add(f"{p['entity_acronym']} — {p['entity_name']} ({p['uf']}, e-MEC {p.get('emec_code') or '—'})")
        p["institution_id"] = iid or ""
        p["institution_link_method"] = metodo
        if iid and p.get("capes_entity_code"):
            ident_inst_capes[(iid, p["capes_entity_code"])] = {
                "institution_id": iid,
                "scheme": "capes_entidade",
                "value": p["capes_entity_code"],
                "source": f"capes_programas_{ano_ini}-{ano_fim}+{metodo}",
                "confidence": 1.0 if metodo == "emec" else 0.9,
                "verified_at": AGORA,
            }
        if not inst_por_id.get(iid or "", {}).get("legal_nature") and p.get("legal_nature_capes"):
            p["_natureza_sugerida"] = p["legal_nature_capes"]
    ids_prog.salvar()

    # ------------------------------------------------------------------- docentes
    ids_pesq = RegistroIds("researcher")
    vinculos: list[dict[str, Any]] = []
    pessoas: dict[str, dict[str, Any]] = {}
    linhas_lidas = 0
    colunas_vistas: list[str] = []
    for ano, caminho in locais_doc:
        linhas = _ler(caminho)
        linhas_lidas += len(linhas)
        colunas_vistas = list(linhas[0].keys()) if linhas else colunas_vistas
        for lin in linhas:
            p = programas.get(lin.get("CD_PROGRAMA_IES", ""))
            if p is None:
                continue
            pid = (lin.get("ID_PESSOA") or "").strip()
            if not pid:
                continue
            rid = ids_pesq.obter([f"capes_id_pessoa:{pid}"])
            vinculos.append(
                {
                    "program_id": p["id"],
                    "researcher_id": rid,
                    "capes_id_pessoa": pid,
                    "base_year": ano,
                    "category": lin.get("DS_CATEGORIA_DOCENTE", ""),
                    "bond_type": lin.get("DS_TIPO_VINCULO_DOCENTE_IES", ""),
                    "work_regime": lin.get("DS_REGIME_TRABALHO", ""),
                    "pq_category": "" if lin.get("CD_CAT_BOLSA_PRODUTIVIDADE") in ("NA", "", None) else lin["CD_CAT_BOLSA_PRODUTIVIDADE"],
                    "is_doctor": lin.get("IN_DOUTOR") == "S",
                    "degree_year": lin.get("AN_TITULACAO", ""),
                    "degree_level": lin.get("NM_GRAU_TITULACAO", ""),
                    "degree_area": lin.get("NM_AREA_BASICA_TITULACAO", ""),
                    "degree_institution": lin.get("SG_IES_TITULACAO", "") or lin.get("NM_IES_TITULACAO", ""),
                    "degree_country": lin.get("NM_PAIS_IES_TITULACAO", ""),
                }
            )
            pe = pessoas.setdefault(pid, {"id": rid, "capes_id_pessoa": pid, "programs": set(), "institutions": set(), "years": set(), "pq": {}})
            nome = (lin.get("NM_DOCENTE") or "").strip()
            if ano >= max(pe["years"], default=0):
                pe["display_name"] = nome
            pe["programs"].add(p["capes_code"])
            if p["institution_id"]:
                pe["institutions"].add(p["institution_id"])
            pe["years"].add(ano)
            if vinculos[-1]["pq_category"]:
                pe["pq"][ano] = vinculos[-1]["pq_category"]
    ids_pesq.salvar()
    descartadas = sorted(COLUNAS_DESCARTADAS & set(colunas_vistas))

    # contagem de docentes por programa no ano mais recente
    ultimo_ano = max(ano for ano, _ in locais_doc)
    doc_por_prog = collections.Counter(v["program_id"] for v in vinculos if v["base_year"] == ultimo_ano)
    for p in programas.values():
        p["faculty_count_last_year"] = doc_por_prog.get(p["id"], 0)
        p["base_years"] = sorted(p["base_years"])

    pesquisadores = []
    for pe in pessoas.values():
        pq = pe["pq"][max(pe["pq"])] if pe["pq"] else ""
        pesquisadores.append(
            {
                "id": pe["id"],
                "display_name": pe["display_name"].title() if pe["display_name"].isupper() else pe["display_name"],
                "normalized_name": normalizar(pe["display_name"]),
                "capes_id_pessoa": pe["capes_id_pessoa"],
                "programs": sorted(pe["programs"]),
                "institution_ids": sorted(pe["institutions"]),
                "base_years": sorted(pe["years"]),
                "pq_category_latest": pq,
                "source": "capes_docentes",
                "updated_at": AGORA,
            }
        )
    identificadores_pesq = [
        {"researcher_id": pe["id"], "scheme": "capes_id_pessoa", "value": pe["capes_id_pessoa"], "source": f"capes_docentes_{ano_ini}-{ano_fim}", "confidence": 1.0, "verified_at": AGORA}
        for pe in pessoas.values()
    ]

    # -------------------------------------------------------------------- saídas
    campos_prog = [
        "id", "capes_code", "name", "degree", "modality", "evaluation_area", "evaluation_area_code", "major_area", "knowledge_area",
        "basic_area", "grade", "status", "start_year", "uf", "municipality_name", "institution_id", "institution_link_method",
        "capes_entity_code", "emec_code", "entity_acronym", "entity_name", "legal_nature_capes", "network_program", "base_years",
        "faculty_count_last_year",
    ]
    escrever_csv(DIR_PROCESSADOS / "graduate_programs.csv", sorted(programas.values(), key=lambda p: p["capes_code"]), campos_prog)
    escrever_csv(
        DIR_PROCESSADOS / "program_faculty.csv",
        vinculos,
        ["program_id", "researcher_id", "capes_id_pessoa", "base_year", "category", "bond_type", "work_regime", "pq_category", "is_doctor",
         "degree_year", "degree_level", "degree_area", "degree_institution", "degree_country"],
    )
    escrever_csv(DIR_PROCESSADOS / "researchers_capes.csv", pesquisadores, ["id", "display_name", "normalized_name", "capes_id_pessoa", "programs", "institution_ids", "base_years", "pq_category_latest", "source", "updated_at"])
    escrever_csv(DIR_PROCESSADOS / "researcher_identifiers_capes.csv", identificadores_pesq, ["researcher_id", "scheme", "value", "source", "confidence", "verified_at"])
    escrever_csv(DIR_PROCESSADOS / "institution_identifiers_capes.csv", ident_inst_capes.values(), ["institution_id", "scheme", "value", "source", "confidence", "verified_at"])
    escrever_csv(DIR_PROCESSADOS / "institution_review_queue_capes.csv", revisao, ["entity", "candidate_a", "candidate_b", "score", "evidence", "status", "created_at"])

    progs_ultimo = [p for p in programas.values() if ultimo_ano in p["base_years"]]
    stats = {
        "gerado_em": AGORA,
        "periodo": f"{ano_ini}-{ano_fim}",
        "anos_programas": [a for a, _ in locais_prog],
        "anos_docentes": [a for a, _ in locais_doc],
        "licenca": LICENCA,
        "programas_distintos": len(programas),
        "programas_ultimo_ano": len(progs_ultimo),
        "programas_por_uf": dict(collections.Counter(p["uf"] for p in progs_ultimo).most_common()),
        "programas_por_area": dict(collections.Counter(p["evaluation_area"] for p in progs_ultimo).most_common()),
        "programas_por_grau": dict(collections.Counter(p["degree"] for p in progs_ultimo).most_common()),
        "programas_por_conceito": dict(sorted(collections.Counter(p["grade"] for p in progs_ultimo).items())),
        "programas_ligados_a_instituicao": dict(collections.Counter(p["institution_link_method"] or "sem_vinculo" for p in programas.values())),
        "entidades_sem_instituicao": sorted(sem_inst),
        "fila_revisao": len(revisao),
        "linhas_docentes_lidas_brasil": linhas_lidas,
        "vinculos_docente_programa_ano": len(vinculos),
        "docentes_distintos": len(pessoas),
        "docentes_ultimo_ano": len({v["capes_id_pessoa"] for v in vinculos if v["base_year"] == ultimo_ano}),
        "docentes_por_categoria_ultimo_ano": dict(collections.Counter(v["category"] for v in vinculos if v["base_year"] == ultimo_ano).most_common()),
        "docentes_com_bolsa_pq_ultimo_ano": len({v["capes_id_pessoa"] for v in vinculos if v["base_year"] == ultimo_ano and v["pq_category"]}),
        "docentes_em_mais_de_um_programa": sum(1 for pe in pessoas.values() if len(pe["programs"]) > 1),
        "colunas_pessoais_descartadas": descartadas,
        "conflitos_ids": ids_pesq.conflitos + ids_prog.conflitos,
        "top_programas_docentes": [
            {"programa": p["name"], "ies": p["entity_acronym"], "uf": p["uf"], "conceito": p["grade"], "docentes": p["faculty_count_last_year"]}
            for p in sorted(progs_ultimo, key=lambda p: -p["faculty_count_last_year"])[:15]
        ],
    }
    _relatorio(stats)
    return stats


def _relatorio(s: dict[str, Any]) -> None:
    j = lambda x: json.dumps(x, ensure_ascii=False)  # noqa: E731
    L = [
        "# Parte 2 — Programas de pós-graduação e docentes (CAPES), recorte Ciência Nordeste",
        "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte2_capes`. Período {s['periodo']}; anos-base disponíveis: "
        f"programas {s['anos_programas']}, docentes {s['anos_docentes']}. Licença: {s['licenca']}.",
        "",
        "## Resumo",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Programas distintos no recorte (todos os anos) | {s['programas_distintos']} |",
        f"| Programas no último ano-base | {s['programas_ultimo_ano']} |",
        f"| Ligação programa → instituição | {j(s['programas_ligados_a_instituicao'])} |",
        f"| Pares para revisão (entidade CAPES × instituição) | {s['fila_revisao']} |",
        f"| Docentes distintos (ID_PESSOA) | {s['docentes_distintos']} |",
        f"| Docentes no último ano-base | {s['docentes_ultimo_ano']} |",
        f"| ...com bolsa de produtividade (PQ/DT) | {s['docentes_com_bolsa_pq_ultimo_ano']} |",
        f"| Docentes em mais de um programa | {s['docentes_em_mais_de_um_programa']} |",
        f"| Vínculos docente × programa × ano | {s['vinculos_docente_programa_ano']} (de {s['linhas_docentes_lidas_brasil']} linhas lidas no Brasil) |",
        f"| Colunas pessoais descartadas | {', '.join(s['colunas_pessoais_descartadas'])} |",
        "",
        f"Programas por UF: {j(s['programas_por_uf'])}",
        "",
        f"Por área de avaliação: {j(s['programas_por_area'])}",
        "",
        f"Por grau: {j(s['programas_por_grau'])}",
        "",
        f"Por conceito: {j(s['programas_por_conceito'])}",
        "",
        f"Vínculos docente × programa por categoria (último ano; um docente pode ter vários): {j(s['docentes_por_categoria_ultimo_ano'])}",
        "",
        "## Programas com mais docentes (último ano-base)",
        "",
        "| Programa | IES | UF | Conceito | Docentes |",
        "|---|---|---|---|---|",
    ]
    L += [f"| {t['programa']} | {t['ies']} | {t['uf']} | {t['conceito']} | {t['docentes']} |" for t in s["top_programas_docentes"]]
    if s["entidades_sem_instituicao"]:
        L += ["", "## Entidades CAPES sem instituição correspondente (conferir / incluir na Parte 1)", ""]
        L += [f"- {e}" for e in s["entidades_sem_instituicao"]]
    if s["conflitos_ids"]:
        L += ["", "## Conflitos no registro de IDs", "", f"```\n{json.dumps(s['conflitos_ids'], ensure_ascii=False)}\n```"]
    L += [
        "",
        "## Arquivos",
        "",
        "`ingest/dados/processados/`: graduate_programs.csv, program_faculty.csv, researchers_capes.csv, researcher_identifiers_capes.csv, "
        "institution_identifiers_capes.csv, institution_review_queue_capes.csv. Registros de UUID: `ingest/dados/ids/graduate_program.csv`, "
        "`ingest/dados/ids/researcher.csv`. Brutos: `ingest/dados/brutos/capes/`.",
    ]
    (DIR_RELATORIOS / "parte2_capes.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte2_capes.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-cache", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar(sem_cache=a.sem_cache)
    print(json.dumps({k: s[k] for k in ("programas_distintos", "programas_ultimo_ano", "programas_ligados_a_instituicao", "docentes_distintos", "docentes_ultimo_ano", "fila_revisao")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
