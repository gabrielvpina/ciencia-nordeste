"""Parte 7 — Fotos de pesquisadores (Wikidata P18 → Wikimedia Commons, só licença livre).

Regras (SCHEME.md §13, D-008): nada de Lattes ou Google Acadêmico; só imagens do Commons com licença livre
(CC0, domínio público, CC BY, CC BY-SA), com crédito e licença gravados para exibição. Conversão para WebP,
lado máximo 400 px, qualidade ~80, sem metadados EXIF. O padrão de todo perfil é o avatar com iniciais; o upload
próprio entra na Fase D.

Busca: ORCIDs dos pesquisadores do recorte → Wikidata (P496 + P18) em lotes com VALUES (consultas leves).
Saídas: ingest/dados/fotos/<researcher_id>.webp, ingest/dados/processados/researcher_photos.csv,
relatório ingest/relatorios/parte7_fotos.md.

Uso:
    python -m ingest.carga.parte7_fotos [--lote 200] [--limite-lotes N] [-v]
"""

from __future__ import annotations

import argparse
import collections
import html
import io
import json
import logging
import re
import sys
from typing import Any
from urllib.parse import unquote

from PIL import Image

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp
from .comum import AGORA, DIR_DADOS, DIR_PROCESSADOS, DIR_RELATORIOS, escrever_csv, ler_csv

log = logging.getLogger("ingest.parte7")

WDQS = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DIR_FOTOS = DIR_DADOS / "fotos"
LADO_MAX = 400
QUALIDADE = 80
LICENCAS_LIVRES = re.compile(r"^(CC0|CC[- ]?Zero|Public domain|PD\b|PD-|CC BY(-SA)?( \d(\.\d)?)?|Attribution)", re.I)


def orcids_do_recorte() -> dict[str, str]:
    """ORCID -> researcher_id (canônico, após consolidação)."""
    out: dict[str, str] = {}
    for r in ler_csv(DIR_PROCESSADOS / "researcher_identifiers.csv"):
        if r["scheme"] == "orcid" and re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", r["value"]):
            out.setdefault(r["value"], r["researcher_id"])
    return out


def buscar_wikidata(http: ClienteHttp, orcids: list[str], lote: int, limite_lotes: int | None) -> dict[str, list[str]]:
    achados: dict[str, list[str]] = collections.defaultdict(list)
    lotes = [orcids[i : i + lote] for i in range(0, len(orcids), lote)]
    if limite_lotes:
        lotes = lotes[:limite_lotes]
    for n, grupo in enumerate(lotes):
        valores = " ".join(f'"{o}"' for o in grupo)
        consulta = f"SELECT ?orcid ?img WHERE {{ VALUES ?orcid {{ {valores} }} ?item wdt:P496 ?orcid ; wdt:P18 ?img . }}"
        r = http.get(WDQS, params={"query": consulta, "format": "json"}, cabecalhos={"Accept": "application/sparql-results+json"})
        if not r.ok:
            log.warning("WDQS lote %d: HTTP %s", n, r.status)
            continue
        for b in r.json()["results"]["bindings"]:
            achados[b["orcid"]["value"]].append(unquote(b["img"]["value"].rsplit("/", 1)[-1]).replace("_", " "))
        if n % 50 == 0:
            log.info("Wikidata: lote %d/%d, %d ORCIDs com imagem até agora", n + 1, len(lotes), len(achados))
    return achados


def metadados_commons(http: ClienteHttp, titulos: list[str]) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for i in range(0, len(titulos), 50):
        lote = titulos[i : i + 50]
        d = http.get_json(
            COMMONS_API,
            params={
                "action": "query", "format": "json", "titles": "|".join(f"File:{t}" for t in lote), "prop": "imageinfo",
                "iiprop": "url|size|extmetadata", "iiurlwidth": LADO_MAX,
                "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit|Restrictions|AttributionRequired|UsageTerms",
            },
        )
        normalizados = {n["to"]: n["from"] for n in (d.get("query") or {}).get("normalized", [])}
        for pg in (d.get("query") or {}).get("pages", {}).values():
            info = (pg.get("imageinfo") or [{}])[0]
            em = info.get("extmetadata") or {}
            v = lambda k: html.unescape(re.sub(r"<[^>]+>", "", (em.get(k) or {}).get("value", ""))).strip()  # noqa: E731
            titulo = normalizados.get(pg.get("title", ""), pg.get("title", "")).removeprefix("File:")
            meta[titulo] = {
                "thumburl": info.get("thumburl"), "pagina": info.get("descriptionurl"), "licenca": v("LicenseShortName"),
                "licenca_url": v("LicenseUrl"), "autor": v("Artist") or v("Credit"), "restricoes": v("Restrictions"),
            }
    return meta


def converter_webp(bruto: bytes, destino: Any) -> tuple[int, int]:
    img: Image.Image = Image.open(io.BytesIO(bruto))
    img = img.convert("RGB")  # descarta alfa e paleta; EXIF não é copiado no save abaixo
    img.thumbnail((LADO_MAX, LADO_MAX))
    img.save(destino, "WEBP", quality=QUALIDADE, method=6)  # sem exif= nem icc_profile=: nenhum metadado é gravado
    return img.size


def executar(lote: int, limite_lotes: int | None) -> dict[str, Any]:
    cfg = carregar_config()
    if not cfg.contact_email:
        raise SystemExit("Defina CONTACT_EMAIL no .env: a Wikimedia exige contato no User-Agent")
    orcids = orcids_do_recorte()
    log.info("ORCIDs no recorte: %d", len(orcids))
    http = ClienteHttp(cfg)
    linhas: list[dict[str, Any]] = []
    c: collections.Counter[str] = collections.Counter()
    try:
        achados = buscar_wikidata(http, sorted(orcids), lote, limite_lotes)
        primeiros = {o: imgs[0] for o, imgs in achados.items()}
        meta = metadados_commons(http, sorted(set(primeiros.values())))
        DIR_FOTOS.mkdir(parents=True, exist_ok=True)
        for orcid, titulo in sorted(primeiros.items()):
            m = meta.get(titulo)
            rid = orcids[orcid]
            if not m or not m.get("thumburl"):
                c["sem_metadados"] += 1
                continue
            if not LICENCAS_LIVRES.match(m["licenca"] or ""):
                c["licenca_nao_livre"] += 1
                log.info("Ignorada (licença '%s'): %s", m["licenca"], titulo)
                continue
            try:
                r = http.get(m["thumburl"])
                if not r.ok:
                    c["download_falhou"] += 1
                    continue
                destino = DIR_FOTOS / f"{rid}.webp"
                w, h = converter_webp(r.corpo, destino)
            except Exception as e:  # noqa: BLE001
                log.warning("Falha em %s: %s", titulo, e)
                c["conversao_falhou"] += 1
                continue
            c["ok"] += 1
            c[f"licenca:{m['licenca']}"] += 1
            if m["restricoes"]:
                c[f"restricao:{m['restricoes']}"] += 1
            linhas.append(
                {
                    "researcher_id": rid, "source": "wikimedia_commons", "file_name": destino.name, "source_title": titulo,
                    "source_page_url": m["pagina"], "license": m["licenca"], "license_url": m["licenca_url"], "author": m["autor"][:300],
                    "width": w, "height": h, "retrieved_at": AGORA,
                }
            )
    finally:
        http.fechar()
    escrever_csv(
        DIR_PROCESSADOS / "researcher_photos.csv",
        linhas,
        ["researcher_id", "source", "file_name", "source_title", "source_page_url", "license", "license_url", "author", "width", "height", "retrieved_at"],
    )
    s = {
        "gerado_em": AGORA,
        "orcids_consultados": len(orcids) if not limite_lotes else min(len(orcids), lote * limite_lotes),
        "orcids_com_imagem_no_wikidata": len(achados),
        "fotos_gravadas": c["ok"],
        "contagens": dict(c.most_common()),
        "tamanho_total_kb": round(sum((DIR_FOTOS / x["file_name"]).stat().st_size for x in linhas) / 1024, 1),
    }
    _relatorio(s)
    return s


def _relatorio(s: dict[str, Any]) -> None:
    L = [
        "# Parte 7 — Fotos de pesquisadores (Wikimedia Commons)", "",
        f"Gerado em {s['gerado_em']} por `python -m ingest.carga.parte7_fotos`.", "",
        "| Item | Valor |", "|---|---|",
        f"| ORCIDs do recorte consultados no Wikidata | {s['orcids_consultados']} |",
        f"| Com imagem (P18) no Wikidata | {s['orcids_com_imagem_no_wikidata']} |",
        f"| **Fotos gravadas (licença livre, WebP ≤ {LADO_MAX} px, sem EXIF)** | **{s['fotos_gravadas']}** ({s['tamanho_total_kb']} KB) |", "",
        f"Detalhe: `{json.dumps(s['contagens'], ensure_ascii=False)}`", "",
        "Todos os demais perfis usam o avatar com iniciais. Cada foto é exibida com autor e licença (exigência das licenças CC BY/BY-SA).",
        "Pedidos de remoção de foto são atendidos como os de perfil (LGPD).",
    ]
    (DIR_RELATORIOS / "parte7_fotos.md").write_text("\n".join(L) + "\n")
    (DIR_RELATORIOS / "parte7_fotos.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lote", type=int, default=200, help="ORCIDs por consulta SPARQL (padrão 200)")
    p.add_argument("--limite-lotes", type=int, default=None, help="Para testes: processa só os N primeiros lotes")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    s = executar(a.lote, a.limite_lotes)
    print(json.dumps({k: s[k] for k in ("orcids_consultados", "orcids_com_imagem_no_wikidata", "fotos_gravadas", "contagens")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
