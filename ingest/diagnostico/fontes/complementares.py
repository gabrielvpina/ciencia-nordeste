"""Grupo 7 — Informações complementares (financiamento, bolsistas PQ, infraestrutura, áreas)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from ..contexto import Contexto
from ..http import ErroHttp
from ..modelos import ResultadoFonte
from ..recorte import UFS_NORDESTE, filtro_openalex_campos, filtro_openalex_regioes, normalizar
from .grupos import _links

FAPS_NE = {
    "MA": "FAPEMA", "PI": "FAPEPI", "CE": "FUNCAP", "RN": "FAPERN", "PB": "FAPESQ",
    "PE": "FACEPE", "AL": "FAPEAL", "SE": "FAPITEC", "BA": "FAPESB",
}


def openalex_funders(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="openalex_funders",
        nome="OpenAlex /funders e /awards — FAPs do Nordeste e financiadores do recorte",
        grupo="7. Complementares",
        url_base="https://api.openalex.org/funders",
        forma_acesso="API REST + snapshot S3",
        formato="JSON",
        licenca="CC0 1.0",
        frequencia_atualizacao="API contínua",
        identificadores=["Crossref Funder ID/DOI", "ROR", "Wikidata", "funder_award_id (nº do processo)"],
    )
    fundadores: list[dict[str, Any]] = []
    for pagina in range(1, 6):
        d = ctx.oa.consultar("funders", filter="country_code:BR", sort="works_count:desc", per_page=100, page=pagina, select="id,display_name,works_count,awards_count,ids,alternate_titles")
        res = d.get("results", [])
        fundadores.extend(res)
        if len(res) < 100:
            break
    r.registrar_resposta(200, None)
    faps: dict[str, Any] = {}
    for uf, sigla in FAPS_NE.items():
        nome_uf = next(u.nome for u in UFS_NORDESTE if u.sigla == uf)
        cand = [
            f for f in fundadores
            if sigla.lower() in (f["display_name"] + " " + " ".join(f.get("alternate_titles") or [])).lower()
            or (("amparo" in f["display_name"].lower() or "apoio" in f["display_name"].lower()) and normalizar(nome_uf) in normalizar(f["display_name"]))
        ]
        faps[sigla] = [{"id": f["id"], "nome": f["display_name"], "works": f.get("works_count"), "awards": f.get("awards_count")} for f in cand[:3]]
    r.detalhes["financiadores_br"] = len(fundadores)
    r.detalhes["faps_ne"] = faps
    achadas = [s for s, v in faps.items() if v]
    r.observacoes.append(f"FAPs do NE encontradas no OpenAlex: {len(achadas)}/9 ({', '.join(achadas) or 'nenhuma'}).")
    filtro_rec = f"{filtro_openalex_regioes('authorships.institutions.geo.region')},{filtro_openalex_campos('primary_topic.field.id')},publication_year:{ctx.anos}"
    try:
        top = ctx.oa.agrupar("works", "funders.id", filtro_rec)
        r.detalhes["works_recorte_por_financiador_top"] = top[:25]
        ids_faps = {x["id"] for v in faps.values() for x in v}
        r.detalhes["works_recorte_com_fap_ne"] = sum(g["contagem"] or 0 for g in top if g["chave"] in ids_faps)
        r.detalhes["works_recorte_com_financiador"] = ctx.oa.contar("works", f"{filtro_rec},funders.id:!null")
    except ErroHttp as e:
        r.erro("works do recorte por financiador", e)
    ids = [x["id"].rsplit("/", 1)[-1] for v in faps.values() for x in v]
    if ids:
        try:
            r.detalhes["awards_faps_ne"] = ctx.oa.contar("awards", "funder.id:" + "|".join(ids))
        except ErroHttp as e:
            r.erro("awards das FAPs NE", e)
    r.registros_br = r.detalhes.get("works_recorte_com_financiador")
    r.registros_obs = "works do recorte com algum financiador identificado"
    r.riscos.append("Financiamento vem dos agradecimentos/Crossref: subnotificado para CNPq/CAPES/FAPs; nº de processo raramente estruturado.")
    r.recomendacao = "complementar"
    r.justificativa = "Mostra quem financia a pesquisa em saúde no NE; bom para filtros, não para auditoria de fomento."
    return r


def cnpq_bolsistas_pq(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="cnpq_bolsistas_pq",
        nome="CNPq — Bolsistas de produtividade (PQ/DT)",
        grupo="7. Complementares",
        url_base="https://www.gov.br/cnpq/pt-br/acesso-a-informacao/dados-abertos",
        forma_acesso="A verificar (dados abertos do CNPq)",
        identificadores=["nome", "instituição", "nível PQ"],
    )
    resp = ctx.http.get("https://www.gov.br/cnpq/pt-br/acesso-a-informacao/dados-abertos")
    r.registrar_resposta(resp.status, resp.tempo_ms)
    links = _links(resp.texto(), resp.url_final or resp.url)
    rel = [lk for lk in links if re.search(r"bolsa|produtividade|fomento|pagamento", lk["rotulo"] + " " + lk["href"], re.I)]
    r.detalhes["links_bolsas"] = rel[:40]
    r.observacoes.append(
        "Alternativa já disponível: a coluna CD_CAT_BOLSA_PRODUTIVIDADE do conjunto de docentes da CAPES indica a categoria PQ de cada docente de pós."
    )
    r.licenca = "Dados públicos (LAI)"
    r.recomendacao = "complementar" if rel else "precisa de acordo ou pedido LAI"
    r.justificativa = "Usar a coluna PQ dos docentes CAPES; lista completa (inclui quem não é docente de pós) via dados abertos ou LAI."
    return r


def pnipe(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="pnipe",
        nome="PNIPE/MCTI — Plataforma Nacional de Infraestrutura de Pesquisa",
        grupo="7. Complementares",
        url_base="https://pnipe.mcti.gov.br/",
        forma_acesso="Aplicação web (SPA); sem API pública documentada encontrada",
        identificadores=["instituição", "laboratório", "equipamento"],
    )
    resp = ctx.http.get("https://pnipe.mcti.gov.br/")
    r.registrar_resposta(resp.status, resp.tempo_ms)
    t = resp.texto()
    r.detalhes["spa_react"] = "id=\"root\"" in t
    r.detalhes["titulo"] = (re.search(r"<title>(.*?)</title>", t) or [None, None])[1]
    r.observacoes.append("Site é aplicação JavaScript; dados vêm de API interna não documentada (não usar sem autorização).")
    r.licenca = "Não declarada"
    r.recomendacao = "precisa de acordo ou pedido LAI"
    r.justificativa = "Pedir ao MCTI exportação aberta (CSV) de laboratórios/equipamentos multiusuário ou procurar no dados.gov.br com token."
    return r


def areas_conhecimento(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="areas_conhecimento",
        nome="Tabela de Áreas do Conhecimento / Áreas de Avaliação (CAPES)",
        grupo="7. Complementares",
        url_base="https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/instrumentos/documentos-de-apoio/tabela-de-areas-de-conhecimento-avaliacao",
        forma_acesso="Arquivo para download (PDF/XLSX) em página gov.br",
        identificadores=["código da área (8 dígitos)", "área de avaliação CAPES"],
    )
    resp = ctx.http.get(r.url_base)
    r.registrar_resposta(resp.status, resp.tempo_ms)
    arquivos: list[dict[str, Any]] = []
    if resp.ok:
        links = _links(resp.texto(), resp.url_final or r.url_base)
        for lk in links:
            if re.search(r"\.(xlsx?|pdf|csv|ods)(/view)?(\?|$)", lk["href"], re.I) and re.search(r"[áa]rea|tabela", lk["rotulo"] + lk["href"], re.I):
                arquivos.append(lk)
        for a in arquivos[:5]:
            try:
                tam, h = ctx.http.tamanho_remoto(a["href"])
                a["bytes"] = tam
                a["tipo"] = h.cabecalhos.get("content-type")
            except Exception as e:  # noqa: BLE001
                a["erro"] = str(e)
    r.detalhes["arquivos"] = arquivos
    if not arquivos:
        r.observacoes.append("Nenhum link de arquivo (PDF/XLSX) da tabela encontrado automaticamente na página; conferir manualmente.")
    r.formato = ", ".join(sorted({re.sub(r".*\.([a-z]+)(/view)?$", r"\1", a["href"].split("?")[0].lower()) for a in arquivos})) or "?"
    r.tamanho_bytes = sum(a.get("bytes") or 0 for a in arquivos) or None
    r.observacoes.append(
        "Os conjuntos CAPES já trazem CD_AREA_AVALIACAO, NM_GRANDE_AREA_CONHECIMENTO, NM_AREA_CONHECIMENTO e CD_AREA_BASICA: a tabela pode ser derivada deles."
    )
    r.observacoes.append("Para ligar a OpenAlex (topics/fields) será preciso uma tabela de correspondência manual por subárea.")
    r.licenca = "Documento público oficial"
    r.recomendacao = "usar"
    r.justificativa = "Vocabulário de áreas usado por CAPES/CNPq; necessário para filtros em português."
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [
    ("openalex_funders", openalex_funders),
    ("cnpq_bolsistas_pq", cnpq_bolsistas_pq),
    ("pnipe", pnipe),
    ("areas_conhecimento", areas_conhecimento),
]
