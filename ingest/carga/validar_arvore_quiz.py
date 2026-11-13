"""Validação da estrutura do quiz "Que cientista é você?" (etapa 13; desenho em docs/etapas/13-quiz-alinhamento.md).

A estrutura é dado versionado em apps/web/lib/quiz/arvore.json: uma sequência fixa de telas (facetas). As telas de
**nicho** (método, objeto, sub-objeto, foco, escala, ambiente, impacto) alimentam o match com pesquisadores; as de
**perfil** (habitat, estilo, vínculo) só montam o título do banner e não podem ter sinais de match.

  python -m ingest.carga.validar_arvore_quiz estatico       # estrutura, títulos neutros, separação perfil × match (sem banco; no verificar.sh)
  python -m ingest.carga.validar_arvore_quiz levantamento   # subfields/topics com pesquisadores ativos -> relatorios/quiz_levantamento.md
  python -m ingest.carga.validar_arvore_quiz banco          # núcleo método × sub-objeto contra o banco -> relatorios/quiz_validacao.md

O comando `banco` usa o Postgres do docker compose (psql dentro do container `db`) e só lê. Para cada par do núcleo:
  - pesquisadores ativos (>= 3 publicações no período, não ocultos) com >= 2 publicações que casam o método E o sub-objeto;
  - quantos sobram sem a maior instituição do par (e as ligadas a ela por parent/child);
  - top 10 por encaixe no nicho (só as publicações que casam o núcleo: soma / (publicações + 2) × ln(1 + casadas)),
    para medir a sobreposição (Jaccard) entre sub-objetos irmãos do mesmo método.
Uma publicação casa um sinal por tópico (work_topics: principal 1,0 · secundário 0,5), subfield (0,5), field (0,25) ou termo
(0,7) no início de uma palavra do título ou das palavras-chave; o peso de cada faceta vem de `pesos_faceta` no JSON.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import itertools
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
ARQ_ARVORE = RAIZ / "apps" / "web" / "lib" / "quiz" / "arvore.json"
DIR_RELATORIOS = RAIZ / "ingest" / "relatorios"

MIN_OPCOES, MAX_OPCOES = 2, 8
MAX_TELAS = 11                                   # contando a instituição
RAROS = 5                                        # pares do núcleo com menos que isto vão para revisão (o banner mostra "até 5")
MAX_JACCARD = 0.5                                # top 10 de sub-objetos irmãos (mesmo método e objeto)
MAX_TITULO = 42                                  # caracteres
FACETAS_NICHO = {"metodo", "objeto", "sub_objeto", "foco", "escala", "ambiente", "impacto"}
FACETAS_PERFIL = {"habitat", "estilo", "vinculo"}
RE_TOPIC, RE_NUM = re.compile(r"^T\d+$"), re.compile(r"^\d+$")
CONTRACAO = {"o": "do", "a": "da", "os": "dos", "as": "das"}


def carregar(arq: Path = ARQ_ARVORE) -> dict[str, Any]:
    return json.loads(arq.read_text(encoding="utf-8"))


def opcoes(q: dict[str, Any]) -> list[dict[str, Any]]:
    """Todas as opções de uma pergunta (as condicionais vêm agrupadas por resposta anterior)."""
    if "opcoes_por" in q:
        return [o for grupo in q["opcoes_por"].values() for o in grupo]
    return list(q.get("opcoes", []))


def de(sintagma: dict[str, str]) -> str:
    return f"{CONTRACAO[sintagma['artigo']]} {sintagma['nome']}"


def titulos(arv: dict[str, Any]) -> list[str]:
    """Todos os títulos principais possíveis (arquétipos + vínculos × sintagmas)."""
    T = arv["titulos"]
    P = arv["perguntas"]
    saida = [t for linha in T["arquetipos"].values() for t in linha.values()] + [T["padrao"]]
    alvos = {"sub_objeto": [o["sintagma"] for o in opcoes(P["sub_objeto"]) if "sintagma" in o],
             "ambiente": [o["sintagma"] for o in opcoes(P["ambiente"]) if "sintagma" in o]}
    for v in T["vinculos"].values():
        if v["modelo"]:   # sem ambiente essencial, o vínculo "proteger" usa o sub-objeto (lib/quiz/titulo.ts)
            usa = alvos["sub_objeto"] + (alvos["ambiente"] if v["usa"] == "ambiente" else [])
            saida += [v["modelo"].replace("{de}", de(s)) for s in usa]
    return saida


# ---------------------------------------------------------------- estático
def estatico(arv: dict[str, Any]) -> list[str]:
    erros: list[str] = []
    P = arv.get("perguntas", {})
    telas = arv.get("telas", [])
    if len(telas) + 1 > MAX_TELAS:
        erros.append(f"{len(telas) + 1} telas com a instituição (máximo {MAX_TELAS})")
    erros += [f"tela {t!r} sem pergunta" for t in telas if t not in P]
    erros += [f"pergunta {q!r} fora das telas" for q in P if q not in telas]
    erros += [f"núcleo {n!r} não é tela" for n in arv.get("nucleo", []) if n not in telas]
    if erros:
        return erros
    ids: set[str] = set()
    obj_ids = {o["id"] for o in opcoes(P["objeto"])}
    for qid, q in P.items():
        faceta, bloco = q.get("faceta"), q.get("bloco")
        if not q.get("texto"):
            erros.append(f"{qid}: sem texto")
        if bloco == "nicho" and faceta not in FACETAS_NICHO or bloco == "perfil" and faceta not in FACETAS_PERFIL or bloco not in ("nicho", "perfil"):
            erros.append(f"{qid}: bloco/faceta inválidos ({bloco}/{faceta})")
        grupos = q["opcoes_por"].values() if "opcoes_por" in q else [q.get("opcoes", [])]
        if "opcoes_por" in q:
            dep = q.get("depende_de")
            if dep not in P or telas.index(dep) > telas.index(qid):
                erros.append(f"{qid}: depende_de {dep!r} inválido (precisa vir antes)")
            faltam = obj_ids - set(q["opcoes_por"]) if dep == "objeto" else set()
            erros += [f"{qid}: sem opções para {f}" for f in sorted(faltam)]
        filtrada = any("objetos" in o for o in opcoes(q))      # opções filtradas pelo objeto: conta-se por objeto, abaixo
        for grupo in ([] if filtrada else grupos):
            if not MIN_OPCOES <= len(grupo) <= MAX_OPCOES:
                erros.append(f"{qid}: grupo com {len(grupo)} opções (esperado {MIN_OPCOES}–{MAX_OPCOES})")
        for o in opcoes(q):
            oid = o.get("id", "")
            if not oid or not o.get("rotulo"):
                erros.append(f"{qid}: opção sem id ou rótulo")
            if oid in ids:
                erros.append(f"{oid}: id repetido")
            ids.add(oid)
            s = o.get("sinais", {})
            if bloco == "perfil" and (s or o.get("objetos")):
                erros.append(f"{oid}: pergunta de perfil não pode ter sinais de match (o banner não interfere no match)")
            if bloco == "nicho":
                if any(s.get(k) for k in ("topics", "subfields", "fields", "termos")) and not s.get("frase"):
                    erros.append(f"{oid}: tem sinais mas não tem frase (texto da consulta vetorial)")
                erros += [f"{oid}: topic inválido {t!r}" for t in s.get("topics", []) if not RE_TOPIC.match(str(t))]
                erros += [f"{oid}: subfield/field inválido {t!r}" for t in s.get("subfields", []) + s.get("fields", []) if not RE_NUM.match(str(t))]
            if faceta in ("sub_objeto", "ambiente") and s and "sintagma" not in o:
                erros.append(f"{oid}: sem sintagma (artigo + nome) para o título")
            if "sintagma" in o and o["sintagma"].get("artigo") not in CONTRACAO:
                erros.append(f"{oid}: artigo do sintagma inválido")
            if faceta in ("metodo", "sub_objeto") and not o.get("nicho"):
                erros.append(f"{oid}: sem fragmento do nicho escrito")
            erros += [f"{oid}: objeto desconhecido {x!r}" for x in o.get("objetos", []) if x not in obj_ids]
            met_ids = {m["id"] for m in opcoes(P["metodo"])}
            erros += [f"{oid}: método desconhecido {x!r}" for x in o.get("metodos", []) + o.get("sem_metodos", []) if x not in met_ids]
    # filtros por método: cada método oferece >= 2 objetos, e cada objeto >= 2 sub-objetos para cada método que o oferece
    for m in opcoes(P["metodo"]):
        objs = [o for o in opcoes(P["objeto"]) if m["id"] in o.get("metodos", [m["id"]])]
        if len(objs) < MIN_OPCOES:
            erros.append(f"{m['id']}: só {len(objs)} objeto(s) oferecido(s)")
        for o in objs:
            subs = [s for s in P["sub_objeto"]["opcoes_por"].get(o["id"], []) if m["id"] not in s.get("sem_metodos", [])]
            if len(subs) < MIN_OPCOES:
                erros.append(f"{m['id']} × {o['id']}: só {len(subs)} sub-objeto(s)")
    # cada objeto precisa de pelo menos 2 focos
    if "foco" in P:
        por_obj = collections.Counter(x for o in opcoes(P["foco"]) for x in o.get("objetos", sorted(obj_ids)))
        erros += [f"foco: objeto {x} com {por_obj[x]} opção(ões) (esperado {MIN_OPCOES}–{MAX_OPCOES})" for x in sorted(obj_ids)
                  if not MIN_OPCOES <= por_obj[x] <= MAX_OPCOES]
    # títulos: completos, neutros, sem nomes licenciados, curtos
    T = arv.get("titulos", {})
    hab = [o["id"] for o in opcoes(P["habitat"])]
    est = [o["id"] for o in opcoes(P["estilo"])]
    vin = [o["id"] for o in opcoes(P["vinculo"])]
    for h, e in itertools.product(hab, est):
        if not T.get("arquetipos", {}).get(h, {}).get(e):
            erros.append(f"títulos: falta o arquétipo {h} × {e}")
    erros += [f"títulos: falta o vínculo {v}" for v in vin if v not in T.get("vinculos", {})]
    if erros:
        return erros
    proibidos = [p.lower() for p in T.get("proibidos", [])]
    for t in titulos(arv):
        tl = f" {t.lower()} "
        erros += [f"título com termo proibido ({p.strip()!r}): {t}" for p in proibidos if p in tl]
        if len(t) > MAX_TITULO:
            erros.append(f"título longo demais ({len(t)} > {MAX_TITULO}): {t}")
    return erros


# ---------------------------------------------------------------- banco (psql no container)
def psql(sql: str) -> list[dict[str, str]]:
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "sh", "-c",
         'psql -v ON_ERROR_STOP=1 -q -X --csv -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        input=sql, capture_output=True, text=True, cwd=RAIZ, check=False)
    if r.returncode != 0:
        raise SystemExit(f"psql falhou:\n{r.stderr[-2000:]}")
    # com várias instruções, o --csv imprime um bloco por SELECT; usamos só o último
    blocos = [b for b in r.stdout.strip().split("\n\n") if b.strip()]
    return list(csv.DictReader(io.StringIO(blocos[-1]))) if blocos else []


SQL_ATIVOS = """
CREATE TEMP TABLE ativos AS
  SELECT a.researcher_id AS rid, count(DISTINCT a.work_id)::int AS n
    FROM work_authorships a JOIN researchers r ON r.id = a.researcher_id AND NOT r.is_hidden
   GROUP BY 1 HAVING count(DISTINCT a.work_id) >= 3;
CREATE UNIQUE INDEX ON ativos (rid);
CREATE TEMP TABLE rw AS SELECT DISTINCT a.researcher_id AS rid, a.work_id FROM work_authorships a JOIN ativos t ON t.rid = a.researcher_id;
CREATE INDEX ON rw (work_id); ANALYZE ativos; ANALYZE rw;
"""


def levantamento() -> Path:
    linhas = psql(SQL_ATIVOS + """
      CREATE TEMP TABLE rt AS SELECT rw.rid, w.primary_topic_id AS tp, count(*) AS n FROM rw JOIN works w ON w.id = rw.work_id GROUP BY 1, 2;
      SELECT t.field, t.subfield, t.subfield_id, t.openalex_id, t.name, count(*) FILTER (WHERE rt.n >= 2) AS pesq2, sum(rt.n) AS autorias
        FROM rt JOIN topics t ON t.openalex_id = rt.tp GROUP BY 1, 2, 3, 4, 5 HAVING count(*) FILTER (WHERE rt.n >= 2) >= 15
       ORDER BY 1, 2, 6 DESC;""")
    total = psql(SQL_ATIVOS + "SELECT count(*) AS n FROM ativos;")[0]["n"]
    por_sub: dict[tuple[str, str, str], list[dict[str, str]]] = collections.defaultdict(list)
    for lin in linhas:
        por_sub[(lin["field"], lin["subfield"], lin["subfield_id"])].append(lin)
    L = ["# Quiz — levantamento de subfields e topics do recorte", "",
         f"Pesquisadores ativos (≥ 3 publicações no período, não ocultos): **{int(total):,}**".replace(",", "."), "",
         "Por topic: pesquisadores com ≥ 2 publicações (tópico principal) no topic. Só topics com ≥ 15 pesquisadores.", ""]
    for (fld, sub, sid), ts in sorted(por_sub.items(), key=lambda kv: -sum(int(t["pesq2"]) for t in kv[1])):
        L += [f"## {sub} (`{sid}`) · {fld}", "", "| topic | nome | pesquisadores (≥2) | autorias |", "|---|---|---|---|"]
        L += [f"| `{t['openalex_id']}` | {t['name']} | {t['pesq2']} | {t['autorias']} |" for t in ts]
        L.append("")
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    arq = DIR_RELATORIOS / "quiz_levantamento.md"
    arq.write_text("\n".join(L) + "\n", encoding="utf-8")
    return arq


def _lit(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


@dataclass
class Par:
    """Um par do núcleo (método × sub-objeto), com os sinais que o encaixe usa."""
    metodo: str
    objeto: str
    sub: str
    nome: str
    sinais: list[tuple[str, str, float, str]] = field(default_factory=list)   # (tipo, valor, peso, papel: metodo | sub | "")


def _sinais(o: dict[str, Any], peso: float, papel: str) -> list[tuple[str, str, float, str]]:
    s = o.get("sinais", {})
    return [(t, str(v), peso, papel) for t, chave in (("topic", "topics"), ("subfield", "subfields"), ("field", "fields"), ("termo", "termos"))
            for v in s.get(chave, [])]


def pares(arv: dict[str, Any]) -> list[Par]:
    P, w = arv["perguntas"], arv["pesos_faceta"]
    objetos = {o["id"]: o for o in opcoes(P["objeto"])}
    saida = []
    for m in opcoes(P["metodo"]):
        for oid, subs in P["sub_objeto"]["opcoes_por"].items():
            if m["id"] not in objetos[oid].get("metodos", [m["id"]]):
                continue                                          # objeto não oferecido para este método
            for s in subs:
                if m["id"] in s.get("sem_metodos", []):
                    continue                                      # par sem nicho, retirado
                saida.append(Par(m["id"], oid, s["id"], f"{m['rotulo']} × {s['rotulo']}",
                                 _sinais(m, w["metodo"], "metodo") + _sinais(objetos[oid], w["objeto"], "")
                                 + _sinais(s, w["sub_objeto"], "sub")))
    return saida


def banco(arv: dict[str, Any]) -> tuple[Path, bool]:
    ps = pares(arv)
    # 1. ids existem (todas as opções de nicho)
    usados: dict[str, set[str]] = {"topic": set(), "subfield": set(), "field": set()}
    for q in arv["perguntas"].values():
        for o in opcoes(q):
            for t, v, _, _ in _sinais(o, 1, ""):
                if t in usados:
                    usados[t].add(v)
    existe = psql(f"""SELECT 'topic' AS t, openalex_id AS v FROM topics WHERE openalex_id IN ({','.join(map(_lit, usados['topic'])) or "''"})
      UNION SELECT DISTINCT 'subfield', subfield_id FROM topics WHERE subfield_id IN ({','.join(map(_lit, usados['subfield'])) or "''"})
      UNION SELECT DISTINCT 'field', field_id FROM topics WHERE field_id IN ({','.join(map(_lit, usados['field'])) or "''"});""")
    achados = {(e["t"], e["v"]) for e in existe}
    faltando = sorted(f"{t} {v}" for t, vs in usados.items() for v in vs if (t, v) not in achados)

    # 2. núcleo: >= 2 publicações que casam método E sub-objeto (uma consulta só, com todos os pares)
    sinais = [(i, t, v, w, f) for i, p in enumerate(ps) for t, v, w, f in p.sinais]
    termos = sorted({v for _, t, v, _, _ in sinais if t == "termo"})
    valores = ",\n".join(f"({i},{_lit(t)},{_lit(v)},{w},{_lit(f)})" for i, t, v, w, f in sinais)
    sql = SQL_ATIVOS + f"""
CREATE TEMP TABLE sinal (cam int, tipo text, valor text, peso real, papel text);
INSERT INTO sinal VALUES {valores};
-- termos: no início de uma palavra, no título e nas palavras-chave ("fertiliz" casa "fertilization"; "app" não casa "approach")
CREATE TEMP TABLE termo AS SELECT t AS termo, '\\m' || lower(f_unaccent(t)) AS re FROM unnest(ARRAY[{','.join(map(_lit, termos))}]::text[]) t;
CREATE TEMP TABLE termo_work AS
  SELECT t.termo, w.id AS work_id FROM works w JOIN termo t ON lower(f_unaccent(w.title)) ~ t.re
  UNION
  SELECT t.termo, k.work_id FROM termo t
    JOIN work_keywords k ON lower(f_unaccent(k.keyword)) LIKE '%' || lower(f_unaccent(t.termo)) || '%' AND lower(f_unaccent(k.keyword)) ~ t.re;
CREATE INDEX ON termo_work (termo);
CREATE TEMP TABLE work_sub AS SELECT w.id AS work_id, tp.subfield_id, w.primary_field_id AS field_id FROM works w JOIN topics tp ON tp.openalex_id = w.primary_topic_id;
CREATE TEMP TABLE casa AS
SELECT cam, work_id, sum(v) AS v, bool_or(papel = 'metodo') AS m, bool_or(papel = 'sub') AS s FROM (
  SELECT cam, work_id, papel, max(v) AS v FROM (
    SELECT s.cam, wt.work_id, s.peso * CASE WHEN wt.is_primary THEN 1.0 ELSE 0.5 END AS v, s.papel
      FROM sinal s JOIN work_topics wt ON wt.topic_openalex_id = s.valor WHERE s.tipo = 'topic'
    UNION ALL SELECT s.cam, ws.work_id, s.peso * 0.5, s.papel FROM sinal s JOIN work_sub ws ON ws.subfield_id = s.valor WHERE s.tipo = 'subfield'
    UNION ALL SELECT s.cam, ws.work_id, s.peso * 0.25, s.papel FROM sinal s JOIN work_sub ws ON ws.field_id = s.valor WHERE s.tipo = 'field'
    UNION ALL SELECT s.cam, tw.work_id, s.peso * 0.7, s.papel FROM sinal s JOIN termo_work tw ON tw.termo = s.valor WHERE s.tipo = 'termo'
  ) x GROUP BY 1, 2, 3            -- melhor sinal de cada faceta na publicação; as facetas se somam
) y GROUP BY 1, 2;
CREATE TEMP TABLE fit AS
SELECT c.cam, rw.rid, count(*) FILTER (WHERE c.m AND c.s)::int AS n_nucleo, sum(c.v) FILTER (WHERE c.m AND c.s) AS soma   -- só as publicações do nicho
  FROM casa c JOIN rw ON rw.work_id = c.work_id GROUP BY 1, 2 HAVING count(*) FILTER (WHERE c.m AND c.s) >= 2;
CREATE TEMP TABLE fit2 AS
SELECT f.cam, f.rid, f.n_nucleo, (f.soma / (a.n + 2)) * ln(1 + f.n_nucleo) AS escore, r.main_institution_id AS inst
  FROM fit f JOIN ativos a ON a.rid = f.rid JOIN researchers r ON r.id = f.rid;
CREATE TEMP TABLE maior AS
SELECT DISTINCT ON (cam) cam, inst, count(*) AS n FROM fit2 WHERE inst IS NOT NULL GROUP BY cam, inst ORDER BY cam, count(*) DESC;
CREATE TEMP TABLE excl AS
SELECT m.cam, m.inst FROM maior m
UNION SELECT m.cam, r.related_institution_id FROM maior m JOIN institution_relations r ON r.institution_id = m.inst
   AND r.relation IN ('parent', 'child') AND r.related_institution_id IS NOT NULL
UNION SELECT m.cam, r.institution_id FROM maior m JOIN institution_relations r ON r.related_institution_id = m.inst AND r.relation IN ('parent', 'child');
SELECT f.cam, count(*) AS total,
       count(*) FILTER (WHERE f.inst IS NULL OR NOT EXISTS (SELECT 1 FROM excl e WHERE e.cam = f.cam AND e.inst = f.inst)) AS sem_maior,
       (SELECT coalesce(i.acronym, i.name) FROM maior m JOIN institutions i ON i.id = m.inst WHERE m.cam = f.cam) AS maior_inst,
       (SELECT string_agg(rid::text, ',' ORDER BY escore DESC) FROM (SELECT rid, escore FROM fit2 g WHERE g.cam = f.cam ORDER BY escore DESC LIMIT 10) t) AS top10,
       (SELECT string_agg(nome, '; ') FROM (SELECT rr.display_name AS nome FROM fit2 g JOIN researchers rr ON rr.id = g.rid
          WHERE g.cam = f.cam ORDER BY g.escore DESC LIMIT 3) t) AS top3
  FROM fit2 f GROUP BY f.cam ORDER BY f.cam;
"""
    res = {int(r["cam"]): r for r in psql(sql)}
    vazio = {"total": "0", "sem_maior": "0", "maior_inst": "", "top10": "", "top3": ""}
    linhas = [(p, res.get(i, vazio)) for i, p in enumerate(ps)]
    tops = {i: set(filter(None, (r["top10"] or "").split(","))) for i, (_, r) in enumerate(linhas)}

    def jaccards(chave: Any) -> list[tuple[float, str, str]]:
        grupos: dict[Any, list[int]] = collections.defaultdict(list)
        for i, p in enumerate(ps):
            grupos[chave(p)].append(i)
        out = []
        for idx in grupos.values():
            for a, b in itertools.combinations(idx, 2):
                if tops[a] and tops[b]:
                    out.append((len(tops[a] & tops[b]) / len(tops[a] | tops[b]), ps[a].nome, ps[b].nome))
        return out

    irmas = jaccards(lambda p: (p.metodo, p.objeto))          # sub-objetos irmãos no mesmo método: devem diferir
    metodos = jaccards(lambda p: p.sub)                         # métodos diferentes no mesmo sub-objeto: só aviso
    parecidas = sorted((j for j in irmas if j[0] > MAX_JACCARD), reverse=True)
    vazios = [p for p, r in linhas if int(r["total"] or 0) == 0]
    raros = [(p, int(r["sem_maior"] or 0)) for p, r in linhas if 0 < int(r["sem_maior"] or 0) < RAROS]
    ok = not faltando and not parecidas
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0.0  # noqa: E731
    contagens = sorted(int(r["sem_maior"] or 0) for _, r in linhas)
    L = ["# Quiz — validação da estrutura contra o banco", "",
         f"Estrutura: `{ARQ_ARVORE.relative_to(RAIZ)}` (versão {arv.get('versao')}). Núcleo do match: método × sub-objeto = **{len(ps)} pares**.", "",
         f"- ids de topic/subfield/field inexistentes: **{len(faltando)}** {('· ' + ', '.join(faltando)) if faltando else ''}",
         f"- pares sem nenhum pesquisador: **{len(vazios)}** · pares com 1 a {RAROS - 1} (sem a maior instituição): **{len(raros)}**",
         f"- pesquisadores por par, sem a maior instituição: mediana **{med(contagens)}**, mínimo {contagens[0] if contagens else 0}, máximo {contagens[-1] if contagens else 0}",
         f"- sub-objetos irmãos (mesmo método) com Jaccard dos top 10 > {MAX_JACCARD}: **{len(parecidas)}** "
         f"(mediana {med([j for j, _, _ in irmas]):.2f}, máximo {max((j for j, _, _ in irmas), default=0):.2f}, {len(irmas)} pares)",
         f"- aviso: métodos diferentes no mesmo sub-objeto — Jaccard mediano {med([j for j, _, _ in metodos]):.2f}, máximo {max((j for j, _, _ in metodos), default=0):.2f}",
         f"- resultado: **{'OK' if ok else 'há pendências'}**", ""]
    if parecidas:
        L += ["## Sub-objetos irmãos parecidos demais", "", "| Jaccard | par A | par B |", "|---|---|---|"]
        L += [f"| {j:.2f} | {a} | {b} |" for j, a, b in parecidas] + [""]
    if vazios:
        L += ["## Pares vazios (o quiz pode oferecer, mas o match volta sem ninguém)", ""] + [f"- {p.nome}" for p in vazios] + [""]
    if raros:
        L += [f"## Pares raros (1 a {RAROS - 1} pesquisadores)", ""] + [f"- {p.nome}: {n}" for p, n in raros] + [""]
    L += ["## Todos os pares", "", "| método × sub-objeto | pesquisadores | sem a maior | maior instituição | 3 primeiros (só encaixe) |", "|---|---|---|---|---|"]
    L += [f"| {p.nome} | {r['total']} | {r['sem_maior']} | {r['maior_inst'] or '—'} | {r['top3'] or ''} |" for p, r in linhas]
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    arq = DIR_RELATORIOS / "quiz_validacao.md"
    arq.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR_RELATORIOS / "quiz_validacao.json").write_text(json.dumps({
        "pares": [{"metodo": p.metodo, "objeto": p.objeto, "sub": p.sub, "nome": p.nome, "total": int(r["total"] or 0),
                   "sem_maior": int(r["sem_maior"] or 0), "maior": r["maior_inst"]} for p, r in linhas],
        "faltando": faltando, "parecidas": [[round(j, 3), a, b] for j, a, b in parecidas],
        "jaccard_metodos": sorted([[round(j, 3), a, b] for j, a, b in metodos], reverse=True)[:30],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return arq, ok


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["estatico", "levantamento", "banco"])
    a = p.parse_args(argv)
    if a.comando == "levantamento":
        print(f"gravado {levantamento().relative_to(RAIZ)}")
        return 0
    arv = carregar()
    erros = estatico(arv)
    if erros:
        print("estrutura do quiz: ERROS", *erros, sep="\n  ")
        return 1
    print(f"estrutura do quiz: ok ({len(arv['telas']) + 1} telas com a instituição, {len(pares(arv))} pares no núcleo, "
          f"{len(titulos(arv))} títulos principais)")
    if a.comando == "banco":
        arq, ok = banco(arv)
        print(f"gravado {arq.relative_to(RAIZ)}: {'OK' if ok else 'há pendências'}")
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
