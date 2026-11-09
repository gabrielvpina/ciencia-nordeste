"""Serviço de embedding das consultas (busca por tema, D-028).

Transforma a frase digitada pelo usuário num vetor com o MESMO modelo usado para as publicações
(intfloat/multilingual-e5-base, commit fixo). Só na rede interna do Docker; sem dependências web além da stdlib.

GET  /saude                    -> {"ok": true, "modelo": ...}
POST /embed {"texto": "..."}   -> {"vetor": [768 floats]}   (prefixo "query:" do e5 aplicado aqui)
"""

from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from sentence_transformers import SentenceTransformer

MODELO = os.environ.get("MODELO", "intfloat/multilingual-e5-base")
REVISAO = os.environ.get("REVISAO", "d128750597153bb5987e10b1c3493a34e5a4502a")
MAX_CARACTERES = 300

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
torch.set_num_threads(int(os.environ.get("THREADS", "2")))
modelo = SentenceTransformer(MODELO, revision=REVISAO, device="cpu", model_kwargs={"use_safetensors": True})
modelo.encode(["query: aquecimento"], normalize_embeddings=True)
logging.info("Modelo %s@%s carregado", MODELO, REVISAO[:7])


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, corpo: dict) -> None:
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/saude":
            self._json(200, {"ok": True, "modelo": f"{MODELO}@{REVISAO[:7]}"})
        else:
            self._json(404, {"erro": "não encontrado"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/embed":
            self._json(404, {"erro": "não encontrado"})
            return
        try:
            n = min(int(self.headers.get("content-length", "0")), 4096)
            texto = str(json.loads(self.rfile.read(n) or b"{}").get("texto", "")).strip()[:MAX_CARACTERES]
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"erro": "json inválido"})
            return
        if not texto:
            self._json(400, {"erro": "texto vazio"})
            return
        vetor = modelo.encode([f"query: {texto}"], normalize_embeddings=True)[0]
        self._json(200, {"vetor": [round(float(x), 5) for x in vetor]})

    def log_message(self, fmt: str, *args: object) -> None:  # não registra o texto das consultas (privacidade)
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
