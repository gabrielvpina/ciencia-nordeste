"""Utilidades das cargas (Partes 1+): caminhos, registro de IDs estáveis, CSV, normalização e geografia."""

from __future__ import annotations

import csv
import datetime as dt
import logging
import math
import re
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..diagnostico.config import RAIZ_INGEST
from ..diagnostico.recorte import UFS_NORDESTE, normalizar

log = logging.getLogger(__name__)

DIR_DADOS = RAIZ_INGEST / "dados"
DIR_BRUTOS = DIR_DADOS / "brutos"
DIR_PROCESSADOS = DIR_DADOS / "processados"
DIR_IDS = DIR_DADOS / "ids"
DIR_RELATORIOS = RAIZ_INGEST / "relatorios"

AGORA = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RegistroIds:
    """Registro persistente de UUIDs internos.

    Cada entidade (ex.: 'institution') tem um CSV `uuid,chave,criado_em` em ingest/dados/ids/.
    Uma chave é 'esquema:valor' (ex.: 'ror:020jkns84', 'emec:2'). O UUID de uma entidade, uma vez
    criado, nunca muda: novas chaves que se ligam a ela passam a apontar para o mesmo UUID.
    Este arquivo é dado de produção: faz parte do backup.
    """

    def __init__(self, entidade: str, diretorio: Path = DIR_IDS) -> None:
        self.caminho = diretorio / f"{entidade}.csv"
        self.chave_para_uuid: dict[str, str] = {}
        self.novas: list[tuple[str, str]] = []
        self.conflitos: list[dict[str, Any]] = []
        if self.caminho.exists():
            with self.caminho.open(newline="", encoding="utf-8") as f:
                for lin in csv.DictReader(f):
                    self.chave_para_uuid[lin["chave"]] = lin["uuid"]

    def obter(self, chaves: Iterable[str]) -> str:
        chaves = [c for c in dict.fromkeys(chaves) if c]
        if not chaves:
            raise ValueError("Entidade sem nenhuma chave")
        existentes = {self.chave_para_uuid[c] for c in chaves if c in self.chave_para_uuid}
        if len(existentes) > 1:
            # Duas entidades já registradas agora parecem a mesma: não mescla, registra o conflito.
            self.conflitos.append({"chaves": chaves, "uuids": sorted(existentes)})
            escolhido = self.chave_para_uuid[next(c for c in chaves if c in self.chave_para_uuid)]
            log.warning("Conflito de IDs para %s: %s (mantido %s)", chaves, existentes, escolhido)
        elif existentes:
            escolhido = existentes.pop()
        else:
            escolhido = str(uuid.uuid4())
        for c in chaves:
            if c not in self.chave_para_uuid:
                self.chave_para_uuid[c] = escolhido
                self.novas.append((escolhido, c))
        return escolhido

    def salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        novo = not self.caminho.exists()
        with self.caminho.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["uuid", "chave", "criado_em"])
            for u, c in self.novas:
                w.writerow([u, c, AGORA])
        log.info("Registro de IDs %s: %d chaves (%d novas)", self.caminho.name, len(self.chave_para_uuid), len(self.novas))
        self.novas = []


def escrever_csv(caminho: Path, linhas: Iterable[Mapping[str, Any]], campos: list[str]) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for lin in linhas:
            w.writerow({k: _fmt(v) for k, v in lin.items()})
            n += 1
    log.info("Gravado %s (%d linhas)", caminho.relative_to(RAIZ_INGEST.parent), n)
    return n


def _fmt(v: Any) -> Any:
    if isinstance(v, (list, tuple, set)):
        return "|".join(str(x) for x in v)
    if isinstance(v, float):
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return v


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


PALAVRAS_VAZIAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "EM", "A", "O", "THE", "OF", "AND"}


def tokens(nome: str) -> set[str]:
    return {t for t in re.split(r"[^A-Z0-9]+", normalizar(nome)) if t and t not in PALAVRAS_VAZIAS}


# Palavras que aparecem em quase todo nome de instituição e não ajudam a distinguir.
GENERICAS = {
    "UNIVERSIDADE", "UNIVERSITY", "CENTRO", "UNIVERSITARIO", "FACULDADE", "FACULDADES", "INSTITUTO", "INSTITUTE",
    "FEDERAL", "ESTADUAL", "STATE", "EDUCACAO", "CIENCIA", "CIENCIAS", "TECNOLOGIA", "ESCOLA", "SCHOOL", "COLLEGE",
    "SUPERIOR", "ENSINO", "INTEGRADA", "INTEGRADAS", "UNIDADE", "ACADEMIA",
}


# Nomes de lugares do NE (estados, capitais, região) também não distinguem instituições da mesma UF.
LUGARES: set[str] = set()
for _uf in UFS_NORDESTE:
    LUGARES |= {x for x in re.split(r"[^A-Z0-9]+", normalizar(f"{_uf.nome} {_uf.capital}")) if x}
LUGARES |= {"NORDESTE", "BRASIL", "BRAZIL", "NORTE", "SUL", "LESTE", "OESTE", "VALE", "SAO", "SANTA", "SANTO", "RIO", "GRANDE", "JOAO", "PESSOA"}


def similaridade(a: str, b: str) -> float:
    """Jaccard só das palavras distintivas (sem genéricas e sem nomes de lugar); 0 se não sobrar nenhuma."""
    ta, tb = tokens(a) - GENERICAS - LUGARES, tokens(b) - GENERICAS - LUGARES
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def valores_ror(campo: str) -> list[str]:
    """'pt: Universidade X; en: University X' -> ['Universidade X', 'University X']."""
    saida = []
    for parte in (campo or "").split(";"):
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"^([a-z_]{2,15}):\s*(.*)$", parte)
        saida.append(m.group(2).strip() if m else parte)
    return saida


def valores_ror_por_idioma(campo: str) -> dict[str, list[str]]:
    saida: dict[str, list[str]] = {}
    for parte in (campo or "").split(";"):
        parte = parte.strip()
        m = re.match(r"^([a-z_]{2,15}):\s*(.*)$", parte)
        if m:
            saida.setdefault(m.group(1), []).append(m.group(2).strip())
    return saida
