"""Grupo 6 — Fotos de pesquisadores (Wikidata P18 / Wikimedia Commons).

Google Acadêmico e Lattes estão fora por regra do projeto. A fonte principal de fotos será o
upload feito pelo próprio pesquisador ao reivindicar o perfil; o padrão é um avatar gerado
com as iniciais.
"""

from __future__ import annotations

import collections
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

from ..contexto import Contexto
from ..modelos import ResultadoFonte
from ..recorte import UFS_NORDESTE

WDQS = "https://query.wikidata.org/sparql"

_ISOS_NE = " ".join(f'"BR-{u.sigla}"' for u in UFS_NORDESTE)
_VINCULO_NE = f"""
  VALUES ?iso {{ {_ISOS_NE} }}
  ?uf wdt:P300 ?iso .
  ?org wdt:P131+ ?uf .
  ?p wdt:P496 ?orcid ; (wdt:P108|wdt:P1416) ?org .
"""

CONSULTA_CONTAGEM = f"""
SELECT (COUNT(DISTINCT ?p) AS ?total) (COUNT(DISTINCT ?pi) AS ?com_imagem) WHERE {{
  {_VINCULO_NE}
  OPTIONAL {{ ?p wdt:P18 ?img . BIND(?p AS ?pi) }}
}}
"""

CONSULTA_AMOSTRA_IMAGENS = f"""
SELECT DISTINCT ?img WHERE {{
  {_VINCULO_NE}
  ?p wdt:P18 ?img .
}} LIMIT 100
"""


def _sparql(ctx: Contexto, consulta: str) -> list[dict[str, Any]]:
    resp = ctx.http.get(WDQS, params={"query": consulta, "format": "json"}, cabecalhos={"Accept": "application/sparql-results+json"})
    if not resp.ok:
        raise RuntimeError(f"WDQS HTTP {resp.status}: {resp.texto()[:300]}")
    return list(resp.json()["results"]["bindings"])


def wikidata_fotos(ctx: Contexto) -> ResultadoFonte:
    r = ResultadoFonte(
        id="wikidata_fotos",
        nome="Wikidata (P18) + Wikimedia Commons — fotos de pesquisadores com ORCID e vínculo no Nordeste",
        grupo="6. Fotos",
        url_base=WDQS,
        forma_acesso="SPARQL (WDQS) + API MediaWiki do Commons",
        formato="JSON",
        licenca="Wikidata: CC0; imagens do Commons: licença por arquivo (CC-BY, CC-BY-SA, domínio público...)",
        frequencia_atualizacao="Contínua",
        identificadores=["Wikidata QID", "ORCID (P496)", "Lattes (P1007)", "Google Scholar (P1960)"],
    )
    linhas = _sparql(ctx, CONSULTA_CONTAGEM)
    st = ctx.http.chamadas[-1]
    r.registrar_resposta(st.status, st.tempo_ms)
    total = int(linhas[0]["total"]["value"]) if linhas else 0
    com_img = int(linhas[0]["com_imagem"]["value"]) if linhas else 0
    r.registros_br = com_img
    r.registros_obs = f"pessoas com ORCID e vínculo (P108/P1416) a organização localizada no NE: {total}; com imagem P18: {com_img}"
    r.detalhes["contagem"] = {"com_orcid_e_vinculo_ne": total, "com_imagem_p18": com_img, "pct": round(100 * com_img / total, 2) if total else None}
    # Licenças de uma amostra de imagens
    try:
        imgs = [b["img"]["value"] for b in _sparql(ctx, CONSULTA_AMOSTRA_IMAGENS)]
        nomes = [unquote(u.rsplit("/", 1)[-1]).replace("_", " ") for u in imgs]
        licencas: collections.Counter[str] = collections.Counter()
        for i in range(0, len(nomes), 25):
            lote = nomes[i : i + 25]
            d = ctx.http.get_json(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": "|".join(f"File:{n}" for n in lote),
                    "prop": "imageinfo",
                    "iiprop": "extmetadata",
                    "iiextmetadatafilter": "LicenseShortName",
                    "format": "json",
                },
            )
            for pg in (d.get("query") or {}).get("pages", {}).values():
                info = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
                licencas[(info.get("LicenseShortName") or {}).get("value", "desconhecida")] += 1
        r.detalhes["licencas_amostra"] = {"n": sum(licencas.values()), "distribuicao": dict(licencas.most_common())}
    except Exception as e:  # noqa: BLE001
        r.erro("licenças no Commons", e)
        if "HTTP 403" in str(e) and not ctx.cfg.contact_email:
            r.observacoes.append(
                "Commons respondeu 403: a política de User-Agent da Wikimedia exige contato no UA. "
                "Defina CONTACT_EMAIL no .env e rode `--fonte wikidata_fotos --sem-cache` para obter as licenças."
            )
    r.observacoes += [
        "Fonte principal de fotos: upload do próprio pesquisador ao reivindicar o perfil (consentimento explícito).",
        "Padrão para todos os perfis: avatar gerado com as iniciais (sem dado pessoal adicional).",
        "Wikidata/Commons só para quem já tem imagem com licença livre; exibir crédito e licença junto da foto.",
    ]
    r.riscos.append("CC-BY-SA exige atribuição e compartilhamento pela mesma licença da obra derivada (a miniatura WebP).")
    r.riscos.append("Cobertura muito pequena; foto é dado pessoal (LGPD): respeitar pedido de remoção.")
    r.riscos.append("A contagem não filtra por área (Wikidata não tem área de pesquisa confiável); o recorte de saúde é menor ainda.")
    r.recomendacao = "complementar"
    r.justificativa = "Cobertura baixa; usar só com licença livre e atribuição; upload próprio é a via principal."
    return r


AVALIACOES: list[tuple[str, Callable[[Contexto], ResultadoFonte]]] = [("wikidata_fotos", wikidata_fotos)]
