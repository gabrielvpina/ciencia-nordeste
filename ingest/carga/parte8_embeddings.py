"""Parte 8 — Busca vetorial por tema: palavras-chave, embeddings multilíngues e carga no pgvector (D-028).

Subcomandos (rodar em ordem):
    python -m ingest.carga.parte8_embeddings coletar-keywords   # OpenAlex: keywords dos works do recorte (~1.100 chamadas)
    python -m ingest.carga.parte8_embeddings benchmark [--n 2000]   # mede velocidade/memória antes de rodar tudo
    python -m ingest.carga.parte8_embeddings embeddings          # calcula os vetores (incremental: só textos novos/alterados)
    python -m ingest.carga.parte8_embeddings carregar            # grava em work_embeddings (Postgres local) e reconstrói o índice HNSW

Texto de cada publicação (formato do modelo e5): "passage: <título>. Palavras-chave: k1; k2. Tópicos: t1; t2".
Modelo: intfloat/multilingual-e5-base fixado num commit (MODELO/REVISAO); vetores normalizados (cosseno = produto interno).
Saídas: ingest/dados/processados/work_keywords.csv e ingest/dados/processados/embeddings/{vetores.npy, indice.csv, meta.json}.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import sys
import time
from typing import Any

from ..diagnostico.config import RAIZ_REPO, carregar_config
from ..diagnostico.http import ClienteHttp
from ..diagnostico.openalex import OpenAlex
from ..diagnostico.recorte import filtro_openalex_campos
from .comum import AGORA, DIR_BRUTOS, DIR_PROCESSADOS, DIR_RELATORIOS, escrever_csv, ler_csv

log = logging.getLogger("ingest.parte8")

MODELO = "intfloat/multilingual-e5-base"
REVISAO = "d128750597153bb5987e10b1c3493a34e5a4502a"   # commit do modelo no Hugging Face (MIT), conferido em 2026-11-09
ID_MODELO = f"{MODELO}@{REVISAO[:7]}"
DIM = 768
DIR_EMB = DIR_PROCESSADOS / "embeddings"
DIR_OA = DIR_BRUTOS / "openalex"
MAX_KEYWORDS = 6
MAX_TOPICOS = 3


# ------------------------------------------------------------------ palavras-chave


def coletar_keywords(recoletar: bool = False) -> dict[str, Any]:
    cfg = carregar_config()
    ids_ne = (DIR_PROCESSADOS / "openalex_institution_ids_ne.txt").read_text().split()
    area = filtro_openalex_campos("primary_topic.field.id")
    anos = f"{cfg.year_start}-{cfg.year_end}"
    http = ClienteHttp(cfg)
    oa = OpenAlex(http)
    arquivos = []
    try:
        for n, i in enumerate(range(0, len(ids_ne), 100)):
            destino = DIR_OA / f"keywords_lote{n:02d}.jsonl.gz"
            ok = destino.with_suffix(".ok")
            arquivos.append(destino)
            if ok.exists() and destino.exists() and not recoletar:
                log.info("Lote %d de keywords já coletado", n)
                continue
            filtro = f"authorships.institutions.lineage:{'|'.join(ids_ne[i : i + 100])},{area},publication_year:{anos}"
            total = 0
            parcial = destino.with_suffix(".parcial")
            with gzip.open(parcial, "wt", encoding="utf-8") as f:
                for pagina in oa.paginar("works", filter=filtro, select="id,keywords"):
                    for w in pagina:
                        f.write(json.dumps({"id": w["id"].rsplit("/", 1)[-1], "keywords": w.get("keywords") or []}, ensure_ascii=False) + "\n")
                    total += len(pagina)
                    if total % 10000 < 100:
                        log.info("  keywords lote %d: %d", n, total)
            parcial.replace(destino)
            ok.write_text(f"{total} works em {AGORA}\n")
        creditos = http.creditos_openalex
    finally:
        http.fechar()

    oa_para_work = {w["openalex_id"]: w["id"] for w in ler_csv(DIR_PROCESSADOS / "works.csv")}
    linhas, vistos, com_kw = [], set(), 0
    for a in arquivos:
        with gzip.open(a, "rt", encoding="utf-8") as f:
            for lin in f:
                d = json.loads(lin)
                wid = oa_para_work.get(d["id"])
                if not wid or wid in vistos:
                    continue
                vistos.add(wid)
                if d["keywords"]:
                    com_kw += 1
                for k in d["keywords"]:
                    linhas.append({"work_id": wid, "keyword_id": k.get("id", "").rsplit("/", 1)[-1], "keyword": k.get("display_name", ""), "score": k.get("score")})
    escrever_csv(DIR_PROCESSADOS / "work_keywords.csv", linhas, ["work_id", "keyword_id", "keyword", "score"])
    s = {"works_com_keywords": com_kw, "works_vistos": len(vistos), "keywords": len(linhas), "creditos_openalex": creditos}
    log.info("Keywords: %s", s)
    return s


# ------------------------------------------------------------------ textos


def montar_textos() -> list[tuple[str, str]]:
    """(work_id, texto) para todos os works, no formato 'passage:' do e5."""
    kws: dict[str, list[tuple[float, str]]] = {}
    caminho_kw = DIR_PROCESSADOS / "work_keywords.csv"
    if caminho_kw.exists():
        for k in ler_csv(caminho_kw):
            kws.setdefault(k["work_id"], []).append((float(k["score"] or 0), k["keyword"]))
    else:
        log.warning("Sem work_keywords.csv: textos só com título e tópicos (rode coletar-keywords)")
    nomes_topico = {t["openalex_id"]: t["name"] for t in ler_csv(DIR_PROCESSADOS / "topics.csv")}
    tops: dict[str, list[tuple[float, str]]] = {}
    for t in ler_csv(DIR_PROCESSADOS / "work_topics.csv"):
        tops.setdefault(t["work_id"], []).append((float(t["score"] or 0), nomes_topico.get(t["topic_openalex_id"], "")))
    saida = []
    for w in ler_csv(DIR_PROCESSADOS / "works.csv"):
        titulo = " ".join((w["title"] or "").split())
        if not titulo:
            continue
        partes = [f"passage: {titulo.rstrip('.')}."]
        palavras = [x for _, x in sorted(kws.get(w["id"], []), reverse=True)[:MAX_KEYWORDS] if x]
        if palavras:
            partes.append("Palavras-chave: " + "; ".join(palavras) + ".")
        topicos = [x for _, x in sorted(tops.get(w["id"], []), reverse=True)[:MAX_TOPICOS] if x]
        if topicos:
            partes.append("Tópicos: " + "; ".join(topicos) + ".")
        saida.append((w["id"], " ".join(partes)))
    return saida


def _hash(texto: str) -> str:
    return hashlib.sha1(f"{ID_MODELO}|{texto}".encode()).hexdigest()


def _carregar_modelo() -> Any:
    import torch
    from sentence_transformers import SentenceTransformer

    disp = "mps" if torch.backends.mps.is_available() else "cpu"
    log.info("Carregando %s (rev %s) em %s", MODELO, REVISAO[:7], disp)
    return SentenceTransformer(MODELO, revision=REVISAO, device=disp, model_kwargs={"use_safetensors": True})


# ------------------------------------------------------------------ benchmark / embeddings


def benchmark(n: int, lote: int) -> dict[str, Any]:
    import resource

    textos = [t for _, t in montar_textos()][:n]
    modelo = _carregar_modelo()
    modelo.encode(textos[:lote], batch_size=lote, normalize_embeddings=True)  # aquecimento
    t0 = time.monotonic()
    vet = modelo.encode(textos, batch_size=lote, normalize_embeddings=True, show_progress_bar=False)
    dt = time.monotonic() - t0
    total = len(montar_textos())
    s = {
        "textos": len(textos), "segundos": round(dt, 1), "textos_por_segundo": round(len(textos) / dt, 1),
        "estimativa_total_min": round(total / (len(textos) / dt) / 60, 1), "total_textos": total, "dim": int(vet.shape[1]),
        "memoria_max_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024),
        "tamanho_medio_texto": round(sum(len(t) for t in textos) / len(textos)),
    }
    log.info("Benchmark: %s", s)
    return s


def calcular_embeddings(lote: int) -> dict[str, Any]:
    import numpy as np

    DIR_EMB.mkdir(parents=True, exist_ok=True)
    textos = montar_textos()
    hashes = [_hash(t) for _, t in textos]
    # Incremental: reaproveita vetores cujo texto (e modelo) não mudou.
    antigos: dict[str, tuple[str, int]] = {}
    vet_antigos = None
    if (DIR_EMB / "indice.csv").exists() and (DIR_EMB / "vetores.npy").exists():
        vet_antigos = np.load(DIR_EMB / "vetores.npy", mmap_mode="r")
        for i, r in enumerate(ler_csv(DIR_EMB / "indice.csv")):
            antigos[r["work_id"]] = (r["texto_hash"], i)
    faltam = [i for i, ((wid, _), h) in enumerate(zip(textos, hashes)) if antigos.get(wid, ("", -1))[0] != h]
    log.info("Textos: %d; a calcular: %d; reaproveitados: %d", len(textos), len(faltam), len(textos) - len(faltam))
    saida = np.zeros((len(textos), DIM), dtype=np.float16)
    a_calcular = set(faltam)
    if vet_antigos is not None:
        for i, (wid, _) in enumerate(textos):
            if i not in a_calcular:
                saida[i] = vet_antigos[antigos[wid][1]]
    pronto = [i not in a_calcular for i in range(len(textos))]

    def gravar() -> None:
        """Checkpoint: linhas ainda não calculadas ficam com hash vazio e são refeitas numa nova execução."""
        tmp = DIR_EMB / "vetores.parcial.npy"
        np.save(tmp, saida)
        tmp.replace(DIR_EMB / "vetores.npy")
        escrever_csv(DIR_EMB / "indice.csv", ({"work_id": w, "texto_hash": h if pronto[i] else ""} for i, ((w, _), h) in enumerate(zip(textos, hashes))), ["work_id", "texto_hash"])

    if faltam:
        modelo = _carregar_modelo()
        t0 = time.monotonic()
        bloco = 2048
        for n, ini in enumerate(range(0, len(faltam), bloco)):
            idx = faltam[ini : ini + bloco]
            v = modelo.encode([textos[i][1] for i in idx], batch_size=lote, normalize_embeddings=True, show_progress_bar=False)
            saida[idx] = v.astype(np.float16)
            for i in idx:
                pronto[i] = True
            feito = min(ini + bloco, len(faltam))
            vel = feito / (time.monotonic() - t0)
            log.info("  %d/%d (%.0f textos/s, faltam ~%.1f min)", feito, len(faltam), vel, (len(faltam) - feito) / vel / 60)
            if n % 8 == 7:   # a cada ~16 mil textos
                gravar()
                log.info("  checkpoint gravado (%d prontos)", sum(pronto))
    gravar()
    meta = {"modelo": ID_MODELO, "dim": DIM, "n": len(textos), "calculados_nesta_execucao": len(faltam), "gerado_em": AGORA}
    (DIR_EMB / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


# ------------------------------------------------------------------ carga no Postgres


def _conexao() -> Any:
    import psycopg
    from dotenv import dotenv_values

    env = dotenv_values(RAIZ_REPO / ".env")
    return psycopg.connect(
        host=os.getenv("PGHOST", "127.0.0.1"), port=int(os.getenv("PGPORT", "5432")),
        user=env.get("POSTGRES_USER", "ciencia"), password=env.get("POSTGRES_PASSWORD"), dbname=env.get("POSTGRES_DB", "ciencia"),
    )


def carregar() -> dict[str, Any]:
    import numpy as np

    vet = np.load(DIR_EMB / "vetores.npy", mmap_mode="r")
    indice = ler_csv(DIR_EMB / "indice.csv")
    t0 = time.monotonic()
    with _conexao() as con, con.cursor() as cur:
        cur.execute("CREATE TEMP TABLE _emb (work_id uuid, texto_hash text, embedding halfvec(768)) ON COMMIT DROP")
        with cur.copy("COPY _emb (work_id, texto_hash, embedding) FROM STDIN") as cp:
            for i, r in enumerate(indice):
                cp.write_row((r["work_id"], r["texto_hash"], "[" + ",".join(f"{x:.4f}" for x in vet[i]) + "]"))
        log.info("COPY de %d vetores em %.0f s", len(indice), time.monotonic() - t0)
        cur.execute("DROP INDEX IF EXISTS work_embeddings_hnsw")
        cur.execute(
            """INSERT INTO work_embeddings (work_id, model, texto_hash, embedding, updated_at)
               SELECT e.work_id, %s, e.texto_hash, e.embedding, now() FROM _emb e JOIN works w ON w.id = e.work_id
               ON CONFLICT (work_id) DO UPDATE SET model = EXCLUDED.model, texto_hash = EXCLUDED.texto_hash,
                   embedding = EXCLUDED.embedding, updated_at = now()
               WHERE work_embeddings.texto_hash IS DISTINCT FROM EXCLUDED.texto_hash""",
            (ID_MODELO,),
        )
        atualizados = cur.rowcount
        cur.execute("DELETE FROM work_embeddings WHERE work_id NOT IN (SELECT work_id FROM _emb)")
        t1 = time.monotonic()
        cur.execute("SET LOCAL maintenance_work_mem = '512MB'")
        cur.execute("CREATE INDEX work_embeddings_hnsw ON work_embeddings USING hnsw (embedding halfvec_cosine_ops)")
        log.info("Índice HNSW em %.0f s", time.monotonic() - t1)
        cur.execute("SELECT count(*), pg_size_pretty(pg_total_relation_size('work_embeddings')) FROM work_embeddings")
        n, tamanho = cur.fetchone()
    s = {"vetores_no_banco": n, "inseridos_ou_atualizados": atualizados, "tamanho_tabela_com_indice": tamanho, "segundos": round(time.monotonic() - t0)}
    log.info("Carga: %s", s)
    return s


# ------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("coletar-keywords")
    k.add_argument("--recoletar", action="store_true")
    b = sub.add_parser("benchmark")
    b.add_argument("--n", type=int, default=2000)
    b.add_argument("--lote", type=int, default=64)
    e = sub.add_parser("embeddings")
    e.add_argument("--lote", type=int, default=64)
    sub.add_parser("carregar")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if a.cmd == "coletar-keywords":
        out = coletar_keywords(a.recoletar)
    elif a.cmd == "benchmark":
        out = benchmark(a.n, a.lote)
    elif a.cmd == "embeddings":
        out = calcular_embeddings(a.lote)
    else:
        out = carregar()
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    (DIR_RELATORIOS / f"parte8_{a.cmd}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
