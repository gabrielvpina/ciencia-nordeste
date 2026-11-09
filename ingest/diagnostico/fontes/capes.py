"""Grupo 2 — Programas de pós-graduação e docentes (CAPES, dadosabertos.capes.gov.br).

O robots.txt do portal bloqueia /api/ e pede Crawl-delay de 10 s. Por isso não usamos a API
CKAN: lemos a página HTML de cada conjunto (permitida), fazemos HEAD nos arquivos para o
tamanho e uma requisição Range (256 KB) no arquivo mais recente para colunas e estimativa
de linhas. O cliente HTTP aplica o intervalo de 10 s automaticamente.
"""

from __future__ import annotations

import collections
import html
import re
from typing import Any

from ..config import MAX_BYTES_DOWNLOAD
from ..contexto import Contexto
from ..http import ErroHttp, ler_csv_texto
from ..modelos import ResultadoFonte
from ..recorte import AREAS_AVALIACAO_CAPES, AREAS_AVALIACAO_CAPES_OPCIONAIS, SIGLAS_NE, eh_area_capes, normalizar

BASE = "https://dadosabertos.capes.gov.br"

CONJUNTOS: list[dict[str, Any]] = [
    {
        "id": "capes_programas",
        "nome": "CAPES — Programas de pós-graduação stricto sensu (2021–2024)",
        "slug": "2021-a-2024-programas-da-pos-graduacao-stricto-sensu-no-brasil",
        "anterior": "2017-a-2020-programas-da-pos-graduacao-stricto-sensu-no-brasil",
        "recomendacao": "usar",
        "justificativa": "Programas com conceito (nota), área de avaliação e código e-MEC da IES.",
    },
    {
        "id": "capes_docentes",
        "nome": "CAPES — Docentes da pós-graduação stricto sensu (2021–2024)",
        "slug": "2021-a-2024-docentes-da-pos-graduacao-stricto-sensu-no-brasil",
        "anterior": "2017-a-2020-docentes-da-pos-graduacao-stricto-sensu-no-brasil",
        "recomendacao": "usar",
        "justificativa": "Base de pessoas com ID_PESSOA estável da CAPES, vínculo ao programa e categoria de bolsa PQ.",
    },
    {
        "id": "capes_membros_projetos",
        "nome": "CAPES — Membros de projetos dos programas (2021–2024)",
        "slug": "2021-a-2024-membros-de-projetos-dos-programas-de-pos-graduacao-stricto-sensu-no-brasil",
        "anterior": "2017-a-2020-membros-de-projetos-dos-programas-de-pos-graduacao-stricto-sensu-no-brasil",
        "recomendacao": "complementar",
        "justificativa": "Liga pessoas a projetos; útil para colaboração, mas inclui discentes/externos.",
    },
    {
        "id": "capes_teses",
        "nome": "CAPES — Catálogo de teses e dissertações (2021–2024)",
        "slug": "2021-a-2024-catalogo-de-teses-e-dissertacoes-brasil",
        "anterior": "2017-2020-catalogo-de-teses-e-dissertacoes-da-capes",
        "recomendacao": "usar",
        "justificativa": "Autor e orientador por trabalho: gera relações de orientação (Parte 6).",
    },
    {
        "id": "capes_producao",
        "nome": "CAPES — Produção intelectual dos programas (2021–2024)",
        "slug": "2021-a-2024-producao-intelectual-de-pos-graduacao-stricto-sensu-no-brasil",
        "anterior": "2017-a-2020-producao-intelectual-de-pos-graduacao-stricto-sensu-no-brasil",
        "recomendacao": "complementar",
        "justificativa": "Produção declarada na Plataforma Sucupira; cruzar com OpenAlex por DOI.",
    },
    {
        "id": "capes_producao_bibliografica",
        "nome": "CAPES — Detalhes da produção bibliográfica (2021–2024)",
        "slug": "2021-a-2024-detalhes-da-producao-intelectual-bibliografica-de-programas-de-pos-graduacao",
        "anterior": "2017-a-2020-detalhes-da-producao-intelectual-bibliografica-de-programas-de-pos-graduacao",
        "recomendacao": "complementar",
        "justificativa": "Onde ficam DOI/ISSN/ISBN da produção bibliográfica.",
        "amostrar_todos": True,
    },
    {
        "id": "capes_autor_producao",
        "nome": "CAPES — Autores da produção intelectual (2021–2024)",
        "slug": "2021-a-2024-autor-da-producao-intelectual-de-programas-de-pos-graduacao-stricto-sensu-no-brasil",
        "anterior": "2017-a-2020-autor-da-producao-intelectual-de-programas-de-pos-graduacao-stricto-sensu",
        "recomendacao": "complementar",
        "justificativa": "Liga produção ↔ pessoa (ID_PESSOA): permite casar docente CAPES com autor OpenAlex via DOI.",
    },
]

PADROES_ID = {
    "capes_id_pessoa": r"^ID_PESSOA|^ID_PESSOA_",
    "orcid": r"ORCID",
    "lattes": r"LATTES",
    "doi": r"DOI",
    "cpf_mascarado": r"NR_DOCUMENTO|CPF",
    "codigo_emec": r"EMEC",
    "codigo_capes_entidade": r"CD_ENTIDADE_CAPES",
    "codigo_programa_capes": r"CD_PROGRAMA",
    "codigo_ibge_municipio": r"IBGE|CO_MUNICIPIO|CD_MUNICIPIO",
    "issn_isbn": r"ISSN|ISBN",
}


def _ler_pagina(ctx: Contexto, slug: str) -> dict[str, Any]:
    resp = ctx.http.get(f"{BASE}/dataset/{slug}")
    if not resp.ok:
        raise ErroHttp(f"HTTP {resp.status} na página do conjunto {slug}")
    t = resp.texto()
    downloads = sorted(set(re.findall(r'href="(https://dadosabertos\.capes\.gov\.br/dataset/[^"]+/download/[^"]+)"', t)))
    lic = re.search(r'rel="dc:rights"[^>]*>([^<]+)<', t)
    datas = re.search(r"Publicado:\s*([^,<]+),\s*Última Atualização:\s*([^<]+)<", t)
    extras = dict(
        (html.unescape(re.sub(r"<[^>]+>", "", k)).strip(), html.unescape(re.sub(r"<[^>]+>", "", v)).strip())
        for k, v in re.findall(r'<th[^>]*class="dataset-label"[^>]*>(.*?)</th>\s*<td[^>]*class="dataset-details"[^>]*>(.*?)</td>', t, re.S)
    )
    return {
        "status": resp.status,
        "tempo_ms": resp.tempo_ms,
        "downloads": downloads,
        "licenca": html.unescape(lic.group(1)).strip() if lic else "",
        "publicado": datas.group(1).strip() if datas else "",
        "atualizado": datas.group(2).strip() if datas else "",
        "extras": extras,
    }


def _anos_do_arquivo(url: str) -> list[int]:
    """Anos-base cobertos por um arquivo, a partir do nome.

    Ex.: 'br-capes-colsucup-docente-2024-2025-12-01.csv' -> [2024] (o 2º ano é a data de extração);
         'br-capes-colsucup-producao-2021a2024-2025-12-01-bibliografica-anais.csv' -> [2021..2024].
    """
    nome = url.rsplit("/", 1)[-1]
    faixa = re.search(r"(?<!\d)(20\d{2})a(20\d{2})(?!\d)", nome)
    if faixa:
        return list(range(int(faixa.group(1)), int(faixa.group(2)) + 1))
    anos = [int(a) for a in re.findall(r"(?<!\d)(20\d{2})(?!\d)", nome)]
    return anos[:1]


def _avaliar_conjunto(ctx: Contexto, c: dict[str, Any]) -> ResultadoFonte:
    r = ResultadoFonte(
        id=c["id"],
        nome=c["nome"],
        grupo="2. Pós-graduação (CAPES)",
        url_base=f"{BASE}/dataset/{c['slug']}",
        forma_acesso="Download de arquivo (portal CKAN; API /api/ bloqueada no robots.txt)",
        formato="CSV (;) e XLSX, um arquivo por ano-base",
        frequencia_atualizacao="Anual (coleta Sucupira)",
    )
    pag = _ler_pagina(ctx, c["slug"])
    r.registrar_resposta(pag["status"], pag["tempo_ms"])
    r.licenca = pag["licenca"] or "não informada na página"
    r.ultima_atualizacao = pag["atualizado"]
    r.detalhes["metadados_pagina"] = pag["extras"]
    csvs = [u for u in pag["downloads"] if u.lower().endswith(".csv")]
    if not csvs:
        csvs = [u for u in pag["downloads"] if not u.lower().endswith((".pdf", ".xlsx"))]
    arquivos: list[dict[str, Any]] = []
    for u in csvs:
        try:
            tam, resp = ctx.http.tamanho_remoto(u)
            anos_arq = _anos_do_arquivo(u)
            arquivos.append(
                {"url": u, "anos_base": anos_arq, "ano_base": max(anos_arq) if anos_arq else None, "bytes": tam, "ultima_modificacao": resp.cabecalhos.get("last-modified")}
            )
        except Exception as e:  # noqa: BLE001
            arquivos.append({"url": u, "erro": str(e)})
    r.detalhes["arquivos_csv"] = arquivos
    anos = sorted({ano for a in arquivos for ano in (a.get("anos_base") or [])})
    r.detalhes["anos_disponiveis"] = anos
    total = sum(a.get("bytes") or 0 for a in arquivos)
    r.tamanho_bytes = total or None
    r.tamanho_obs = f"{len(arquivos)} CSV(s), anos-base {anos[0]}–{anos[-1]}" if anos else f"{len(arquivos)} CSV(s)"
    acima = [a for a in arquivos if (a.get("bytes") or 0) > 50 * 1024 * 1024]
    if acima:
        r.observacoes.append(f"{len(acima)} arquivo(s) acima de 50 MB: só amostrados via Range.")
    # Amostra do arquivo mais recente (maior ano-base)
    com_tam = [a for a in arquivos if a.get("bytes")]
    if com_tam:
        recente = max(com_tam, key=lambda a: (a.get("ano_base") or 0, a["bytes"]))
        amostra = ctx.http.amostrar_csv(recente["url"], recente["bytes"])
        colunas_todas: dict[str, list[str]] = {}
        if c.get("amostrar_todos"):
            # Arquivos por subtipo (livro, artigo, anais...) têm colunas diferentes: lê o cabeçalho de todos.
            for a in com_tam:
                try:
                    colunas_todas[a["url"].rsplit("/", 1)[-1]] = ctx.http.amostrar_csv(a["url"], a["bytes"], n_bytes=16 * 1024).get("colunas", [])
                except Exception as e:  # noqa: BLE001
                    r.erro(f"cabeçalho {a['url']}", e)
            r.detalhes["colunas_por_arquivo"] = colunas_todas
        exemplo = amostra.pop("exemplo_primeira_linha", None)
        r.detalhes["amostra_arquivo_recente"] = {"url": recente["url"], **amostra}
        if exemplo:
            # só tipos/formatos, para não replicar dados pessoais no relatório
            r.detalhes["amostra_arquivo_recente"]["exemplo_valores_mascarados"] = {
                k: (v[:3] + "…" if isinstance(v, str) and len(v) > 3 and k.startswith(("NM_", "NR_")) else v) for k, v in exemplo.items()
            }
        cols = sorted(set(amostra.get("colunas", [])) | {col for cs in colunas_todas.values() for col in cs})
        ids = {nome: [col for col in cols if re.search(p, col, re.I)] for nome, p in PADROES_ID.items()}
        ids = {k: v for k, v in ids.items() if v}
        r.detalhes["colunas_identificadoras"] = ids
        r.identificadores = sorted(ids.keys())
        media = amostra.get("bytes_medios_por_linha")
        if media:
            # Linhas no Brasil dentro do período do recorte: cada arquivo pesa pela fração dos seus anos-base que cai no período.
            anos_rec = set(range(ctx.cfg.year_start, ctx.cfg.year_end + 1))
            bytes_periodo = 0.0
            for a in com_tam:
                ab = a.get("anos_base") or []
                if ab:
                    bytes_periodo += a["bytes"] * len(anos_rec & set(ab)) / len(ab)
            linhas_br = int(bytes_periodo / media)
            r.detalhes["linhas_brasil_no_periodo_estimadas"] = linhas_br
            r.detalhes["anos_no_periodo"] = sorted(anos_rec & set(anos))
            if c["id"] == "capes_programas":
                _recorte_programas(ctx, r, com_tam)
            else:
                frac = ctx.compartilhado.get("capes_frac_programas")
                if frac is not None:
                    r.registros_br = int(linhas_br * frac)
                    r.registros_obs = (
                        f"ESTIMATIVA: {linhas_br:,} linhas no Brasil em {', '.join(map(str, r.detalhes['anos_no_periodo']))} "
                        f"× {frac:.1%} (fatia de programas NE de saúde/biológicas)".replace(",", ".")
                    )
                else:
                    r.registros_obs = "rode também capes_programas para estimar o recorte"
    if not ctx.cfg.year_end or (anos and max(anos) < ctx.cfg.year_end):
        r.observacoes.append(f"Último ano-base publicado: {max(anos) if anos else '?'}; anos posteriores ainda não saíram (coleta Sucupira anual).")
    if "orcid" not in r.identificadores:
        r.observacoes.append("Sem coluna de ORCID.")
    if "lattes" not in r.identificadores:
        r.observacoes.append("Sem ID Lattes.")
    if ctx.cfg.year_start < 2021 and c.get("anterior"):
        r.observacoes.append(f"Ano-base {ctx.cfg.year_start} está no conjunto anterior: {BASE}/dataset/{c['anterior']}")
    r.recomendacao = c["recomendacao"]
    r.justificativa = c["justificativa"]
    if "capes_id_pessoa" in r.identificadores or "cpf_mascarado" in r.identificadores:
        r.riscos.append("Contém dados pessoais (nomes e IDs de pessoas; em docentes, ano de nascimento e CPF mascarado): tratar sob LGPD e não exibir campos sensíveis.")
    return r


def _recorte_programas(ctx: Contexto, r: ResultadoFonte, arquivos: list[dict[str, Any]]) -> None:
    """Baixa os CSVs de programas (pequenos) e conta exatamente o recorte NE × saúde/biológicas."""
    por_ano: dict[int, dict[str, Any]] = {}
    programas_rec: set[str] = set()
    por_uf: collections.Counter[str] = collections.Counter()
    por_area: collections.Counter[str] = collections.Counter()
    por_conceito: collections.Counter[str] = collections.Counter()
    por_ies: collections.Counter[str] = collections.Counter()
    areas_vistas: set[str] = set()
    for a in arquivos:
        ano = a.get("ano_base")
        if not ano or ano < ctx.cfg.year_start or a["bytes"] > MAX_BYTES_DOWNLOAD:
            continue
        resp = ctx.http.get(a["url"])
        try:
            texto = resp.corpo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = resp.corpo.decode("latin-1")
        linhas = ler_csv_texto(texto)
        total = len({lin.get("CD_PROGRAMA_IES") for lin in linhas})
        ne = [lin for lin in linhas if lin.get("SG_UF_PROGRAMA") in SIGLAS_NE]
        rec = [lin for lin in ne if eh_area_capes(lin.get("NM_AREA_AVALIACAO", ""))]
        areas_vistas |= {normalizar(lin.get("NM_AREA_AVALIACAO", "")) for lin in linhas}
        por_ano[ano] = {
            "programas_brasil": total,
            "programas_ne": len({lin.get("CD_PROGRAMA_IES") for lin in ne}),
            "programas_ne_saude": len({lin.get("CD_PROGRAMA_IES") for lin in rec}),
            "programas_brasil_saude": len({lin.get("CD_PROGRAMA_IES") for lin in linhas if eh_area_capes(lin.get("NM_AREA_AVALIACAO", ""))}),
            "programas_ne_areas_opcionais": len({lin.get("CD_PROGRAMA_IES") for lin in ne if normalizar(lin.get("NM_AREA_AVALIACAO", "")) in AREAS_AVALIACAO_CAPES_OPCIONAIS}),
        }
        if ano == max(x.get("ano_base") or 0 for x in arquivos):
            for lin in rec:
                por_uf[lin["SG_UF_PROGRAMA"]] += 1
                por_area[lin.get("NM_AREA_AVALIACAO", "")] += 1
                por_conceito[lin.get("CD_CONCEITO_PROGRAMA", "")] += 1
                por_ies[lin.get("SG_ENTIDADE_ENSINO", "")] += 1
        programas_rec |= {lin.get("CD_PROGRAMA_IES", "") for lin in rec}
    if not por_ano:
        raise ErroHttp("Nenhum arquivo de programas no período")
    ultimo = max(por_ano)
    u = por_ano[ultimo]
    frac = u["programas_ne_saude"] / u["programas_brasil"] if u["programas_brasil"] else 0.0
    ctx.compartilhado["capes_frac_programas"] = frac
    ctx.compartilhado["capes_programas_recorte"] = sorted(programas_rec)
    r.registros_br = u["programas_ne_saude"]
    r.registros_obs = (
        f"programas NE de saúde/biológicas no ano-base {ultimo} (exato; {len(programas_rec)} distintos em {min(por_ano)}–{ultimo}); "
        f"{frac:.1%} dos {u['programas_brasil']} programas do país"
    )
    r.detalhes["recorte_por_ano"] = por_ano
    r.detalhes["recorte_ultimo_ano"] = {
        "por_uf": dict(por_uf.most_common()),
        "por_area_avaliacao": dict(por_area.most_common()),
        "por_conceito": dict(sorted(por_conceito.items())),
        "top_ies": dict(por_ies.most_common(15)),
    }
    r.detalhes["fracao_programas_recorte"] = frac
    faltando = [a for a in AREAS_AVALIACAO_CAPES if a not in areas_vistas]
    if faltando:
        r.riscos.append(f"Áreas de avaliação da lista não encontradas nos dados (conferir grafia): {', '.join(faltando)}")


def _fabrica(c: dict[str, Any]):  # type: ignore[no-untyped-def]
    def avaliar(ctx: Contexto) -> ResultadoFonte:
        return _avaliar_conjunto(ctx, c)

    avaliar.__name__ = c["id"]
    return avaliar


AVALIACOES = [(c["id"], _fabrica(c)) for c in CONJUNTOS]
