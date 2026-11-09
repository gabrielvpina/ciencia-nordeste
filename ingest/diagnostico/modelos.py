"""Estrutura do resultado de cada fonte avaliada."""

from __future__ import annotations

import time
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Recomendacao = Literal["usar", "complementar", "descartar", "precisa de acordo ou pedido LAI", "indefinido"]


@dataclass
class ResultadoFonte:
    id: str
    nome: str
    grupo: str
    url_base: str
    acessivel: bool | None = None
    status_http: int | None = None
    tempo_resposta_ms: float | None = None
    forma_acesso: str = ""
    formato: str = ""
    tamanho_bytes: int | None = None
    tamanho_obs: str = ""
    registros_br: int | None = None
    registros_obs: str = ""
    licenca: str = ""
    ultima_atualizacao: str = ""
    frequencia_atualizacao: str = ""
    identificadores: list[str] = field(default_factory=list)
    observacoes: list[str] = field(default_factory=list)
    riscos: list[str] = field(default_factory=list)
    recomendacao: Recomendacao = "indefinido"
    justificativa: str = ""
    detalhes: dict[str, Any] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)
    avaliado_em: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    duracao_s: float | None = None

    def registrar_resposta(self, status: int | None, tempo_ms: float | None) -> None:
        """Usa a primeira resposta 'principal' como medida de acessibilidade."""
        if self.status_http is None:
            self.status_http = status
            self.tempo_resposta_ms = round(tempo_ms, 1) if tempo_ms is not None else None
        if status is not None:
            self.acessivel = (self.acessivel or False) or (200 <= status < 400)

    def erro(self, contexto: str, exc: BaseException) -> None:
        msg = f"{contexto}: {type(exc).__name__}: {exc}"
        self.erros.append(msg)
        self.detalhes.setdefault("_traceback", []).append(traceback.format_exc(limit=3))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
