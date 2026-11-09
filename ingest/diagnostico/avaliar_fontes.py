"""Parte 0 — Diagnóstico de disponibilidade e tamanho das fontes.

Uso:
    python -m ingest.diagnostico.avaliar_fontes                 # todas as fontes
    python -m ingest.diagnostico.avaliar_fontes --fonte ror     # só uma fonte (ou um grupo: capes, producao...)
    python -m ingest.diagnostico.avaliar_fontes --year-start 2018 --sem-cache

Nunca baixa arquivos maiores que 50 MB; lê cabeçalhos, manifests, metadados e amostras via Range.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import EXCECOES_ROBOTS, carregar_config
from .contexto import Contexto
from .fontes import TODAS, selecionar
from .http import ClienteHttp
from .modelos import ResultadoFonte
from .openalex import OpenAlex
from .relatorio import agora, carregar_anterior, estimativas, gerar_markdown, salvar

log = logging.getLogger("ingest.diagnostico")


def _args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fonte", action="append", help="id da fonte ou nome do grupo; pode repetir. Padrão: todas.")
    p.add_argument("--year-start", type=int, default=None, help="Ano inicial do recorte (padrão: YEAR_START do .env ou 2020).")
    p.add_argument("--sem-cache", action="store_true", help="Ignora o cache em ingest/.cache/ (as respostas novas são gravadas).")
    p.add_argument("--amostra-orcid", type=int, default=None, help="Tamanho da amostra para sobreposição OpenAlex×ORCID (padrão 500).")
    p.add_argument("--listar", action="store_true", help="Lista as fontes e grupos disponíveis e sai.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = _args(argv)
    logging.basicConfig(
        level=logging.DEBUG if a.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if a.listar:
        from .fontes import GRUPOS

        for g, itens in GRUPOS.items():
            print(f"{g}: {', '.join(i for i, _ in itens)}")
        return 0

    cfg = carregar_config(year_start=a.year_start, usar_cache=not a.sem_cache, amostra_orcid=a.amostra_orcid)
    if not cfg.contact_email:
        log.warning("CONTACT_EMAIL não definido no .env: o User-Agent sai sem e-mail de contato.")
    if not cfg.openalex_api_key:
        log.warning("OPENALEX_API_KEY não definido: usando o orçamento sem chave (US$ 0,10/dia por IP).")
    http = ClienteHttp(cfg)
    ctx = Contexto(cfg=cfg, http=http, oa=OpenAlex(http))
    escolhidas = selecionar(a.fonte)

    anterior = carregar_anterior()
    fontes_ant: dict[str, dict] = {}
    if anterior and anterior.get("year_start") == cfg.year_start:
        fontes_ant = anterior.get("fontes", {})

    novos: dict[str, dict] = {}
    try:
        for fid, avaliar in escolhidas:
            log.info("== Avaliando %s", fid)
            t0 = time.monotonic()
            try:
                r = avaliar(ctx)
            except Exception as e:  # noqa: BLE001  (continua mesmo se uma fonte falhar)
                log.exception("Falha ao avaliar %s", fid)
                r = ResultadoFonte(id=fid, nome=fid, grupo=_grupo_de(fid), url_base="")
                ant = fontes_ant.get(fid)
                if ant:
                    r.nome, r.grupo, r.url_base = ant.get("nome", fid), ant.get("grupo", r.grupo), ant.get("url_base", "")
                r.acessivel = False if r.acessivel is None else r.acessivel
                r.erro("avaliação interrompida", e)
            r.duracao_s = round(time.monotonic() - t0, 1)
            novos[fid] = r.to_dict()
            log.info("   %s: acessível=%s registros=%s tamanho=%s erros=%d (%.1fs)", fid, r.acessivel, r.registros_br, r.tamanho_bytes, len(r.erros), r.duracao_s)
    finally:
        http.fechar()

    # Mescla com o relatório anterior (para --fonte) mantendo a ordem do registro.
    ordem = [fid for fid, _ in TODAS]
    juntas = {**fontes_ant, **novos}
    fontes = {fid: juntas[fid] for fid in ordem if fid in juntas}
    dados = {
        "gerado_em": agora(),
        "year_start": cfg.year_start,
        "year_end": cfg.year_end,
        "user_agent": cfg.user_agent,
        "openalex_com_chave": bool(cfg.openalex_api_key),
        "openalex_creditos_execucao": http.creditos_openalex,
        "openalex_custo_execucao_usd": round(http.custo_openalex_usd, 6),
        "excecoes_robots": EXCECOES_ROBOTS,
        "fontes": fontes,
        "chamadas_execucao": [c.__dict__ for c in http.chamadas],
    }
    dados["estimativas"] = estimativas(fontes)
    pj, pm = salvar(dados)
    log.info("Relatórios: %s | %s", pj, pm)
    # imprime só a tabela-resumo
    md = gerar_markdown(dados)
    ini = md.index("## Tabela-resumo")
    fim = md.index("## Detalhes por fonte")
    print(md[ini:fim])
    return 0


def _grupo_de(fid: str) -> str:
    from .fontes import GRUPOS

    nomes = {
        "instituicoes": "1. Instituições",
        "capes": "2. Pós-graduação (CAPES)",
        "grupos": "3. Grupos de pesquisa",
        "pesquisadores": "4. Pesquisadores",
        "producao": "5. Produção científica",
        "fotos": "6. Fotos",
        "complementares": "7. Complementares",
    }
    for g, itens in GRUPOS.items():
        if any(i == fid for i, _ in itens):
            return nomes[g]
    return "?"


if __name__ == "__main__":
    sys.exit(main())
