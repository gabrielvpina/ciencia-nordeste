"""Grupo 5 — Produção científica (OpenAlex works, snapshot S3, SciELO, BDTD, Oasisbr)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contexto import Contexto
from ..http import ErroHttp
from ..modelos import ResultadoFonte
from ..recorte import (
    CAMPOS_OPENALEX_OPCIONAIS,
    SUBCAMPOS_OPENALEX_OPCIONAIS,
    TERMOS_BUSCA,
    UFS_NORDESTE,
    eh_instituicao_ne,
    filtro_openalex_campos,
    filtro_openalex_regioes,
)

S3 = "https://openalex.s3.amazonaws.com"
ENTIDADES_SNAPSHOT = ["works", "authors", "institutions", "sources", "topics"]
FILTRO_REGIAO_WORKS = filtro_openalex_regioes("authorships.institutions.geo.region")
FILTRO_AREA_WORKS = filtro_openalex_campos("primary_topic.field.id")


def _filtro_works(ctx: Contexto) -> str:
    """Filtro do recorte (região × área), sem o período."""
    ctx.compartilhado["filtro_works_br"] = FILTRO_REGIAO_WORKS
    return f"{FILTRO_REGIAO_WORKS},{FILTRO_AREA_WORKS}"


def openalex_works(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="openalex_works",
        nome=f"OpenAlex /works com instituição do NE, área de saúde/biomédicas ({ctx.anos})",
        grupo="5. Produção científica",
        url_base="https://api.openalex.org/works",
        forma_acesso="API REST (JSON) + snapshot S3",
        formato="JSON / JSONL.gz / Parquet",
        licenca="CC0 1.0",
        frequencia_atualizacao="API contínua; snapshot público trimestral",
        identificadores=["DOI", "OpenAlex ID", "PMID/PMCID", "ORCID e ROR nas autorias"],
    )
    frec = _filtro_works(ctx)
    filtro = f"{frec},publication_year:{ctx.anos}"
    r.detalhes["filtro_usado"] = filtro
    total = ctx.oa.contar("works", filtro)
    r.registrar_resposta(200, None)
    total_all = ctx.oa.contar("works", filtro, corpus="all")
    r.registros_br = total
    r.registros_obs = f"works com ≥1 instituição do NE e primary topic em saúde (corpus padrão); com corpus=all (inclui XPAC, igual ao snapshot): {total_all}"
    ctx.compartilhado["works_br"] = total
    ctx.compartilhado["works_br_all"] = total_all
    r.detalhes["total_corpus_padrao"] = total
    r.detalhes["total_corpus_all"] = total_all
    # Tamanho médio de um registro completo (para estimar disco e transferência)
    try:
        resp = ctx.http.get("https://api.openalex.org/works", params=ctx.oa._params({"filter": filtro, "per_page": 25, "sort": "publication_date:desc"}))
        n = len(resp.json().get("results", []))
        if n:
            r.detalhes["bytes_medios_por_work_json"] = int(len(resp.corpo) / n)
            ctx.compartilhado["bytes_por_work"] = r.detalhes["bytes_medios_por_work_json"]
    except Exception as e:  # noqa: BLE001
        r.erro("amostra de tamanho de work", e)
    extras = {
        "todos_works_ne_periodo": f"{FILTRO_REGIAO_WORKS},publication_year:{ctx.anos}",
        "works_br_saude_periodo": f"authorships.institutions.country_code:BR,{FILTRO_AREA_WORKS},publication_year:{ctx.anos}",
        "opcional_campos": (
            f"{FILTRO_REGIAO_WORKS},{filtro_openalex_campos('primary_topic.field.id', CAMPOS_OPENALEX_OPCIONAIS)},publication_year:{ctx.anos}"
            if CAMPOS_OPENALEX_OPCIONAIS else None
        ),
        "opcional_engenharia_biomedica": f"{FILTRO_REGIAO_WORKS},primary_topic.subfield.id:{'|'.join(map(str, SUBCAMPOS_OPENALEX_OPCIONAIS))},publication_year:{ctx.anos}",
        "com_autor_ne_e_outra_regiao_br": None,
    }
    for nome, f in extras.items():
        if f:
            try:
                r.detalhes[nome] = ctx.oa.contar("works", f)
            except ErroHttp as e:
                r.erro(nome, e)
    if r.detalhes.get("todos_works_ne_periodo"):
        r.observacoes.append(f"O recorte é {total / r.detalhes['todos_works_ne_periodo']:.1%} de toda a produção do NE no período.")
    if r.detalhes.get("works_br_saude_periodo"):
        r.observacoes.append(f"O NE responde por {total / r.detalhes['works_br_saude_periodo']:.1%} da produção brasileira em saúde/biomédicas no período.")
    r.observacoes.append(
        f"Áreas opcionais fora da contagem principal: fields opcionais {r.detalhes.get('opcional_campos', '—')} works; "
        f"Engenharia Biomédica {r.detalhes.get('opcional_engenharia_biomedica', '?')} works."
    )
    # Por estado (group_by de região não existe para works): uma chamada por UF
    por_uf: list[dict[str, Any]] = []
    for uf in UFS_NORDESTE:
        valor = f'"{uf.nome}"' if " " in uf.nome else uf.nome
        try:
            por_uf.append({"chave": uf.sigla, "nome": uf.nome, "contagem": ctx.oa.contar("works", f"authorships.institutions.geo.region:{valor},{FILTRO_AREA_WORKS},publication_year:{ctx.anos}")})
        except ErroHttp as e:
            r.erro(f"works {uf.sigla}", e)
    por_uf.sort(key=lambda g: -int(g["contagem"] or 0))
    r.detalhes["por_estado"] = por_uf
    # Lacuna do filtro por geo.region: works do recorte com instituições do NE (lista do ROR) que estão sem geo.region.
    ids_fora = ctx.compartilhado.get("openalex_ids_ne_sem_regiao") or []
    if ids_fora:
        extra = 0
        try:
            for i in range(0, len(ids_fora), 100):
                lote = "|".join(ids_fora[i : i + 100])
                extra += ctx.oa.contar("works", f"authorships.institutions.id:{lote},{FILTRO_AREA_WORKS},publication_year:{ctx.anos}")
            r.detalhes["works_instituicoes_ne_sem_geo_region"] = extra
            r.detalhes["faixa_recorte"] = [total, total + extra]
            r.registros_obs += f"; faixa considerando instituições NE sem geo.region: {total}–{total + extra}"
            r.observacoes.append(
                f"{len(ids_fora)} instituições do NE (lista do ROR) não têm geo.region no OpenAlex e somam {extra} works no recorte, "
                f"parte deles já contada por coautoria com outra instituição do NE: o recorte real fica entre {total} e {total + extra}."
            )
            ctx.compartilhado["works_recorte_max"] = total + extra
        except ErroHttp as e:
            r.erro("works de instituições sem geo.region", e)
    r.observacoes.append("Autores distintos nos works do recorte: só com cursor paging (exige chave); calcular na Parte 5.")
    for campo in ("publication_year", "type", "open_access.oa_status", "primary_topic.field.id", "primary_topic.subfield.id", "language", "has_doi"):
        try:
            r.detalhes[f"por_{campo}"] = ctx.oa.agrupar("works", campo, filtro)
        except ErroHttp as e:
            r.erro(f"group_by {campo}", e)
    try:
        pt = next((g["contagem"] for g in r.detalhes.get("por_language", []) if g["chave"] in ("pt", "languages/pt", "https://openalex.org/languages/pt")), None)
        if pt:
            r.observacoes.append(f"{pt} trabalhos em português ({pt / total:.1%}).")
    except Exception:  # noqa: BLE001
        pass
    doi = next((g["contagem"] for g in r.detalhes.get("por_has_doi", []) if str(g["chave"]).lower() == "true"), None)
    if doi:
        r.observacoes.append(f"{doi / total:.1%} têm DOI (chave para cruzar com CAPES/SciELO).")
    r.riscos.append("Cobertura menor em humanidades e em periódicos nacionais sem DOI/Crossref; complementar com SciELO e BDTD.")
    r.riscos.append("Afiliação vem do texto da autoria: trabalhos sem afiliação estruturada ficam fora do recorte.")
    r.riscos.append("Instituições sem geo.region no OpenAlex ficam fora do filtro por estado (ver validação na fonte 'ror'); na Parte 5, filtrar por lista de IDs de instituições do NE.")
    r.riscos.append("primary_topic é atribuído por modelo: trabalhos interdisciplinares podem cair fora (ou dentro) do recorte.")
    r.recomendacao = "usar"
    r.justificativa = "Fonte principal da produção, com autorias, ORCID, ROR, tópicos e citações."
    return r


def openalex_snapshot(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="openalex_snapshot",
        nome="OpenAlex — snapshot público no S3 (manifests)",
        grupo="5. Produção científica",
        url_base=f"{S3}/data/jsonl/",
        forma_acesso="S3 público sem login (aws s3 sync --no-sign-request ou HTTPS)",
        formato="JSONL.gz particionado por updated_date (também Parquet)",
        licenca="CC0 1.0",
        frequencia_atualizacao="Trimestral (2ª quarta-feira de jan/abr/jul/out)",
        identificadores=["mesmos da API (DOI, ORCID, ROR, OpenAlex ID)"],
    )
    resp = ctx.http.get(f"{S3}/data/jsonl/manifest.json")
    r.registrar_resposta(resp.status, resp.tempo_ms)
    if not resp.ok:
        raise ErroHttp(f"manifest combinado: HTTP {resp.status}")
    comb = resp.json()
    r.ultima_atualizacao = str(comb.get("date") or comb.get("meta", {}).get("date") or "")
    r.detalhes["manifest_combinado_meta"] = comb.get("meta")
    entidades: dict[str, Any] = {}
    for ent in ENTIDADES_SNAPSHOT:
        try:
            m = ctx.http.get_json(f"{S3}/data/jsonl/{ent}/manifest.json")
            entidades[ent] = {
                "data": m.get("date"),
                "registros": m.get("record_count"),
                "bytes_comprimidos": m.get("content_length"),
                "arquivos": len(m.get("files", [])),
            }
        except Exception as e:  # noqa: BLE001
            r.erro(f"manifest {ent}", e)
    r.detalhes["entidades"] = entidades
    try:
        pq = ctx.http.get_json(f"{S3}/data/parquet/manifest.json")
        r.detalhes["parquet_meta"] = pq.get("meta")
    except Exception as e:  # noqa: BLE001
        r.erro("manifest parquet", e)
    try:
        notas = ctx.http.get(f"{S3}/RELEASE_NOTES.txt", intervalo_bytes=(0, 4095), aceitar_status=(206,))
        r.detalhes["release_notes_inicio"] = notas.texto()[:1500]
    except Exception as e:  # noqa: BLE001
        r.erro("RELEASE_NOTES", e)
    total_bytes = sum(e.get("bytes_comprimidos") or 0 for e in entidades.values())
    r.tamanho_bytes = (comb.get("meta") or {}).get("content_length") or total_bytes
    r.tamanho_obs = "snapshot JSONL completo (comprimido)"
    w = entidades.get("works", {})
    works_br_all = ctx.compartilhado.get("works_br_all")
    if works_br_all is None:
        try:
            filtro = f"{_filtro_works(ctx)},publication_year:{ctx.anos}"
            works_br_all = ctx.oa.contar("works", filtro, corpus="all")
            ctx.compartilhado["works_br_all"] = works_br_all
        except Exception as e:  # noqa: BLE001
            r.erro("contagem works BR (corpus=all)", e)
    if w.get("registros") and w.get("bytes_comprimidos") and works_br_all:
        frac = works_br_all / w["registros"]
        bytes_br = int(frac * w["bytes_comprimidos"])
        r.registros_br = works_br_all
        r.registros_obs = f"works do recorte {ctx.anos} no snapshot ({frac:.3%} do total)"
        r.detalhes["estimativa_recorte_br"] = {
            "fracao_works": frac,
            "bytes_comprimidos_works_br": bytes_br,
            "bytes_descomprimidos_works_br_aprox": bytes_br * 5,
            "bytes_works_a_processar": w["bytes_comprimidos"],
            "observacao": "Partições são por updated_date, não por país/ano: é preciso ler TODOS os arquivos de works para filtrar o recorte.",
        }
        ctx.compartilhado["snapshot_works_bytes"] = w["bytes_comprimidos"]
        ctx.compartilhado["snapshot_bytes_br"] = bytes_br
    est_br = r.detalhes.get("estimativa_recorte_br") or {}
    frac_txt = f"{est_br['fracao_works']:.2%}" if est_br else "uma fração pequena"
    r.riscos.append(
        f"Download de {w.get('bytes_comprimidos', 0) / 1e9:.0f} GB de works para aproveitar {frac_txt}; "
        "exige disco temporário e banda (pode ser feito em streaming, arquivo a arquivo)."
    )
    r.riscos.append("Snapshot defasa até 3 meses; atualização diária só nos planos pagos.")
    r.recomendacao = "complementar"
    r.justificativa = "Alternativa à API para carga completa; ver comparação de custo na seção final."
    return r


SIGLAS_VUFIND_NE = tuple(
    s for s in (
        "UFBA", "UFRB", "UFSB", "UFOB", "UNEB", "UEFS", "UESB", "UESC", "UFPE", "UFRPE", "UPE", "UNICAP", "UFC", "UECE",
        "URCA", "UNIFOR", "UNILAB", "UFRN", "UERN", "UFERSA", "UFPB", "UEPB", "UFCG", "UFAL", "UNCISAL", "UFS", "UNIT",
        "UFPI", "UESPI", "UFMA", "UEMA", "UNIVASF", "UFCA", "UFDPAR", "UFAPE", "IFBA", "IFPE", "IFCE", "IFRN", "IFPB",
        "IFAL", "IFS", "IFPI", "IFMA", "IFBAIANO", "IF SERTÃO-PE", "UNP", "UNIFACS", "EBMSP", "IMIP", "CESMAC",
    )
)


def _vufind(ctx: Contexto, base: str, anos: tuple[int, int]) -> dict[str, Any]:
    """Contagens no VuFind: total do período, recorte temático e soma das instituições do NE (por sigla)."""
    api = f"{base}/vufind/api/v1/search"
    periodo = ("filter[]", f'publishDate:"[{anos[0]} TO {anos[1]}]"')
    out: dict[str, Any] = {}
    resp = ctx.http.get(api, params=[("lookfor", "*"), ("limit", 0), periodo])
    out["status"], out["tempo_ms"] = resp.status, resp.tempo_ms
    out["total_periodo_brasil"] = resp.json().get("resultCount")
    tema = ctx.http.get_json(api, params=[("lookfor", TERMOS_BUSCA), ("type", "AllFields"), ("limit", 0), periodo, ("facet[]", "institution")])
    out["tema_periodo_todas_instituicoes"] = tema.get("resultCount")
    top = [(f["value"], f["count"]) for f in (tema.get("facets") or {}).get("institution", [])]
    out["top30_instituicoes_tema"] = top
    por_sigla: dict[str, int] = {}
    for sigla in SIGLAS_VUFIND_NE:
        try:
            d = ctx.http.get_json(api, params=[("lookfor", TERMOS_BUSCA), ("type", "AllFields"), ("limit", 0), periodo, ("filter[]", f'institution:"{sigla}"')])
            if d.get("resultCount"):
                por_sigla[sigla] = int(d["resultCount"])
        except Exception as e:  # noqa: BLE001
            out.setdefault("erros_sigla", {})[sigla] = str(e)[:200]
    out["tema_periodo_ne_por_sigla"] = dict(sorted(por_sigla.items(), key=lambda x: -x[1]))
    out["tema_periodo_ne"] = sum(por_sigla.values())
    nao_listadas = [(v, c) for v, c in top if eh_instituicao_ne(v) and v not in por_sigla]
    if nao_listadas:
        out["siglas_ne_no_top30_fora_da_lista"] = nao_listadas
    try:
        oai = ctx.http.get(f"{base}/vufind/OAI/Server", params={"verb": "Identify"})
        out["oai_pmh"] = {"url": f"{base}/vufind/OAI/Server", "status": oai.status}
    except Exception as e:  # noqa: BLE001
        out["oai_pmh"] = {"erro": str(e)}
    return out


def bdtd(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="bdtd",
        nome="BDTD/IBICT — Biblioteca Digital Brasileira de Teses e Dissertações",
        grupo="5. Produção científica",
        url_base="https://bdtd.ibict.br/vufind/",
        forma_acesso="API VuFind (JSON) e OAI-PMH",
        formato="JSON (API) / XML Dublin Core (OAI)",
        licenca="Metadados públicos; texto completo com licença de cada repositório",
        frequencia_atualizacao="Contínua (coleta dos repositórios institucionais)",
        identificadores=["Handle/URL do repositório", "nome do autor e orientador", "ID Lattes (às vezes no metadado)"],
    )
    d = _vufind(ctx, "https://bdtd.ibict.br", (ctx.cfg.year_start, ctx.cfg.year_end))
    r.registrar_resposta(d.pop("status"), d.pop("tempo_ms"))
    r.detalhes.update(d)
    r.registros_br = d.get("tema_periodo_ne")
    r.registros_obs = (
        f"teses/dissertações {ctx.anos} de instituições do NE (soma por sigla) com termos de saúde/biomédicas; "
        f"Brasil no tema: {d.get('tema_periodo_todas_instituicoes')}; Brasil no período, todos os temas: {d.get('total_periodo_brasil')}"
    )
    r.recomendacao = "complementar"
    r.justificativa = "Redundante em parte com o catálogo CAPES; útil para link ao texto completo."
    r.riscos.append("Metadados heterogêneos (Dublin Core); orientador nem sempre estruturado.")
    return r


def oasisbr(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="oasisbr",
        nome="Oasisbr/IBICT — portal agregador de produção científica brasileira em acesso aberto",
        grupo="5. Produção científica",
        url_base="https://oasisbr.ibict.br/vufind/",
        forma_acesso="API VuFind (JSON) e OAI-PMH",
        formato="JSON (API) / XML (OAI)",
        licenca="Metadados públicos; conteúdo com licença de cada fonte",
        frequencia_atualizacao="Contínua",
        identificadores=["DOI (parcial)", "Handle", "ISSN"],
    )
    d = _vufind(ctx, "https://oasisbr.ibict.br", (ctx.cfg.year_start, ctx.cfg.year_end))
    r.registrar_resposta(d.pop("status"), d.pop("tempo_ms"))
    r.detalhes.update(d)
    r.registros_br = d.get("tema_periodo_ne")
    r.registros_obs = (
        f"registros {ctx.anos} de instituições do NE (soma por sigla) com termos de saúde/biomédicas; "
        f"todas as instituições no tema: {d.get('tema_periodo_todas_instituicoes')}"
    )
    r.recomendacao = "complementar"
    r.justificativa = "Cobre repositórios e revistas nacionais fora do Crossref; muita duplicação com OpenAlex/BDTD."
    r.riscos.append("Agrega registros de várias fontes: duplicatas entre repositório, revista e BDTD.")
    return r


def scielo(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="scielo",
        nome="SciELO Brasil — periódicos (ArticleMeta) × works do recorte no OpenAlex",
        grupo="5. Produção científica",
        url_base="https://articlemeta.scielo.org/api/v1/",
        forma_acesso="API REST (JSON) + OAI-PMH",
        formato="JSON (ISIS/XYLOSE) / XML",
        licenca="Metadados abertos; artigos majoritariamente CC-BY",
        frequencia_atualizacao="Contínua",
        identificadores=["DOI", "PID SciELO", "ISSN", "ORCID (parcial, nos autores)"],
    )
    resp = ctx.http.get("https://articlemeta.scielo.org/api/v1/journal/identifiers/", params={"collection": "scl", "limit": 1000})
    r.registrar_resposta(resp.status, resp.tempo_ms)
    d = resp.json()
    issns = sorted({o.get("code") for o in d.get("objects", []) if o.get("code")})
    r.detalhes["periodicos_scl"] = len(issns)
    filtro = f"{_filtro_works(ctx)},publication_year:{ctx.anos}"
    total = 0
    for i in range(0, len(issns), 100):
        lote = "|".join(issns[i : i + 100])
        total += ctx.oa.contar("works", f"{filtro},primary_location.source.issn:{lote}")
    r.registros_br = total
    r.registros_obs = f"works do recorte publicados em periódicos do SciELO Brasil ({len(issns)} periódicos, via ISSN no OpenAlex)"
    try:
        art = ctx.http.get_json(
            "https://articlemeta.scielo.org/api/v1/article/identifiers/",
            params={"collection": "scl", "from": f"{ctx.cfg.year_start}-01-01", "until": f"{ctx.cfg.year_end}-12-31", "limit": 1},
        )
        r.detalhes["artigos_scl_processados_no_periodo"] = (art.get("meta") or {}).get("total")
    except Exception as e:  # noqa: BLE001
        r.erro("artigos scl", e)
    r.observacoes.append("ArticleMeta não filtra por região nem área; o recorte é medido cruzando os ISSNs dos periódicos com os works do OpenAlex.")
    r.observacoes.append("Esses works já estão no OpenAlex; o SciELO agrega resumo/afiliação em português e ORCID declarado no XML.")
    r.recomendacao = "complementar"
    r.justificativa = "Cruzar por DOI para enriquecer afiliações e resumos em português."
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [
    ("openalex_works", openalex_works),
    ("openalex_snapshot", openalex_snapshot),
    ("scielo", scielo),
    ("bdtd", bdtd),
    ("oasisbr", oasisbr),
]
