"""Cliente HTTP do diagnóstico.

Recursos:
- cache em disco (ingest/.cache/) por método + URL + Range;
- respeito a robots.txt (RFC 9309), com exceções explícitas para APIs documentadas;
- intervalo mínimo por host (maior entre a configuração e o Crawl-delay);
- retry com backoff exponencial para erros de rede, 429 e 5xx, respeitando Retry-After;
- timeout em todas as chamadas;
- trava de tamanho: nunca baixa mais que MAX_BYTES_DOWNLOAD;
- utilitários para ler só o diretório central de um ZIP e o começo de um CSV via Range.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import ssl
import struct
import time
import urllib.robotparser
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import truststore

from .config import (
    DIR_CACHE,
    EXCECOES_ROBOTS,
    INTERVALO_PADRAO,
    INTERVALO_POR_HOST,
    MAX_BYTES_DOWNLOAD,
    Config,
)

log = logging.getLogger(__name__)

PARAMS_SECRETOS = {"api_key"}
CABECALHOS_GUARDADOS = (
    "content-type",
    "content-length",
    "content-range",
    "last-modified",
    "etag",
    "location",
    "retry-after",
    "x-ratelimit-credits-used",
    "x-ratelimit-cost-usd",
    "x-ratelimit-remaining",
    "x-ratelimit-remaining-usd",
    "x-ratelimit-limit-usd",
)


class ErroHttp(Exception):
    """Falha definitiva numa chamada HTTP."""


class BloqueadoPorRobots(ErroHttp):
    pass


class ArquivoGrandeDemais(ErroHttp):
    pass


@dataclass
class Resposta:
    url: str
    metodo: str
    status: int
    cabecalhos: dict[str, str]
    corpo: bytes
    tempo_ms: float
    do_cache: bool = False
    url_final: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return json.loads(self.corpo.decode("utf-8"))

    def texto(self) -> str:
        for enc in ("utf-8", "latin-1"):
            try:
                return self.corpo.decode(enc)
            except UnicodeDecodeError:
                continue
        return self.corpo.decode("utf-8", errors="replace")

    def tamanho_declarado(self) -> int | None:
        cr = self.cabecalhos.get("content-range")
        if cr and "/" in cr:
            total = cr.rsplit("/", 1)[1]
            if total.isdigit():
                return int(total)
        cl = self.cabecalhos.get("content-length")
        return int(cl) if cl and cl.isdigit() else None


@dataclass
class RegistroChamada:
    metodo: str
    url: str
    status: int | None
    tempo_ms: float | None
    do_cache: bool
    erro: str | None = None


def _sem_segredos(url: str) -> str:
    partes = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True) if k not in PARAMS_SECRETOS]
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(q), partes.fragment))


def _montar_url(url: str, params: dict[str, Any] | list[tuple[str, Any]] | None) -> str:
    """params pode ser dict ou lista de pares (para chaves repetidas, ex.: filter[] duas vezes)."""
    if not params:
        return url
    partes = urlsplit(url)
    q = parse_qsl(partes.query, keep_blank_values=True)
    pares = params.items() if isinstance(params, dict) else params
    q.extend((k, str(v)) for k, v in pares if v is not None)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(q, safe=":,|*"), partes.fragment))


@dataclass
class _EstadoHost:
    robots: urllib.robotparser.RobotFileParser | None = None
    robots_status: str = "nao_verificado"
    ultimo_acesso: float = 0.0
    intervalo: float = INTERVALO_PADRAO


class ClienteHttp:
    def __init__(self, cfg: Config, dir_cache: Path = DIR_CACHE, timeout: float = 45.0, tentativas: int = 5) -> None:
        self.cfg = cfg
        self.dir_cache = dir_cache
        self.dir_cache.mkdir(parents=True, exist_ok=True)
        self.tentativas = tentativas
        self._hosts: dict[str, _EstadoHost] = {}
        self.chamadas: list[RegistroChamada] = []
        self.creditos_openalex = 0
        self.custo_openalex_usd = 0.0
        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=15.0),
            headers={"User-Agent": cfg.user_agent},
            follow_redirects=True,
            # Repositório de certificados do sistema: sites gov.br usam cadeias (ICP-Brasil/intermediárias)
            # que o bundle do certifi nem sempre valida. A verificação TLS continua ligada.
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )

    def fechar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ cache
    def _chave(self, metodo: str, url: str, extra: str = "") -> str:
        return hashlib.sha256(f"{metodo}|{_sem_segredos(url)}|{extra}".encode()).hexdigest()

    def _ler_cache(self, chave: str) -> Resposta | None:
        if not self.cfg.usar_cache:
            return None
        meta_p = self.dir_cache / f"{chave}.json"
        corpo_p = self.dir_cache / f"{chave}.bin"
        if not meta_p.exists():
            return None
        meta = json.loads(meta_p.read_text())
        corpo = corpo_p.read_bytes() if corpo_p.exists() else b""
        return Resposta(
            url=meta["url"],
            metodo=meta["metodo"],
            status=meta["status"],
            cabecalhos=meta["cabecalhos"],
            corpo=corpo,
            tempo_ms=meta["tempo_ms"],
            do_cache=True,
            url_final=meta.get("url_final"),
        )

    def _gravar_cache(self, chave: str, r: Resposta) -> None:
        meta = {
            "url": _sem_segredos(r.url),
            "metodo": r.metodo,
            "status": r.status,
            "cabecalhos": r.cabecalhos,
            "tempo_ms": r.tempo_ms,
            "url_final": _sem_segredos(r.url_final) if r.url_final else None,
            "gravado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        (self.dir_cache / f"{chave}.json").write_text(json.dumps(meta, ensure_ascii=False))
        if r.corpo:
            (self.dir_cache / f"{chave}.bin").write_bytes(r.corpo)

    # ----------------------------------------------------------------- robots
    def _estado(self, host: str) -> _EstadoHost:
        if host not in self._hosts:
            self._hosts[host] = _EstadoHost(intervalo=INTERVALO_POR_HOST.get(host, INTERVALO_PADRAO))
        return self._hosts[host]

    def _carregar_robots(self, scheme: str, host: str) -> _EstadoHost:
        est = self._estado(host)
        if est.robots_status != "nao_verificado":
            return est
        url = f"{scheme}://{host}/robots.txt"
        chave = self._chave("ROBOTS", url)
        cache = self._ler_cache(chave)
        status: int | None
        texto = ""
        if cache is not None:
            status, texto = cache.status, cache.texto()
        else:
            status = None
            for tentativa in range(1, 4):
                try:
                    r = self._http.get(url, timeout=30.0)
                    status, texto = r.status_code, r.text if r.status_code == 200 else ""
                    if status >= 500:
                        raise httpx.HTTPStatusError(f"HTTP {status}", request=r.request, response=r)
                    self._gravar_cache(chave, Resposta(url, "GET", status, {}, texto.encode("utf-8"), 0.0))
                    break
                except httpx.HTTPError as e:
                    status = None
                    log.warning("robots.txt inacessível em %s (tentativa %d/3): %s", host, tentativa, e)
                    if tentativa < 3:
                        time.sleep(5 * tentativa)
        rp = urllib.robotparser.RobotFileParser()
        if status == 200 and texto.lstrip().lower().startswith(("<!doctype", "<html")):
            # Alguns servidores devolvem a página inicial em vez de robots.txt: tratar como ausente.
            rp.parse([])
            est.robots_status = "ausente(html)"
        elif status == 200:
            rp.parse(texto.splitlines())
            est.robots_status = "ok"
        elif status is not None and 400 <= status < 500:
            rp.parse([])  # RFC 9309: 4xx => sem restrições
            est.robots_status = f"ausente({status})"
        else:
            rp.parse(["User-agent: *", "Disallow: /"])  # RFC 9309: inacessível => tudo bloqueado
            est.robots_status = f"inacessivel({status})"
        est.robots = rp
        delay = rp.crawl_delay(self.cfg.user_agent) or rp.crawl_delay("*")
        if delay:
            est.intervalo = max(est.intervalo, float(delay))
        return est

    def robots_permite(self, url: str) -> tuple[bool, str]:
        partes = urlsplit(url)
        host = partes.hostname or ""
        est = self._carregar_robots(partes.scheme, host)
        assert est.robots is not None
        if est.robots.can_fetch(self.cfg.user_agent, url):
            return True, est.robots_status
        if host in EXCECOES_ROBOTS:
            return True, f"excecao_api_documentada: {EXCECOES_ROBOTS[host]}"
        return False, est.robots_status

    # -------------------------------------------------------------- requisição
    def _esperar(self, host: str) -> None:
        est = self._estado(host)
        falta = est.intervalo - (time.monotonic() - est.ultimo_acesso)
        if falta > 0:
            time.sleep(falta)
        est.ultimo_acesso = time.monotonic()

    def requisitar(
        self,
        metodo: str,
        url: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        cabecalhos: dict[str, str] | None = None,
        intervalo_bytes: tuple[int | None, int | None] | None = None,
        max_bytes: int = MAX_BYTES_DOWNLOAD,
        corpo_json: Any | None = None,
        cache: bool = True,
        aceitar_status: tuple[int, ...] = (),
    ) -> Resposta:
        url_completa = _montar_url(url, params)
        range_hdr = None
        if intervalo_bytes is not None:
            ini, fim = intervalo_bytes
            range_hdr = f"bytes=-{fim}" if ini is None else f"bytes={ini}-{'' if fim is None else fim}"
        extra = (range_hdr or "") + (json.dumps(corpo_json, sort_keys=True) if corpo_json is not None else "")
        extra += json.dumps(cabecalhos or {}, sort_keys=True)
        chave = self._chave(metodo, url_completa, extra)
        if cache:
            em_cache = self._ler_cache(chave)
            if em_cache is not None:
                self.chamadas.append(RegistroChamada(metodo, _sem_segredos(url_completa), em_cache.status, em_cache.tempo_ms, True))
                return em_cache

        permitido, motivo = self.robots_permite(url_completa)
        if not permitido:
            self.chamadas.append(RegistroChamada(metodo, _sem_segredos(url_completa), None, None, False, f"robots.txt: {motivo}"))
            raise BloqueadoPorRobots(f"robots.txt de {urlsplit(url_completa).hostname} não permite {urlsplit(url_completa).path}")

        hdrs = dict(cabecalhos or {})
        if range_hdr:
            hdrs["Range"] = range_hdr
        host = urlsplit(url_completa).hostname or ""
        ultimo_erro: str | None = None
        for tentativa in range(1, self.tentativas + 1):
            self._esperar(host)
            t0 = time.monotonic()
            try:
                with self._http.stream(metodo, url_completa, headers=hdrs, json=corpo_json) as r:
                    tamanho = r.headers.get("content-length")
                    # Servidor ignorou um Range de prefixo (bytes=a-b) e mandou o arquivo inteiro (200):
                    # lemos só os bytes pedidos e fechamos a conexão, sem baixar o resto.
                    limite_prefixo: int | None = None
                    if range_hdr and r.status_code == 200 and intervalo_bytes is not None:
                        ini, fim = intervalo_bytes
                        if ini is None:
                            raise ErroHttp(f"Servidor ignorou Range de sufixo em {_sem_segredos(url_completa)}")
                        limite_prefixo = (fim if fim is not None else max_bytes) + 1
                        if ini > 0:
                            raise ErroHttp(f"Servidor ignorou Range (início {ini}) em {_sem_segredos(url_completa)}")
                    if (
                        limite_prefixo is None
                        and metodo != "HEAD"
                        and r.status_code < 300
                        and tamanho
                        and tamanho.isdigit()
                        and int(tamanho) > max_bytes
                    ):
                        raise ArquivoGrandeDemais(f"{_sem_segredos(url_completa)} tem {int(tamanho)} bytes (> {max_bytes})")
                    corpo = bytearray()
                    if metodo != "HEAD":
                        for bloco in r.iter_bytes():
                            corpo.extend(bloco)
                            if limite_prefixo is not None and len(corpo) >= limite_prefixo:
                                del corpo[limite_prefixo:]
                                break
                            if len(corpo) > max_bytes:
                                raise ArquivoGrandeDemais(f"{_sem_segredos(url_completa)} passou de {max_bytes} bytes; download interrompido")
                    tempo_ms = (time.monotonic() - t0) * 1000
                    status = r.status_code
                    hdr_resp = {k: r.headers[k] for k in CABECALHOS_GUARDADOS if k in r.headers}
                    url_final = str(r.url)
            except ArquivoGrandeDemais:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as e:
                ultimo_erro = f"{type(e).__name__}: {e}"
                espera = min(2 ** tentativa, 60)
                log.warning("Erro de rede em %s (tentativa %d/%d): %s; nova tentativa em %ss", _sem_segredos(url_completa), tentativa, self.tentativas, ultimo_erro, espera)
                time.sleep(espera)
                continue

            if host == "api.openalex.org":
                self._contabilizar_openalex(hdr_resp)

            if status == 429 or status >= 500:
                retry_after = hdr_resp.get("retry-after", "")
                espera = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else min(2 ** tentativa, 60)
                ultimo_erro = f"HTTP {status}"
                if espera > 900:
                    log.error("HTTP %s em %s com Retry-After=%ss; desistindo (cota diária esgotada?)", status, _sem_segredos(url_completa), espera)
                    break
                log.warning("HTTP %s em %s (tentativa %d/%d); aguardando %ss", status, _sem_segredos(url_completa), tentativa, self.tentativas, espera)
                time.sleep(espera)
                continue

            resp = Resposta(url_completa, metodo, status, hdr_resp, bytes(corpo), tempo_ms, url_final=url_final)
            self.chamadas.append(RegistroChamada(metodo, _sem_segredos(url_completa), status, round(tempo_ms, 1), False))
            if cache and (resp.ok or status in aceitar_status or status in (404, 401, 403)):
                self._gravar_cache(chave, resp)
            return resp

        self.chamadas.append(RegistroChamada(metodo, _sem_segredos(url_completa), None, None, False, ultimo_erro))
        raise ErroHttp(f"Falha após {self.tentativas} tentativas em {_sem_segredos(url_completa)}: {ultimo_erro}")

    def _contabilizar_openalex(self, hdr: dict[str, str]) -> None:
        cred = hdr.get("x-ratelimit-credits-used")
        custo = hdr.get("x-ratelimit-cost-usd")
        if cred and cred.isdigit():
            self.creditos_openalex += int(cred)
        try:
            self.custo_openalex_usd += float(custo) if custo else 0.0
        except ValueError:
            pass

    # ---------------------------------------------------------------- atalhos
    def get(self, url: str, **kw: Any) -> Resposta:
        return self.requisitar("GET", url, **kw)

    def head(self, url: str, **kw: Any) -> Resposta:
        return self.requisitar("HEAD", url, **kw)

    def get_json(self, url: str, **kw: Any) -> Any:
        r = self.get(url, **kw)
        if not r.ok:
            corpo = r.texto()
            if "html" in r.cabecalhos.get("content-type", "") or corpo.lstrip().startswith("<"):
                titulo = re.search(r"<title>(.*?)</title>", corpo, re.S | re.I)
                corpo = f"(página HTML: {titulo.group(1).strip() if titulo else 'sem título'})"
            raise ErroHttp(f"HTTP {r.status} em {_sem_segredos(r.url)[:200]}: {corpo[:300]}")
        return r.json()

    def tamanho_remoto(self, url: str) -> tuple[int | None, Resposta]:
        """Tamanho do arquivo via HEAD; se o servidor não informar, tenta GET com Range 0-0."""
        r = self.head(url)
        tam = r.tamanho_declarado() if r.ok else None
        if tam is None:
            r2 = self.get(url, intervalo_bytes=(0, 0), aceitar_status=(206,))
            if r2.status in (200, 206):
                tam = r2.tamanho_declarado()
                if r2.status == 206:
                    r2.cabecalhos.setdefault("last-modified", r.cabecalhos.get("last-modified", ""))
                return tam, r2
        return tam, r

    # --------------------------------------------------------- download real
    def baixar(self, url: str, destino: Path, max_bytes: int = 5 * 1024**3) -> Path:
        """Baixa um arquivo para `destino` (streaming). Idempotente: se já existe com o mesmo tamanho remoto, não baixa.

        Usado a partir da Parte 1 (a trava de 50 MB vale só para o diagnóstico).
        """
        destino.parent.mkdir(parents=True, exist_ok=True)
        tam_remoto: int | None = None
        try:
            tam_remoto, _ = self.tamanho_remoto(url)
        except ErroHttp as e:
            log.warning("Sem tamanho remoto para %s: %s", _sem_segredos(url), e)
        if destino.exists() and (tam_remoto is None or destino.stat().st_size == tam_remoto):
            log.info("Já baixado: %s (%d bytes)", destino.name, destino.stat().st_size)
            return destino
        if tam_remoto and tam_remoto > max_bytes:
            raise ArquivoGrandeDemais(f"{_sem_segredos(url)} tem {tam_remoto} bytes (> {max_bytes})")
        permitido, motivo = self.robots_permite(url)
        if not permitido:
            raise BloqueadoPorRobots(f"robots.txt não permite {url} ({motivo})")
        host = urlsplit(url).hostname or ""
        parcial = destino.with_suffix(destino.suffix + ".parcial")
        ultimo_erro = ""
        for tentativa in range(1, self.tentativas + 1):
            self._esperar(host)
            t0 = time.monotonic()
            try:
                with self._http.stream("GET", url, timeout=httpx.Timeout(120.0, connect=20.0)) as r:
                    if r.status_code != 200:
                        raise ErroHttp(f"HTTP {r.status_code} em {_sem_segredos(url)}")
                    n = 0
                    with parcial.open("wb") as f:
                        for bloco in r.iter_bytes(1024 * 1024):
                            f.write(bloco)
                            n += len(bloco)
                            if n > max_bytes:
                                raise ArquivoGrandeDemais(f"{_sem_segredos(url)} passou de {max_bytes} bytes")
                if tam_remoto and n != tam_remoto:
                    raise ErroHttp(f"Download incompleto: {n} de {tam_remoto} bytes")
                parcial.replace(destino)
                dt_s = time.monotonic() - t0
                self.chamadas.append(RegistroChamada("GET", _sem_segredos(url), 200, round(dt_s * 1000, 1), False))
                log.info("Baixado %s: %.1f MB em %.0f s", destino.name, n / 1e6, dt_s)
                return destino
            except ArquivoGrandeDemais:
                parcial.unlink(missing_ok=True)
                raise
            except (httpx.HTTPError, ErroHttp) as e:
                ultimo_erro = f"{type(e).__name__}: {e}"
                espera = min(2**tentativa, 60)
                log.warning("Falha ao baixar %s (tentativa %d/%d): %s; nova tentativa em %ss", _sem_segredos(url), tentativa, self.tentativas, ultimo_erro, espera)
                time.sleep(espera)
        parcial.unlink(missing_ok=True)
        raise ErroHttp(f"Falha ao baixar {_sem_segredos(url)}: {ultimo_erro}")

    # ------------------------------------------------------------- ZIP parcial
    def listar_zip(self, url: str, tamanho: int | None = None) -> list[dict[str, Any]]:
        """Lê só o diretório central de um ZIP remoto (Range nos últimos bytes)."""
        if tamanho is None:
            tamanho, _ = self.tamanho_remoto(url)
        if not tamanho:
            raise ErroHttp("Tamanho do ZIP desconhecido; não dá para ler o diretório central")
        cauda_n = min(tamanho, 256 * 1024)
        cauda = self.get(url, intervalo_bytes=(tamanho - cauda_n, tamanho - 1), aceitar_status=(206,)).corpo
        pos = cauda.rfind(b"PK\x05\x06")
        if pos < 0:
            raise ErroHttp("Fim do diretório central (EOCD) não encontrado")
        _, _, _, _, n_total, cd_tam, cd_off, _ = struct.unpack("<IHHHHIIH", cauda[pos : pos + 22])
        if cd_off == 0xFFFFFFFF or cd_tam == 0xFFFFFFFF:
            loc = cauda.rfind(b"PK\x06\x07")
            z64_off = struct.unpack("<Q", cauda[loc + 8 : loc + 16])[0]
            inicio_cauda = tamanho - cauda_n
            rec = cauda[z64_off - inicio_cauda : z64_off - inicio_cauda + 56]
            cd_tam, cd_off = struct.unpack("<QQ", rec[40:56])
        inicio_cauda = tamanho - cauda_n
        if cd_off >= inicio_cauda:
            cd = cauda[cd_off - inicio_cauda : cd_off - inicio_cauda + cd_tam]
        else:
            cd = self.get(url, intervalo_bytes=(cd_off, cd_off + cd_tam - 1), aceitar_status=(206,)).corpo
        entradas: list[dict[str, Any]] = []
        i = 0
        while i + 46 <= len(cd) and cd[i : i + 4] == b"PK\x01\x02":
            (comp_metodo,) = struct.unpack("<H", cd[i + 10 : i + 12])
            comp, descomp = struct.unpack("<II", cd[i + 20 : i + 28])
            n_nome, n_extra, n_coment = struct.unpack("<HHH", cd[i + 28 : i + 34])
            (off_local,) = struct.unpack("<I", cd[i + 42 : i + 46])
            nome = cd[i + 46 : i + 46 + n_nome].decode("utf-8", errors="replace")
            extra = cd[i + 46 + n_nome : i + 46 + n_nome + n_extra]
            if 0xFFFFFFFF in (comp, descomp, off_local):
                j = 0
                while j + 4 <= len(extra):
                    hid, hlen = struct.unpack("<HH", extra[j : j + 4])
                    if hid == 0x0001:
                        vals = list(struct.unpack(f"<{hlen // 8}Q", extra[j + 4 : j + 4 + (hlen // 8) * 8]))
                        if descomp == 0xFFFFFFFF and vals:
                            descomp = vals.pop(0)
                        if comp == 0xFFFFFFFF and vals:
                            comp = vals.pop(0)
                        if off_local == 0xFFFFFFFF and vals:
                            off_local = vals.pop(0)
                    j += 4 + hlen
            entradas.append(
                {"nome": nome, "comprimido": comp, "descomprimido": descomp, "metodo": comp_metodo, "offset": off_local}
            )
            i += 46 + n_nome + n_extra + n_coment
        return entradas

    def inicio_de_arquivo_no_zip(self, url: str, entrada: dict[str, Any], n_bytes: int = 256 * 1024) -> bytes:
        """Descomprime só o começo de um arquivo dentro de um ZIP remoto."""
        off = int(entrada["offset"])
        cab = self.get(url, intervalo_bytes=(off, off + 29), aceitar_status=(206,)).corpo
        n_nome, n_extra = struct.unpack("<HH", cab[26:30])
        ini = off + 30 + n_nome + n_extra
        bruto = self.get(url, intervalo_bytes=(ini, ini + n_bytes - 1), aceitar_status=(206,)).corpo
        if entrada["metodo"] == 0:
            return bruto
        d = zlib.decompressobj(-15)
        return d.decompress(bruto)

    def arquivo_inteiro_do_zip(self, url: str, entrada: dict[str, Any]) -> bytes:
        """Baixa (via Range) e descomprime UM arquivo de dentro de um ZIP remoto, se couber no limite."""
        comp = int(entrada["comprimido"])
        if comp > MAX_BYTES_DOWNLOAD:
            raise ArquivoGrandeDemais(f"{entrada['nome']} tem {comp} bytes comprimidos (> {MAX_BYTES_DOWNLOAD})")
        off = int(entrada["offset"])
        cab = self.get(url, intervalo_bytes=(off, off + 29), aceitar_status=(206,)).corpo
        n_nome, n_extra = struct.unpack("<HH", cab[26:30])
        ini = off + 30 + n_nome + n_extra
        bruto = self.get(url, intervalo_bytes=(ini, ini + comp - 1), aceitar_status=(206,)).corpo
        if len(bruto) != comp:
            raise ErroHttp(f"Leitura parcial de {entrada['nome']}: {len(bruto)} de {comp} bytes")
        return bruto if entrada["metodo"] == 0 else zlib.decompressobj(-15).decompress(bruto)

    # ------------------------------------------------------------- CSV parcial
    def amostrar_csv(self, url: str, tamanho: int | None, n_bytes: int = 256 * 1024) -> dict[str, Any]:
        r = self.get(url, intervalo_bytes=(0, n_bytes - 1), aceitar_status=(206,))
        return analisar_amostra_csv(r.corpo, tamanho)


def analisar_amostra_csv(amostra: bytes, tamanho_total: int | None) -> dict[str, Any]:
    """Colunas, separador, codificação e estimativa de linhas a partir do começo de um CSV."""
    texto = None
    codificacao = None
    corte = amostra.rfind(b"\n")
    if corte > 0:
        amostra = amostra[: corte + 1]  # descarta a última linha (provavelmente cortada no meio)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            texto = amostra.decode(enc)
            codificacao = enc
            break
        except UnicodeDecodeError:
            continue
    if texto is None:  # pragma: no cover
        texto = amostra.decode("utf-8", errors="replace")
        codificacao = "desconhecida"
    linhas = [lk for lk in texto.splitlines() if lk.strip()]
    if not linhas:
        return {"colunas": [], "erro": "amostra vazia"}
    cabecalho = linhas[0]
    sep = max([";", ",", "|", "\t"], key=cabecalho.count)
    colunas = next(csv.reader([cabecalho], delimiter=sep))
    colunas = [c.strip().strip('"') for c in colunas]
    corpo = linhas[1:]
    est_linhas = None
    media = None
    if corpo and tamanho_total:
        enc = codificacao if codificacao and codificacao != "utf-8-sig" else "utf-8"
        bytes_corpo = sum(len(lk.encode(enc, errors="replace")) + 1 for lk in corpo)
        media = bytes_corpo / len(corpo)
        est_linhas = int((tamanho_total - len(cabecalho) - 1) / media)
    exemplo = None
    if corpo:
        valores = next(csv.reader([corpo[0]], delimiter=sep))
        exemplo = dict(zip(colunas, valores))
    return {
        "colunas": colunas,
        "separador": sep,
        "codificacao": codificacao,
        "linhas_amostradas": len(corpo),
        "bytes_medios_por_linha": round(media, 1) if media else None,
        "linhas_estimadas": est_linhas,
        "exemplo_primeira_linha": exemplo,
    }


def ler_csv_texto(texto: str, sep: str | None = None) -> list[dict[str, str]]:
    if sep is None:
        primeira = texto.split("\n", 1)[0]
        sep = max([";", ",", "|", "\t"], key=primeira.count)
    return list(csv.DictReader(io.StringIO(texto), delimiter=sep))
