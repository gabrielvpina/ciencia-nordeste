"""Ambientes estratificados no quiz (D-054): grupos de ambiente e a pergunta "Onde, exatamente?", com estratos medidos nos dados.

  python -m ingest.carga.quiz_ambientes medir     # pesquisadores por estrato -> ingest/relatorios/quiz_ambientes.md
  python -m ingest.carga.quiz_ambientes aplicar   # grava grupos, estratos (só os com gente suficiente) e novos habitats no arvore.json

Uma publicação está num estrato se o título ou as palavras-chave trazem um dos termos (termo curto = palavra inteira, como no
quiz_preparar) ou se o tópico principal é um dos tópicos do estrato. Conta-se quem tem >= 2 publicações no estrato.
Os ids de ambiente que já existiam continuam (links antigos); o estrato é uma pergunta nova, opcional, que depende do ambiente.
"""
from __future__ import annotations

import json
import sys

from .validar_arvore_quiz import ARQ_ARVORE, DIR_RELATORIOS, _lit, psql

MIN_PESQ = 40

# grupo (ambiente) -> [(id, rótulo, artigo, nome do sintagma, trecho do nicho, termos, tópicos, frase)]
E = tuple[str, str, str, str, str, list[str], list[str], str]
ESTRATOS: dict[str, list[E]] = {
    "ambiente.caatinga": [
        ("amb.caatinga", "Caatinga", "a", "caatinga", "da caatinga", ["caatinga", "seasonally dry tropical forest", "floresta tropical sazonalmente seca"], [], "caatinga e florestas secas"),
        ("amb.cerrado", "Cerrado e áreas de transição", "o", "cerrado", "do cerrado", ["cerrado", "savanna", "savana", "ecotone", "ecótono"], [], "cerrado e áreas de transição"),
        ("amb.serras", "Serras, chapadas e brejos de altitude", "as", "serras", "das serras e chapadas", ["chapada", "serra da", "serra do", "brejo de altitude", "highland", "montane", "altitude"], [], "serras, chapadas e brejos de altitude"),
        ("amb.sertao_irrigado", "Sertão irrigado e vale do São Francisco", "o", "sertão irrigado", "do sertão irrigado", ["irrigated perimeter", "perímetro irrigado", "são francisco valley", "vale do são francisco", "petrolina", "juazeiro"], [], "agricultura irrigada no vale do São Francisco"),
        ("amb.cavernas", "Cavernas", "as", "cavernas", "das cavernas", ["cave", "caverna", "cavern", "subterranean", "subterrâne", "troglob"], [], "cavernas e ambientes subterrâneos"),
    ],
    "ambiente.mata": [
        ("amb.mata_atlantica", "Mata atlântica", "a", "mata atlântica", "da mata atlântica", ["atlantic forest", "mata atlântica", "atlantic rainforest"], [], "mata atlântica"),
        ("amb.restinga", "Restingas e dunas", "as", "restingas", "das restingas e dunas", ["restinga", "dunes", "dunas", "sand dune", "coastal sandy"], [], "restingas e dunas"),
        ("amb.amazonia", "Amazônia maranhense e mata dos cocais", "a", "Amazônia", "da Amazônia maranhense", ["amazon", "amazôn", "babassu", "babaçu", "mata dos cocais", "pre-amazon", "pré-amazôn"], [], "Amazônia maranhense e mata dos cocais"),
        ("amb.fragmentos", "Fragmentos florestais e áreas urbanas verdes", "os", "fragmentos de mata", "dos fragmentos florestais", ["forest fragment", "fragmento florestal", "fragmentos florestais", "urban forest", "arborização urbana", "urban green"], [], "fragmentos florestais e verde urbano"),
    ],
    "ambiente.mar": [
        ("amb.manguezais", "Manguezais e estuários", "os", "manguezais", "dos manguezais e estuários", ["mangrove", "manguezal", "manguezais", "estuar"], [], "manguezais e estuários"),
        ("amb.praias_recifes", "Praias e recifes de coral", "os", "recifes de coral", "das praias e recifes", ["coral reef", "recifes de coral", "beach", "praia", "reef fish", "sandy beach", "ambientes recifais"], [], "praias e recifes de coral"),
        ("amb.mar_aberto", "Mar aberto e plataforma continental", "o", "mar aberto", "do mar aberto", ["oceanic", "oceânic", "continental shelf", "plataforma continental", "offshore", "pelagic", "pelágic", "fisheries", "pesca"], ["T10230"], "oceano, plataforma continental e pesca"),
        ("amb.ilhas", "Ilhas oceânicas", "as", "ilhas oceânicas", "das ilhas oceânicas", ["fernando de noronha", "atol das rocas", "oceanic island", "ilha oceânica", "são pedro e são paulo", "archipelago", "arquipélago"], [], "ilhas oceânicas como Fernando de Noronha"),
    ],
    "ambiente.aguas": [
        ("amb.rios", "Rios e o São Francisco", "os", "rios", "dos rios", ["river", "rio são francisco", "são francisco river", "riverine", "riparian", "ripári", "fluvial", "watershed", "bacia hidrográfica"], [], "rios e bacias hidrográficas"),
        ("amb.acudes", "Açudes e reservatórios", "os", "açudes", "dos açudes e reservatórios", ["reservoir", "reservatório", "açude", "dam", "barragem", "semiarid reservoir"], [], "açudes e reservatórios do semiárido"),
        ("amb.lagoas", "Lagoas e áreas úmidas", "as", "lagoas", "das lagoas e áreas úmidas", ["lagoon", "lagoa", "wetland", "área úmida", "áreas úmidas", "pond", "temporary pool", "poça temporária"], [], "lagoas, poças temporárias e áreas úmidas"),
        ("amb.aquifero", "Água subterrânea e poços", "os", "poços", "da água subterrânea", ["groundwater", "água subterrânea", "aquifer", "aquífero", "well water", "poços"], [], "água subterrânea, aquíferos e poços"),
    ],
    "ambiente.lavouras": [
        ("amb.agricultura_familiar", "Agricultura familiar e assentamentos", "a", "agricultura familiar", "da agricultura familiar", ["smallholder", "agricultura familiar", "family farm", "assentamento", "settlement", "agroecolog", "agroecológ"], [], "agricultura familiar e agroecologia"),
        ("amb.agronegocio", "Grandes lavouras e agronegócio", "o", "agronegócio", "das grandes lavouras", ["commercial farm", "agronegócio", "agribusiness", "soybean", "soja", "sugarcane", "cana-de-açúcar", "monoculture", "monocultura"], [], "grandes lavouras e agronegócio"),
        ("amb.pastagens", "Pastagens e criação a campo", "as", "pastagens", "das pastagens e da criação a campo", ["pasture", "pastagem", "grazing", "pastejo", "rangeland", "extensive system", "sistema extensivo"], ["T13591"], "pastagens e criação extensiva"),
        ("amb.estufas", "Estufas, viveiros e hortas", "as", "estufas", "das estufas e viveiros", ["greenhouse", "casa de vegetação", "nursery", "viveiro", "vegetable garden", "horta", "hydroponic", "hidropônic"], ["T13391"], "estufas, viveiros e hortas"),
    ],
    "ambiente.cidades": [
        ("amb.hospitais", "Hospitais e UTIs", "os", "hospitais", "dos hospitais", ["hospital", "intensive care", "terapia intensiva", "uti", "icu", "emergency department", "pronto-socorro", "inpatient", "internação"], [], "hospitais, UTIs e emergências"),
        ("amb.atencao_primaria", "Atenção primária e saúde da família", "a", "atenção primária", "da atenção primária", ["primary care", "atenção primária", "atenção básica", "family health", "saúde da família", "community health worker", "agente comunitário"], ["T11590"], "atenção primária e estratégia saúde da família"),
        ("amb.escolas", "Escolas e universidades", "as", "escolas", "das escolas e universidades", ["school", "escola", "schoolchildren", "escolares", "students", "estudantes", "university", "universitári"], [], "escolas, estudantes e universidades"),
        ("amb.urbano", "Bairros, periferias e ambiente urbano", "os", "bairros", "das cidades e periferias", ["urban", "urbano", "urbana", "city", "cidade", "neighborhood", "bairro", "slum", "periferia"], [], "ambiente urbano, bairros e periferias"),
        ("amb.prisoes", "Prisões e instituições", "as", "prisões", "do sistema prisional", ["prison", "prisional", "presídio", "incarcerated", "privados de liberdade"], [], "sistema prisional e instituições"),
    ],
    "ambiente.comunidades": [
        ("amb.indigenas", "Povos indígenas", "os", "povos indígenas", "dos povos indígenas", ["indigenous", "indígena", "indígenas", "aldeia", "etnia"], [], "povos indígenas"),
        ("amb.quilombolas", "Comunidades quilombolas", "os", "quilombos", "das comunidades quilombolas", ["quilombola", "quilombo", "maroon"], [], "comunidades quilombolas"),
        ("amb.pescadores", "Pescadores artesanais e ribeirinhos", "os", "pescadores", "dos pescadores artesanais", ["artisanal fish", "pesca artesanal", "pescadores", "fishermen", "fishers", "ribeirinh", "marisqueir", "shellfish gatherers"], [], "pescadores artesanais, marisqueiras e ribeirinhos"),
        ("amb.rurais", "Comunidades rurais e sertanejas", "as", "comunidades rurais", "das comunidades rurais", ["rural communit", "comunidade rural", "comunidades rurais", "rural population", "população rural", "rural area", "zona rural"], [], "comunidades rurais e sertanejas"),
    ],
}
GRUPOS_NOVOS = [
    {"id": "ambiente.aguas", "rotulo": "Rios, açudes e lagoas", "visual": {"cor": "mar"},
     "sinais": {"termos": ["river", "reservoir", "reservatório", "açude", "freshwater", "água doce", "lagoon", "lagoa", "wetland", "groundwater", "água subterrânea"], "frase": "rios, açudes, lagoas e água doce"},
     "sintagma": {"artigo": "as", "nome": "águas doces"}, "nicho": "das águas doces"},
    {"id": "ambiente.comunidades", "rotulo": "Comunidades tradicionais e rurais", "visual": {"cor": "lavoura"},
     "sinais": {"termos": ["indigenous", "indígena", "quilombola", "artisanal fish", "pesca artesanal", "ribeirinh", "rural communit", "comunidade rural", "comunidades rurais", "traditional communit", "comunidades tradicionais"],
                "frase": "povos indígenas, quilombolas, pescadores artesanais e comunidades rurais"},
     "sintagma": {"artigo": "as", "nome": "comunidades tradicionais"}, "nicho": "das comunidades tradicionais"},
]
ROTULOS_GRUPO = {"ambiente.mata": "Matas úmidas, restingas e brejos", "ambiente.mar": "Litoral, mangues e mar", "ambiente.cidades": "Cidades, hospitais, escolas e serviços"}

# novos lugares de trabalho (perfil: só cor e título, não entram no match) e seus títulos por estilo
HABITATS_NOVOS = [
    {"id": "habitat.clinica", "rotulo": "No hospital ou no consultório", "descricao": "pacientes, exames e plantões", "visual": {"cor": "pessoas"}},
    {"id": "habitat.aula", "rotulo": "Em sala de aula", "descricao": "turmas, oficinas e extensão", "visual": {"cor": "colecoes"}},
    {"id": "habitat.agua", "rotulo": "Na água", "descricao": "barco, mergulho, rio ou açude", "visual": {"cor": "agua"}},
    {"id": "habitat.estufa", "rotulo": "Na estufa ou no biotério", "descricao": "plantas, animais e experimentos controlados", "visual": {"cor": "estufa"}},
]
ARQUETIPOS_NOVOS = {
    "habitat.clinica": {"estilo.testa": "Plantão experimental", "estilo.junta": "Prontuário vivo", "estilo.modelo": "Estrategista de plantão", "estilo.gente": "Cuidado em pessoa", "estilo.inedito": "Pioneirismo de consultório"},
    "habitat.aula": {"estilo.testa": "Laboratório de giz", "estilo.junta": "Acervo de sala de aula", "estilo.modelo": "Mapa da turma", "estilo.gente": "Ponte com a escola", "estilo.inedito": "Ideia fora da caixa"},
    "habitat.agua": {"estilo.testa": "Teste de maré", "estilo.junta": "Rede cheia de amostras", "estilo.modelo": "Correnteza calculada", "estilo.gente": "Conversa de beira de rio", "estilo.inedito": "Mergulho no desconhecido"},
    "habitat.estufa": {"estilo.testa": "Experimento sob controle", "estilo.junta": "Viveiro de amostras", "estilo.modelo": "Clima calculado", "estilo.gente": "Mutirão de bancada verde", "estilo.inedito": "Broto inédito"},
}


def _re(t: str) -> str:
    return "\\m" + t + ("(s|es)?\\M" if len(t) <= 4 else "")


def medir() -> list[dict]:
    out = []
    for grupo, ests in ESTRATOS.items():
        for eid, rot, _a, _n, _ni, termos, topicos, _f in ests:
            res = "|".join(_re(t.lower()) for t in termos)
            cond_t = f"OR w.primary_topic_id IN ({','.join(map(_lit, topicos))})" if topicos else ""
            r = psql(f"""
              WITH tw AS (SELECT w.id AS work_id FROM works w WHERE lower(f_unaccent(w.title)) ~ lower(f_unaccent({_lit(res)})) {cond_t}
                          UNION SELECT k.work_id FROM work_keywords k WHERE lower(f_unaccent(k.keyword)) ~ lower(f_unaccent({_lit(res)}))),
                   rp AS (SELECT a.researcher_id FROM work_authorships a JOIN tw USING (work_id) WHERE a.researcher_id IS NOT NULL GROUP BY 1 HAVING count(*) >= 2)
              SELECT (SELECT count(*) FROM tw) AS works, (SELECT count(*) FROM rp) AS pesq;""")[0]
            out.append({"grupo": grupo, "id": eid, "rotulo": rot, "works": int(r["works"]), "pesq": int(r["pesq"])})
            print(f"{grupo:22} {rot:46} {r['works']:>6} publ. {r['pesq']:>5} pesq.")
    L = ["# Quiz: estratos de ambiente (D-054)", "", f"Pesquisadores com ≥ 2 publicações no estrato. Mínimo para virar opção: {MIN_PESQ}.", "",
         "| grupo | estrato | publicações | pesquisadores | entra? |", "|---|---|---|---|---|"]
    L += [f"| {x['grupo']} | {x['rotulo']} | {x['works']} | {x['pesq']} | {'sim' if x['pesq'] >= MIN_PESQ else 'não'} |" for x in out]
    (DIR_RELATORIOS / "quiz_ambientes.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def aplicar() -> int:
    n = {x["id"]: x["pesq"] for x in medir()}
    a = json.loads(ARQ_ARVORE.read_text(encoding="utf-8"))
    P = a["perguntas"]
    amb = P["ambiente"]["opcoes"]
    qualquer = [o for o in amb if o["id"] == "ambiente.qualquer"]
    resto = [o for o in amb if o["id"] != "ambiente.qualquer"]
    for g in GRUPOS_NOVOS:
        if not any(o["id"] == g["id"] for o in resto):
            resto.append(g)
    for o in resto:
        if o["id"] in ROTULOS_GRUPO:
            o["rotulo"] = ROTULOS_GRUPO[o["id"]]
    P["ambiente"]["opcoes"] = resto + qualquer   # "não depende de um lugar" sempre por último
    opcoes_por = {}
    for grupo, ests in ESTRATOS.items():
        ops = [{"id": eid, "rotulo": rot, "sinais": {"termos": termos, **({"topics": tps} if tps else {}), "frase": fr}, "sintagma": {"artigo": art, "nome": nome}, "nicho": nicho}
               for eid, rot, art, nome, nicho, termos, tps, fr in ests if n.get(eid, 0) >= MIN_PESQ]
        if len(ops) >= 2:
            opcoes_por[grupo] = ops
    P["estrato"] = {"bloco": "nicho", "faceta": "estrato", "texto": "Onde, exatamente?", "depende_de": "ambiente", "opcoes_por": opcoes_por}
    if "estrato" not in a["telas"]:
        a["telas"].insert(a["telas"].index("ambiente") + 1, "estrato")
    a["pesos_faceta"]["estrato"] = 2.0
    # habitats novos (perfil) e seus arquétipos
    hab = P["habitat"]["opcoes"]
    for h in HABITATS_NOVOS:
        if not any(o["id"] == h["id"] for o in hab):
            hab.append(h)
    a["titulos"]["arquetipos"].update(ARQUETIPOS_NOVOS)
    a["versao"] = max(a["versao"], 8)
    ARQ_ARVORE.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ambientes: {len(resto)} grupos + 'não depende'; {sum(len(v) for v in opcoes_por.values())} estratos em {len(opcoes_por)} grupos; {len(hab)} habitats")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "aplicar":
        sys.exit(aplicar())
    medir()
