"""Grupo 1 — Instituições do Nordeste: OpenAlex, ROR, e-MEC/INEP, IBGE."""

from __future__ import annotations

import collections
import csv
import io
import re
import zipfile
from collections.abc import Callable
from typing import Any

from ..config import MAX_BYTES_DOWNLOAD
from ..contexto import Contexto
from ..http import ErroHttp
from ..modelos import ResultadoFonte
from ..recorte import CODIGOS_IBGE_NE, SIGLAS_NE, UFS_NORDESTE, filtro_openalex_regioes

ROR_CONCEPT_DOI = "https://doi.org/10.5281/zenodo.6347574"  # DOI-conceito do "ROR Data" (sempre a última versão)
FILTRO_INST_NE = f"country_code:BR,{filtro_openalex_regioes('geo.region')}"
NOME_PARA_SIGLA = {u.nome: u.sigla for u in UFS_NORDESTE}

# INEP: TP_CATEGORIA_ADMINISTRATIVA (dicionário do Censo): 1 federal, 2 estadual, 3 municipal = pública; demais privadas.
CATEGORIA_PUBLICA = {"1", "2", "3"}
# INEP cursos: área geral CINE 09 = Saúde e bem-estar; área 05 inclui ciências biológicas (051).
CINE_SAUDE = "09"
CINE_BIOLOGICAS = "051"
CINE_AGRARIAS = "08"  # agricultura, silvicultura, pesca e veterinária (D-017)


def openalex_institutions(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="openalex_institutions",
        nome="OpenAlex /institutions (Nordeste)",
        grupo="1. Instituições",
        url_base="https://api.openalex.org/institutions",
        forma_acesso="API REST (JSON) + snapshot S3",
        formato="JSON / JSONL.gz / Parquet",
        licenca="CC0 1.0",
        frequencia_atualizacao="API contínua; snapshot público trimestral",
        identificadores=["OpenAlex ID", "ROR", "Wikidata", "GRID (legado)"],
    )
    total = ctx.oa.contar("institutions", FILTRO_INST_NE)
    r.registrar_resposta(200, None)
    r.registros_br = total
    r.registros_obs = "instituições BR com geo.region num dos 9 estados do Nordeste"
    r.detalhes["filtro"] = FILTRO_INST_NE
    r.detalhes["por_tipo"] = ctx.oa.agrupar("institutions", "type", FILTRO_INST_NE)
    r.detalhes["por_estado_geo_region"] = ctx.oa.agrupar("institutions", "geo.region", FILTRO_INST_NE)
    r.detalhes["total_br"] = ctx.oa.contar("institutions", "country_code:BR")
    try:
        r.detalhes["br_sem_geo_region"] = ctx.oa.contar("institutions", "country_code:BR,geo.region:null")
    except ErroHttp as e:
        r.erro("contagem sem geo.region", e)
    amostra = ctx.oa.consultar(
        "institutions", filter=FILTRO_INST_NE, per_page=25, select="id,display_name,ror,type,geo,works_count", sort="works_count:desc"
    )
    res = amostra.get("results", [])
    r.detalhes["top25_por_works"] = [
        {"nome": i["display_name"], "tipo": i.get("type"), "cidade": (i.get("geo") or {}).get("city"), "uf": NOME_PARA_SIGLA.get((i.get("geo") or {}).get("region", ""), ""), "works": i.get("works_count")}
        for i in res
    ]
    com_coord = sum(1 for i in res if (i.get("geo") or {}).get("latitude") is not None)
    r.observacoes.append(f"{com_coord}/{len(res)} das 25 maiores têm latitude/longitude.")
    sem = r.detalhes.get("br_sem_geo_region")
    if sem:
        r.riscos.append(
            f"{sem} de {r.detalhes['total_br']} instituições BR estão sem geo.region no OpenAlex e não entram no filtro por estado; "
            "a validação pela lista do ROR (fonte 'ror') mede quanto isso afeta o recorte."
        )
    r.riscos.append("Sem código e-MEC/CNPJ: o cruzamento com INEP/CAPES será por nome+município (fila de revisão) ou via Wikidata.")
    r.recomendacao = "usar"
    r.justificativa = "Base principal de instituições ligadas à produção; ROR como chave de cruzamento."
    return r


def ror(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="ror",
        nome="ROR — Research Organization Registry (dump Zenodo), Nordeste",
        grupo="1. Instituições",
        url_base=ROR_CONCEPT_DOI,
        forma_acesso="Download de arquivo (Zenodo) e API REST",
        formato="ZIP com JSON e CSV (schema v2)",
        licenca="CC0 1.0",
        frequencia_atualizacao="Dump a cada release (aprox. mensal)",
        identificadores=["ROR", "GRID", "ISNI", "Wikidata", "Crossref Funder ID", "GeoNames"],
    )
    resp = ctx.http.get(ROR_CONCEPT_DOI)
    r.registrar_resposta(resp.status, resp.tempo_ms)
    m = re.search(r"/records/(\d+)", resp.url_final or "")
    if not m:
        raise ErroHttp(f"Não achei o registro do Zenodo a partir do DOI-conceito (url final: {resp.url_final})")
    rec_id = m.group(1)
    exp = ctx.http.get_json(f"https://zenodo.org/records/{rec_id}/export/json")
    md = exp.get("metadata", {})
    r.ultima_atualizacao = md.get("publication_date", "")
    r.detalhes["zenodo_registro"] = f"https://zenodo.org/records/{rec_id}"
    zips = {k: v for k, v in exp.get("files", {}).get("entries", {}).items() if k.endswith(".zip")}
    if not zips:
        raise ErroHttp("Registro do Zenodo sem .zip")
    nome_zip, info = next(iter(zips.items()))
    tamanho = int(info.get("size") or 0)
    r.tamanho_bytes = tamanho
    r.tamanho_obs = f"{nome_zip} (comprimido; o arquivo é mundial)"
    if not tamanho or tamanho > MAX_BYTES_DOWNLOAD:
        raise ErroHttp(f"Dump com {tamanho} bytes: acima do limite da Parte 0")
    z = ctx.http.get(f"https://zenodo.org/records/{rec_id}/files/{nome_zip}?download=1")
    zf = zipfile.ZipFile(io.BytesIO(z.corpo))
    nome_csv = next(n for n in zf.namelist() if n.endswith(".csv"))
    analise = _analisar_csv_ror(zf.read(nome_csv).decode("utf-8"))
    rors_ne = analise.pop("_rors_ne")
    r.detalhes.update(analise)
    r.registros_br = analise["organizacoes_ne"]
    r.registros_obs = "organizações do Nordeste no dump (country_subdivision_code)"
    ctx.compartilhado["rors_ne"] = rors_ne

    # Validação: quantas organizações NE do ROR o filtro do OpenAlex por geo.region deixa de fora?
    try:
        r.detalhes["validacao_openalex"] = _validar_openalex(ctx, rors_ne)
        v = r.detalhes["validacao_openalex"]
        r.observacoes.append(
            f"Das {v['encontradas_no_openalex']} organizações NE do ROR que existem no OpenAlex, {v['sem_geo_region_ne']} não têm geo.region de estado do NE "
            f"({v['works_fora_do_filtro_pct']:.1f}% dos works dessas instituições ficariam fora de um filtro só por geo.region)."
        )
    except Exception as e:  # noqa: BLE001
        r.erro("validação ROR × OpenAlex", e)
    r.recomendacao = "usar"
    r.justificativa = "Lista canônica das organizações do NE com estado, coordenadas e IDs externos; serve para filtrar o OpenAlex por ROR."
    r.riscos.append("ROR não tem código e-MEC/INEP nem código IBGE; faculdades privadas pequenas quase não aparecem.")
    return r


def _analisar_csv_ror(texto: str) -> dict[str, Any]:
    leitor = csv.DictReader(io.StringIO(texto))
    colunas = leitor.fieldnames or []
    c_pais = "locations.geonames_details.country_code"
    c_uf = "locations.geonames_details.country_subdivision_code"
    c_lat = "locations.geonames_details.lat"
    total_br = 0
    ne: list[str] = []
    por_uf: collections.Counter[str] = collections.Counter()
    tipos: collections.Counter[str] = collections.Counter()
    ativos = 0
    com_lat = 0
    com_wikidata = 0
    exemplos_uf: set[str] = set()
    for linha in leitor:
        if "BR" not in (linha.get(c_pais) or "").split(";"):
            continue
        total_br += 1
        uf = (linha.get(c_uf) or "").split(";")[0].replace("BR-", "").strip()
        exemplos_uf.add(uf)
        if uf not in SIGLAS_NE:
            continue
        ne.append(linha.get("id", ""))
        por_uf[uf] += 1
        if linha.get("status") == "active":
            ativos += 1
        for t in (linha.get("types") or "").split(";"):
            tipos[t.strip()] += 1
        if linha.get(c_lat):
            com_lat += 1
        if linha.get("external_ids.type.wikidata.all") or linha.get("external_ids.type.wikidata.preferred"):
            com_wikidata += 1
    return {
        "organizacoes_br": total_br,
        "organizacoes_ne": len(ne),
        "organizacoes_ne_ativas": ativos,
        "ne_por_uf": dict(por_uf.most_common()),
        "ne_por_tipo": dict(tipos.most_common()),
        "ne_com_coordenadas": com_lat,
        "ne_com_wikidata": com_wikidata,
        "valores_subdivisao_vistos": sorted(exemplos_uf)[:40],
        "colunas_csv": colunas,
        "_rors_ne": ne,
    }


def _validar_openalex(ctx: Contexto, rors: list[str]) -> dict[str, Any]:
    encontradas = 0
    sem_regiao = 0
    works_total = 0
    works_fora = 0
    exemplos: list[dict[str, Any]] = []
    ids_fora: list[str] = []
    for i in range(0, len(rors), 100):
        lote = [x.rsplit("/", 1)[-1] for x in rors[i : i + 100]]
        d = ctx.oa.consultar("institutions", filter="ror:" + "|".join(lote), per_page=100, select="id,display_name,ror,geo,works_count,type")
        for inst in d.get("results", []):
            encontradas += 1
            w = inst.get("works_count") or 0
            works_total += w
            if (inst.get("geo") or {}).get("region") not in NOME_PARA_SIGLA:
                sem_regiao += 1
                ids_fora.append(inst["id"].rsplit("/", 1)[-1])
                works_fora += w
                exemplos.append({"nome": inst["display_name"], "region": (inst.get("geo") or {}).get("region"), "works": w})
    exemplos.sort(key=lambda x: -x["works"])
    ctx.compartilhado["openalex_ids_ne_sem_regiao"] = ids_fora
    return {
        "rors_ne": len(rors),
        "encontradas_no_openalex": encontradas,
        "sem_geo_region_ne": sem_regiao,
        "works_total": works_total,
        "works_fora_do_filtro": works_fora,
        "works_fora_do_filtro_pct": 100 * works_fora / works_total if works_total else 0.0,
        "maiores_fora_do_filtro": exemplos[:10],
    }


def inep_censo_superior(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="inep_censo_superior",
        nome="INEP — Censo da Educação Superior (cadastro de IES e cursos), Nordeste",
        grupo="1. Instituições",
        url_base="https://download.inep.gov.br/microdados/",
        forma_acesso="Download de arquivo ZIP (HTTP); leitura parcial por Range",
        formato="ZIP com CSV (separador ;) + dicionário XLSX",
        licenca="Dados públicos (Lei 12.527/2011, LAI); uso livre com citação da fonte",
        frequencia_atualizacao="Anual (ano-base t publicado em t+1)",
        identificadores=["CO_IES (= código e-MEC)", "CO_MUNICIPIO (IBGE 7 dígitos)", "CO_MANTENEDORA"],
    )
    anos: dict[int, Any] = {}
    for ano in range(ctx.cfg.year_start - 1, ctx.cfg.year_end + 1):
        url = f"https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_{ano}.zip"
        try:
            tam, resp = ctx.http.tamanho_remoto(url)
            if resp.ok and tam:
                anos[ano] = {"url": url, "bytes": tam, "ultima_modificacao": resp.cabecalhos.get("last-modified")}
                r.registrar_resposta(resp.status, resp.tempo_ms)
            else:
                anos[ano] = {"url": url, "status": resp.status}
        except Exception as e:  # noqa: BLE001
            anos[ano] = {"url": url, "erro": str(e)}
    r.detalhes["arquivos_por_ano"] = anos
    disponiveis = [a for a, v in anos.items() if v.get("bytes")]
    if not disponiveis:
        raise ErroHttp("Nenhum arquivo de microdados encontrado")
    ultimo = max(disponiveis)
    url = anos[ultimo]["url"]
    r.tamanho_bytes = anos[ultimo]["bytes"]
    r.tamanho_obs = f"ZIP {ultimo} (nacional); da tabela de IES só ~1 MB é lido"
    r.ultima_atualizacao = f"ano-base {ultimo} ({anos[ultimo].get('ultima_modificacao')})"
    entradas = ctx.http.listar_zip(url, anos[ultimo]["bytes"])
    r.detalhes["conteudo_zip_ultimo"] = [{k: e[k] for k in ("nome", "comprimido", "descomprimido")} for e in entradas]

    ies = next((e for e in entradas if re.search(r"IES.*\.csv$", e["nome"], re.I)), None)
    if not ies:
        raise ErroHttp("Tabela de IES não encontrada no ZIP")
    linhas = list(csv.DictReader(io.StringIO(ctx.http.arquivo_inteiro_do_zip(url, ies).decode("latin-1")), delimiter=";"))
    ne = [lin for lin in linhas if lin.get("SG_UF_IES") in SIGLAS_NE]
    ies_ne = {lin["CO_IES"] for lin in ne}
    r.registros_br = len(ne)
    r.registros_obs = f"IES com sede no Nordeste no ano-base {ultimo} (de {len(linhas)} no Brasil), contagem exata"
    r.detalhes["ies_ne_por_uf"] = dict(collections.Counter(lin["SG_UF_IES"] for lin in ne).most_common())
    r.detalhes["ies_ne_publicas"] = sum(1 for lin in ne if lin.get("TP_CATEGORIA_ADMINISTRATIVA") in CATEGORIA_PUBLICA)
    r.detalhes["ies_ne_por_organizacao_academica"] = dict(collections.Counter(lin.get("TP_ORGANIZACAO_ACADEMICA") for lin in ne).most_common())
    r.detalhes["ies_ne_municipios_ibge_validos"] = sum(1 for lin in ne if (lin.get("CO_MUNICIPIO_IES") or "")[:2].isdigit() and int(lin["CO_MUNICIPIO_IES"][:2]) in CODIGOS_IBGE_NE)

    # Cursos: quais IES do NE oferecem cursos de saúde/biológicas (CINE)?
    cursos = next((e for e in entradas if re.search(r"CADASTRO_CURSOS.*\.csv$", e["nome"], re.I)), None)
    if cursos:
        r.detalhes["tabela_cursos"] = {"arquivo": cursos["nome"], "comprimido": cursos["comprimido"], "descomprimido": cursos["descomprimido"]}
        if cursos["comprimido"] > MAX_BYTES_DOWNLOAD:
            r.observacoes.append(
                f"Tabela de cursos ({cursos['comprimido'] / 1e6:.0f} MB, gravada sem compressão no ZIP) passa do limite da Parte 0: "
                "a contagem de IES do NE com cursos de saúde (CINE 09/051) fica para a Parte 1."
            )
        else:
            try:
                texto = ctx.http.arquivo_inteiro_do_zip(url, cursos).decode("latin-1")
                leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
                col_cine = next((c for c in (leitor.fieldnames or []) if c.startswith("CO_CINE_AREA_GERAL")), None)
                col_cine_esp = next((c for c in (leitor.fieldnames or []) if c.startswith("CO_CINE_AREA_ESPECIFICA")), None)
                ies_saude: set[str] = set()
                n_cursos = 0
                for lin in leitor:
                    if lin.get("CO_IES") not in ies_ne:
                        continue
                    geral = (lin.get(col_cine) or "").zfill(2) if col_cine else ""
                    esp = (lin.get(col_cine_esp) or "").zfill(3) if col_cine_esp else ""
                    if geral in (CINE_SAUDE, CINE_AGRARIAS) or esp == CINE_BIOLOGICAS:
                        ies_saude.add(lin["CO_IES"])
                        n_cursos += 1
                r.detalhes["ies_ne_com_cursos_saude_ou_biologicas"] = len(ies_saude)
                r.detalhes["cursos_saude_ou_biologicas_ne"] = n_cursos
                r.observacoes.append(
                    f"{len(ies_saude)} das {len(ne)} IES do NE oferecem cursos de Saúde e bem-estar (CINE 09) ou Ciências Biológicas (CINE 051); "
                    f"{n_cursos} registros de curso."
                )
            except Exception as e:  # noqa: BLE001
                r.erro("tabela de cursos", e)
    r.recomendacao = "usar"
    r.justificativa = "Cadastro oficial de IES com código e-MEC, natureza e município IBGE; os cursos mostram quais atuam em saúde."
    r.riscos.append("Não tem ROR: cruzamento com OpenAlex/ROR por nome+município (fila de revisão) ou via Wikidata.")
    r.riscos.append("Só cobre IES; Fiocruz, hospitais, Lacens e institutos de pesquisa ficam de fora (vêm de ROR/OpenAlex).")
    return r


def emec_dados_gov(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="emec_dados_gov",
        nome="Cadastro e-MEC via dados.gov.br (API do portal)",
        grupo="1. Instituições",
        url_base="https://dados.gov.br/dados/api/publico/conjuntos-dados",
        forma_acesso="API do portal dados.gov.br (exige token chave-api-dados-abertos)",
        formato="CSV (recursos do conjunto)",
        licenca="Varia por conjunto (em geral Licença Aberta/CC-BY)",
        identificadores=["Código e-MEC da IES", "Código do curso", "Município"],
    )
    hdrs = {"chave-api-dados-abertos": ctx.cfg.dados_gov_br_token} if ctx.cfg.dados_gov_br_token else {}
    resp = ctx.http.get("https://dados.gov.br/dados/api/publico/conjuntos-dados", params={"nomeConjuntoDados": "e-mec", "pagina": 1}, cabecalhos=hdrs)
    r.registrar_resposta(resp.status, resp.tempo_ms)
    r.acessivel = resp.ok
    if resp.status in (401, 403):
        r.observacoes.append(f"dados.gov.br respondeu HTTP {resp.status}: a API exige token gerado com login gov.br (DADOS_GOV_BR_TOKEN no .env).")
    r.recomendacao = "complementar"
    r.justificativa = "O Censo da Educação Superior (INEP) já traz o cadastro com código e-MEC; dados.gov.br só se precisarmos de cursos atualizados."
    r.riscos.append("emec.mec.gov.br é sistema de consulta (sem download em lote); não fazer crawler.")
    return r


def ibge_municipios(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="ibge_municipios",
        nome="IBGE — municípios do Nordeste (API de Localidades) + coordenadas das sedes",
        grupo="1. Instituições",
        url_base="https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
        forma_acesso="API REST (JSON) + arquivo CSV",
        formato="JSON; CSV para coordenadas",
        licenca="IBGE: dados públicos, uso livre com citação da fonte",
        frequencia_atualizacao="Anual (DTB) / quando há novos municípios",
        identificadores=["Código IBGE do município (7 dígitos)", "Código UF"],
    )
    resp = ctx.http.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios")
    r.registrar_resposta(resp.status, resp.tempo_ms)
    if resp.ok:
        munis = resp.json()
        ne = [m for m in munis if int(str(m["id"])[:2]) in CODIGOS_IBGE_NE]
        r.registros_br = len(ne)
        r.registros_obs = f"municípios do Nordeste (de {len(munis)} no Brasil)"
        r.tamanho_bytes = len(resp.corpo)
        r.tamanho_obs = "JSON nacional da API de localidades"
        r.detalhes["ne_por_uf"] = dict(collections.Counter(str(m["id"])[:2] for m in ne))
        r.observacoes.append("API de Localidades não traz latitude/longitude.")
    url_kelvins = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    try:
        tam, resp2 = ctx.http.tamanho_remoto(url_kelvins)
        if resp2.status in (200, 206):
            a = ctx.http.amostrar_csv(url_kelvins, tam, n_bytes=16 * 1024)
            r.detalhes["coordenadas_kelvins"] = {"url": url_kelvins, "bytes": tam, "colunas": a["colunas"], "linhas_estimadas": a["linhas_estimadas"], "licenca": "MIT (dados derivados do IBGE)"}
            r.observacoes.append("Coordenadas das sedes: CSV kelvins/municipios-brasileiros (MIT, derivado do IBGE), com código IBGE.")
    except Exception as e:  # noqa: BLE001
        r.erro("CSV de coordenadas (kelvins)", e)
    r.recomendacao = "usar"
    r.justificativa = "Código IBGE é a chave de geolocalização; coordenadas da sede municipal resolvem o mapa por cidade."
    r.riscos.append("Coordenada é da sede do município, não do campus; para campus usar ROR/OpenAlex quando existir.")
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [
    ("openalex_institutions", openalex_institutions),
    ("ror", ror),
    ("inep_censo_superior", inep_censo_superior),
    ("emec_dados_gov", emec_dados_gov),
    ("ibge_municipios", ibge_municipios),
]
