"""Técnicas por método para o quiz (D-053): candidatas medidas contra os dados antes de virar opção.

  python -m ingest.carga.quiz_tecnicas medir      # pesquisadores por técnica, dentro das publicações do método -> relatorios/quiz_tecnicas.md
  python -m ingest.carga.quiz_tecnicas aplicar    # grava a pergunta "tecnica" no arvore.json (só as técnicas com gente suficiente)

Uma publicação usa a técnica se o título ou as palavras-chave trazem um dos termos (termo curto = palavra inteira, como no
quiz_preparar) ou se o tópico principal é um dos tópicos da técnica. Conta-se quem tem >= 2 publicações do método com a técnica.
"""
from __future__ import annotations

import json
import sys

from .validar_arvore_quiz import ARQ_ARVORE, DIR_RELATORIOS, _lit, psql

MIN_PESQ = 40   # abaixo disto, a técnica não vira opção

# método -> [(id, rótulo, trecho do nicho (substitui o do método), termos, tópicos, frase)]
TECNICAS: dict[str, list[tuple[str, str, str, list[str], list[str], str]]] = {
    "metodo.bioinfo": [
        ("tec.genomica", "Genômica e sequenciamento", "Genômica", ["genome", "genoma", "genomic", "genômic", "whole-genome", "sequencing", "sequenciamento"], [], "genômica e sequenciamento de genomas"),
        ("tec.metagenomica", "Metagenômica e microbiomas", "Metagenômica", ["metagenom", "16s rrna", "16s rdna", "microbiome", "microbioma", "amplicon"], [], "metagenômica e microbiomas"),
        ("tec.filogenia", "Filogenia e evolução", "Filogenia", ["phylogen", "filogen", "phylogeograph", "filogeogr", "molecular evolution"], [], "filogenia e evolução molecular"),
        ("tec.docking", "Docking e modelagem molecular", "Modelagem molecular", ["docking", "molecular dynamics", "dinâmica molecular", "in silico", "virtual screening", "qsar"], ["T10211"], "docking e modelagem molecular de fármacos"),
        ("tec.transcriptomica", "Transcriptômica e expressão", "Transcriptômica", ["transcriptom", "rna-seq", "rnaseq", "differential expression"], [], "transcriptômica e RNA-seq"),
    ],
    "metodo.genetica": [
        ("tec.marcadores", "Marcadores moleculares", "Genética com marcadores moleculares", ["microsatellite", "microssatélite", "ssr", "snp", "molecular marker", "marcador molecular", "issr"], [], "marcadores moleculares e genotipagem"),
        ("tec.pcr", "PCR e diagnóstico molecular", "Diagnóstico molecular", ["pcr", "qpcr", "rt-pcr", "real-time pcr", "molecular diagnosis", "diagnóstico molecular"], [], "PCR e diagnóstico molecular"),
        ("tec.expressao", "Expressão gênica", "Genética da expressão gênica", ["gene expression", "expressão gênica", "expressão de genes", "polymorphism", "polimorfismo"], [], "expressão gênica e polimorfismos"),
        ("tec.citogenetica", "Citogenética", "Citogenética", ["cytogenetic", "citogenét", "karyotype", "cariótipo", "chromosome", "cromossom"], [], "citogenética e cromossomos"),
        ("tec.populacoes", "Genética de populações", "Genética de populações", ["population structure", "estrutura populacional", "genetic diversity", "diversidade genética", "gene flow"], ["T10012"], "genética de populações"),
    ],
    "metodo.bancada": [
        ("tec.celulas", "Cultura de células", "Cultura de células", ["cell culture", "cultura de células", "cell line", "linhagem celular", "cytotoxicity", "citotoxicidade", "in vitro"], [], "cultura de células e ensaios in vitro"),
        ("tec.modelos_animais", "Modelos animais", "Experimentação animal", ["rats", "ratos", "mice", "camundongos", "wistar", "murine", "murino", "zebrafish"], [], "experimentos com modelos animais"),
        ("tec.microbiologia", "Ensaios microbiológicos", "Microbiologia de bancada", ["antimicrobial activity", "atividade antimicrobiana", "minimum inhibitory", "concentração inibitória", "antibacterial", "antibacteriana", "biofilm"], [], "ensaios antimicrobianos e microbiológicos"),
        ("tec.histologia", "Histologia e patologia", "Histopatologia", ["histolog", "histopatol", "histopathol", "immunohistochem", "imuno-histoquím", "morphometr"], [], "histologia e histopatologia"),
        ("tec.bioquimica", "Bioquímica e estresse oxidativo", "Bioquímica experimental", ["oxidative stress", "estresse oxidativo", "enzymatic", "enzimátic", "antioxidant", "antioxidante", "biochemical"], [], "bioquímica e estresse oxidativo"),
        ("tec.nano", "Nanotecnologia", "Nanotecnologia", ["nanopartic", "nanoparticle", "nanoemuls", "nanostruct", "nanocomposit", "liposom", "lipossom"], ["T10704", "T10256"], "nanotecnologia e sistemas de liberação"),
    ],
    "metodo.quimica": [
        ("tec.produtos_naturais", "Extração e produtos naturais", "Química de produtos naturais", ["essential oil", "óleo essencial", "extract", "extrato", "flavonoid", "flavonoide", "phytochemical", "fitoquímic"], [], "extração e química de produtos naturais"),
        ("tec.sintese", "Síntese de compostos", "Síntese química", ["synthesis", "síntese", "synthetic", "sintétic", "derivatives", "derivados"], [], "síntese de compostos e derivados"),
        ("tec.complexos", "Complexos metálicos", "Química de complexos metálicos", ["metal complex", "complexos metálicos", "ruthenium", "rutênio", "copper(ii)", "cobre(ii)", "coordination compound"], ["T10163"], "complexos metálicos e química de coordenação"),
        ("tec.analitica", "Cromatografia e análise química", "Química analítica", ["hplc", "chromatograph", "cromatograf", "mass spectrometry", "espectrometria", "lc-ms", "gc-ms", "voltammetr"], [], "cromatografia e química analítica"),
        ("tec.nano_q", "Nanomateriais", "Química de nanomateriais", ["nanopartic", "nanoparticle", "nanomaterial", "nanocomposit", "graphene", "grafeno"], [], "nanomateriais"),
        ("tec.docking_q", "Docking e modelagem molecular", "Química computacional", ["docking", "molecular dynamics", "dinâmica molecular", "in silico", "virtual screening", "qsar", "dft"], ["T10211"], "docking, modelagem molecular e química computacional"),
        ("tec.alimentos_q", "Análise de alimentos", "Química de alimentos", ["physicochemical", "físico-químic", "proximate composition", "composição centesimal", "sensory", "sensorial"], [], "análise físico-química de alimentos"),
    ],
    "metodo.dados": [
        ("tec.ml", "Aprendizado de máquina e IA", "Inteligência artificial", ["machine learning", "aprendizado de máquina", "deep learning", "neural network", "redes neurais", "artificial intelligence", "inteligência artificial", "random forest"], ["T11396", "T10616"], "aprendizado de máquina e inteligência artificial"),
        ("tec.geo", "Geoprocessamento e sensoriamento", "Geoprocessamento", ["remote sensing", "sensoriamento remoto", "geoprocessamento", "gis", "sig", "ndvi", "satellite", "satélite", "landsat", "sentinel-2"], [], "geoprocessamento e sensoriamento remoto"),
        ("tec.espacial", "Estatística espacial", "Estatística espacial", ["spatial analysis", "análise espacial", "spatial distribution", "distribuição espacial", "scan statistic", "spatiotemporal", "espaço-temporal"], ["T11819"], "análise espacial e espaço-temporal"),
        ("tec.modelagem", "Modelos matemáticos", "Modelagem matemática", ["mathematical model", "modelo matemático", "modelagem", "simulation model", "compartmental model", "nonlinear model"], [], "modelagem matemática e simulação"),
        ("tec.series", "Séries temporais e previsão", "Séries temporais", ["time series", "séries temporais", "série temporal", "forecast", "previsão", "joinpoint", "trend analysis"], [], "séries temporais e previsão"),
    ],
    "metodo.epidemio": [
        ("tec.transversal", "Estudos transversais", "Epidemiologia transversal", ["cross-sectional", "transversal", "prevalence", "prevalência"], [], "estudos transversais de prevalência"),
        ("tec.coorte", "Coortes e acompanhamento", "Epidemiologia de coortes", ["cohort", "coorte", "longitudinal", "follow-up", "seguimento"], [], "estudos de coorte e longitudinais"),
        ("tec.revisao", "Revisões sistemáticas e meta-análises", "Revisão sistemática", ["systematic review", "revisão sistemática", "meta-analysis", "metanálise", "meta-análise", "scoping review", "revisão de escopo"], [], "revisões sistemáticas e meta-análises"),
        ("tec.espacial_epi", "Análise espacial e temporal", "Epidemiologia espacial", ["spatial analysis", "análise espacial", "spatial distribution", "distribuição espacial", "temporal trend", "tendência temporal", "ecological study", "estudo ecológico"], ["T11819"], "epidemiologia espacial e tendências temporais"),
        ("tec.inqueritos", "Inquéritos e sistemas de informação", "Epidemiologia com bases nacionais", ["national health survey", "pesquisa nacional de saúde", "vigitel", "datasus", "sinan", "sim", "sinasc", "information system", "sistema de informação"], [], "inquéritos nacionais e sistemas de informação em saúde"),
        ("tec.qualitativa", "Pesquisa qualitativa", "Pesquisa qualitativa em saúde", ["qualitative", "qualitativ", "interviews", "entrevistas", "focus group", "grupo focal", "content analysis", "análise de conteúdo"], [], "pesquisa qualitativa em saúde"),
    ],
    "metodo.clinica": [
        ("tec.ensaio", "Ensaios clínicos", "Ensaios clínicos", ["randomized", "randomizado", "randomised", "clinical trial", "ensaio clínico", "placebo"], [], "ensaios clínicos randomizados"),
        ("tec.caso", "Relatos e séries de casos", "Relatos de caso", ["case report", "relato de caso", "case series", "série de casos"], [], "relatos e séries de casos clínicos"),
        ("tec.validacao", "Validação de instrumentos", "Validação de instrumentos", ["validation", "validação", "psychometric", "psicométric", "reliability", "confiabilidade", "cross-cultural adaptation", "adaptação transcultural"], ["T13117"], "validação e adaptação de instrumentos"),
        ("tec.imagem", "Diagnóstico por imagem", "Diagnóstico por imagem", ["ultrasound", "ultrassom", "ultrassonograf", "tomography", "tomografia", "magnetic resonance", "ressonância magnética", "radiograph"], [], "diagnóstico por imagem"),
        ("tec.intervencao", "Intervenções educativas e de cuidado", "Intervenções em saúde", ["educational intervention", "intervenção educativa", "educational technology", "tecnologia educacional", "health education", "educação em saúde"], [], "intervenções educativas e de cuidado"),
        ("tec.qualitativa_c", "Pesquisa qualitativa", "Pesquisa qualitativa em saúde", ["qualitative", "qualitativ", "focus group", "grupo focal", "content analysis", "análise de conteúdo", "phenomenolog", "fenomenol"], [], "pesquisa qualitativa em saúde"),
        ("tec.exercicio", "Exercício e reabilitação", "Reabilitação clínica", ["therapeutic exercise", "exercício terapêutico", "training program", "programa de treinamento", "physical therapy", "fisioterapia"], [], "exercício terapêutico e reabilitação"),
    ],
    "metodo.campo": [
        ("tec.inventario", "Levantamentos e inventários", "Inventário de campo", ["inventory", "inventário", "checklist", "species richness", "riqueza de espécies", "levantamento florístico", "floristic survey", "new records", "novos registros"], [], "levantamentos e inventários de espécies"),
        ("tec.experimentos_campo", "Experimentos agronômicos", "Experimentação agronômica", ["field experiment", "experimento de campo", "cultivars", "cultivares", "yield", "produtividade", "agronomic performance"], [], "experimentos agronômicos de campo"),
        ("tec.entrevistas", "Entrevistas e saberes locais", "Pesquisa com comunidades", ["interviews", "entrevistas", "questionnaire", "questionário", "ethnobotan", "etnobotân", "traditional knowledge", "conhecimento tradicional", "local communities"], [], "entrevistas e conhecimento tradicional"),
        ("tec.captura", "Captura e armadilhas", "Amostragem de fauna", ["traps", "armadilhas", "pitfall", "mist net", "rede de neblina", "camera trap", "armadilha fotográfica", "capture-recapture"], [], "captura e amostragem de fauna"),
        ("tec.monitoramento", "Monitoramento ambiental", "Monitoramento ambiental", ["monitoring", "monitoramento", "seasonal variation", "variação sazonal", "long-term"], [], "monitoramento ambiental"),
        ("tec.sensores_campo", "Drones e sensores", "Sensoriamento no campo", ["uav", "drone", "remote sensing", "sensoriamento remoto", "ndvi", "multispectral", "multiespectral"], ["T10616"], "drones, sensores e sensoriamento remoto"),
    ],
}


def _re(termo: str) -> str:
    return "\\m" + termo + ("(s|es)?\\M" if len(termo) <= 4 else "")


def medir() -> list[dict]:
    linhas = []
    for metodo, tecs in TECNICAS.items():
        for tid, rotulo, _n, termos, topicos, _f in tecs:
            res = "|".join(_re(t.lower()) for t in termos)
            cond_t = f"OR w.primary_topic_id IN ({','.join(map(_lit, topicos))})" if topicos else ""
            r = psql(f"""
              WITH mw AS (SELECT work_id FROM quiz_opcao_work WHERE opcao_id = {_lit(metodo)}),
                   tw AS (SELECT w.id AS work_id FROM works w JOIN mw ON mw.work_id = w.id
                           WHERE lower(f_unaccent(w.title)) ~ lower(f_unaccent({_lit(res)})) {cond_t}
                          UNION
                          SELECT k.work_id FROM work_keywords k JOIN mw ON mw.work_id = k.work_id
                           WHERE lower(f_unaccent(k.keyword)) ~ lower(f_unaccent({_lit(res)}))),
                   rp AS (SELECT a.researcher_id FROM work_authorships a JOIN tw USING (work_id) WHERE a.researcher_id IS NOT NULL GROUP BY 1 HAVING count(*) >= 2)
              SELECT (SELECT count(*) FROM tw) AS works, (SELECT count(*) FROM rp) AS pesq;""")[0]
            linhas.append({"metodo": metodo, "id": tid, "rotulo": rotulo, "works": int(r["works"]), "pesq": int(r["pesq"])})
            print(f"{metodo:16} {rotulo:42} {r['works']:>6} publ. {r['pesq']:>5} pesq.")
    L = ["# Quiz: técnicas candidatas por método (D-053)", "", f"Pesquisadores com ≥ 2 publicações do método que usam a técnica. Mínimo para virar opção: {MIN_PESQ}.", "",
         "| método | técnica | publicações | pesquisadores | entra? |", "|---|---|---|---|---|"]
    L += [f"| {x['metodo']} | {x['rotulo']} | {x['works']} | {x['pesq']} | {'sim' if x['pesq'] >= MIN_PESQ else 'não'} |" for x in linhas]
    (DIR_RELATORIOS / "quiz_tecnicas.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return linhas


def aplicar() -> int:
    contagem = {x["id"]: x["pesq"] for x in medir()}
    a = json.loads(ARQ_ARVORE.read_text(encoding="utf-8"))
    opcoes_por = {}
    for metodo, tecs in TECNICAS.items():
        ops = [{"id": tid, "rotulo": rot, "sinais": {"termos": termos, **({"topics": tps} if tps else {}), "frase": fr}, "nicho": nicho}
               for tid, rot, nicho, termos, tps, fr in tecs if contagem.get(tid, 0) >= MIN_PESQ]
        if len(ops) >= 2:
            opcoes_por[metodo] = ops
    a["perguntas"]["tecnica"] = {"bloco": "nicho", "faceta": "tecnica", "texto": "E qual técnica você mais usa?", "depende_de": "metodo", "opcoes_por": opcoes_por}
    if "tecnica" not in a["telas"]:
        a["telas"].insert(a["telas"].index("metodo") + 1, "tecnica")
    a["pesos_faceta"]["tecnica"] = 1.5
    a["versao"] = max(a["versao"], 7)
    ARQ_ARVORE.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"pergunta de técnica: {sum(len(v) for v in opcoes_por.values())} técnicas em {len(opcoes_por)} métodos")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "aplicar":
        sys.exit(aplicar())
    medir()
