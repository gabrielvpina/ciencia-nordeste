"""Base de compressão do texto livre do quiz (etapa 13, D-040).

A pessoa descreve a pesquisa em poucas palavras; o app transforma o texto em vetor (e5, 768 dimensões) e o
projeta nesta base: as 128 primeiras componentes principais (PCA) dos perfis temáticos dos pesquisadores
(researcher_embeddings). Cada coeficiente vira 6 bits (um caractere base64url), e o link do resultado leva
só esse código de 129 caracteres — nunca o texto. O match reconstrói um vetor aproximado a partir do código.

Medição com 30 consultas de exemplo (35.724 perfis): correlação de Spearman 0,991 entre a similaridade exata e a
reconstruída; 82% de sobreposição entre os 100 perfis mais próximos (mínimo 75%).

A base precisa ser ESTÁVEL: links já compartilhados dependem dela. Por isso o script não sobrescreve uma versão
existente; uma base nova (ex.: depois de trocar o modelo de embedding) exige --versao N, e o app passa a aceitar
os códigos das duas versões enquanto a antiga existir em apps/web/lib/quiz/.

Uso: .venv/bin/python -m ingest.carga.quiz_base_texto [--versao 1]   (precisa de numpy: requirements-embeddings.txt)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

K = 128          # componentes guardadas (= caracteres do código, além do de versão)
BITS = 6         # bits por coeficiente: um caractere base64url
LIMITE = 3.0     # coeficientes cortados em ±3 desvios-padrão da população
RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "apps" / "web" / "lib" / "quiz"


def ler_perfis() -> np.ndarray:
    """Lê os perfis pelo psql do container do banco (mesma forma dos outros scripts de carga)."""
    sql = "SELECT embedding::text FROM researcher_embeddings ORDER BY researcher_id"
    cmd = ["docker", "compose", "exec", "-T", "db", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "{sql}"']
    saida = subprocess.run(cmd, cwd=RAIZ, check=True, capture_output=True, text=True).stdout
    linhas = [l for l in saida.splitlines() if l.startswith("[")]
    return np.array([np.array(l[1:-1].split(","), dtype=np.float32) for l in linhas])


def b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f2").tobytes()).decode()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--versao", type=int, default=1, help="número da base (1 caractere no código: 1–9)")
    args = ap.parse_args()
    if not 1 <= args.versao <= 9:
        sys.exit("versão deve ser de 1 a 9")
    arq = DESTINO / f"base-texto-v{args.versao}.json"
    if arq.exists():
        sys.exit(f"{arq.relative_to(RAIZ)} já existe: links compartilhados dependem dela. Use outra --versao.")

    P = ler_perfis()
    print(f"{len(P)} perfis × {P.shape[1]} dimensões")
    media = P.mean(axis=0)
    _, S, Vt = np.linalg.svd(P - media, full_matrices=False)
    sigma = S[:K] / np.sqrt(len(P))
    var = float((S[:K] ** 2).sum() / (S ** 2).sum())
    # float16 basta (erro ~1e-3 por componente, muito abaixo do da quantização de 6 bits)
    dados = {
        "versao": args.versao, "k": K, "bits": BITS, "limite": LIMITE, "dimensoes": int(P.shape[1]),
        "perfis": int(len(P)), "variancia_explicada": round(var, 4),
        "media": b64(media), "sigma": b64(sigma), "componentes": b64(Vt[:K]),
    }
    arq.write_text(json.dumps(dados, separators=(",", ":")) + "\n")
    print(f"gravado {arq.relative_to(RAIZ)} ({os.path.getsize(arq) // 1024} KB); variância explicada {var:.2f}")


if __name__ == "__main__":
    main()
