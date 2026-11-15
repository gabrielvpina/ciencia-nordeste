"""Parte 10: biografias públicas do ORCID (D-055) -> tabela researcher_bios (migração 0020).

  python -m ingest.carga.parte10_bios [--limite 25000] [--dias 90]

- Quem: pesquisadores visíveis com ORCID, em ordem de produção (mais ativos primeiro), que nunca foram consultados ou foram
  há mais de `--dias` dias. Incremental e retomável: grava em lotes, e uma nova execução continua de onde parou.
- Como: API pública do ORCID (`/v3.0/{orcid}/biography`; liberada em D-003), pelo ClienteHttp do projeto (ritmo por host,
  novas tentativas). Sem cache em disco (a tabela guarda o resultado) e sem e-mail de contato no User-Agent.
- Limpeza: sem HTML, espaços normalizados, e-mails e telefones removidos por precaução; textos com menos de 80 caracteres
  não são exibidos (status 204). Idioma por contagem de palavras comuns (pt/en).
Os dados públicos dos registros ORCID são CC0. O texto é escrito pelo próprio pesquisador; o site mostra a fonte e a data.
"""
from __future__ import annotations

import argparse
import dataclasses
import html
import re
import sys
import time
from datetime import datetime, timezone

from ..diagnostico.config import carregar_config
from ..diagnostico.http import ClienteHttp
from .validar_arvore_quiz import _lit, psql

MIN_CARACTERES = 80
LOTE = 200
PT = set("de da do das dos em no na nos nas com para pela pelo e é um uma possui graduação mestrado doutorado professor professora universidade pesquisa área".split())
EN = set("the of and in with for at is a an has degree master phd professor university research field".split())
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RE_FONE = re.compile(r"(\+?55\s?)?(\(\d{2}\)\s?9?\d{4}-?\d{4}|\b\d{2}\s?9\d{4}-\d{4}\b)")   # com DDD; não pega "2005-2009"


def limpar(texto: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    t = RE_EMAIL.sub("", t)
    t = RE_FONE.sub("", t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\s*\n\s*\n\s*", "\n\n", t)          # parágrafos
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)           # quebras soltas viram espaço
    t = re.sub(r"[ ]+([,.;:!?])", r"\1", t)            # sem espaço antes da pontuação
    # rótulos de contato que ficaram vazios depois de tirar e-mail e telefone ("Contato: , ou .")
    t = re.sub(r"\b(Contato|Contatos|E-?mail|Tel\.?|Telefone|Contact|Phone)\s*:?(\s|[,;]|\b(ou|e|or|and)\b)*(?=[.\n]|$)", "", t, flags=re.I)
    t = re.sub(r"\.\s*\.", ".", t)
    return re.sub(r"[ ]{2,}", " ", t).strip()


def idioma(texto: str) -> str:
    p = re.findall(r"[a-zà-ú]+", texto.lower())
    pt, en = sum(w in PT for w in p), sum(w in EN for w in p)
    return "pt" if pt >= en else "en"


def gravar(linhas: list[tuple]) -> None:
    if not linhas:
        return
    valores = ",".join(
        f"({_lit(rid)}::uuid,{_lit(orc)},{st},{_lit(tx) if tx else 'NULL'},{_lit(lg) if lg else 'NULL'},{_lit(dt) + '::timestamptz' if dt else 'NULL'},now())"
        for rid, orc, st, tx, lg, dt in linhas)
    psql(f"""INSERT INTO researcher_bios (researcher_id, orcid, status, texto, idioma, atualizado_orcid, coletado_em) VALUES {valores}
             ON CONFLICT (researcher_id) DO UPDATE SET orcid = EXCLUDED.orcid, status = EXCLUDED.status, texto = EXCLUDED.texto,
               idioma = EXCLUDED.idioma, atualizado_orcid = EXCLUDED.atualizado_orcid, coletado_em = EXCLUDED.coletado_em;
             SELECT 1 AS ok;""")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limite", type=int, default=25000)
    p.add_argument("--dias", type=int, default=90)
    a = p.parse_args(argv)
    alvos = psql(f"""
      SELECT r.id::text AS id, regexp_replace(r.orcid, '^https?://orcid.org/', '') AS orcid
        FROM researchers r JOIN mv_pesquisador_busca b ON b.id = r.id
        LEFT JOIN researcher_bios rb ON rb.researcher_id = r.id
       WHERE NOT r.is_hidden AND r.orcid IS NOT NULL
         AND (rb.researcher_id IS NULL OR rb.coletado_em < now() - interval '{int(a.dias)} days')
       ORDER BY b.works DESC NULLS LAST, r.id LIMIT {int(a.limite)};""")
    print(f"{len(alvos)} pesquisadores a consultar", flush=True)
    cfg = dataclasses.replace(carregar_config(), contact_email=None)   # sem e-mail no User-Agent (o ORCID não exige)
    http = ClienteHttp(cfg)
    lote: list[tuple] = []
    cont = {"com": 0, "sem": 0, "curta": 0, "erro": 0}
    t0 = time.monotonic()
    for i, alvo in enumerate(alvos, 1):
        try:
            r = http.get(f"https://pub.orcid.org/v3.0/{alvo['orcid']}/biography", cabecalhos={"Accept": "application/json"},
                         cache=False, aceitar_status=(403, 404, 409, 410))
        except Exception as e:   # falha de rede depois das novas tentativas: segue e tenta de novo na próxima execução
            cont["erro"] += 1
            print(f"erro em {alvo['orcid']}: {str(e)[:120]}", flush=True)
            continue
        texto = lg = dt = None
        st = r.status
        if r.ok:
            j = r.json() or {}
            bruto = j.get("content") or ""
            texto = limpar(bruto) if bruto else None
            ms = (j.get("last-modified-date") or {}).get("value")
            dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms else None
            if not texto:
                st, texto = 404, None
            elif len(texto) < MIN_CARACTERES:
                st, texto = 204, None
            else:
                lg = idioma(texto)
        cont["com" if st == 200 else "curta" if st == 204 else "sem"] += 1
        lote.append((alvo["id"], alvo["orcid"], st, texto, lg, dt))
        if len(lote) >= LOTE:
            gravar(lote); lote = []
        if i % 1000 == 0:
            print(f"{i}/{len(alvos)} · {cont} · {time.monotonic() - t0:.0f} s", flush=True)
    gravar(lote)
    print(f"fim: {cont} em {time.monotonic() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
