"""Validação da árvore do quiz "Que cientista é você?" (etapa 13, D-036).

A árvore é dado versionado em apps/web/lib/quiz/arvore.json. Três comandos:

  python -m ingest.carga.validar_arvore_quiz estatico       # estrutura, sem banco (roda no scripts/verificar.sh)
  python -m ingest.carga.validar_arvore_quiz levantamento   # subfields/topics com pesquisadores ativos -> relatorios/quiz_levantamento.md
  python -m ingest.carga.validar_arvore_quiz banco          # ids existem, folhas com >= 15 pesquisadores sem a maior instituição,
                                                            # sobreposição dos top 10 entre ramos irmãos -> relatorios/quiz_validacao.md

O comando `banco` usa o Postgres do docker compose (psql dentro do container `db`) e só lê.
Encaixe usado aqui (o mesmo de apps/web/lib/quiz/alinhamento.ts, sem a parte vetorial e sem a proeminência):
  cada publicação do pesquisador no recorte vale o maior sinal que ela casa no caminho:
    tópico (work_topics: principal 1,0 · secundário 0,5) · subfield 0,5 · field 0,25 · termo no título/palavras-chave 0,7,
  multiplicado pelo peso da profundidade da resposta (respostas mais fundas pesam mais);
  pesquisador "casa" a folha com >= 2 publicações que casam ao mesmo tempo as duas últimas respostas (as mais específicas);
  termos casam no início de uma palavra (regex de início de palavra do Postgres), para "app" não casar "approach"; ordem = (soma / (publicações + 2)) × ln(1 + casadas).
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
ARQ_ARVORE = RAIZ / "apps" / "web" / "lib" / "quiz" / "arvore.json"
DIR_RELATORIOS = RAIZ / "ingest" / "relatorios"

MIN_OPCOES, MAX_OPCOES = 2, 6
MIN_PROFUNDIDADE, MAX_PROFUNDIDADE = 3, 6       # perguntas respondidas por caminho (sem contar a instituição)
MIN_PESQUISADORES = 15                           # por folha, sem a maior instituição do tema
MAX_JACCARD = 0.5                                # top 10 de folhas irmãs
CAMADAS_ARTE = {"fundo", "elemento", "detalhe"}
RE_TOPIC, RE_NUM = re.compile(r"^T\d+$"), re.compile(r"^\d+$")


# ---------------------------------------------------------------- árvore e caminhos
@dataclass
class Caminho:
    respostas: list[str]                         # ids das opções, em ordem
    rotulos: list[str]
    sinais: list[tuple[str, str, float, str]] = field(default_factory=list)   # (tipo, valor, peso, papel: folha | penultima | "")
    pai: str = ""                                # prefixo (pergunta + respostas anteriores): define os irmãos

    @property
    def nome(self) -> str:
        return " → ".join(self.rotulos)


def carregar(arq: Path = ARQ_ARVORE) -> dict[str, Any]:
    return json.loads(arq.read_text(encoding="utf-8"))


def caminhos(arv: dict[str, Any]) -> Iterator[Caminho]:
    """Todos os caminhos da raiz até uma folha (opção com proxima = null). O pular da raiz conta como caminho (genérico)."""
    pesos = arv["pesos_profundidade"]
    P = arv["perguntas"]

    def andar(qid: str, resp: list[str], rot: list[str], sin: list[tuple[str, str, float, str]]) -> Iterator[Caminho]:
        q = P[qid]
        prof = len(resp)
        w = pesos[min(prof, len(pesos) - 1)]
        for o in q["opcoes"]:
            s = o.get("sinais", {})
            novos = [(t, str(v), w, str(len(resp))) for t, chave in (("topic", "topics"), ("subfield", "subfields"), ("field", "fields"), ("termo", "termos"))
                     for v in s.get(chave, [])]
            if o["proxima"] is None:
                todos = sin + novos          # papel: a última resposta é a "folha"; a anterior, a "penultima"
                n = len(resp)
                papel = {str(n): "folha", str(n - 1): "penultima"}
                yield Caminho(resp + [o["id"]], rot + [o["rotulo"]], [(t, v, w, papel.get(p, "")) for t, v, w, p in todos],
                              pai=" | ".join(resp + [qid]))
            else:
                yield from andar(o["proxima"], resp + [o["id"]], rot + [o["rotulo"]], sin + novos)
        if q.get("pular") and prof == 0:
            yield from andar(q["pular"], resp, rot + ["(pulou)"], sin)

    yield from andar(arv["raiz"], [], [], [])


# ---------------------------------------------------------------- estático
def estatico(arv: dict[str, Any]) -> list[str]:
    erros: list[str] = []
    P = arv.get("perguntas", {})
    if arv.get("raiz") not in P:
        return [f"raiz {arv.get('raiz')!r} não existe"]
    ids_opcao: dict[str, str] = {}
    for qid, q in P.items():
        ops = q.get("opcoes", [])
        if not q.get("texto"):
            erros.append(f"{qid}: sem texto")
        if not MIN_OPCOES <= len(ops) <= MAX_OPCOES:
            erros.append(f"{qid}: {len(ops)} opções (esperado {MIN_OPCOES}–{MAX_OPCOES})")
        if q.get("pular") is not None and q["pular"] not in P:
            erros.append(f"{qid}: pular → {q['pular']!r} não existe")
        for o in ops:
            oid = o.get("id", "")
            if not oid or not o.get("rotulo"):
                erros.append(f"{qid}: opção sem id ou rótulo")
            if oid in ids_opcao and ids_opcao[oid] != qid:
                erros.append(f"{oid}: id repetido em {ids_opcao[oid]} e {qid}")
            ids_opcao[oid] = qid
            if o.get("proxima") is not None and o["proxima"] not in P:
                erros.append(f"{oid}: proxima → {o['proxima']!r} não existe")
            s = o.get("sinais", {})
            erros += [f"{oid}: topic inválido {t!r}" for t in s.get("topics", []) if not RE_TOPIC.match(str(t))]
            erros += [f"{oid}: subfield/field inválido {t!r}" for t in s.get("subfields", []) + s.get("fields", []) if not RE_NUM.match(str(t))]
            if not s.get("frase"):
                erros.append(f"{oid}: sem frase (texto da consulta vetorial)")
            if not o.get("perfil"):
                erros.append(f"{oid}: sem fragmento de perfil")
            a = o.get("arte")
            if not a or a.get("camada") not in CAMADAS_ARTE or not a.get("id"):
                erros.append(f"{oid}: arte ausente ou camada inválida")
    # alcançáveis, ciclos
    vistos: set[str] = set()

    def dfs(qid: str, pilha: tuple[str, ...]) -> None:
        if qid in pilha:
            erros.append("ciclo: " + " → ".join(pilha + (qid,)))
            return
        if qid in vistos:
            return
        vistos.add(qid)
        q = P[qid]
        for o in q["opcoes"]:
            if o.get("proxima") in P:
                dfs(o["proxima"], pilha + (qid,))
        if q.get("pular") in P:
            dfs(q["pular"], pilha + (qid,))

    dfs(arv["raiz"], ())
    erros += [f"{qid}: pergunta órfã (inalcançável)" for qid in P if qid not in vistos]
    if erros:
        return erros
    for c in caminhos(arv):
        n = len(c.respostas)
        if not MIN_PROFUNDIDADE <= n <= MAX_PROFUNDIDADE:
            erros.append(f"profundidade {n} fora de {MIN_PROFUNDIDADE}–{MAX_PROFUNDIDADE}: {c.nome}")
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


def banco(arv: dict[str, Any]) -> tuple[Path, bool]:
    cams = list(caminhos(arv))
    # 1. ids existem
    usados: dict[str, set[str]] = {"topic": set(), "subfield": set(), "field": set()}
    for c in cams:
        for t, v, _, _ in c.sinais:
            if t in usados:
                usados[t].add(v)
    existe = psql(f"""SELECT 'topic' AS t, openalex_id AS v FROM topics WHERE openalex_id IN ({','.join(map(_lit, usados['topic'])) or "''"})
      UNION SELECT DISTINCT 'subfield', subfield_id FROM topics WHERE subfield_id IN ({','.join(map(_lit, usados['subfield'])) or "''"})
      UNION SELECT DISTINCT 'field', field_id FROM topics WHERE field_id IN ({','.join(map(_lit, usados['field'])) or "''"});""")
    achados = {(e["t"], e["v"]) for e in existe}
    faltando = sorted(f"{t} {v}" for t, vs in usados.items() for v in vs if (t, v) not in achados)

    # 2. encaixe por folha (uma consulta só, com todas as folhas)
    sinais = [(i, t, v, w, f) for i, c in enumerate(cams) for t, v, w, f in c.sinais]
    termos = sorted({v for _, t, v, _, _ in sinais if t == "termo"})
    valores = ",\n".join(f"({i},{_lit(t)},{_lit(v)},{w},{_lit(f)})" for i, t, v, w, f in sinais)
    sql = SQL_ATIVOS + f"""
CREATE TEMP TABLE sinal (cam int, tipo text, valor text, peso real, papel text);
INSERT INTO sinal VALUES {valores};
-- termos: no início de uma palavra (\\m), no título e nas palavras-chave ("fertiliz" casa "fertilization"; "app" não casa "approach")
CREATE TEMP TABLE termo AS SELECT t AS termo, '\\m' || lower(f_unaccent(t)) AS re FROM unnest(ARRAY[{','.join(map(_lit, termos))}]::text[]) t;
CREATE TEMP TABLE termo_work AS
  SELECT t.termo, w.id AS work_id FROM works w JOIN termo t ON lower(f_unaccent(w.title)) ~ t.re
  UNION
  SELECT t.termo, k.work_id FROM termo t
    JOIN work_keywords k ON lower(f_unaccent(k.keyword)) LIKE '%' || lower(f_unaccent(t.termo)) || '%' AND lower(f_unaccent(k.keyword)) ~ t.re;
CREATE INDEX ON termo_work (termo);
CREATE TEMP TABLE work_sub AS SELECT w.id AS work_id, tp.subfield_id, w.primary_field_id AS field_id FROM works w JOIN topics tp ON tp.openalex_id = w.primary_topic_id;
-- melhor sinal de cada publicação em cada caminho
CREATE TEMP TABLE casa AS
SELECT cam, work_id, max(v) AS v, bool_or(papel = 'folha') AS folha, bool_or(papel = 'penultima') AS penult FROM (
  SELECT s.cam, wt.work_id, s.peso * CASE WHEN wt.is_primary THEN 1.0 ELSE 0.5 END AS v, s.papel
    FROM sinal s JOIN work_topics wt ON wt.topic_openalex_id = s.valor WHERE s.tipo = 'topic'
  UNION ALL SELECT s.cam, ws.work_id, s.peso * 0.5, s.papel FROM sinal s JOIN work_sub ws ON ws.subfield_id = s.valor WHERE s.tipo = 'subfield'
  UNION ALL SELECT s.cam, ws.work_id, s.peso * 0.25, s.papel FROM sinal s JOIN work_sub ws ON ws.field_id = s.valor WHERE s.tipo = 'field'
  UNION ALL SELECT s.cam, tw.work_id, s.peso * 0.7, s.papel FROM sinal s JOIN termo_work tw ON tw.termo = s.valor WHERE s.tipo = 'termo'
) x GROUP BY 1, 2;
-- o pesquisador casa a folha com >= 2 publicações que casam AS DUAS ÚLTIMAS respostas ao mesmo tempo
-- (a penúltima só conta se tiver sinais; ex.: "Genomas" × "Saúde humana", "Frutíferas" × "Pragas")
CREATE TEMP TABLE tem_penult AS SELECT DISTINCT cam FROM sinal WHERE papel = 'penultima';
CREATE TEMP TABLE fit AS
SELECT c.cam, rw.rid, count(*)::int AS n_casa, sum(c.v) AS soma
  FROM casa c JOIN rw ON rw.work_id = c.work_id
 GROUP BY 1, 2
HAVING count(*) FILTER (WHERE c.folha AND (c.penult OR c.cam NOT IN (SELECT cam FROM tem_penult))) >= 2;
CREATE TEMP TABLE fit2 AS
SELECT f.cam, f.rid, f.n_casa, (f.soma / (a.n + 2)) * ln(1 + f.n_casa) AS escore, r.main_institution_id AS inst
  FROM fit f JOIN ativos a ON a.rid = f.rid JOIN researchers r ON r.id = f.rid;
-- maior instituição de cada folha e as ligadas a ela (parent/child)
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

    # 3. relatório
    linhas_folha = []
    magras, parecidas = [], []
    for i, c in enumerate(cams):
        r = res.get(i, {"total": "0", "sem_maior": "0", "maior_inst": "", "top10": "", "top3": ""})
        sem = int(r["sem_maior"] or 0)
        if sem < MIN_PESQUISADORES:
            magras.append((c, sem))
        linhas_folha.append((c, int(r["total"] or 0), sem, r["maior_inst"] or "—", r["top3"] or ""))
    grupos: dict[str, list[int]] = collections.defaultdict(list)
    for i, c in enumerate(cams):
        grupos[c.pai].append(i)
    jacc_max: list[tuple[float, str, str]] = []
    for idx in grupos.values():
        tops = {i: set(filter(None, (res.get(i, {}).get("top10") or "").split(","))) for i in idx}
        for a in idx:
            for b in idx:
                if a < b and tops[a] and tops[b]:
                    j = len(tops[a] & tops[b]) / len(tops[a] | tops[b])
                    jacc_max.append((j, cams[a].nome, cams[b].nome))
                    if j > MAX_JACCARD:
                        parecidas.append((j, cams[a].nome, cams[b].nome))
    jaccs = [j for j, _, _ in jacc_max]
    ok = not faltando and not magras and not parecidas
    L = ["# Quiz — validação da árvore contra o banco", "",
         f"Árvore: `{ARQ_ARVORE.relative_to(RAIZ)}` (versão {arv.get('versao')}). {len(cams)} caminhos até as folhas.", "",
         f"- ids de topic/subfield/field inexistentes: **{len(faltando)}** {('· ' + ', '.join(faltando)) if faltando else ''}",
         f"- folhas com menos de {MIN_PESQUISADORES} pesquisadores sem a maior instituição do tema: **{len(magras)}**",
         f"- pares de folhas irmãs com Jaccard dos top 10 > {MAX_JACCARD}: **{len(parecidas)}**"
         + (f" (Jaccard entre irmãs: mediana {sorted(jaccs)[len(jaccs) // 2]:.2f}, máximo {max(jaccs):.2f}, {len(jaccs)} pares)" if jaccs else ""),
         f"- resultado: **{'OK' if ok else 'há pendências'}**", ""]
    if magras:
        L += ["## Folhas magras", "", "| caminho | sem a maior |", "|---|---|"] + [f"| {c.nome} | {n} |" for c, n in magras] + [""]
    if parecidas:
        L += ["## Irmãs parecidas demais", "", "| Jaccard | folha A | folha B |", "|---|---|---|"]
        L += [f"| {j:.2f} | {a} | {b} |" for j, a, b in sorted(parecidas, reverse=True)] + [""]
    L += ["## Todas as folhas", "", "| caminho | pesquisadores | sem a maior | maior instituição | 3 primeiros (só encaixe) |", "|---|---|---|---|---|"]
    L += [f"| {c.nome} | {t} | {s} | {m} | {top} |" for c, t, s, m, top in linhas_folha]
    DIR_RELATORIOS.mkdir(parents=True, exist_ok=True)
    arq = DIR_RELATORIOS / "quiz_validacao.md"
    arq.write_text("\n".join(L) + "\n", encoding="utf-8")
    (DIR_RELATORIOS / "quiz_validacao.json").write_text(json.dumps({
        "caminhos": len(cams), "faltando": faltando, "magras": [[c.nome, n] for c, n in magras],
        "parecidas": [[round(j, 3), a, b] for j, a, b in parecidas],
        "folhas": [{"caminho": c.nome, "respostas": c.respostas, "total": t, "sem_maior": s, "maior": m} for c, t, s, m, _ in linhas_folha],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return arq, ok


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["estatico", "levantamento", "banco"])
    a = p.parse_args(argv)
    arv = carregar()
    if a.comando == "levantamento":
        print(f"gravado {levantamento().relative_to(RAIZ)}")
        return 0
    erros = estatico(arv)
    if erros:
        print("árvore do quiz: ERROS na estrutura", *erros, sep="\n  ")
        return 1
    n = sum(1 for _ in caminhos(arv))
    print(f"árvore do quiz: estrutura ok ({len(arv['perguntas'])} perguntas, {n} caminhos)")
    if a.comando == "banco":
        arq, ok = banco(arv)
        print(f"gravado {arq.relative_to(RAIZ)}: {'OK' if ok else 'há pendências'}")
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
