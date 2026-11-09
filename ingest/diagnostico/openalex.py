"""Chamadas mínimas à API do OpenAlex para o diagnóstico (só contagens e group_by).

Documentação conferida em 2026-11-09:
- https://help.openalex.org/access/example-costs.md  (list+filter e group_by em lista: 1 crédito = US$ 0,0001)
- https://help.openalex.org/api/authentication.md    (api_key; sem chave: US$ 0,10/dia por IP; per_page máx. 100;
  cursor paging só com chave)
- https://help.openalex.org/api/grouping.md          (até 200 grupos por página)
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .http import ClienteHttp, ErroHttp

BASE = "https://api.openalex.org"


class OpenAlex:
    def __init__(self, http: ClienteHttp) -> None:
        self.http = http

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        p = dict(extra)
        if self.http.cfg.openalex_api_key:
            p["api_key"] = self.http.cfg.openalex_api_key
        return p

    def consultar(self, entidade: str, **params: Any) -> dict[str, Any]:
        r = self.http.get(f"{BASE}/{entidade}", params=self._params(params))
        if not r.ok:
            raise ErroHttp(f"OpenAlex HTTP {r.status}: {r.texto()[:400]}")
        dados: dict[str, Any] = r.json()
        dados["_http"] = {"status": r.status, "tempo_ms": r.tempo_ms, "creditos": r.cabecalhos.get("x-ratelimit-credits-used")}
        return dados

    def contar(self, entidade: str, filtro: str | None = None, **extra: Any) -> int:
        params: dict[str, Any] = {"per_page": 1, "select": "id"}
        if filtro:
            params["filter"] = filtro
        params.update(extra)
        return int(self.consultar(entidade, **params)["meta"]["count"])

    def agrupar(self, entidade: str, campo: str, filtro: str | None = None, **extra: Any) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"group_by": campo, "per_page": 200}
        if filtro:
            params["filter"] = filtro
        params.update(extra)
        dados = self.consultar(entidade, **params)
        return [
            {"chave": g.get("key"), "nome": g.get("key_display_name"), "contagem": g.get("count")}
            for g in dados.get("group_by", [])
        ]

    def paginar(self, entidade: str, **params: Any) -> Iterator[list[dict[str, Any]]]:
        """Cursor paging (exige chave). Rende uma lista de resultados por página; não usa o cache em disco."""
        if not self.http.cfg.openalex_api_key:
            raise ErroHttp("Cursor paging do OpenAlex exige OPENALEX_API_KEY")
        cursor = "*"
        while cursor:
            p = self._params({**params, "per_page": 100, "cursor": cursor})
            r = self.http.get(f"{BASE}/{entidade}", params=p, cache=False)
            if not r.ok:
                raise ErroHttp(f"OpenAlex HTTP {r.status}: {r.texto()[:400]}")
            dados = r.json()
            yield dados.get("results", [])
            cursor = dados.get("meta", {}).get("next_cursor")
