"""Geração do relatório (JSON bruto + Markdown legível) e das estimativas finais."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from .config import DIR_RELATORIOS
from .recorte import CAMPOS_OPENALEX, NOME_RECORTE, UFS_NORDESTE

CUSTO_LIST_USD = 0.0001  # list+filter: US$ 0,10 por 1.000 chamadas (help.openalex.org/access/example-costs)
CHAMADAS_DIA_CHAVE_GRATIS = 10_000  # US$ 1/dia com chave gratuita
PER_PAGE = 100


def fmt_bytes(n: int | float | None) -> str:
    if not n:
        return "—"
    n = float(n)
    for unid in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unid == "TB":
            return f"{n:.0f} {unid}" if unid in ("B", "KB") else f"{n:.1f} {unid}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_int(n: int | None) -> str:
    return "—" if n is None else f"{n:,}".replace(",", ".")


def _d(res: dict[str, dict[str, Any]], fid: str) -> dict[str, Any]:
    return res.get(fid, {}).get("detalhes", {}) or {}


def estimativas(res: dict[str, dict[str, Any]]) -> dict[str, Any]:
    faixa = _d(res, "openalex_works").get("faixa_recorte")
    works = faixa[1] if faixa else res.get("openalex_works", {}).get("registros_br")  # usa o teto da faixa
    works_all = _d(res, "openalex_works").get("total_corpus_all") or res.get("openalex_snapshot", {}).get("registros_br")
    # Autores a buscar = autores distintos nos works do recorte (lote de 100 IDs por chamada); senão, o filtro de /authors.
    autores = res.get("openalex_authors", {}).get("registros_br")
    inst = res.get("openalex_institutions", {}).get("registros_br")
    b_work = _d(res, "openalex_works").get("bytes_medios_por_work_json") or 8000
    b_autor = _d(res, "openalex_authors").get("bytes_medios_por_author_json") or 6000
    snap = _d(res, "openalex_snapshot")
    snap_works_bytes = (snap.get("entidades", {}).get("works") or {}).get("bytes_comprimidos")
    snap_br = (snap.get("estimativa_recorte_br") or {}).get("bytes_comprimidos_works_br")

    api: dict[str, Any] = {}
    if works and autores:
        ch_works = math.ceil(works / PER_PAGE)
        ch_works_all = math.ceil((works_all or works) / PER_PAGE)
        ch_aut = math.ceil(autores / PER_PAGE)
        ch_inst = math.ceil((inst or 0) / PER_PAGE)
        total = ch_works + ch_aut + ch_inst
        api = {
            "chamadas_works": ch_works,
            "chamadas_works_corpus_all": ch_works_all,
            "chamadas_authors": ch_aut,
            "chamadas_institutions": ch_inst,
            "chamadas_total": total,
            "custo_usd": round(total * CUSTO_LIST_USD, 2),
            "custo_usd_corpus_all": round((ch_works_all + ch_aut + ch_inst) * CUSTO_LIST_USD, 2),
            "dias_com_chave_gratis": round(total / CHAMADAS_DIA_CHAVE_GRATIS, 1),
            "transferencia_bytes": works * b_work + autores * b_autor,
            "premissas": f"per_page=100, cursor paging (exige chave), list+filter = US$ {CUSTO_LIST_USD}/chamada; {b_work} B/work e {b_autor} B/author medidos na amostra",
        }

    # Disco: arquivos brutos a baixar nas próximas partes (só fontes 'usar'/'complementar' com download)
    brutos: dict[str, int] = {}
    inep = _d(res, "inep_censo_superior").get("arquivos_por_ano", {})
    brutos["INEP Censo Superior (ZIPs nacionais dos anos do recorte; só IES/cursos são lidos)"] = sum(v.get("bytes") or 0 for v in inep.values())
    brutos["ROR dump (ZIP)"] = res.get("ror", {}).get("tamanho_bytes") or 0
    for fid, r in res.items():
        if fid.startswith("capes_") and r.get("recomendacao") in ("usar", "complementar"):
            brutos[r.get("nome", fid)] = r.get("tamanho_bytes") or 0
    brutos["IBGE municípios + coordenadas"] = (res.get("ibge_municipios", {}).get("tamanho_bytes") or 0) + ((_d(res, "ibge_municipios").get("coordenadas_kelvins") or {}).get("bytes") or 0)
    brutos["OpenAlex: recorte via API (JSON bruto, works + autores)"] = api.get("transferencia_bytes") or 0
    total_brutos = sum(brutos.values())
    # Banco: só o necessário (SCHEME.md §6: não espelhar o OpenAlex). Premissa: ~1,5 KB/work, 1 KB/autor,
    # + índices (x1,5), + tabelas CAPES normalizadas (~40% do CSV).
    capes_csv = sum(v for k, v in brutos.items() if k.startswith("CAPES"))
    frac_capes = _d(res, "capes_programas").get("fracao_programas_recorte") or 1.0
    banco = int(((works or 0) * 1500 + (autores or 0) * 1000) * 1.5 + capes_csv * 0.4 * frac_capes)
    return {
        "api_openalex": api,
        "snapshot": {
            "bytes_works_a_baixar": snap_works_bytes,
            "bytes_works_br_comprimido": snap_br,
            "horas_download_50MBps": round(snap_works_bytes / 50e6 / 3600, 1) if snap_works_bytes else None,
            "horas_download_20MBps": round(snap_works_bytes / 20e6 / 3600, 1) if snap_works_bytes else None,
        },
        "disco": {
            "brutos_por_fonte": brutos,
            "brutos_total": total_brutos,
            "banco_postgres_estimado": banco,
            "trabalho_temporario_recomendado": int(total_brutos * 2.5),
        },
    }


def _linha(r: dict[str, Any]) -> str:
    acess = {True: "sim", False: "não", None: "n/a"}[r.get("acessivel")]
    if r.get("erros") and r.get("acessivel") is not True:
        acess = "erro"
    ids = ", ".join(r.get("identificadores") or []) or "—"
    tam = fmt_bytes(r.get("tamanho_bytes"))
    if r.get("tamanho_obs") and r.get("tamanho_bytes"):
        tam += f" ({r['tamanho_obs']})"
    reg = fmt_int(r.get("registros_br"))
    lic = (r.get("licenca") or "—").replace("|", "/")
    return f"| {r['nome']} | {acess} | {r.get('forma_acesso') or '—'} | {tam} | {reg} | {lic} | {ids} | **{r.get('recomendacao')}** |"


def gerar_markdown(dados: dict[str, Any]) -> str:
    res: dict[str, dict[str, Any]] = dados["fontes"]
    est = dados["estimativas"]
    ys, ye = dados["year_start"], dados["year_end"]
    L: list[str] = []
    L.append(f"# Diagnóstico de fontes — {NOME_RECORTE}, {ys}–{ye}")
    L.append("")
    L.append(
        "Recorte: instituições com sede nos 9 estados do Nordeste ("
        + ", ".join(u.sigla for u in UFS_NORDESTE)
        + f"); produção {ys}–{ye}; áreas = OpenAlex fields "
        + ", ".join(f"{k} {v}" for k, v in CAMPOS_OPENALEX.items())
        + "; CAPES = áreas de avaliação de saúde e ciências biológicas (lista em `ingest/diagnostico/recorte.py`)."
    )
    L.append("")
    L.append(f"Gerado em {dados['gerado_em']} por `python -m ingest.diagnostico.avaliar_fontes`. Dados brutos em `diagnostico_fontes.json`.")
    L.append("")
    L.append(f"OpenAlex: {'com chave de API' if dados['openalex_com_chave'] else 'SEM chave (orçamento compartilhado de US$ 0,10/dia por IP)'}; "
             f"créditos gastos nesta execução: {dados['openalex_creditos_execucao']} (US$ {dados['openalex_custo_execucao_usd']:.4f}).")
    L.append("")
    L.append("## Tabela-resumo")
    L.append("")
    L.append("| Fonte | Acessível | Forma de acesso | Tamanho | Registros (recorte) | Licença | Identificadores | Recomendação |")
    L.append("|---|---|---|---|---|---|---|---|")
    grupo_atual = None
    for r in res.values():
        if r.get("grupo") != grupo_atual:
            grupo_atual = r.get("grupo")
            L.append(f"| **{grupo_atual}** | | | | | | | |")
        L.append(_linha(r))
    L.append("")
    L.append("## Detalhes por fonte")
    for r in res.values():
        L.append("")
        L.append(f"### {r['nome']}  (`--fonte {r['id']}`)")
        L.append("")
        L.append(f"- URL: {r['url_base']}")
        L.append(f"- Acessível: {r.get('acessivel')} — HTTP {r.get('status_http')}, {r.get('tempo_resposta_ms') or '—'} ms")
        L.append(f"- Acesso/formato: {r.get('forma_acesso')} / {r.get('formato') or '—'}")
        L.append(f"- Tamanho: {fmt_bytes(r.get('tamanho_bytes'))} {('— ' + r['tamanho_obs']) if r.get('tamanho_obs') else ''}")
        L.append(f"- Registros: {fmt_int(r.get('registros_br'))} {('— ' + r['registros_obs']) if r.get('registros_obs') else ''}")
        L.append(f"- Licença: {r.get('licenca') or '—'}")
        L.append(f"- Última atualização: {r.get('ultima_atualizacao') or '—'}; frequência: {r.get('frequencia_atualizacao') or '—'}")
        L.append(f"- Identificadores para cruzamento: {', '.join(r.get('identificadores') or []) or '—'}")
        L.append(f"- Recomendação: **{r.get('recomendacao')}** — {r.get('justificativa') or ''}")
        for o in r.get("observacoes") or []:
            L.append(f"- Obs.: {o}")
        for o in r.get("riscos") or []:
            L.append(f"- Risco: {o}")
        for e in r.get("erros") or []:
            L.append(f"- ERRO: `{e}`")
        L.extend(_detalhes_extras(r))
    L.append("")
    L.append("## Estimativas finais")
    L.append("")
    api = est.get("api_openalex") or {}
    snap = est.get("snapshot") or {}
    disco = est.get("disco") or {}
    L.append("### Espaço em disco")
    L.append("")
    L.append("| Item | Tamanho |")
    L.append("|---|---|")
    for k, v in (disco.get("brutos_por_fonte") or {}).items():
        L.append(f"| {k} | {fmt_bytes(v)} |")
    L.append(f"| **Total de arquivos brutos** | **{fmt_bytes(disco.get('brutos_total'))}** |")
    L.append(f"| Banco Postgres estimado (só campos do perfil + índices, recorte) | {fmt_bytes(disco.get('banco_postgres_estimado'))} |")
    L.append(f"| Espaço de trabalho recomendado (brutos + descompactação) | {fmt_bytes(disco.get('trabalho_temporario_recomendado'))} |")
    L.append("")
    L.append("### Custo e tempo: API do OpenAlex vs. snapshot")
    L.append("")
    if api:
        L.append(f"- **API**: {fmt_int(api['chamadas_total'])} chamadas (works {fmt_int(api['chamadas_works'])}, autores em lotes de 100 IDs {fmt_int(api['chamadas_authors'])}, institutions {fmt_int(api['chamadas_institutions'])}) "
                 f"≈ **US$ {api['custo_usd']:.2f}** (com corpus=all: US$ {api['custo_usd_corpus_all']:.2f}). "
                 f"Com chave gratuita (US$ 1/dia ≈ 10.000 chamadas) leva ~{api['dias_com_chave_gratis']} dia(s); com saldo pré-pago, poucas horas. "
                 f"Transferência ≈ {fmt_bytes(api['transferencia_bytes'])} de JSON (menos com `select=`).")
        L.append(f"  - Premissas: {api['premissas']}.")
    if snap.get("bytes_works_a_baixar"):
        L.append(f"- **Snapshot**: grátis, mas exige baixar e ler {fmt_bytes(snap['bytes_works_a_baixar'])} de works (partições por data de atualização, não por país) "
                 f"para ficar com ~{fmt_bytes(snap.get('bytes_works_br_comprimido'))} comprimidos do recorte. "
                 f"Download: ~{snap.get('horas_download_50MBps')} h a 50 MB/s, ~{snap.get('horas_download_20MBps')} h a 20 MB/s, mais o processamento (filtrar ~500 M registros JSON: várias horas em 8 núcleos).")
    L.append("- **Recomendação**: puxar o recorte pela **API com chave** (custo baixo, incremental por data de atualização depois), "
             "e deixar o snapshot para quando o recorte crescer muito ou se quisermos reprocessar tudo offline. Ver docs/decisoes.md.")
    L.append("")
    L.append("### Tempo estimado de ingestão (todas as partes)")
    L.append("")
    L.append("- Downloads de arquivos (INEP, ROR, CAPES, IBGE): < 1 h com boa conexão; CAPES pede Crawl-delay de 10 s entre requisições.")
    if api:
        L.append(f"- OpenAlex via API: ~{api['dias_com_chave_gratis']} dia(s) dentro da cota gratuita, ou ~{max(1, round(api['chamadas_total'] / 10 / 3600, 1))} h a 10 req/s com saldo.")
    L.append("- ORCID: só sob demanda (login/reivindicação) ou em lotes pequenos; não fazer varredura em massa pela API pública.")
    L.append("- Resolução de identidade e revisão manual: o gargalo real (fila de revisão para casos sem identificador comum).")
    L.append("")
    L.append("### Ordem recomendada das próximas partes")
    L.append("")
    L.append("1. **Parte 1 — Instituições do NE**: ROR (lista canônica por UF) + OpenAlex + INEP (código e-MEC, natureza, município IBGE, cursos de saúde) + IBGE. A lista de IDs OpenAlex/ROR do NE vira o filtro das partes seguintes (cobre instituições sem geo.region).")
    L.append("2. **Parte 2 — CAPES**: programas NE de saúde/biológicas (contagem exata já possível) e seus docentes, teses e orientações; filtro local por CD_PROGRAMA_IES.")
    L.append("3. **Parte 4 — Pesquisadores**: autores dos works do recorte + docentes CAPES + ORCID, com o modelo de identificadores e fila de revisão.")
    L.append("4. **Parte 5 — Produção**: works do recorte pela API com chave (filtro por instituições do NE × fields de saúde), coautorias e tópicos.")
    L.append("5. **Parte 3 — Grupos de pesquisa**: pedido LAI ao CNPq já recortado (NE × Ciências da Saúde/Biológicas); piloto com portais das universidades do NE.")
    L.append("6. **Parte 6 — Complementos** (FAPs do NE, teses BDTD) e **Parte 7 — Fotos**.")
    L.append("")
    if dados.get("excecoes_robots"):
        L.append("### Exceções ao robots.txt usadas (APIs documentadas, decisão D-003)")
        L.append("")
        for h, j in dados["excecoes_robots"].items():
            L.append(f"- `{h}`: {j}")
        L.append("")
    return "\n".join(L) + "\n"


def _detalhes_extras(r: dict[str, Any]) -> list[str]:
    d = r.get("detalhes") or {}
    out: list[str] = []
    for chave in (
        "por_publication_year", "por_type", "por_open_access.oa_status", "por_primary_topic.field.id", "por_estado",
        "por_tipo", "por_estado_geo_region", "por_last_known_institutions.geo.region", "por_field",
    ):
        grupos = d.get(chave)
        if grupos:
            txt = "; ".join(f"{g.get('nome') or g.get('chave')}: {fmt_int(g.get('contagem'))}" for g in grupos[:30])
            out.append(f"- {chave.replace('por_', 'Por ')}: {txt}")
    for chave in ("ne_por_uf", "ies_ne_por_uf", "tema_periodo_ne_por_sigla", "faps_ne"):
        if d.get(chave):
            out.append(f"- {chave}: {json.dumps(d[chave], ensure_ascii=False)[:900]}")
    if d.get("validacao_openalex"):
        v = {k: x for k, x in d["validacao_openalex"].items() if k != "maiores_fora_do_filtro"}
        out.append(f"- Validação ROR × OpenAlex geo.region: {json.dumps(v, ensure_ascii=False)}")
        out.append(f"- Maiores instituições NE fora do filtro por geo.region: {json.dumps(d['validacao_openalex'].get('maiores_fora_do_filtro'), ensure_ascii=False)[:900]}")
    if d.get("recorte_por_ano"):
        out.append(f"- Programas por ano: {json.dumps(d['recorte_por_ano'], ensure_ascii=False)}")
        out.append(f"- Último ano, recorte: {json.dumps(d.get('recorte_ultimo_ano'), ensure_ascii=False)[:1200]}")
    if d.get("top25_por_works") and r.get("id") == "openalex_institutions":
        out.append("- Maiores instituições do NE (works): " + "; ".join(f"{i['nome']} ({i['uf']})" for i in d["top25_por_works"][:15]))
    amostra = d.get("amostra_arquivo_recente")
    if amostra:
        out.append(f"- Colunas ({len(amostra.get('colunas', []))}): `{', '.join(amostra.get('colunas', []))}`")
    if d.get("colunas_identificadoras"):
        out.append(f"- Colunas identificadoras: {json.dumps(d['colunas_identificadoras'], ensure_ascii=False)}")
    if d.get("anos_disponiveis"):
        out.append(f"- Anos-base disponíveis: {', '.join(map(str, d['anos_disponiveis']))}")
    if d.get("tabela_ies"):
        t = d["tabela_ies"]
        out.append(f"- Tabela de IES `{t.get('arquivo')}`: colunas `{', '.join(t.get('colunas', []))}`")
    if d.get("amostra_sobreposicao"):
        out.append(f"- Sobreposição OpenAlex×ORCID: {json.dumps({k: v for k, v in d['amostra_sobreposicao'].items() if k != 'metodo'}, ensure_ascii=False)}")
    if d.get("public_data_file"):
        p = d["public_data_file"]
        out.append(f"- Public Data File {p.get('ano')}: {fmt_bytes(p.get('bytes_total'))} no total; {p.get('url')}; licença {p.get('licenca')}")
    if d.get("entidades"):
        for ent, v in d["entidades"].items():
            out.append(f"- Snapshot `{ent}`: {fmt_int(v.get('registros'))} registros, {fmt_bytes(v.get('bytes_comprimidos'))} comprimidos, {v.get('arquivos')} arquivos (data {v.get('data')})")
    if d.get("estimativa_recorte_br"):
        e = d["estimativa_recorte_br"]
        out.append(f"- Recorte BR no snapshot: {e['fracao_works']:.2%} dos works ≈ {fmt_bytes(e['bytes_comprimidos_works_br'])} comprimidos (~{fmt_bytes(e['bytes_descomprimidos_works_br_aprox'])} descomprimidos)")
    if d.get("contagem") and r.get("id") == "wikidata_fotos":
        out.append(f"- Contagem Wikidata: {json.dumps(d['contagem'], ensure_ascii=False)}")
    if d.get("licencas_amostra"):
        out.append(f"- Licenças (amostra Commons): {json.dumps(d['licencas_amostra'], ensure_ascii=False)}")
    if d.get("por_universidade"):
        for s, v in d["por_universidade"].items():
            out.append(f"- {s}: {'ERRO ' + v['erro'] if v.get('erro') else 'via ' + str(v.get('via')) + ', conjuntos com grupo: ' + (', '.join(v.get('titulos_com_grupo') or []) or 'nenhum')}")
    if d.get("top25") and r.get("id") == "openalex_funders":
        out.append("- Maiores financiadores BR: " + "; ".join(f"{f['nome']} ({fmt_int(f['works'])} works)" for f in d["top25"][:12]))
    return out


def salvar(dados: dict[str, Any], dir_saida: Path = DIR_RELATORIOS) -> tuple[Path, Path]:
    dir_saida.mkdir(parents=True, exist_ok=True)
    pj = dir_saida / "diagnostico_fontes.json"
    pm = dir_saida / "diagnostico_fontes.md"
    pj.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str))
    pm.write_text(gerar_markdown(dados))
    return pj, pm


def carregar_anterior(dir_saida: Path = DIR_RELATORIOS) -> dict[str, Any] | None:
    pj = dir_saida / "diagnostico_fontes.json"
    if pj.exists():
        try:
            return json.loads(pj.read_text())
        except json.JSONDecodeError:
            return None
    return None


def agora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
