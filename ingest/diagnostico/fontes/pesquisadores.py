"""Grupo 4 — Pesquisadores e identificadores (OpenAlex /authors, ORCID)."""

from __future__ import annotations

import collections
import re
from collections.abc import Callable
from typing import Any

from ..contexto import Contexto
from ..http import ErroHttp
from ..modelos import ResultadoFonte
from ..recorte import CAMPOS_OPENALEX, UFS_NORDESTE, filtro_openalex_campos, filtro_openalex_regioes, normalizar

FILTRO_AUTORES_NE = f"last_known_institutions.country_code:BR,{filtro_openalex_regioes('last_known_institutions.geo.region')}"
FILTRO_AUTORES_BR = f"{FILTRO_AUTORES_NE},{filtro_openalex_campos('topics.field.id')}"  # recorte: NE × áreas de saúde


def openalex_authors(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="openalex_authors",
        nome="OpenAlex /authors (instituição mais recente no NE, tópicos de saúde/biomédicas)",
        grupo="4. Pesquisadores",
        url_base="https://api.openalex.org/authors",
        forma_acesso="API REST (JSON) + snapshot S3",
        formato="JSON / JSONL.gz / Parquet",
        licenca="CC0 1.0",
        frequencia_atualizacao="API contínua; snapshot público trimestral",
        identificadores=["OpenAlex ID", "ORCID", "Scopus (parcial)"],
    )
    total = ctx.oa.contar("authors", FILTRO_AUTORES_BR)
    r.registrar_resposta(200, None)
    com_orcid = ctx.oa.contar("authors", f"{FILTRO_AUTORES_BR},has_orcid:true")
    r.registros_br = total
    r.registros_obs = f"perfis com instituição recente no NE e algum tópico nos fields de saúde; {com_orcid} com ORCID ({com_orcid / total:.1%})" if total else ""
    r.detalhes["filtro"] = FILTRO_AUTORES_BR
    r.detalhes["todos_autores_ne"] = ctx.oa.contar("authors", FILTRO_AUTORES_NE)
    r.detalhes["total"] = total
    r.detalhes["com_orcid"] = com_orcid
    try:
        resp = ctx.http.get("https://api.openalex.org/authors", params=ctx.oa._params({"filter": FILTRO_AUTORES_BR, "per_page": 25}))
        n = len(resp.json().get("results", []))
        if n:
            r.detalhes["bytes_medios_por_author_json"] = int(len(resp.corpo) / n)
            ctx.compartilhado["bytes_por_author"] = r.detalhes["bytes_medios_por_author_json"]
    except Exception as e:  # noqa: BLE001
        r.erro("amostra de tamanho de author", e)
    ctx.compartilhado["autores_br"] = total
    ctx.compartilhado["autores_br_orcid"] = com_orcid
    # Autores BR com publicação recente (proxy de "ativos"): last_known é do trabalho mais recente.
    try:
        r.detalhes["com_5_ou_mais_trabalhos"] = ctx.oa.contar("authors", f"{FILTRO_AUTORES_BR},works_count:>4")
    except ErroHttp as e:
        r.erro("contagem works_count>4", e)
    try:
        r.detalhes["por_last_known_institutions.type"] = ctx.oa.agrupar("authors", "last_known_institutions.type", FILTRO_AUTORES_BR)
    except ErroHttp as e:
        r.erro("group_by last_known_institutions.type", e)
    # A API não agrupa por last_known_institutions.geo.region (é resolvido na hora da consulta),
    # mas aceita o filtro: uma contagem por estado do NE.
    try:
        base = f"last_known_institutions.country_code:BR,{filtro_openalex_campos('topics.field.id')}"
        por_estado: list[dict[str, Any]] = []
        for uf in UFS_NORDESTE:
            valor = f'"{uf.nome}"' if " " in uf.nome else uf.nome
            n = ctx.oa.contar("authors", f"{base},last_known_institutions.geo.region:{valor}")
            por_estado.append({"chave": uf.sigla, "nome": uf.nome, "contagem": n})
        por_estado.sort(key=lambda g: -(g["contagem"] or 0))
        r.detalhes["por_last_known_institutions.geo.region"] = por_estado
        soma = sum(int(g["contagem"]) for g in por_estado)
        r.observacoes.append(f"Por estado (1 chamada por UF); soma {soma} vs total {total} (autor com instituições recentes em 2 estados conta 2 vezes).")
    except ErroHttp as e:
        r.erro("contagem por estado", e)
    try:
        r.detalhes["por_field"] = ctx.oa.agrupar("authors", "topics.field.id", FILTRO_AUTORES_NE)
        r.detalhes["por_field"] = [g for g in r.detalhes["por_field"] if str(g["chave"]).rsplit("/", 1)[-1] in {str(c) for c in CAMPOS_OPENALEX}]
    except ErroHttp as e:
        r.erro("group_by topics.field.id", e)
    r.riscos.append(
        "O filtro topics.field.id pega quem tem QUALQUER tópico nesses fields entre seus principais: inclui pesquisadores de outras áreas "
        "com produção pontual em saúde. A contagem de autores distintos nos works do recorte (fonte openalex_works) é a medida mais justa."
    )
    r.riscos.append(
        "Perfis fragmentados/mesclados errados são comuns (no OpenAlex todo, ~1 em 10 perfis tem ORCID; no recorte, "
        f"{com_orcid / total:.0%}); contagem de perfis > número de pessoas."
    )
    r.riscos.append("last_known_institutions reflete só o trabalho mais recente: quem mudou para o exterior sai do recorte, quem chegou entra.")
    r.recomendacao = "usar"
    r.justificativa = "Base principal de perfis pré-populados; ORCID permite reivindicação."
    return r


def _amostra_autores_orcid(ctx: Contexto, n: int) -> list[dict[str, Any]]:
    autores: list[dict[str, Any]] = []
    paginas = (n + 99) // 100
    for p in range(1, paginas + 1):
        d = ctx.oa.consultar(
            "authors",
            filter=f"{FILTRO_AUTORES_BR},has_orcid:true",
            sample=n,
            seed=42,
            per_page=100,
            page=p,
            select="id,orcid,display_name,last_known_institutions",
        )
        autores.extend(d.get("results", []))
    return autores[:n]


def _paises_emprego(js: dict[str, Any]) -> list[str]:
    return [p for p, _ in _enderecos_emprego(js)]


def _enderecos_emprego(js: dict[str, Any]) -> list[tuple[str, str]]:
    """(país, 'região cidade') de cada emprego registrado no ORCID."""
    saida: list[tuple[str, str]] = []
    for grupo in js.get("affiliation-group", []) or []:
        for s in grupo.get("summaries", []) or []:
            end = (((s.get("employment-summary") or {}).get("organization") or {}).get("address")) or {}
            if end.get("country"):
                saida.append((end["country"], f"{end.get('region') or ''} {end.get('city') or ''}"))
    return saida


def _eh_ne(texto: str) -> bool:
    n = normalizar(texto)
    return any(normalizar(u.nome) in n or re.search(rf"(?<![A-Z]){u.sigla}(?![A-Z])", n) or normalizar(u.capital) in n for u in UFS_NORDESTE)


def orcid(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="orcid",
        nome="ORCID — API pública v3.0 e Public Data File anual",
        grupo="4. Pesquisadores",
        url_base="https://pub.orcid.org/v3.0/",
        forma_acesso="API REST pública (sem login, limite de taxa) + arquivo anual (figshare)",
        formato="JSON/XML (API); TAR.GZ de XML (Public Data File)",
        licenca="Dados públicos do ORCID: CC0 1.0 (Public Data File); API pública sujeita aos termos de uso",
        frequencia_atualizacao="API em tempo real; Public Data File anual (outubro)",
        identificadores=["ORCID", "afiliações com ROR/Ringgold/GRID", "DOI das obras", "Scopus/ResearcherID"],
    )
    r.observacoes += [
        "API pública: acesso anônimo permitido; limite documentado de 24 req/s (rajada 40). Para uso contínuo, registrar credenciais Public API (client_id) e usar token /read-public.",
        "Termos: https://info.orcid.org/public-client-terms-of-service/ — uso não comercial gratuito; atribuição recomendada.",
        "pub.orcid.org bloqueia robôs no robots.txt; uso autorizado como API documentada (decisão D-003).",
        "Filtrar por país no Public Data File exige processar o arquivo inteiro (summaries) olhando employment/education com address.country=BR.",
    ]
    # Public Data File (figshare)
    try:
        busca = ctx.http.requisitar(
            "POST",
            "https://api.figshare.com/v2/articles/search",
            corpo_json={"search_for": '"ORCID Public Data File"', "page_size": 20},
        ).json()
        candidatos = [(int(m.group(1)), a) for a in busca if (m := re.match(r"^ORCID Public Data File (\d{4})$", a.get("title", "")))]
        if candidatos:
            ano, art = max(candidatos, key=lambda x: x[0])
            det = ctx.http.get_json(f"https://api.figshare.com/v2/articles/{art['id']}")
            arquivos = [{"nome": f["name"], "bytes": f["size"]} for f in det.get("files", [])]
            r.detalhes["public_data_file"] = {
                "ano": ano,
                "url": det.get("url_public_html") or art.get("url_public_html"),
                "publicado": det.get("published_date"),
                "licenca": (det.get("license") or {}).get("name"),
                "arquivos": arquivos,
                "bytes_total": sum(f["bytes"] for f in arquivos),
            }
            resumo = [f for f in arquivos if "summaries" in f["nome"].lower()]
            r.tamanho_bytes = resumo[0]["bytes"] if resumo else sum(f["bytes"] for f in arquivos)
            r.tamanho_obs = f"Public Data File {ano}: arquivo summaries" if resumo else f"Public Data File {ano} (todos os arquivos)"
            r.ultima_atualizacao = det.get("published_date", "")
            if (det.get("license") or {}).get("name"):
                r.licenca = f"Public Data File: {(det.get('license') or {}).get('name')}; API pública sujeita aos termos de uso"
    except Exception as e:  # noqa: BLE001
        r.erro("figshare (Public Data File)", e)

    # Sobreposição: amostra de autores BR do OpenAlex com ORCID
    n = ctx.cfg.amostra_orcid
    try:
        autores = _amostra_autores_orcid(ctx, n)
    except Exception as e:  # noqa: BLE001
        r.erro("amostra OpenAlex", e)
        autores = []
    contagem: collections.Counter[str] = collections.Counter()
    paises_total: collections.Counter[str] = collections.Counter()
    for a in autores:
        oid = (a.get("orcid") or "").rsplit("/", 1)[-1]
        if not oid:
            continue
        try:
            resp = ctx.http.get(f"https://pub.orcid.org/v3.0/{oid}/employments", cabecalhos={"Accept": "application/json"})
            r.registrar_resposta(resp.status, resp.tempo_ms)
            if not resp.ok:
                contagem[f"http_{resp.status}"] += 1
                continue
            enderecos = _enderecos_emprego(resp.json())
            paises = [p for p, _ in enderecos]
            contagem["consultados"] += 1
            if not paises:
                contagem["sem_emprego_registrado"] += 1
            elif "BR" in paises:
                contagem["com_emprego_br"] += 1
                if any(p == "BR" and _eh_ne(reg) for p, reg in enderecos):
                    contagem["com_emprego_ne"] += 1
            else:
                contagem["so_emprego_exterior"] += 1
            paises_total.update(set(paises))
        except Exception as e:  # noqa: BLE001
            contagem["erros"] += 1
            if contagem["erros"] <= 3:
                r.erro(f"ORCID {oid}", e)
    consult = contagem.get("consultados", 0)
    r.detalhes["amostra_sobreposicao"] = {
        "tamanho_pedido": n,
        "autores_openalex_amostrados": len(autores),
        **dict(contagem),
        "pct_com_emprego_br": round(100 * contagem.get("com_emprego_br", 0) / consult, 1) if consult else None,
        "pct_sem_emprego": round(100 * contagem.get("sem_emprego_registrado", 0) / consult, 1) if consult else None,
        "pct_com_emprego_ne": round(100 * contagem.get("com_emprego_ne", 0) / consult, 1) if consult else None,
        "paises_mais_frequentes": dict(paises_total.most_common(10)),
        "metodo": "OpenAlex authors do recorte (NE × saúde, has_orcid, sample seed=42) -> ORCID /v3.0/{id}/employments; país e região em organization.address",
    }
    if consult:
        pct = 100 * contagem.get("com_emprego_br", 0) / consult
        r.observacoes.append(
            f"Amostra: {consult} ORCIDs consultados; {pct:.1f}% têm emprego no Brasil registrado no ORCID "
            f"({100 * contagem.get('com_emprego_ne', 0) / consult:.1f}% com emprego em estado do NE); "
            f"{100 * contagem.get('sem_emprego_registrado', 0) / consult:.1f}% não têm nenhum emprego registrado."
        )
        aut_orcid = ctx.compartilhado.get("autores_br_orcid") or ctx.oa.contar("authors", f"{FILTRO_AUTORES_BR},has_orcid:true")
        if aut_orcid:
            r.registros_br = int(aut_orcid * pct / 100)
            r.registros_obs = "estimativa de ORCIDs com emprego BR registrado entre os autores do recorte com ORCID (amostra)"
    r.recomendacao = "usar"
    r.justificativa = "Identificador de referência e base da reivindicação; API para enriquecer sob demanda (no login), não em massa."
    r.riscos.append("Muitos ORCIDs têm registro vazio ou privado: não usar ausência de afiliação como negativa.")
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [
    ("openalex_authors", openalex_authors),
    ("orcid", orcid),
]
