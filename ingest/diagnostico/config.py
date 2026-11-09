"""Configuração do diagnóstico: variáveis de ambiente, caminhos e limites."""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from .recorte import ANOS_RECORTE

RAIZ_REPO = Path(__file__).resolve().parents[2]
RAIZ_INGEST = RAIZ_REPO / "ingest"
DIR_CACHE = RAIZ_INGEST / ".cache"
DIR_RELATORIOS = RAIZ_INGEST / "relatorios"

NOME_PROJETO = "ciencia-nordeste"
VERSAO = "0.1"

# Regra da Parte 0: nunca baixar mais que 50 MB de um arquivo.
MAX_BYTES_DOWNLOAD = 50 * 1024 * 1024

# Hosts cujo robots.txt bloqueia robôs, mas que publicam APIs oficiais e documentadas
# para uso programático. Decisão do usuário (docs/decisoes.md, D-003): nessas APIs
# seguimos os termos de uso da própria API (limite de taxa, User-Agent identificado).
EXCECOES_ROBOTS: dict[str, str] = {
    "pub.orcid.org": (
        "API pública do ORCID (https://info.orcid.org/documentation/api-tutorials/). "
        "Limite documentado: 24 req/s, rajada de 40. Usamos <= 5 req/s."
    ),
    "query.wikidata.org": (
        "Wikidata Query Service (https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual). "
        "Exige User-Agent identificado; 1 consulta por vez."
    ),
    "servicodados.ibge.gov.br": (
        "API de serviços de dados do IBGE (https://servicodados.ibge.gov.br/api/docs). "
        "O robots.txt não responde (timeout), o que pela RFC 9309 equivaleria a bloqueio total; "
        "tratamos como API documentada e fazemos poucas chamadas."
    ),
    "commons.wikimedia.org": (
        "API MediaWiki do Commons (https://www.mediawiki.org/wiki/API:Etiquette). "
        "Requisições seriais com User-Agent identificado."
    ),
}

# Intervalo mínimo entre requisições por host (segundos). O Crawl-delay do robots.txt,
# quando maior, prevalece.
INTERVALO_POR_HOST: dict[str, float] = {
    "api.openalex.org": 0.15,
    "pub.orcid.org": 0.2,
    "query.wikidata.org": 2.0,
    "commons.wikimedia.org": 0.5,
    "openalex.s3.amazonaws.com": 0.2,
    # IBICT (BDTD/Oasisbr): firewall sensível; ver D-011.
    "bdtd.ibict.br": 5.0,
    "oasisbr.ibict.br": 5.0,
}
INTERVALO_PADRAO = 1.0


@dataclass(frozen=True)
class Config:
    contact_email: str | None
    openalex_api_key: str | None
    dados_gov_br_token: str | None
    year_start: int
    year_end: int
    usar_cache: bool = True
    amostra_orcid: int = 500
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def user_agent(self) -> str:
        base = f"{NOME_PROJETO}-diagnostico/{VERSAO} (projeto de dados abertos sobre pesquisa em saude no Nordeste"
        if self.contact_email:
            return f"{base}; mailto:{self.contact_email})"
        return f"{base}; contato nao configurado)"


def carregar_config(year_start: int | None = None, usar_cache: bool = True, amostra_orcid: int | None = None) -> Config:
    load_dotenv(RAIZ_REPO / ".env")
    ano_atual = dt.date.today().year
    # Padrão: últimos ANOS_RECORTE anos, contando o atual (ex.: 2022–2026 em 2026).
    ys = year_start if year_start is not None else int(os.getenv("YEAR_START") or ano_atual - ANOS_RECORTE + 1)
    return Config(
        contact_email=os.getenv("CONTACT_EMAIL") or None,
        openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
        dados_gov_br_token=os.getenv("DADOS_GOV_BR_TOKEN") or None,
        year_start=ys,
        year_end=ano_atual,
        usar_cache=usar_cache,
        amostra_orcid=amostra_orcid if amostra_orcid is not None else int(os.getenv("AMOSTRA_ORCID", "500")),
    )
