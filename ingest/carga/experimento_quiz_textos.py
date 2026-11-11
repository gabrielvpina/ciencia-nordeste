"""Experimento (D-040, passo 1): quantos campos de texto o quiz deve ter, e onde?

Compara, em 20 casos (nicho das respostas + descrição do OBJETO + descrição da TÉCNICA), estas variantes do texto livre:
  sem        — só as respostas (como antes da D-040)
  objeto     — só "o que você estuda, exatamente" (organismo, doença, sistema)
  metodo     — só "que técnica ou abordagem você usa"
  junto      — os dois textos num só ("objeto; técnica"), um vetor
  media      — média dos dois vetores (equivale a somar as duas similaridades com o mesmo peso)
  obj70      — 0,7 × objeto + 0,3 × técnica
Todas usam o mesmo caminho do app: vetor e5 → código PCA de 6 bits (lib/quiz/texto.ts) → POST /api/quiz/resultado.

Métrica, nos 15 da lista e nos 5 do banner: fração de pessoas com >= 2 publicações cujo título, palavras-chave (OpenAlex)
ou tópico trazem algum termo do OBJETO descrito; o mesmo para a TÉCNICA; e "ambos" (as duas condições).
As publicações não têm resumo na base, então técnicas citadas só no resumo não contam (a métrica as subestima).

Uso (app local no ar; precisa de numpy): .venv/bin/python -m ingest.carga.experimento_quiz_textos
Relatório: ingest/relatorios/quiz_textos_experimento.md
"""
from __future__ import annotations

import base64
import json
import statistics
import subprocess
import sys

import httpx
import numpy as np

from .avaliar_quiz import norm
from .validar_arvore_quiz import DIR_RELATORIOS, RAIZ, _lit, psql

# (nome, respostas de nicho, objeto descrito, termos do objeto, técnica descrita, termos da técnica) — termos sem acento
CASOS: list[tuple[str, list[str], str, list[str], str, list[str]]] = [
    ("Bactérias", ["metodo.bancada", "objeto.micro", "sub.bacterias"],
     "Klebsiella pneumoniae resistente a carbapenêmicos em hospitais", ["klebsiella", "carbapenem"],
     "sequenciamento do genoma completo e PCR de genes de resistência", ["whole genome", "whole-genome", "sequenc", "pcr", "polymerase chain"]),
    ("Vírus", ["metodo.bioinfo", "objeto.micro", "sub.virus"],
     "arbovírus como dengue, zika e chikungunya", ["dengue", "zika", "chikungunya", "arbovir"],
     "vigilância genômica com sequenciamento por nanoporo e filogenia", ["nanopore", "genomic surveillance", "phylogen", "filogen"]),
    ("Medicinais (bancada)", ["metodo.bancada", "objeto.plantas", "sub.medicinais"],
     "plantas da caatinga com ação anti-inflamatória e analgésica", ["inflamat", "analges", "nocicep", "edema"],
     "ensaios em camundongos e ratos, modelo de edema de pata", ["mice", "mouse", "rats", "camundong", "in vivo", "paw"]),
    ("Medicinais (química)", ["metodo.quimica", "objeto.plantas", "sub.medicinais"],
     "óleos essenciais de plantas aromáticas", ["essential oil", "oleo essencial", "oleos essenciais"],
     "cromatografia gasosa acoplada à espectrometria de massas", ["chromatograph", "cromatograf", "mass spectrom", "gc-ms", "gc/ms"]),
    ("Infecções", ["metodo.epidemio", "objeto.humanos", "sub.infeccoes"],
     "tuberculose e coinfecção com HIV", ["tubercul", "mycobacter"],
     "análise espacial e geoprocessamento dos casos notificados", ["spatial", "espacial", "geograph", "scan statistic", "geoprocess", "cluster"]),
    ("Mente", ["metodo.dados", "objeto.humanos", "sub.mente"],
     "depressão e ansiedade em estudantes universitários", ["depress", "anxiety", "ansiedade"],
     "aprendizado de máquina com dados de questionários", ["machine learning", "aprendizado de maquina", "deep learning", "neural network", "random forest"]),
    ("Boca", ["metodo.clinica", "objeto.humanos", "sub.boca"],
     "doença periodontal em adultos", ["periodon", "gingiv"],
     "ensaio clínico randomizado com laserterapia", ["laser", "photobiomod", "fotobiomod"]),
    ("Caprinos (genética)", ["metodo.genetica", "objeto.producao", "sub.caprinos"],
     "cabras leiteiras e produção de leite", ["dairy goat", "milk", "leite", "lactat"],
     "estudo de associação genômica ampla com marcadores SNP", ["gwas", "genome-wide", "snp", "single nucleotide"]),
    ("Caprinos (nutrição)", ["metodo.bancada", "objeto.producao", "sub.caprinos"],
     "ovinos alimentados com palma forrageira", ["cactus", "palma", "opuntia", "nopalea"],
     "digestibilidade e fermentação ruminal in vitro", ["digestib", "rumen", "ruminal"]),
    ("Abelhas", ["metodo.campo", "objeto.insetos", "sub.abelhas"],
     "abelhas sem ferrão nativas", ["stingless", "melipon", "sem ferrao", "scaptotrigona"],
     "redes de interação planta-polinizador", ["network", "interaction", "interac"]),
    ("Fungos", ["metodo.bancada", "objeto.micro", "sub.fungos"],
     "Candida resistente a antifúngicos", ["candida", "antifung", "fluconazol"],
     "nanopartículas com ação antimicrobiana", ["nanopartic", "nanoparticle"]),
    ("Anfíbios", ["metodo.campo", "objeto.fauna", "sub.herpeto"],
     "anfíbios anuros em brejos de altitude", ["anura", "anuran", "frog", "amphib", "anfib"],
     "bioacústica e gravação de vocalizações", ["acoustic", "acustic", "vocaliz", "advertisement call"]),
    ("Clima", ["metodo.dados", "objeto.ambiente", "sub.clima"],
     "secas e desertificação no semiárido", ["drought", "seca", "desertif", "aridity"],
     "sensoriamento remoto com imagens de satélite", ["remote sensing", "sensoriamento", "satellite", "landsat", "sentinel", "modis", "ndvi"]),
    ("Água", ["metodo.quimica", "objeto.ambiente", "sub.agua"],
     "contaminação de rios por metais pesados", ["heavy metal", "cadmium", "mercury", "chumbo", "mercurio", "metais pesados", "trace element"],
     "biomonitoramento com peixes e biomarcadores", ["biomarker", "biomarcador", "biomonitor", "fish"]),
    ("Movimento", ["metodo.clinica", "objeto.humanos", "sub.movimento"],
     "reabilitação depois de AVC", ["stroke", "avc", "hemipar"],
     "realidade virtual e treino com videogame", ["virtual reality", "realidade virtual", "exergam", "video game"]),
    ("Câncer", ["metodo.bancada", "objeto.humanos", "sub.cancer"],
     "câncer de mama", ["breast", "mama"],
     "cultura de células e ensaios de citotoxicidade", ["cytotox", "citotox", "cell line", "apoptos"]),
    ("Materno", ["metodo.epidemio", "objeto.humanos", "sub.materno"],
     "sífilis congênita e pré-natal", ["syphilis", "sifilis"],
     "estudo ecológico de séries temporais com dados do SINAN", ["sinan", "time series", "series temporais", "temporal trend", "tendencia"]),
    ("Laticínios", ["metodo.bancada", "objeto.alimentos", "sub.laticinios"],
     "queijo coalho artesanal", ["coalho", "cheese", "queijo"],
     "bactérias láticas probióticas e análise sensorial", ["lactic", "lactobac", "probiot", "sensory", "sensorial"]),
    ("Grãos", ["metodo.genetica", "objeto.plantas", "sub.graos"],
     "feijão-caupi tolerante à seca", ["cowpea", "vigna", "caupi"],
     "marcadores moleculares e seleção genômica", ["molecular marker", "marcador", "ssr", "snp", "genomic selection", "qtl"]),
    ("Cardio", ["metodo.dados", "objeto.humanos", "sub.cardio"],
     "hipertensão arterial na atenção primária", ["hypertens", "hipertens", "blood pressure", "pressao arterial"],
     "estudo de coorte com regressão e dados do sistema de saúde", ["cohort", "coorte", "regression", "longitudinal"]),
]
VARIANTES = ["sem", "objeto", "metodo", "junto", "media", "obj70"]


# ------------------------------------------------------------------ código do texto (igual a apps/web/lib/quiz/texto.ts)
class Base:
    ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    def __init__(self) -> None:
        j = json.loads((RAIZ / "apps/web/lib/quiz/base-texto-v1.json").read_text())
        f16 = lambda s: np.frombuffer(base64.b64decode(s), dtype="<f2").astype(np.float64)
        self.k, self.d, self.max = j["k"], j["dimensoes"], 2 ** (j["bits"] - 1) - 1
        self.media, self.comp = f16(j["media"]), f16(j["componentes"]).reshape(j["k"], j["dimensoes"])
        self.passo = j["limite"] * f16(j["sigma"]) / self.max

    def codificar(self, v: np.ndarray) -> str:
        c = self.comp @ (v - self.media)
        q = np.clip(np.round(c / self.passo), -self.max, self.max).astype(int)
        return "1" + "".join(self.ALFABETO[x + self.max] for x in q)


def embed(textos: list[str]) -> np.ndarray:
    """vetores e5 ("query:", normalizados) pelo próprio modelo do serviço embed (que não publica porta)."""
    cod = ("import json,sys,logging; logging.disable(logging.CRITICAL); import app; "
           "t=json.load(sys.stdin); v=app.modelo.encode(['query: '+x for x in t], normalize_embeddings=True, show_progress_bar=False); "
           "print(json.dumps(v.tolist()))")
    saida = subprocess.run(["docker", "compose", "exec", "-T", "embed", "python", "-c", cod], cwd=RAIZ, input=json.dumps(textos),
                           capture_output=True, text=True, check=True).stdout
    return np.array(json.loads(saida.strip().splitlines()[-1]))


def aderentes(ids: list[str], termos: list[str]) -> set[str]:
    """pessoas com >= 2 publicações cujo título, palavras-chave ou tópico trazem algum termo"""
    if not ids:
        return set()
    padrao = "|".join(t.replace("+", "\\+") for t in termos)
    linhas = psql(f"""
      SELECT a.researcher_id::text AS id FROM work_authorships a JOIN works w ON w.id = a.work_id
       WHERE a.researcher_id IN ({','.join(_lit(i) + '::uuid' for i in ids)})
         AND lower(f_unaccent(concat_ws(' ', w.title, w.primary_topic,
               (SELECT string_agg(k.keyword, ' ') FROM work_keywords k WHERE k.work_id = w.id)))) ~ {_lit(padrao)}
       GROUP BY 1 HAVING count(DISTINCT a.work_id) >= 2;""")
    return {r["id"] for r in linhas}


def main() -> int:
    base = Base()
    textos = [c for _, _, o, _, m, _ in CASOS for c in (o, m, f"{o}; {m}")]
    V = embed(textos).reshape(len(CASOS), 3, -1)
    unit = lambda v: v / np.linalg.norm(v)
    res: dict[str, dict[str, list[float]]] = {v: {m: [] for m in ("lo", "lm", "la", "bo", "bm", "ba")} for v in VARIANTES}
    linhas = []
    with httpx.Client(timeout=90) as cli:
        # conferência: o código do Python é o mesmo do app
        app_cod = cli.post("http://localhost:3000/api/quiz/texto", json={"texto": CASOS[0][2]}).json()["codigo"]
        iguais = sum(a == b for a, b in zip(app_cod, base.codificar(V[0, 0])))
        print(f"código Python × app: {iguais}/129 caracteres iguais")
        for n, (nome, resp, _, t_obj, _, t_met) in enumerate(CASOS):
            o, m, j = V[n]
            codigos = {"sem": None, "objeto": base.codificar(o), "metodo": base.codificar(m), "junto": base.codificar(j),
                       "media": base.codificar(unit(o + m)), "obj70": base.codificar(unit(0.7 * o + 0.3 * m))}
            out = {}
            for v, cod in codigos.items():
                r = cli.post("http://localhost:3000/api/quiz/resultado", json={"instituicao_id": None, "respostas": resp, "texto": cod})
                r.raise_for_status()
                out[v] = r.json()
            ids = list({x["id"] for r in out.values() for x in r["lista"]})
            ao, am = aderentes(ids, [norm(t) for t in t_obj]), aderentes(ids, [norm(t) for t in t_met])
            frac = lambda xs, s: (sum(x["id"] in s for x in xs) / len(xs)) if xs else 0.0
            cel = []
            for v in VARIANTES:
                L, B = out[v]["lista"], out[v]["banner"]
                vals = dict(lo=frac(L, ao), lm=frac(L, am), la=frac(L, ao & am), bo=frac(B, ao), bm=frac(B, am), ba=frac(B, ao & am))
                for k, x in vals.items():
                    res[v][k].append(x)
                cel.append(f"{vals['lo']:.0%} / {vals['lm']:.0%}")
            linhas.append(f"| {nome} ({len(out['sem']['lista'])}) | " + " | ".join(cel) + " |")
            print(linhas[-1])
    media = lambda v, k: statistics.mean(res[v][k])
    resumo = ["| variante | lista: objeto | lista: técnica | lista: ambos | banner: objeto | banner: técnica | banner: ambos |", "|---|---|---|---|---|---|---|"]
    for v in VARIANTES:
        resumo.append(f"| {v} | " + " | ".join(f"{media(v, k):.0%}" for k in ("lo", "lm", "la", "bo", "bm", "ba")) + " |")
    pior = {v: sum(a < b - 1e-9 for a, b in zip(res[v]["la"], res["sem"]["la"])) for v in VARIANTES[1:]}
    rel = DIR_RELATORIOS / "quiz_textos_experimento.md"
    rel.write_text("\n".join([
        "# Quiz: experimento com um ou dois campos de texto", "",
        "Aderência = fração de pessoas com ≥ 2 publicações cujo título, palavras-chave ou tópico trazem algum termo do objeto "
        "(ou da técnica) descrito. Médias de 20 casos.", "", *resumo, "",
        "Casos em que \"ambos\" na lista piorou em relação a sem texto: " + ", ".join(f"{v} {n}" for v, n in pior.items()) + ".", "",
        "## Por caso (lista de 15: objeto / técnica)", "",
        "| caso (tamanho da lista) | " + " | ".join(VARIANTES) + " |", "|---|" + "---|" * len(VARIANTES), *linhas, ""]))
    print("\n".join(resumo))
    print(f"pioras em 'ambos': {pior}\nrelatório em {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
