"""Gera a geometria do mapa próprio do Nordeste (SVG) a partir da malha oficial do IBGE.

Roda uma vez (ou quando a malha mudar); o resultado fica versionado em apps/web/components/mapa/geometria-ne.json
e o app não consulta nenhuma API externa para desenhar o mapa (D-025).

Projeção equirretangular simples ajustada ao Nordeste (x = Δlon·cos(lat₀)·k, y = Δlat·k) — suficiente para um
mapa esquemático; o JSON leva os parâmetros para o app projetar latitude/longitude das instituições igual.

Uso:
    python -m ingest.carga.gerar_mapa_ne
"""

from __future__ import annotations

import json
import logging
import math
import sys
from typing import Any

from ..diagnostico.config import RAIZ_REPO, carregar_config
from ..diagnostico.http import ClienteHttp, ErroHttp
from ..diagnostico.recorte import UFS_NORDESTE

log = logging.getLogger("ingest.mapa")

URL = "https://servicodados.ibge.gov.br/api/v3/malhas/regioes/2"
DESTINO = RAIZ_REPO / "apps" / "web" / "components" / "mapa" / "geometria-ne.json"
LARGURA = 1000.0
MARGEM = 40.0


def _aneis(geom: dict[str, Any]) -> list[list[list[float]]]:
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [poly[0] for poly in geom["coordinates"]]  # só o anel externo de cada polígono (ilhas incluídas)


def _area_centroide(pts: list[tuple[float, float]]) -> tuple[float, float, float]:
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    a /= 2
    return (abs(a), cx / (6 * a), cy / (6 * a)) if a else (0.0, pts[0][0], pts[0][1])


def gerar() -> dict[str, Any]:
    http = ClienteHttp(carregar_config())
    try:
        r = http.get(URL, params={"intrarregiao": "UF", "formato": "application/vnd.geo+json", "qualidade": "minima"})
        if not r.ok:
            raise ErroHttp(f"IBGE malhas HTTP {r.status}")
        fc = r.json()
    finally:
        http.fechar()
    por_codigo = {str(u.codigo_ibge): u for u in UFS_NORDESTE}
    todos = [pt for f in fc["features"] for anel in _aneis(f["geometry"]) for pt in anel]
    lon_min, lon_max = min(p[0] for p in todos), max(p[0] for p in todos)
    lat_min, lat_max = min(p[1] for p in todos), max(p[1] for p in todos)
    lat0 = math.radians((lat_min + lat_max) / 2)
    k = (LARGURA - 2 * MARGEM) / ((lon_max - lon_min) * math.cos(lat0))
    kx = k * math.cos(lat0)
    altura = (lat_max - lat_min) * k + 2 * MARGEM

    def proj(lon: float, lat: float) -> tuple[float, float]:
        return (MARGEM + (lon - lon_min) * kx, MARGEM + (lat_max - lat) * k)

    estados: list[dict[str, Any]] = []
    for f in fc["features"]:
        uf = por_codigo[str(f["properties"]["codarea"])]
        partes, maior = [], (0.0, 0.0, 0.0)
        for anel in _aneis(f["geometry"]):
            pts = [proj(lon, lat) for lon, lat in anel]
            partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
            ac = _area_centroide(pts)
            if ac[0] > maior[0]:
                maior = ac
        estados.append({"uf": uf.sigla, "nome": uf.nome, "codigo": uf.codigo_ibge, "path": "".join(partes), "centro": [round(maior[1], 1), round(maior[2], 1)]})
    estados.sort(key=lambda e: int(e["codigo"]))
    saida = {
        "fonte": "IBGE — API de malhas v3 (regiões/2, intrarregiao=UF, qualidade mínima); dados públicos, uso livre com citação",
        "viewBox": [0, 0, LARGURA, round(altura, 1)],
        "projecao": {"tipo": "equirretangular", "lonMin": lon_min, "latMax": lat_max, "kx": kx, "ky": k, "margem": MARGEM},
        "estados": estados,
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    log.info("Gravado %s (%.1f KB, %d estados, viewBox %s)", DESTINO.relative_to(RAIZ_REPO), DESTINO.stat().st_size / 1024, len(estados), saida["viewBox"])
    return saida


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    gerar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
