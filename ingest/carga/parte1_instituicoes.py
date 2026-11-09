"""Parte 1 — Instituições do Nordeste.

Unifica ROR (lista canônica por UF) + OpenAlex + INEP (cadastro de IES, código e-MEC) + IBGE
(municípios e coordenadas), com cruzamento ROR ↔ e-MEC pelo Wikidata (P6782 × P5148).

Saídas (ingest/dados/processados/):
    municipalities.csv, institutions.csv, institution_identifiers.csv, institution_relations.csv,
    institution_review_queue.csv, openalex_institution_ids_ne.txt
e o relatório ingest/relatorios/parte1_instituicoes.md.

Uso:
    python -m ingest.carga.parte1_instituicoes [--sem-cache] [-v]
"""

from __future__ import annotations

import argparse
import base64
import binascii
import collections
import csv
import io
import json
import logging
import re
import sys
import zipfile
from dataclasses import dataclass, field
from typing import Any

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp, ErroHttp
from ..diagnostico.openalex import OpenAlex
from ..diagnostico.recorte import CODIGOS_IBGE_NE, SIGLAS_NE, UFS_NORDESTE, filtro_openalex_regioes, normalizar
from .comum import (
    AGORA,
    DIR_PROCESSADOS,
    DIR_RELATORIOS,
    RegistroIds,
    distancia_km,
    escrever_csv,
    similaridade,
    valores_ror,
    valores_ror_por_idioma,
)

log = logging.getLogger("ingest.parte1")

ROR_CONCEPT_DOI = "https://doi.org/10.5281/zenodo.6347574"
URL_MUNICIPIOS_COORD = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
URL_INEP = "https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_{ano}.zip"
WDQS = "https://query.wikidata.org/sparql"

CATEGORIA_INEP = {
    "1": ("publica", "Pública Federal"),
    "2": ("publica", "Pública Estadual"),
    "3": ("publica", "Pública Municipal"),
    "4": ("privada", "Privada com fins lucrativos"),
    "5": ("privada", "Privada sem fins lucrativos"),
    "6": ("privada", "Privada - Particular em sentido estrito"),
    "7": ("especial", "Especial"),
    "8": ("privada", "Privada comunitária"),
    "9": ("privada", "Privada confessional"),
}
ORGANIZACAO_INEP = {
    "1": ("universidade", "Universidade"),
    "2": ("centro_universitario", "Centro Universitário"),
    "3": ("faculdade", "Faculdade"),
    "4": ("instituto_federal", "Instituto Federal de Educação, Ciência e Tecnologia"),
    "5": ("cefet", "Centro Federal de Educação Tecnológica"),
}
TIPO_ROR = {
    "education": "ensino",
    "healthcare": "hospital_saude",
    "facility": "instituto_pesquisa",
    "government": "governo",
    "company": "empresa",
    "nonprofit": "organizacao_sem_fins_lucrativos",
    "funder": "financiador",
    "archive": "arquivo",
    "other": "outro",
}
UF_POR_SIGLA = {u.sigla: u for u in UFS_NORDESTE}


@dataclass
class OrgRor:
    ror: str  # sufixo, ex.: 020jkns84
    nome: str
    nome_pt: str | None
    nomes: list[str]
    siglas: list[str]
    tipos: list[str]
    status: str
    cidade: str
    uf: str
    lat: float | None
    lng: float | None
    geonames_id: str
    ids_externos: dict[str, list[str]]
    relacoes: list[tuple[str, str]]
    fundada: str
    site: str
    openalex: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- fontes


def carregar_ror(http: ClienteHttp) -> tuple[dict[str, OrgRor], str]:
    resp = http.get(ROR_CONCEPT_DOI)
    m = re.search(r"/records/(\d+)", resp.url_final or "")
    if not m:
        raise ErroHttp("Registro do ROR no Zenodo não encontrado")
    exp = http.get_json(f"https://zenodo.org/records/{m.group(1)}/export/json")
    nome_zip = next(k for k in exp["files"]["entries"] if k.endswith(".zip"))
    z = http.get(f"https://zenodo.org/records/{m.group(1)}/files/{nome_zip}?download=1")
    zf = zipfile.ZipFile(io.BytesIO(z.corpo))
    texto = zf.read(next(n for n in zf.namelist() if n.endswith(".csv"))).decode("utf-8")
    orgs: dict[str, OrgRor] = {}
    for lin in csv.DictReader(io.StringIO(texto)):
        if "BR" not in (lin["locations.geonames_details.country_code"] or "").split(";"):
            continue
        uf = (lin["locations.geonames_details.country_subdivision_code"] or "").split(";")[0].strip()
        rid = lin["id"].rsplit("/", 1)[-1]
        rotulos = valores_ror_por_idioma(lin["names.types.label"])
        nomes = list(dict.fromkeys([lin["names.types.ror_display"]] + valores_ror(lin["names.types.label"]) + valores_ror(lin["names.types.alias"])))
        rel = []
        for parte in (lin["relationships"] or "").split(";"):
            mm = re.match(r"^\s*([a-z]+):\s*(\S+)", parte)
            if mm:
                rel.append((mm.group(1), mm.group(2).rsplit("/", 1)[-1]))
        ext = {
            esquema: [v.strip() for v in (lin.get(f"external_ids.type.{esquema}.all") or "").split(";") if v.strip()]
            for esquema in ("wikidata", "isni", "grid", "fundref")
        }
        lat = lin["locations.geonames_details.lat"].split(";")[0]
        lng = lin["locations.geonames_details.lng"].split(";")[0]
        orgs[rid] = OrgRor(
            ror=rid,
            nome=lin["names.types.ror_display"],
            nome_pt=(rotulos.get("pt") or [""])[0] or None,
            nomes=nomes,
            siglas=valores_ror(lin["names.types.acronym"]),
            tipos=[t.strip() for t in (lin["types"] or "").split(";") if t.strip()],
            status=lin["status"],
            cidade=lin["locations.geonames_details.name"].split(";")[0],
            uf=uf,
            lat=float(lat) if lat else None,
            lng=float(lng) if lng else None,
            geonames_id=lin["locations.geonames_id"].split(";")[0],
            ids_externos=ext,
            relacoes=rel,
            fundada=lin["established"],
            site=(lin["links.type.website"] or "").split(";")[0].strip(),
        )
    log.info("ROR: %d organizações BR, %d no NE (%s)", len(orgs), sum(1 for o in orgs.values() if o.uf in SIGLAS_NE), nome_zip)
    return orgs, nome_zip


def carregar_openalex(oa: OpenAlex, rors: list[str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Instituições OpenAlex das organizações NE do ROR, e as do filtro geo.region NE (para achar extras)."""
    campos = "id,ror,display_name,type,works_count,cited_by_count,geo,ids"
    por_ror: dict[str, dict[str, Any]] = {}
    for i in range(0, len(rors), 100):
        d = oa.consultar("institutions", filter="ror:" + "|".join(rors[i : i + 100]), per_page=100, select=campos)
        for inst in d.get("results", []):
            if inst.get("ror"):
                por_ror[inst["ror"].rsplit("/", 1)[-1]] = inst
    por_regiao: list[dict[str, Any]] = []
    filtro = f"country_code:BR,{filtro_openalex_regioes('geo.region')}"
    pagina = 1
    while True:
        d = oa.consultar("institutions", filter=filtro, per_page=100, page=pagina, select=campos)
        por_regiao.extend(d.get("results", []))
        if len(d.get("results", [])) < 100:
            break
        pagina += 1
    return por_ror, por_regiao


def carregar_inep(http: ClienteHttp, ano_final: int) -> tuple[list[dict[str, str]], int]:
    for ano in range(ano_final, ano_final - 4, -1):
        url = URL_INEP.format(ano=ano)
        try:
            entradas = http.listar_zip(url)
        except Exception as e:  # noqa: BLE001
            log.info("INEP %d indisponível: %s", ano, e)
            continue
        ies = next(e for e in entradas if re.search(r"IES.*\.csv$", e["nome"], re.I))
        linhas = list(csv.DictReader(io.StringIO(http.arquivo_inteiro_do_zip(url, ies).decode("latin-1")), delimiter=";"))
        ne = [lin for lin in linhas if lin.get("SG_UF_IES") in SIGLAS_NE]
        log.info("INEP %d: %d IES no NE (de %d)", ano, len(ne), len(linhas))
        return ne, ano
    raise ErroHttp("Nenhum ano do Censo da Educação Superior disponível")


def carregar_municipios(http: ClienteHttp) -> dict[int, dict[str, Any]]:
    resp = http.get(URL_MUNICIPIOS_COORD)
    munis: dict[int, dict[str, Any]] = {}
    for lin in csv.DictReader(io.StringIO(resp.texto())):
        cod = int(lin["codigo_ibge"])
        if int(lin["codigo_uf"]) not in CODIGOS_IBGE_NE:
            continue
        uf = next(u.sigla for u in UFS_NORDESTE if u.codigo_ibge == int(lin["codigo_uf"]))
        munis[cod] = {
            "ibge_code": cod,
            "name": lin["nome"],
            "uf": uf,
            "latitude": float(lin["latitude"]),
            "longitude": float(lin["longitude"]),
            "is_capital": lin["capital"] == "1",
        }
    # Confere com a API oficial do IBGE (nomes e quantidade)
    try:
        oficiais = {int(m["id"]): m["nome"] for m in http.get_json("https://servicodados.ibge.gov.br/api/v1/localidades/municipios") if int(str(m["id"])[:2]) in CODIGOS_IBGE_NE}
        faltando = set(oficiais) - set(munis)
        if faltando:
            log.warning("%d municípios do IBGE sem coordenadas no CSV derivado: %s", len(faltando), sorted(faltando)[:10])
            for cod in faltando:
                uf = next(u.sigla for u in UFS_NORDESTE if u.codigo_ibge == cod // 100000)
                munis[cod] = {"ibge_code": cod, "name": oficiais[cod], "uf": uf, "latitude": None, "longitude": None, "is_capital": False}
        for cod, nome in oficiais.items():
            munis[cod]["name"] = nome  # nome oficial prevalece
    except Exception as e:  # noqa: BLE001
        log.warning("Não deu para conferir com a API do IBGE: %s", e)
    log.info("Municípios do NE: %d", len(munis))
    return munis


def _decodificar_emec(valor: str) -> str | None:
    """A P5148 do Wikidata guarda o código e-MEC em base64 (como nas URLs do e-MEC): 'NTg2' -> '586'."""
    v = valor.strip()
    if v.isdigit():
        return str(int(v))
    try:
        dec = base64.b64decode(v + "=" * (-len(v) % 4), validate=True).decode("ascii")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    return str(int(dec)) if dec.isdigit() else None


def carregar_crosswalk_wikidata(http: ClienteHttp) -> dict[str, set[str]]:
    """ROR -> códigos e-MEC (Wikidata P6782 × P5148)."""
    consulta = "SELECT ?ror ?emec WHERE { ?item wdt:P6782 ?ror ; wdt:P5148 ?emec . }"
    resp = http.get(WDQS, params={"query": consulta, "format": "json"}, cabecalhos={"Accept": "application/sparql-results+json"})
    if not resp.ok:
        raise ErroHttp(f"WDQS HTTP {resp.status}")
    mapa: dict[str, set[str]] = collections.defaultdict(set)
    for b in resp.json()["results"]["bindings"]:
        emec = _decodificar_emec(b["emec"]["value"])
        if emec:
            mapa[b["ror"]["value"].strip()].add(emec)
    log.info("Wikidata: %d organizações com ROR e e-MEC", len(mapa))
    return mapa


# ------------------------------------------------------------------------- cruzamentos


def municipio_por_nome(munis: dict[int, dict[str, Any]], nome: str, uf: str) -> int | None:
    alvo = normalizar(nome)
    for cod, m in munis.items():
        if m["uf"] == uf and normalizar(m["name"]) == alvo:
            return cod
    return None


def municipio_mais_proximo(munis: dict[int, dict[str, Any]], lat: float, lng: float, uf: str) -> tuple[int, float] | None:
    cand = [(distancia_km(lat, lng, m["latitude"], m["longitude"]), cod) for cod, m in munis.items() if m["uf"] == uf and m["latitude"] is not None]
    if not cand:
        return None
    d, cod = min(cand)
    return cod, d


@dataclass
class Vinculo:
    emec: str
    ror: str
    confianca: float
    metodo: str
    evidencia: dict[str, Any]


def cruzar_inep_ror(
    inep: list[dict[str, str]], orgs_ne: dict[str, OrgRor], crosswalk: dict[str, set[str]], munis: dict[int, dict[str, Any]]
) -> tuple[list[Vinculo], list[dict[str, Any]]]:
    vinculos: list[Vinculo] = []
    revisao: list[dict[str, Any]] = []
    emec_para_ror: dict[str, str] = {}
    for rid, emecs in crosswalk.items():
        if rid in orgs_ne:
            for e in emecs:
                emec_para_ror[e] = rid
    ror_ja_ligado: dict[str, str] = {}
    por_uf: dict[str, list[OrgRor]] = collections.defaultdict(list)
    for o in orgs_ne.values():
        por_uf[o.uf].append(o)

    # 1) Identificador comum (Wikidata)
    pendentes = []
    for lin in inep:
        emec = str(int(lin["CO_IES"]))
        if emec in emec_para_ror:
            rid = emec_para_ror[emec]
            vinculos.append(Vinculo(emec, rid, 1.0, "wikidata_P6782_P5148", {"inep": lin["NO_IES"], "ror": orgs_ne[rid].nome}))
            ror_ja_ligado[rid] = emec
        else:
            pendentes.append(lin)

    # 2) Nome/sigla + município (auto só quando forte e sem ambiguidade); 3) fila de revisão
    for lin in pendentes:
        emec = str(int(lin["CO_IES"]))
        uf = lin["SG_UF_IES"]
        cidade_inep = normalizar(lin.get("NO_MUNICIPIO_IES", ""))
        sigla_inep = normalizar(lin.get("SG_IES", ""))
        melhores = []
        for o in por_uf.get(uf, []):
            sim = max((similaridade(lin["NO_IES"], n) for n in o.nomes), default=0.0)
            nome_igual = any(normalizar(lin["NO_IES"]) == normalizar(n) for n in o.nomes)
            sigla_igual = bool(sigla_inep) and any(sigla_inep == normalizar(s) for s in o.siglas)
            mesma_cidade = normalizar(o.cidade) == cidade_inep
            score = sim + (0.3 if sigla_igual else 0) + (0.1 if mesma_cidade else 0)
            if sim >= 0.5 or sigla_igual or nome_igual:
                melhores.append((score, o, sim, nome_igual, sigla_igual, mesma_cidade))
        if not melhores:
            continue
        melhores.sort(key=lambda x: -x[0])
        score, o, sim, nome_igual, sigla_igual, mesma_cidade = melhores[0]
        ambiguo = len(melhores) > 1 and melhores[1][0] >= score - 0.05
        evid = {
            "inep_nome": lin["NO_IES"], "inep_sigla": lin.get("SG_IES"), "inep_municipio": lin.get("NO_MUNICIPIO_IES"),
            "ror_nome": o.nome, "ror_siglas": o.siglas, "ror_cidade": o.cidade, "similaridade_nome": round(sim, 3),
            "nome_igual": nome_igual, "sigla_igual": sigla_igual, "mesma_cidade": mesma_cidade, "candidatos": len(melhores),
        }
        forte = mesma_cidade and (nome_igual or (sigla_igual and sim >= 0.5))
        if forte and not ambiguo and o.ror not in ror_ja_ligado:
            vinculos.append(Vinculo(emec, o.ror, 0.9, "nome_sigla_municipio", evid))
            ror_ja_ligado[o.ror] = emec
        else:
            revisao.append(
                {
                    "entity": "institution",
                    "candidate_a": f"emec:{emec}",
                    "candidate_b": f"ror:{o.ror}",
                    "score": round(min(score, 1.0), 3),
                    "evidence": json.dumps(evid, ensure_ascii=False),
                    "status": "pendente",
                    "created_at": AGORA,
                }
            )
    return vinculos, revisao


# ------------------------------------------------------------------------------- main


def executar(sem_cache: bool = False) -> dict[str, Any]:
    cfg = carregar_config(usar_cache=not sem_cache)
    http = ClienteHttp(cfg)
    oa = OpenAlex(http)
    try:
        orgs_br, versao_ror = carregar_ror(http)
        orgs_ne = {k: o for k, o in orgs_br.items() if o.uf in SIGLAS_NE}
        oa_por_ror, oa_regiao = carregar_openalex(oa, sorted(orgs_ne))
        extras = []
        for inst in oa_regiao:
            rid = (inst.get("ror") or "").rsplit("/", 1)[-1]
            if rid and rid not in orgs_ne and rid in orgs_br:
                # OpenAlex diz NE e o ROR não tem (ou tem outra) UF: inclui e registra
                extras.append(rid)
                orgs_ne[rid] = orgs_br[rid]
                oa_por_ror[rid] = inst
        for rid, o in orgs_ne.items():
            o.openalex = oa_por_ror.get(rid, {})
        inep, ano_inep = carregar_inep(http, cfg.year_end)
        munis = carregar_municipios(http)
        try:
            crosswalk = carregar_crosswalk_wikidata(http)
        except Exception as e:  # noqa: BLE001
            log.warning("Crosswalk do Wikidata indisponível: %s", e)
            crosswalk = {}
    finally:
        http.fechar()

    vinculos, revisao = cruzar_inep_ror(inep, orgs_ne, crosswalk, munis)
    ror_para_vinc = {v.ror: v for v in vinculos}
    emec_vinculados = {v.emec for v in vinculos}
    ids = RegistroIds("institution")

    instituicoes: list[dict[str, Any]] = []
    identificadores: list[dict[str, Any]] = []
    relacoes_brutas: list[tuple[str, str, str]] = []
    ror_para_uuid: dict[str, str] = {}
    inep_por_emec = {str(int(lin["CO_IES"])): lin for lin in inep}

    def add_id(iid: str, esquema: str, valor: str, fonte: str, conf: float = 1.0) -> None:
        if valor:
            identificadores.append({"institution_id": iid, "scheme": esquema, "value": valor, "source": fonte, "confidence": conf, "verified_at": AGORA})

    for rid, o in sorted(orgs_ne.items()):
        oa_inst = o.openalex
        oa_id = (oa_inst.get("id") or "").rsplit("/", 1)[-1]
        v = ror_para_vinc.get(rid)
        lin = inep_por_emec.get(v.emec) if v else None
        chaves = [f"ror:{rid}", f"openalex:{oa_id}" if oa_id else "", f"emec:{v.emec}" if v and v.confianca >= 1.0 else ""]
        iid = ids.obter(chaves)
        ror_para_uuid[rid] = iid
        # município
        mun = int(lin["CO_MUNICIPIO_IES"]) if lin and lin.get("CO_MUNICIPIO_IES") else municipio_por_nome(munis, o.cidade, o.uf)
        mun_fonte = "inep" if lin else ("ror_nome_cidade" if mun else None)
        if mun is None and o.lat is not None:
            prox = municipio_mais_proximo(munis, o.lat, o.lng or 0.0, o.uf)
            if prox:
                mun, mun_fonte = prox[0], f"ror_mais_proximo_{prox[1]:.0f}km"
        lat, lng, geo_fonte = (o.lat, o.lng, "ror_geonames") if o.lat is not None else (
            (munis[mun]["latitude"], munis[mun]["longitude"], "sede_municipio") if mun in munis else (None, None, None)
        )
        cat = CATEGORIA_INEP.get(lin.get("TP_CATEGORIA_ADMINISTRATIVA", "")) if lin else None
        org = ORGANIZACAO_INEP.get(lin.get("TP_ORGANIZACAO_ACADEMICA", "")) if lin else None
        kind = org[0] if org else TIPO_ROR.get(o.tipos[0], "outro") if o.tipos else "outro"
        instituicoes.append(
            {
                "id": iid,
                "name": o.nome_pt or o.nome,
                "name_ror": o.nome,
                "acronym": (lin.get("SG_IES") if lin else None) or (o.siglas[0] if o.siglas else ""),
                "kind": kind,
                "ror_types": o.tipos,
                "legal_nature": cat[0] if cat else "",
                "admin_category": cat[1] if cat else "",
                "academic_org": org[1] if org else "",
                "uf": o.uf,
                "municipality_ibge": mun or "",
                "municipality_source": mun_fonte or "",
                "latitude": lat if lat is not None else "",
                "longitude": lng if lng is not None else "",
                "geo_source": geo_fonte or "",
                "is_active": o.status == "active",
                "established": o.fundada,
                "website": o.site,
                "works_count_openalex": oa_inst.get("works_count", ""),
                "openalex_has_ne_region": (oa_inst.get("geo") or {}).get("region") in {u.nome for u in UFS_NORDESTE},
                "sources": ["ror"] + (["openalex"] if oa_id else []) + (["inep"] if lin else []),
                "updated_at": AGORA,
            }
        )
        add_id(iid, "ror", rid, versao_ror)
        add_id(iid, "openalex", oa_id, "openalex")
        if v:
            add_id(iid, "emec", v.emec, f"inep_{ano_inep}+{v.metodo}", v.confianca)
        for esquema, valores in o.ids_externos.items():
            for val in valores:
                add_id(iid, esquema, val, versao_ror)
        for tipo, alvo in o.relacoes:
            relacoes_brutas.append((iid, alvo, tipo))

    # IES do INEP sem correspondente no ROR: viram instituições próprias
    for emec, lin in sorted(inep_por_emec.items(), key=lambda x: int(x[0])):
        if emec in emec_vinculados:
            continue
        iid = ids.obter([f"emec:{emec}"])
        mun = int(lin["CO_MUNICIPIO_IES"]) if lin.get("CO_MUNICIPIO_IES") else None
        m = munis.get(mun) if mun else None
        cat = CATEGORIA_INEP.get(lin.get("TP_CATEGORIA_ADMINISTRATIVA", ""))
        org = ORGANIZACAO_INEP.get(lin.get("TP_ORGANIZACAO_ACADEMICA", ""))
        instituicoes.append(
            {
                "id": iid,
                "name": lin["NO_IES"],
                "acronym": lin.get("SG_IES", ""),
                "kind": org[0] if org else "outro",
                "legal_nature": cat[0] if cat else "",
                "admin_category": cat[1] if cat else "",
                "academic_org": org[1] if org else "",
                "uf": lin["SG_UF_IES"],
                "municipality_ibge": mun or "",
                "municipality_source": "inep",
                "latitude": m["latitude"] if m else "",
                "longitude": m["longitude"] if m else "",
                "geo_source": "sede_municipio" if m else "",
                "is_active": True,
                "sources": ["inep"],
                "updated_at": AGORA,
            }
        )
        add_id(iid, "emec", emec, f"inep_{ano_inep}")
        add_id(iid, "inep_mantenedora", lin.get("CO_MANTENEDORA", ""), f"inep_{ano_inep}")

    relacoes = [
        {"institution_id": a, "related_institution_id": ror_para_uuid.get(alvo, ""), "related_ror": alvo, "relation": tipo, "source": versao_ror}
        for a, alvo, tipo in relacoes_brutas
    ]
    ids.salvar()

    # ----------------------------------------------------------------------- saídas
    campos_inst = [
        "id", "name", "name_ror", "acronym", "kind", "ror_types", "legal_nature", "admin_category", "academic_org", "uf",
        "municipality_ibge", "municipality_source", "latitude", "longitude", "geo_source", "is_active", "established",
        "website", "works_count_openalex", "openalex_has_ne_region", "sources", "updated_at",
    ]
    escrever_csv(DIR_PROCESSADOS / "municipalities.csv", sorted(munis.values(), key=lambda m: m["ibge_code"]), ["ibge_code", "name", "uf", "latitude", "longitude", "is_capital"])
    escrever_csv(DIR_PROCESSADOS / "institutions.csv", instituicoes, campos_inst)
    escrever_csv(DIR_PROCESSADOS / "institution_identifiers.csv", identificadores, ["institution_id", "scheme", "value", "source", "confidence", "verified_at"])
    escrever_csv(DIR_PROCESSADOS / "institution_relations.csv", relacoes, ["institution_id", "related_institution_id", "related_ror", "relation", "source"])
    escrever_csv(DIR_PROCESSADOS / "institution_review_queue.csv", revisao, ["entity", "candidate_a", "candidate_b", "score", "evidence", "status", "created_at"])
    oa_ids = sorted({i["value"] for i in identificadores if i["scheme"] == "openalex"})
    (DIR_PROCESSADOS / "openalex_institution_ids_ne.txt").write_text("\n".join(oa_ids) + "\n")

    stats = {
        "gerado_em": AGORA,
        "versao_ror": versao_ror,
        "ano_inep": ano_inep,
        "ror_ne": len(orgs_ne) - len(extras),
        "ror_extras_pelo_openalex": extras,
        "inep_ies_ne": len(inep),
        "municipios_ne": len(munis),
        "instituicoes_total": len(instituicoes),
        "instituicoes_por_uf": dict(collections.Counter(i["uf"] for i in instituicoes).most_common()),
        "instituicoes_por_kind": dict(collections.Counter(i["kind"] for i in instituicoes).most_common()),
        "instituicoes_por_natureza": dict(collections.Counter(i["legal_nature"] or "desconhecida" for i in instituicoes).most_common()),
        "com_openalex": len(oa_ids),
        "openalex_sem_regiao_ne": sum(1 for i in instituicoes if "openalex" in i["sources"] and not i["openalex_has_ne_region"]),
        "vinculos_inep_ror": dict(collections.Counter(v.metodo for v in vinculos)),
        "fila_revisao": len(revisao),
        "com_coordenadas": sum(1 for i in instituicoes if i["latitude"] != ""),
        "geo_fonte": dict(collections.Counter(i["geo_source"] or "sem" for i in instituicoes)),
        "municipio_fonte": dict(collections.Counter((i["municipality_source"] or "sem").split("_mais")[0] for i in instituicoes)),
        "conflitos_ids": ids.conflitos,
        "identificadores_por_esquema": dict(collections.Counter(i["scheme"] for i in identificadores)),
        "relacoes": len(relacoes),
        "relacoes_internas_ne": sum(1 for r in relacoes if r["related_institution_id"]),
        "creditos_openalex": http.creditos_openalex,
        "top_works": [
            {"nome": i["name"], "uf": i["uf"], "works": i["works_count_openalex"]}
            for i in sorted((i for i in instituicoes if i.get("works_count_openalex") not in ("", None)), key=lambda i: -int(i["works_count_openalex"]))[:20]
        ],
    }
    _relatorio(stats, vinculos)
    return stats


def _relatorio(s: dict[str, Any], vinculos: list[Vinculo]) -> None:
    L = [
        "# Parte 1 — Instituições do Nordeste",
        "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte1_instituicoes`. ROR {s['versao_ror']}; INEP ano-base {s['ano_inep']}.",
        "",
        "## Resumo",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Organizações do NE no ROR | {s['ror_ne']} (+{len(s['ror_extras_pelo_openalex'])} incluídas porque o OpenAlex as põe no NE) |",
        f"| IES do NE no INEP | {s['inep_ies_ne']} |",
        f"| **Instituições unificadas** | **{s['instituicoes_total']}** |",
        f"| Com ID OpenAlex (lista para o recorte da Parte 5) | {s['com_openalex']} |",
        f"| ...das quais sem `geo.region` do NE no OpenAlex (perdidas pelo filtro por estado) | {s['openalex_sem_regiao_ne']} |",
        f"| Vínculos INEP ↔ ROR | {json.dumps(s['vinculos_inep_ror'], ensure_ascii=False)} |",
        f"| Pares para revisão manual | {s['fila_revisao']} |",
        f"| Com coordenadas | {s['com_coordenadas']} ({json.dumps(s['geo_fonte'], ensure_ascii=False)}) |",
        f"| Fonte do município | {json.dumps(s['municipio_fonte'], ensure_ascii=False)} |",
        f"| Relações (ROR) | {s['relacoes']} ({s['relacoes_internas_ne']} entre instituições do NE) |",
        f"| Créditos OpenAlex gastos | {s['creditos_openalex']} |",
        "",
        f"Por UF: {json.dumps(s['instituicoes_por_uf'], ensure_ascii=False)}",
        "",
        f"Por tipo: {json.dumps(s['instituicoes_por_kind'], ensure_ascii=False)}",
        "",
        f"Por natureza: {json.dumps(s['instituicoes_por_natureza'], ensure_ascii=False)}",
        "",
        f"Identificadores: {json.dumps(s['identificadores_por_esquema'], ensure_ascii=False)}",
        "",
        "## Maiores instituições por produção (OpenAlex, todos os anos)",
        "",
        "| Instituição | UF | Works |",
        "|---|---|---|",
    ]
    L += [f"| {t['nome']} | {t['uf']} | {t['works']} |" for t in s["top_works"]]
    L += ["", "## Vínculos INEP ↔ ROR por nome/sigla + município (confiança 0,9; conferir)", ""]
    L += [f"- e-MEC {v.emec} `{v.evidencia['inep_nome']}` → ROR {v.ror} `{v.evidencia['ror_nome']}`" for v in vinculos if v.metodo != "wikidata_P6782_P5148"]
    if s["conflitos_ids"]:
        L += ["", "## Conflitos no registro de IDs", "", f"```\n{json.dumps(s['conflitos_ids'], ensure_ascii=False, indent=1)}\n```"]
    L += [
        "",
        "## Arquivos",
        "",
        "`ingest/dados/processados/`: municipalities.csv, institutions.csv, institution_identifiers.csv, institution_relations.csv, "
        "institution_review_queue.csv, openalex_institution_ids_ne.txt. Registro de UUIDs: `ingest/dados/ids/institution.csv`.",
    ]
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    (DIR_RELATORIOS / "parte1_instituicoes.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte1_instituicoes.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-cache", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar(sem_cache=a.sem_cache)
    print(json.dumps({k: s[k] for k in ("instituicoes_total", "instituicoes_por_uf", "com_openalex", "vinculos_inep_ror", "fila_revisao", "com_coordenadas")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
