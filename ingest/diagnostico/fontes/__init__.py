"""Registro das fontes avaliadas, na ordem do relatório."""

from __future__ import annotations

from collections.abc import Callable

from ..contexto import Contexto
from ..modelos import ResultadoFonte
from . import capes, complementares, fotos, grupos, instituicoes, pesquisadores, producao

Avaliacao = Callable[[Contexto], ResultadoFonte]

GRUPOS: dict[str, list[tuple[str, Avaliacao]]] = {
    "instituicoes": instituicoes.AVALIACOES,
    "capes": capes.AVALIACOES,
    "grupos": grupos.AVALIACOES,
    "pesquisadores": pesquisadores.AVALIACOES,
    "producao": producao.AVALIACOES,
    "fotos": fotos.AVALIACOES,
    "complementares": complementares.AVALIACOES,
}

TODAS: list[tuple[str, Avaliacao]] = [item for itens in GRUPOS.values() for item in itens]


def selecionar(nomes: list[str] | None) -> list[tuple[str, Avaliacao]]:
    """Aceita ids de fonte (ex.: 'ror') ou nomes de grupo (ex.: 'capes')."""
    if not nomes:
        return TODAS
    escolhidas: list[tuple[str, Avaliacao]] = []
    ids = dict(TODAS)
    for n in nomes:
        if n in GRUPOS:
            escolhidas.extend(GRUPOS[n])
        elif n in ids:
            escolhidas.append((n, ids[n]))
        else:
            validos = ", ".join(list(GRUPOS) + list(ids))
            raise SystemExit(f"Fonte desconhecida: {n}. Opções: {validos}")
    vistos: set[str] = set()
    return [x for x in escolhidas if not (x[0] in vistos or vistos.add(x[0]))]  # type: ignore[func-returns-value]
