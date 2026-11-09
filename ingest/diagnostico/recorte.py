"""Recorte do projeto Ciência Nordeste: região, período e áreas.

Tudo que define "o que entra" fica aqui, para as fontes e as próximas partes usarem a mesma régua.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

NOME_RECORTE = "Ciência Nordeste — ciências da vida: saúde, biomedicina, biotecnologia, genética, ciências agrárias e biológicas"


@dataclass(frozen=True)
class UF:
    sigla: str
    nome: str  # como aparece em OpenAlex geo.region, ROR e IBGE
    codigo_ibge: int
    capital: str


UFS_NORDESTE: tuple[UF, ...] = (
    UF("MA", "Maranhão", 21, "São Luís"),
    UF("PI", "Piauí", 22, "Teresina"),
    UF("CE", "Ceará", 23, "Fortaleza"),
    UF("RN", "Rio Grande do Norte", 24, "Natal"),
    UF("PB", "Paraíba", 25, "João Pessoa"),
    UF("PE", "Pernambuco", 26, "Recife"),
    UF("AL", "Alagoas", 27, "Maceió"),
    UF("SE", "Sergipe", 28, "Aracaju"),
    UF("BA", "Bahia", 29, "Salvador"),
)
SIGLAS_NE = {u.sigla for u in UFS_NORDESTE}
CODIGOS_IBGE_NE = {u.codigo_ibge for u in UFS_NORDESTE}

# "Últimos 5 anos" = ano atual e os 4 anteriores (ex.: 2022–2026 em 2026). Sobrescrevível por YEAR_START.
ANOS_RECORTE = 5

# OpenAlex: fields (nível 2 da hierarquia de tópicos), conferidos em /fields em 2026-11-09.
CAMPOS_OPENALEX: dict[int, str] = {
    27: "Medicine",
    13: "Biochemistry, Genetics and Molecular Biology",  # inclui o subfield Biotechnology (1305)
    24: "Immunology and Microbiology",
    28: "Neuroscience",
    30: "Pharmacology, Toxicology and Pharmaceutics",
    29: "Nursing",
    35: "Dentistry",
    36: "Health Professions",
    # Ampliação "opção D" (D-017, 2026-11-09): ciências agrárias e biológicas e veterinária.
    11: "Agricultural and Biological Sciences",  # plantas, ecologia, alimentos, ciência animal, solos, insetos, aquática, agronomia
    34: "Veterinary",
}
# Afins medidos à parte (fora da contagem principal): subfield Biomedical Engineering (2204, dentro de Engineering).
CAMPOS_OPENALEX_OPCIONAIS: dict[int, str] = {}
SUBCAMPOS_OPENALEX_OPCIONAIS: dict[int, str] = {2204: "Biomedical Engineering"}

# CAPES: áreas de avaliação (NM_AREA_AVALIACAO), comparadas sem acento e em maiúsculas.
AREAS_AVALIACAO_CAPES: tuple[str, ...] = (
    "MEDICINA I",
    "MEDICINA II",
    "MEDICINA III",
    "ENFERMAGEM",
    "ODONTOLOGIA",
    "FARMACIA",
    "SAUDE COLETIVA",
    "NUTRICAO",
    "EDUCACAO FISICA",  # inclui fisioterapia, fonoaudiologia e terapia ocupacional
    "CIENCIAS BIOLOGICAS I",  # genética, biologia geral, botânica, zoologia
    "CIENCIAS BIOLOGICAS II",  # morfologia, fisiologia, bioquímica, biofísica, farmacologia
    "CIENCIAS BIOLOGICAS III",  # microbiologia, imunologia, parasitologia
    "BIOTECNOLOGIA",
    # Ampliação "opção D" (D-017):
    "BIODIVERSIDADE",
    "CIENCIAS AGRARIAS I",  # agronomia, recursos florestais, engenharia agrícola
    "CIENCIA DE ALIMENTOS",
    "ZOOTECNIA / RECURSOS PESQUEIROS",
    "MEDICINA VETERINARIA",
)
AREAS_AVALIACAO_CAPES_OPCIONAIS: tuple[str, ...] = ()
GRANDES_AREAS_CAPES: tuple[str, ...] = ("CIENCIAS DA SAUDE", "CIENCIAS BIOLOGICAS", "CIENCIAS AGRARIAS")

# Termos para fontes sem classificação estruturada (BDTD, Oasisbr): busca em todos os campos.
TERMOS_BUSCA = (
    # Até 11 termos: consultas booleanas maiores levaram o firewall do IBICT a responder 403 e depois
    # recusar conexões (2026-11-09). Não aumentar sem falar com o IBICT.
    "saúde OR medicina OR enfermagem OR odontologia OR farmácia OR nutrição OR fisioterapia OR "
    "genética OR genômica OR biotecnologia OR biomédica"
)

# Palavras que identificam instituições do Nordeste em nomes livres (BDTD/Oasisbr). Heurística.
PALAVRAS_INSTITUICOES_NE = tuple(
    [u.nome for u in UFS_NORDESTE]
    + [u.capital for u in UFS_NORDESTE]
    + [
        "Nordeste", "Feira de Santana", "Campina Grande", "Cariri", "Semi-Árido", "Semiárido",
        "Estadual de Santa Cruz", "Recôncavo", "Vale do São Francisco", "Acaraú", "Potiguar", "Tiradentes",
        "Sul da Bahia", "Oeste da Bahia", "Sudoeste da Bahia", "Integração Internacional da Lusofonia",
        "UFBA", "UFRB", "UFSB", "UFOB", "UNEB", "UEFS", "UESB", "UESC", "UFPE", "UFRPE", "UPE", "UNICAP",
        "UFC", "UECE", "URCA", "UNIFOR", "UNILAB", "UFRN", "UERN", "UFERSA", "UFPB", "UEPB", "UFCG",
        "UFAL", "UNCISAL", "UFS", "UNIT", "UFPI", "UESPI", "UFMA", "UEMA", "UNIVASF", "Fiocruz Bahia",
        "Fiocruz Pernambuco", "Fiocruz Ceará", "Aggeu Magalhães", "Gonçalo Moniz",
    ]
)


def normalizar(txt: str) -> str:
    sem = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem).strip().upper()


def eh_area_capes(area_avaliacao: str, incluir_opcionais: bool = False) -> bool:
    a = normalizar(area_avaliacao)
    areas = AREAS_AVALIACAO_CAPES + (AREAS_AVALIACAO_CAPES_OPCIONAIS if incluir_opcionais else ())
    return a in areas


def eh_instituicao_ne(nome: str) -> bool:
    """Heurística por nome (só para fontes sem UF estruturada)."""
    n = normalizar(nome)
    for p in PALAVRAS_INSTITUICOES_NE:
        pn = normalizar(p)
        if len(pn) <= 5:  # siglas: palavra inteira
            if re.search(rf"(?<![A-Z]){re.escape(pn)}(?![A-Z])", n):
                return True
        elif pn in n:
            return True
    return False


def filtro_openalex_regioes(prefixo: str) -> str:
    """Ex.: authorships.institutions.geo.region:Maranhão|Piauí|"Rio Grande do Norte"|..."""
    vals = [f'"{u.nome}"' if " " in u.nome else u.nome for u in UFS_NORDESTE]
    return f"{prefixo}:{'|'.join(vals)}"


def filtro_openalex_campos(prefixo: str, campos: dict[int, str] | None = None) -> str:
    return f"{prefixo}:{'|'.join(str(c) for c in (campos or CAMPOS_OPENALEX))}"
