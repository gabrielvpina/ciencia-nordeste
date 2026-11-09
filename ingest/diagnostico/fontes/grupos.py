"""Grupo 3 — Grupos de pesquisa (DGP/CNPq, portais de universidades, via LAI).

Nesta parte NÃO acessamos o site do DGP (dgp.cnpq.br) nem a Plataforma Lattes: só procuramos
download oficial em portais de dados abertos.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

from ..contexto import Contexto
from ..http import BloqueadoPorRobots, analisar_amostra_csv
from ..modelos import ResultadoFonte

PALAVRAS = re.compile(r"grupo|dgp|diret[óo]rio|pesquisa", re.I)

PAGINAS_CNPQ = [
    "https://www.gov.br/cnpq/pt-br/acesso-a-informacao/dados-abertos",
    "https://dadosabertos.cnpq.br/",
]

UNIVERSIDADES = [
    ("UFRN", "https://dados.ufrn.br"),
    ("UFERSA", "https://dadosabertos.ufersa.edu.br"),
    ("UFPE", "https://dados.ufpe.br"),
    ("UFBA", "https://dados.ufba.br"),
    ("UFPB", "https://dadosabertos.ufpb.br"),
    ("UFCA", "https://dados.ufca.edu.br"),
    ("UFC", "https://dados.ufc.br"),
    ("UFS", "https://dados.ufs.br"),
    ("UFRB", "https://dados.ufrb.edu.br"),
    ("UNIVASF", "https://dados.univasf.edu.br"),
]

PALAVRAS_SAUDE = re.compile(
    r"sa[úu]de|medicina|m[ée]dic|enfermagem|odontolog|farm[áa]c|nutri[çc]|fisioterap|biol[óo]gic|gen[ée]tic|"
    r"biotecnolog|bioqu[íi]mic|imunolog|microbiolog|parasitolog|farmacolog|epidemiolog|biomed",
    re.I,
)


def _links(texto: str, base: str) -> list[dict[str, str]]:
    saida = []
    for href, rotulo in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', texto, re.S):
        rot = html.unescape(re.sub(r"<[^>]+>|\s+", " ", rotulo)).strip()
        saida.append({"href": urljoin(base, href), "rotulo": rot})
    return saida


def cnpq_dgp(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="cnpq_dgp",
        nome="CNPq — Diretório dos Grupos de Pesquisa (download oficial?)",
        grupo="3. Grupos de pesquisa",
        url_base=PAGINAS_CNPQ[0],
        forma_acesso="A verificar (portal de dados abertos do CNPq / dados.gov.br)",
        identificadores=["ID do grupo DGP", "Instituição", "Líderes (nome; ID Lattes no site)"],
    )
    achados: list[dict[str, str]] = []
    for url in PAGINAS_CNPQ:
        try:
            resp = ctx.http.get(url)
            r.registrar_resposta(resp.status, resp.tempo_ms)
            r.detalhes.setdefault("paginas", {})[url] = resp.status
            if resp.ok:
                links = _links(resp.texto(), url)
                rel = [lk for lk in links if re.search(r"grupo|dgp|diret[óo]rio dos grupos", lk["rotulo"] + " " + lk["href"], re.I)]
                arquivos = [lk for lk in links if re.search(r"\.(csv|zip|xlsx?|json)(\?|$)", lk["href"], re.I)]
                achados.extend(rel)
                r.detalhes.setdefault("links_dados", {})[url] = [lk for lk in links if re.search(r"dados|csv|bolsa|grupo|produtividade", lk["rotulo"] + lk["href"], re.I)][:40]
                r.detalhes.setdefault("arquivos_diretos", {})[url] = arquivos[:40]
        except Exception as e:  # noqa: BLE001
            r.erro(url, e)
    # dados.gov.br (exige token)
    hdrs = {"chave-api-dados-abertos": ctx.cfg.dados_gov_br_token} if ctx.cfg.dados_gov_br_token else {}
    try:
        resp = ctx.http.get(
            "https://dados.gov.br/dados/api/publico/conjuntos-dados",
            params={"nomeConjuntoDados": "grupos de pesquisa", "pagina": 1},
            cabecalhos=hdrs,
        )
        r.detalhes["dados_gov_br_status"] = resp.status
        if resp.ok:
            r.detalhes["dados_gov_br_resultado"] = resp.json()
    except Exception as e:  # noqa: BLE001
        r.erro("dados.gov.br", e)
    r.detalhes["links_sobre_grupos"] = achados
    if achados:
        r.observacoes.append(f"{len(achados)} link(s) mencionando grupos/DGP na página de dados abertos do CNPq (ver detalhes).")
    else:
        r.observacoes.append("Nenhum conjunto de dados do DGP para download em lote encontrado nas páginas de dados abertos do CNPq.")
    r.observacoes.append(
        "O DGP oferece consulta web (dgp.cnpq.br) e súmulas estatísticas dos censos; a base corrente não tem download em lote oficial conhecido."
    )
    r.riscos.append("Crawler do DGP violaria a regra do projeto (e os termos da Plataforma Lattes). Não fazer.")
    r.recomendacao = "precisa de acordo ou pedido LAI"
    r.justificativa = "Sem download oficial: pedir a base via Fala.BR (LAI) ou acordo com o CNPq."
    if r.acessivel is None:
        r.acessivel = False
    return r


def _buscar_ckan(ctx: Contexto, base: str, termo: str) -> dict[str, Any]:
    """Tenta a API CKAN (se o robots.txt permitir); se não, a página HTML de busca."""
    try:
        resp = ctx.http.get(f"{base}/api/3/action/package_search", params={"q": termo, "rows": 20})
        if resp.ok:
            d = resp.json()["result"]
            return {
                "via": "api_ckan",
                "status": resp.status,
                "tempo_ms": resp.tempo_ms,
                "total": d.get("count"),
                "titulos": [p.get("title") for p in d.get("results", [])],
                "detalhes": [
                    {
                        "titulo": p.get("title"),
                        "licenca": p.get("license_title"),
                        "modificado": p.get("metadata_modified"),
                        "recursos": [{"formato": x.get("format"), "url": x.get("url")} for x in p.get("resources", [])][:5],
                    }
                    for p in d.get("results", [])
                    if re.search(r"grupo", p.get("title") or "", re.I)
                ],
            }
    except BloqueadoPorRobots:
        pass
    except Exception:  # noqa: BLE001
        pass
    resp = ctx.http.get(f"{base}/dataset", params={"q": termo})
    pares = re.findall(r'class="dataset-heading"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.texto(), re.S)
    titulos = [html.unescape(re.sub(r"<[^>]+>", "", tt)).strip() for _, tt in pares]
    total = re.search(r"([\d\.]+)\s+conjuntos? de dados encontrados?", resp.texto(), re.I)
    detalhes = []
    for href, tt in pares:
        titulo = html.unescape(re.sub(r"<[^>]+>", "", tt)).strip()
        if not re.search(r"grupo", titulo, re.I):
            continue
        try:
            pag = ctx.http.get(urljoin(base + "/", href))
            csvs = sorted(set(re.findall(r'href="([^"]+\.csv)"', pag.texto(), re.I)))
            lic = re.search(r'rel="dc:rights"[^>]*>([^<]+)<', pag.texto())
            detalhes.append({"titulo": titulo, "licenca": html.unescape(lic.group(1)).strip() if lic else None, "recursos": [{"formato": "CSV", "url": urljoin(base + "/", c)} for c in csvs[:3]]})
        except Exception as e:  # noqa: BLE001
            detalhes.append({"titulo": titulo, "erro": str(e)})
    return {
        "via": "html",
        "status": resp.status,
        "tempo_ms": resp.tempo_ms,
        "total": int(total.group(1).replace(".", "")) if total else len(titulos),
        "titulos": titulos,
        "detalhes": detalhes,
    }


def universidades_grupos(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="universidades_grupos",
        nome=f"Portais de dados abertos de universidades do Nordeste (amostra de {len(UNIVERSIDADES)})",
        grupo="3. Grupos de pesquisa",
        url_base=", ".join(u for _, u in UNIVERSIDADES),
        forma_acesso="CKAN (API ou HTML) de cada universidade",
        formato="CSV/JSON (varia)",
        licenca="Varia por portal (em geral ODbL ou CC-BY)",
    )
    por_univ: dict[str, Any] = {}
    com_grupos = 0
    total_registros = 0
    total_saude = 0
    for sigla, base in UNIVERSIDADES:
        try:
            res = _buscar_ckan(ctx, base, "grupos de pesquisa")
            r.registrar_resposta(res.get("status"), res.get("tempo_ms"))
            tem = [t for t in res.get("titulos", []) if t and re.search(r"grupo", t, re.I)]
            res["titulos_com_grupo"] = tem
            if tem:
                com_grupos += 1
            # tamanho de recursos CSV dos conjuntos de grupos (só HEAD)
            for d in res.get("detalhes", []):
                for rec in d.get("recursos", []):
                    if rec.get("url") and (rec.get("formato") or "").upper() in ("CSV", "JSON"):
                        try:
                            tam, _ = ctx.http.tamanho_remoto(rec["url"])
                            rec["bytes"] = tam
                            if (rec.get("formato") or "").upper() == "CSV" and tam:
                                bruto = ctx.http.get(rec["url"], intervalo_bytes=(0, 256 * 1024 - 1), aceitar_status=(206,)).corpo
                                a = analisar_amostra_csv(bruto, tam)
                                a.pop("exemplo_primeira_linha", None)
                                rec["colunas"] = a.get("colunas")
                                rec["linhas_estimadas"] = a.get("linhas_estimadas")
                                linhas = [ln for ln in bruto.decode("utf-8", errors="replace").splitlines()[1:-1] if ln.strip()]
                                saude = sum(1 for ln in linhas if PALAVRAS_SAUDE.search(ln))
                                rec["fracao_saude_amostra"] = round(saude / len(linhas), 3) if linhas else None
                                est = a.get("linhas_estimadas") or 0
                                total_registros += est
                                total_saude += int(est * (saude / len(linhas))) if linhas else 0
                        except Exception as e:  # noqa: BLE001
                            rec["erro"] = str(e)
                        break
            res.pop("tempo_ms", None)
            por_univ[sigla] = {"base": base, **res}
        except Exception as e:  # noqa: BLE001
            por_univ[sigla] = {"base": base, "erro": f"{type(e).__name__}: {e}"}
    r.detalhes["por_universidade"] = por_univ
    r.registros_br = total_saude or None
    r.registros_obs = (
        f"grupos de saúde/biológicas estimados (palavras-chave na amostra) de ~{total_registros} grupos nos CSVs; "
        f"{com_grupos}/{len(UNIVERSIDADES)} portais com conjunto de grupos"
    )
    r.observacoes.append(f"{com_grupos} de {len(UNIVERSIDADES)} portais têm conjunto com 'grupo' no título.")
    r.riscos.append("Cobertura fragmentada: cada universidade publica com esquema, periodicidade e licença próprios; não escala para o país.")
    r.recomendacao = "complementar"
    r.justificativa = "Útil como piloto/validação regional; não substitui a base nacional do DGP."
    r.identificadores = ["Código do grupo no DGP (quando presente)", "Nome do líder"]
    return r


def fala_br_lai(ctx: Contexto) -> ResultadoFonte:  # noqa: ARG001
    r = ResultadoFonte(
        id="fala_br_lai",
        nome="Pedido via Lei de Acesso à Informação (Fala.BR) — base do DGP e bolsistas PQ",
        grupo="3. Grupos de pesquisa",
        url_base="https://falabr.cgu.gov.br/",
        forma_acesso="Pedido formal (LAI, Lei 12.527/2011)",
        formato="O que o órgão entregar (em geral CSV/XLSX)",
        licenca="Informação pública; reuso conforme LAI e LGPD",
        frequencia_atualizacao="Sob demanda (prazo legal: 20 dias + 10 de prorrogação)",
        identificadores=["ID do grupo DGP", "ID Lattes dos líderes (se fornecido)"],
        recomendacao="precisa de acordo ou pedido LAI",
        justificativa="Caminho legal para obter a base completa do DGP sem crawler.",
    )
    r.acessivel = None
    r.observacoes += [
        "Sugestão de pedido ao CNPq: grupos certificados ativos com instituição nos 9 estados do Nordeste e área predominante em Ciências da Saúde ou Ciências Biológicas (mais Biotecnologia/Genética): ID do grupo, nome, instituição, UF, município, área, ano de formação, líderes e linhas de pesquisa, em CSV.",
        "Pedir também a lista de bolsistas de produtividade (PQ/DT) vigentes com instituição, nível e área (dado de interesse público, já divulgado em resultados de chamadas).",
        "Dados pessoais além de nome e vínculo podem ser negados (LGPD): pedir só o necessário.",
    ]
    r.riscos.append("Prazo incerto e possível negativa parcial; resposta não vem com atualização periódica.")
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [
    ("cnpq_dgp", cnpq_dgp),
    ("universidades_grupos", universidades_grupos),
    ("fala_br_lai", fala_br_lai),
]
