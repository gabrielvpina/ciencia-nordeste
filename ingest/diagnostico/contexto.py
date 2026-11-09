"""Contexto compartilhado entre as avaliações de fontes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .http import ClienteHttp
from .openalex import OpenAlex


@dataclass
class Contexto:
    cfg: Config
    http: ClienteHttp
    oa: OpenAlex
    # valores calculados por uma fonte e reutilizados por outra (ex.: contagem de works BR)
    compartilhado: dict[str, Any] = field(default_factory=dict)

    @property
    def anos(self) -> str:
        return f"{self.cfg.year_start}-{self.cfg.year_end}"
