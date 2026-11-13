"""Expansão do quiz guiada pela auditoria (D-051; ingest/relatorios/quiz_auditoria.md).

  python -m ingest.carga.quiz_expandir     # aplica em apps/web/lib/quiz/arvore.json (idempotente: refaz a pergunta de tema)

O que faz:
  1. Nova pergunta **tema** logo depois do sub-objeto ("Qual destes temas é mais o seu?"): opções tiradas dos tópicos do
     OpenAlex mais comuns entre os pesquisadores do Nordeste dentro de cada sub-objeto (auditoria, seção 2). Cada tema tem os
     tópicos reais como sinal, um rótulo em português, o sintagma do título ("Detetive da leishmaniose") e o trecho do nicho.
  2. Novo objeto **Cuidado, serviços e formação em saúde**, com quatro sub-objetos para as lacunas da auditoria (seção 3):
     enfermagem e segurança do paciente, envelhecimento, formação em saúde e saúde do trabalhador.
  3. Reforço do ambiente "mar" com tópicos marinhos (as palavras-chave sozinhas eram poucas depois da correção de "recife").

Nada é removido: os ids existentes continuam válidos, e links antigos (sem tema) continuam abrindo o resultado.
"""
from __future__ import annotations

import json
import sys

from .validar_arvore_quiz import ARQ_ARVORE

# sub-objeto -> [(id, rótulo, tópicos OpenAlex, artigo, nome do sintagma, trecho do nicho, frase da consulta vetorial)]
T = tuple[str, str, list[str], str, str, str, str]
TEMAS: dict[str, list[T]] = {
    "sub.abelhas": [
        ("tema.mel", "Mel, própolis e produtos das abelhas", ["T11386"], "o", "mel", "do mel e da própolis", "mel, própolis e produtos apícolas"),
        ("tema.polinizacao", "Polinização e ecologia das abelhas", ["T10487", "T10702"], "a", "polinização", "da polinização", "polinização e ecologia de abelhas"),
        ("tema.vespas", "Taxonomia de abelhas e vespas", ["T12132"], "as", "vespas e abelhas", "da taxonomia de abelhas e vespas", "taxonomia de abelhas e vespas"),
        ("tema.abelhas_agrotox", "Abelhas e agrotóxicos", ["T11641"], "as", "abelhas", "dos efeitos de agrotóxicos em abelhas", "efeitos de agrotóxicos em abelhas"),
    ],
    "sub.agua": [
        ("tema.irrigacao", "Manejo da irrigação", ["T11404"], "a", "irrigação", "da irrigação", "manejo da irrigação e uso da água na agricultura"),
        ("tema.estresse_hidrico", "Plantas sob seca e sal", ["T10014"], "a", "tolerância à seca", "da tolerância das plantas à seca e ao sal", "estresse hídrico e salino em plantas"),
        ("tema.hidroponia", "Hidroponia e aquaponia", ["T13391"], "a", "hidroponia", "da hidroponia e da aquaponia", "hidroponia e aquaponia"),
        ("tema.bioestimulantes", "Silício e bioestimulantes", ["T12344", "T12407"], "os", "bioestimulantes", "de bioestimulantes e silício na agricultura", "bioestimulantes e silício na agricultura"),
    ],
    "sub.aquicultura": [
        ("tema.nutricao_peixes", "Nutrição de peixes e camarões", ["T10450"], "os", "peixes de cultivo", "da nutrição de peixes e camarões", "nutrição e crescimento na aquicultura"),
        ("tema.sanidade_aquicola", "Doenças e sanidade na aquicultura", ["T10506"], "a", "sanidade aquícola", "da sanidade na aquicultura", "doenças e microbiota na aquicultura"),
        ("tema.reproducao_aquatica", "Reprodução de espécies aquáticas", ["T11505"], "a", "reprodução de peixes", "da reprodução de espécies aquáticas", "reprodução de peixes e espécies aquáticas"),
        ("tema.bivalves", "Ostras, mexilhões e bivalves", ["T11088"], "as", "ostras", "do cultivo de ostras e bivalves", "cultivo de ostras, mexilhões e bivalves"),
    ],
    "sub.aranhas": [
        ("tema.aranhas", "Aranhas", ["T12447"], "as", "aranhas", "de aranhas", "taxonomia e comportamento de aranhas"),
        ("tema.acaros", "Ácaros", ["T12361"], "os", "ácaros", "de ácaros", "espécies de ácaros"),
        ("tema.escorpioes", "Escorpiões e animais peçonhentos", ["T11353"], "os", "escorpiões", "de escorpiões e animais peçonhentos", "escorpiões, venenos e acidentes com animais peçonhentos"),
        ("tema.carrapatos", "Carrapatos e doenças que transmitem", ["T10296"], "os", "carrapatos", "de carrapatos e das doenças que transmitem", "carrapatos e doenças transmitidas por vetores"),
    ],
    "sub.aves": [
        ("tema.nutricao_aves", "Nutrição de aves e suínos", ["T10098", "T10152"], "as", "rações", "da nutrição de aves e suínos", "nutrição e alimentação de aves e suínos"),
        ("tema.bem_estar_aves", "Bem-estar e estresse térmico", ["T12365"], "o", "bem-estar animal", "do bem-estar de aves e suínos", "bem-estar e estresse térmico de aves e suínos"),
        ("tema.aditivos", "Enzimas e aditivos na ração", ["T12991"], "os", "aditivos de ração", "de aditivos e enzimas na ração", "fitase, enzimas e aditivos na ração"),
        ("tema.sanidade_aves", "Parasitos e sanidade", ["T11074", "T10695"], "a", "sanidade das granjas", "da sanidade de aves e suínos", "parasitos e sanidade de aves e suínos"),
    ],
    "sub.bacterias": [
        ("tema.resistencia", "Resistência a antibióticos", ["T10147", "T10195"], "as", "superbactérias", "da resistência bacteriana", "resistência bacteriana a antibióticos"),
        ("tema.antimicrob_naturais", "Antimicrobianos naturais", ["T10225"], "os", "antimicrobianos naturais", "de antimicrobianos naturais", "óleos essenciais e compostos naturais contra bactérias"),
        ("tema.biofilmes", "Biofilmes", ["T10593"], "os", "biofilmes", "de biofilmes bacterianos", "biofilmes bacterianos e quorum sensing"),
        ("tema.bact_plantas", "Bactérias e plantas", ["T10076"], "as", "bactérias das plantas", "da interação entre bactérias e plantas", "interação entre bactérias e plantas"),
    ],
    "sub.boca": [
        ("tema.restauracoes", "Materiais e restaurações", ["T10113"], "as", "restaurações", "de materiais e restaurações dentárias", "materiais dentários e restaurações"),
        ("tema.saude_bucal", "Saúde bucal coletiva", ["T10368"], "a", "saúde bucal", "da saúde bucal coletiva", "saúde bucal coletiva e acesso ao dentista"),
        ("tema.endodontia", "Endodontia (tratamento de canal)", ["T10536"], "a", "endodontia", "da endodontia", "endodontia e tratamento de canal"),
        ("tema.periodontia", "Gengiva e periodontia", ["T10257"], "a", "gengiva", "da periodontia", "doença periodontal e microbiologia oral"),
        ("tema.atm", "ATM e dor orofacial", ["T10852"], "a", "ATM", "da ATM e da dor orofacial", "disfunção temporomandibular e dor orofacial"),
        ("tema.ortodontia", "Ortodontia", ["T10356"], "a", "ortodontia", "da ortodontia", "ortodontia e ortopedia facial"),
        ("tema.patologia_oral", "Patologia oral", ["T11787", "T11452"], "a", "patologia oral", "da patologia oral", "patologia oral e maxilofacial"),
    ],
    "sub.bovinos": [
        ("tema.nutricao_bovinos", "Nutrição de bovinos", ["T10098"], "a", "nutrição de bovinos", "da nutrição de bovinos", "nutrição de ruminantes e bovinos"),
        ("tema.carne_bovina", "Carne e qualidade", ["T10333"], "a", "carne bovina", "da qualidade da carne bovina", "qualidade da carne bovina"),
        ("tema.leite", "Leite e mastite", ["T11226"], "o", "leite", "da qualidade do leite e da mastite", "qualidade do leite e mastite em vacas"),
        ("tema.reproducao_bovina", "Reprodução bovina", ["T10364"], "a", "reprodução bovina", "da reprodução bovina", "reprodução e fertilidade de bovinos"),
        ("tema.calor_bovinos", "Bem-estar e calor", ["T12365"], "o", "bem-estar do rebanho", "do bem-estar e do estresse térmico de bovinos", "estresse térmico e bem-estar de bovinos"),
    ],
    "sub.cancer": [
        ("tema.leucemias", "Leucemias", ["T10309"], "as", "leucemias", "das leucemias", "leucemias e cânceres do sangue"),
        ("tema.falciforme", "Anemia falciforme", ["T10554"], "a", "anemia falciforme", "da anemia falciforme e das hemoglobinopatias", "anemia falciforme e hemoglobinopatias"),
        ("tema.cancer_mulher", "Câncer de mama e do colo do útero", ["T10146", "T13544"], "o", "câncer da mulher", "dos cânceres da mulher", "câncer do colo do útero, HPV e câncer de mama"),
        ("tema.cabeca_pescoco", "Câncer de boca e de cabeça e pescoço", ["T10307", "T12198"], "o", "câncer de boca", "do câncer de cabeça e pescoço", "câncer de boca, cabeça e pescoço"),
        ("tema.rastreamento", "Incidência e rastreamento", ["T10556"], "o", "rastreamento do câncer", "da epidemiologia e do rastreamento do câncer", "incidência e rastreamento do câncer"),
        ("tema.onco_vet", "Câncer em animais", ["T11149"], "a", "oncologia veterinária", "da oncologia veterinária", "oncologia veterinária"),
    ],
    "sub.caprinos": [
        ("tema.nutricao_caprinos", "Nutrição de cabras e ovelhas", ["T10098", "T10152"], "a", "nutrição de caprinos", "da nutrição de caprinos e ovinos", "nutrição de caprinos e ovinos"),
        ("tema.calor_caprinos", "Calor e adaptação ao semiárido", ["T12365"], "a", "adaptação ao calor", "da adaptação de caprinos e ovinos ao calor", "estresse térmico de caprinos e ovinos no semiárido"),
        ("tema.verminoses", "Verminoses", ["T11074"], "as", "verminoses", "das verminoses de caprinos e ovinos", "verminoses e controle de helmintos em pequenos ruminantes"),
        ("tema.reproducao_caprinos", "Reprodução", ["T10584", "T10364"], "a", "reprodução de caprinos", "da reprodução de caprinos e ovinos", "reprodução de caprinos e ovinos"),
        ("tema.racas", "Genética e raças nativas", ["T10594"], "as", "raças nativas", "da genética de caprinos e ovinos", "genética e raças de caprinos e ovinos"),
        ("tema.carne_caprina", "Carne e leite de cabra", ["T10333"], "a", "carne de bode", "da carne e do leite de caprinos", "carne e leite de caprinos e ovinos"),
    ],
    "sub.cardio": [
        ("tema.hipertensao", "Hipertensão", ["T10144"], "a", "pressão alta", "da hipertensão", "hipertensão arterial"),
        ("tema.diabetes", "Diabetes", ["T10793", "T10560", "T10027"], "o", "diabetes", "do diabetes", "diabetes e risco cardiovascular"),
        ("tema.pe_diabetico", "Pé diabético e feridas", ["T11227"], "o", "pé diabético", "do pé diabético", "pé diabético e úlceras"),
        ("tema.insuf_cardiaca", "Insuficiência cardíaca", ["T10198"], "a", "insuficiência cardíaca", "da insuficiência cardíaca", "insuficiência cardíaca"),
        ("tema.exercicio_coracao", "Coração e exercício", ["T11209", "T10745"], "o", "coração em movimento", "da fisiologia cardiovascular do exercício", "fisiologia cardiovascular do exercício e variabilidade da frequência cardíaca"),
    ],
    "sub.carnes": [
        ("tema.qualidade_carne", "Qualidade da carne", ["T10333"], "a", "carne", "da qualidade da carne", "qualidade de carnes"),
        ("tema.higiene_alimentos", "Higiene e segurança", ["T11957"], "a", "higiene dos alimentos", "da segurança microbiológica de carnes e pescados", "segurança e higiene de carnes e pescados"),
        ("tema.pescado", "Pescado", ["T10230", "T10450"], "o", "pescado", "do pescado", "qualidade e processamento do pescado"),
    ],
    "sub.clima": [
        ("tema.seca_plantas", "Plantas e seca", ["T10014"], "a", "seca", "das plantas diante da seca", "respostas das plantas à seca"),
        ("tema.erosao", "Erosão e sedimentos", ["T10889"], "a", "erosão", "da erosão do solo", "erosão do solo e sedimentos"),
        ("tema.geoestatistica", "Mapeamento e geoestatística", ["T10770"], "os", "mapas de solo", "do mapeamento do solo e do clima", "geoestatística e mapeamento de solos"),
        ("tema.florestas_secas", "Florestas e mudança do clima", ["T11880"], "as", "florestas", "das florestas e do clima", "ecologia e manejo florestal"),
        ("tema.calor_rebanhos", "Calor e rebanhos", ["T12365"], "o", "calor", "do estresse térmico nos rebanhos", "estresse térmico em animais de produção"),
    ],
    "sub.ecossistemas": [
        ("tema.ecologia_vegetal", "Ecologia da vegetação", ["T12618"], "a", "vegetação", "da ecologia vegetal", "ecologia vegetal e botânica"),
        ("tema.sementes", "Sementes e germinação", ["T11098"], "as", "sementes", "das sementes nativas", "germinação e fisiologia de sementes"),
        ("tema.florestas", "Florestas e restauração", ["T11880"], "as", "florestas", "das florestas e da restauração ecológica", "florestas e restauração ecológica"),
        ("tema.diversidade_genetica", "Diversidade genética de populações", ["T10012"], "a", "diversidade genética", "da diversidade genética de populações", "diversidade e estrutura genética de populações"),
        ("tema.interacoes", "Interações entre plantas e animais", ["T10487", "T10702"], "as", "interações ecológicas", "das interações entre plantas e animais", "interações ecológicas entre plantas e animais"),
    ],
    "sub.farinhas": [
        ("tema.novos_alimentos", "Novos produtos alimentícios", ["T14127"], "os", "novos alimentos", "do desenvolvimento de novos alimentos", "desenvolvimento de produtos alimentícios"),
        ("tema.proteinas", "Proteínas e glúten", ["T10411"], "as", "proteínas dos alimentos", "das proteínas e do glúten", "proteínas e glúten em alimentos"),
        ("tema.composicao", "Composição de alimentos", ["T10140"], "a", "composição dos alimentos", "da composição dos alimentos", "composição e propriedades de alimentos"),
        ("tema.secagem_farinhas", "Secagem e farinhas", ["T10650", "T12048"], "as", "farinhas", "da secagem e das farinhas", "secagem e produção de farinhas"),
    ],
    "sub.flora": [
        ("tema.botanica", "Botânica e vegetação", ["T12618"], "a", "botânica", "da botânica", "botânica e ecologia vegetal"),
        ("tema.taxonomia_plantas", "Taxonomia e novas espécies", ["T14049", "T10385"], "as", "espécies novas", "da taxonomia e da evolução de plantas", "taxonomia, descrição de espécies e evolução de plantas"),
        ("tema.fungos_plantas", "Fungos de plantas", ["T10825"], "os", "fungos de plantas", "dos fungos que atacam plantas", "fungos fitopatogênicos"),
        ("tema.micorrizas", "Micorrizas", ["T10451"], "as", "micorrizas", "das micorrizas", "fungos micorrízicos"),
    ],
    "sub.forrageiras": [
        ("tema.silagem", "Silagem e nutrição de ruminantes", ["T10098"], "a", "silagem", "da silagem e da nutrição de ruminantes", "silagem e nutrição de ruminantes"),
        ("tema.pastagens", "Pastagens", ["T13591"], "as", "pastagens", "das pastagens", "pastagens e sistemas pastoris"),
        ("tema.consorcios", "Consórcios e sistemas integrados", ["T12436"], "os", "consórcios agrícolas", "dos sistemas integrados e consórcios", "consórcios e sistemas integrados de produção"),
        ("tema.palma", "Palma e plantas forrageiras", ["T12330"], "a", "palma", "da palma forrageira", "palma forrageira e plantas forrageiras da caatinga"),
    ],
    "sub.frutas_alim": [
        ("tema.secagem_frutas", "Secagem de frutas", ["T10650"], "as", "frutas secas", "da secagem de frutas", "secagem e desidratação de frutas"),
        ("tema.pos_colheita_frutas", "Pós-colheita", ["T10473"], "a", "pós-colheita", "da pós-colheita de frutas", "pós-colheita e vida de prateleira de frutas"),
        ("tema.microencapsulacao_frutas", "Microencapsulação", ["T12048"], "a", "microencapsulação", "da microencapsulação de polpas", "microencapsulação e secagem por atomização"),
        ("tema.fermentados_frutas", "Bebidas e fermentados de frutas", ["T10141"], "os", "fermentados de frutas", "de bebidas e fermentados de frutas", "bebidas e fermentados de frutas"),
    ],
    "sub.frutiferas": [
        ("tema.pos_colheita", "Pós-colheita", ["T10473"], "a", "pós-colheita", "da pós-colheita", "pós-colheita de frutas e hortaliças"),
        ("tema.adubacao_frutiferas", "Nutrição e adubação", ["T12113"], "a", "adubação", "da nutrição de frutíferas e hortaliças", "nutrição e adubação de plantas"),
        ("tema.estresse_frutiferas", "Estresse e tolerância", ["T10014"], "a", "tolerância à seca", "do estresse em frutíferas e hortaliças", "estresse abiótico em frutíferas e hortaliças"),
        ("tema.irrigacao_frutiferas", "Irrigação de pomares e hortas", ["T11404"], "a", "irrigação", "da irrigação de frutíferas e hortaliças", "irrigação de frutíferas e hortaliças"),
        ("tema.doencas_frutiferas", "Doenças de plantas", ["T10825"], "as", "doenças de plantas", "das doenças de frutíferas e hortaliças", "doenças fúngicas de frutíferas e hortaliças"),
    ],
    "sub.fungos": [
        ("tema.infeccoes_fungicas", "Infecções fúngicas", ["T10150", "T11037"], "as", "infecções fúngicas", "das infecções fúngicas e dos antifúngicos", "infecções fúngicas, Candida e antifúngicos"),
        ("tema.fungos_plantas2", "Fungos de plantas", ["T10825"], "os", "fungos de plantas", "dos fungos que atacam plantas", "fungos fitopatogênicos"),
        ("tema.micorrizas2", "Micorrizas", ["T10451"], "as", "micorrizas", "das micorrizas", "fungos micorrízicos"),
        ("tema.enzimas_fungos", "Enzimas de fungos", ["T11617", "T10404"], "as", "enzimas", "das enzimas de fungos", "produção e aplicação de enzimas de fungos"),
        ("tema.produtos_microbianos", "Produtos naturais de micróbios", ["T10252"], "os", "produtos de micróbios", "dos produtos naturais microbianos", "produtos naturais e biossíntese microbiana"),
    ],
    "sub.graos": [
        ("tema.cana", "Cana-de-açúcar", ["T12431"], "a", "cana", "da cana-de-açúcar", "cultivo e processamento da cana-de-açúcar"),
        ("tema.melhoramento_graos", "Melhoramento de cultivos", ["T11229"], "o", "melhoramento de plantas", "do melhoramento de grandes culturas", "genética e melhoramento de plantas"),
        ("tema.bact_promotoras", "Bactérias promotoras de crescimento", ["T10076"], "as", "bactérias do solo", "das bactérias promotoras de crescimento", "bactérias promotoras de crescimento de plantas"),
        ("tema.adubacao_graos", "Adubação e manejo", ["T12294", "T12436"], "a", "adubação", "da adubação e do manejo de grandes culturas", "adubação e manejo de grandes culturas"),
        ("tema.seca_graos", "Seca e salinidade", ["T10014"], "a", "seca", "da tolerância de grãos à seca", "tolerância de grandes culturas à seca e ao sal"),
    ],
    "sub.herpeto": [
        ("tema.herpeto_ecologia", "Ecologia e diversidade", ["T10332"], "os", "sapos e lagartos", "da ecologia de anfíbios e répteis", "ecologia e diversidade de anfíbios e répteis"),
        ("tema.serpentes", "Serpentes e venenos", ["T11353"], "as", "serpentes", "das serpentes e seus venenos", "serpentes, venenos e acidentes ofídicos"),
        ("tema.canto_anuros", "Canto e comunicação", ["T11665"], "o", "canto dos sapos", "da comunicação acústica de anfíbios", "comunicação acústica e vocalização de anfíbios"),
    ],
    "sub.infeccoes": [
        ("tema.arboviroses", "Dengue, zika e chikungunya", ["T10166"], "a", "dengue", "das arboviroses", "dengue, zika, chikungunya e arboviroses"),
        ("tema.leishmaniose", "Leishmaniose", ["T10823"], "a", "leishmaniose", "da leishmaniose", "leishmaniose visceral e tegumentar"),
        ("tema.covid", "Covid-19", ["T10041", "T10118", "T11368"], "a", "covid", "da covid-19", "covid-19 e seus efeitos"),
        ("tema.hiv", "HIV e aids", ["T10082"], "o", "HIV", "do HIV e da aids", "HIV e aids"),
        ("tema.hanseniase", "Hanseníase", ["T12107"], "a", "hanseníase", "da hanseníase", "hanseníase"),
        ("tema.tuberculose", "Tuberculose", ["T10038"], "a", "tuberculose", "da tuberculose", "tuberculose"),
        ("tema.sifilis", "Sífilis e outras ISTs", ["T11934"], "a", "sífilis", "da sífilis e das ISTs", "sífilis e infecções sexualmente transmissíveis"),
    ],
    "sub.ingredientes": [
        ("tema.fitoquimicos", "Extratos e fitoquímicos", ["T12657"], "os", "extratos vegetais", "de extratos e fitoquímicos", "extratos vegetais e compostos fitoquímicos"),
        ("tema.polissacarideos", "Polissacarídeos e gomas", ["T12192"], "os", "polissacarídeos", "dos polissacarídeos e das gomas", "polissacarídeos e gomas naturais"),
        ("tema.antioxidantes", "Antioxidantes", ["T10035"], "os", "antioxidantes", "dos antioxidantes", "compostos antioxidantes"),
        ("tema.microencapsulacao", "Microencapsulação", ["T12048"], "a", "microencapsulação", "da microencapsulação", "microencapsulação de compostos"),
    ],
    "sub.insetos_div": [
        ("tema.ecologia_insetos", "Ecologia e comportamento", ["T10702"], "os", "insetos", "da ecologia de insetos", "ecologia e comportamento de insetos"),
        ("tema.besouros", "Besouros", ["T11494", "T13781"], "os", "besouros", "dos besouros", "taxonomia e distribuição de besouros"),
        ("tema.moscas", "Moscas e mosquitos (dípteros)", ["T12606"], "as", "moscas", "das moscas e dos dípteros", "taxonomia e comportamento de dípteros"),
        ("tema.formigas", "Formigas e vespas", ["T12132"], "as", "formigas", "de formigas e vespas", "formigas, vespas e himenópteros"),
        ("tema.inseto_planta", "Insetos e plantas", ["T10135"], "as", "interações inseto-planta", "das interações entre insetos e plantas", "interações entre insetos e plantas"),
    ],
    "sub.laticinios": [
        ("tema.probioticos_lact", "Queijos, iogurtes e probióticos", ["T10141"], "os", "queijos", "de queijos, iogurtes e probióticos", "queijos, iogurtes, kefir e probióticos"),
        ("tema.sensorial", "Fermentação e análise sensorial", ["T10750"], "o", "sabor", "da fermentação e da análise sensorial", "fermentação e análise sensorial de laticínios"),
        ("tema.qualidade_leite", "Qualidade do leite", ["T11226"], "o", "leite", "da qualidade do leite", "qualidade do leite"),
    ],
    "sub.mamiferos": [
        ("tema.morcegos", "Morcegos", ["T11228"], "os", "morcegos", "dos morcegos", "biologia e ecologia de morcegos"),
        ("tema.primatas", "Primatas", ["T10699"], "os", "macacos", "dos primatas", "comportamento e ecologia de primatas"),
        ("tema.canto_aves", "Canto e comunicação animal", ["T11665"], "o", "canto das aves", "da comunicação e do canto das aves", "comunicação acústica e canto de aves"),
        ("tema.comportamento_animal", "Comportamento e reprodução", ["T10174"], "o", "comportamento animal", "do comportamento animal", "comportamento e reprodução de animais silvestres"),
    ],
    "sub.marinha": [
        ("tema.pesca", "Pesca e recursos pesqueiros", ["T10230"], "a", "pesca", "da pesca e dos recursos pesqueiros", "pesca e recursos pesqueiros"),
        ("tema.algas", "Algas marinhas", ["T11390"], "as", "algas", "das algas marinhas", "algas marinhas e seus compostos"),
        ("tema.peixes_ecologia", "Ecologia de peixes", ["T12319"], "os", "peixes", "da ecologia de peixes", "biologia e ecologia de peixes"),
        ("tema.reproducao_marinha", "Reprodução de espécies aquáticas", ["T11505"], "a", "reprodução marinha", "da reprodução de espécies aquáticas", "reprodução de espécies aquáticas"),
    ],
    "sub.materno": [
        ("tema.parto", "Gestação, parto e recém-nascido", ["T10453", "T12741"], "o", "parto", "da gestação, do parto e do recém-nascido", "gestação, parto e cuidado neonatal"),
        ("tema.amamentacao", "Amamentação", ["T10979"], "a", "amamentação", "do aleitamento materno", "aleitamento materno"),
        ("tema.adolescentes", "Saúde sexual de adolescentes", ["T10327"], "os", "adolescentes", "da saúde sexual e reprodutiva de adolescentes", "saúde sexual e reprodutiva de adolescentes"),
        ("tema.sifilis_gestacao", "Sífilis na gestação", ["T11934"], "a", "sífilis", "da sífilis na gestação", "sífilis congênita e na gestação"),
        ("tema.autismo_infantil", "Autismo e desenvolvimento infantil", ["T10106"], "o", "autismo", "do autismo e do desenvolvimento infantil", "autismo e desenvolvimento infantil"),
    ],
    "sub.medicinais": [
        ("tema.fitoquimica", "Fitoquímica e farmacologia", ["T12657", "T14521", "T13090"], "a", "fitoquímica", "da fitoquímica de plantas medicinais", "fitoquímica e farmacologia de plantas medicinais"),
        ("tema.oleos", "Óleos essenciais", ["T10225"], "os", "óleos essenciais", "dos óleos essenciais", "óleos essenciais e atividade biológica"),
        ("tema.etnobotanica", "Etnobotânica", ["T10431"], "a", "etnobotânica", "da etnobotânica", "etnobotânica e uso popular de plantas"),
        ("tema.integrativas", "Práticas integrativas", ["T10902"], "as", "práticas integrativas", "das práticas integrativas e complementares", "práticas integrativas e complementares em saúde"),
        ("tema.inseticidas_botanicos", "Inseticidas naturais", ["T11065"], "os", "inseticidas naturais", "de inseticidas botânicos", "inseticidas botânicos e controle natural de pragas"),
    ],
    "sub.mente": [
        ("tema.autismo", "Autismo", ["T10106"], "o", "autismo", "do autismo", "transtorno do espectro autista"),
        ("tema.enxaqueca", "Enxaqueca e dor de cabeça", ["T10498"], "a", "enxaqueca", "da enxaqueca", "enxaqueca e cefaleias"),
        ("tema.parkinson", "Parkinson", ["T10085"], "o", "Parkinson", "da doença de Parkinson", "doença de Parkinson"),
        ("tema.demencia", "Demência e memória", ["T10009"], "a", "memória", "da demência e do declínio cognitivo", "demência e declínio cognitivo"),
        ("tema.avc", "AVC", ["T10227", "T10510"], "o", "AVC", "do AVC", "acidente vascular cerebral e reabilitação"),
        ("tema.estimulacao", "Estimulação cerebral", ["T10614"], "a", "estimulação cerebral", "da estimulação cerebral não invasiva", "estimulação magnética e elétrica transcraniana"),
        ("tema.drogas", "Álcool e outras drogas", ["T10043"], "as", "drogas", "do uso de álcool e outras drogas", "uso de álcool e outras drogas"),
    ],
    "sub.microbiota": [
        ("tema.probioticos", "Probióticos", ["T10141"], "os", "probióticos", "dos probióticos", "probióticos e alimentos fermentados"),
        ("tema.intestino", "Microbiota intestinal", ["T10066"], "o", "intestino", "da microbiota intestinal", "microbiota intestinal e saúde"),
        ("tema.microbiota_oral", "Microbiota oral", ["T10257"], "a", "microbiota oral", "da microbiota oral", "microbiota oral"),
    ],
    "sub.movimento": [
        ("tema.esporte", "Esporte e treinamento", ["T10157"], "o", "esporte", "do esporte e do treinamento", "desempenho esportivo e treinamento"),
        ("tema.quedas", "Equilíbrio e quedas", ["T10114"], "as", "quedas", "do equilíbrio e da prevenção de quedas", "equilíbrio, marcha e prevenção de quedas"),
        ("tema.dor", "Dor musculoesquelética", ["T10084"], "a", "dor nas costas", "da dor musculoesquelética", "dor musculoesquelética e reabilitação"),
        ("tema.voz", "Voz e fala", ["T10863"], "a", "voz", "da voz e da fala", "distúrbios da voz e da fala"),
        ("tema.audicao", "Audição", ["T10283"], "a", "audição", "da audição", "perda auditiva e reabilitação"),
        ("tema.atividade_fisica", "Atividade física e saúde", ["T10352"], "a", "atividade física", "da atividade física", "atividade física e saúde"),
    ],
    "sub.nativas": [
        ("tema.vegetacao_nativa", "Ecologia da vegetação", ["T12618"], "a", "vegetação nativa", "da vegetação nativa", "ecologia da vegetação nativa"),
        ("tema.taxonomia_nativas", "Taxonomia e evolução", ["T14049", "T10385"], "as", "espécies nativas", "da taxonomia de plantas nativas", "taxonomia e evolução de plantas nativas"),
        ("tema.sementes_nativas", "Sementes e germinação", ["T11098"], "as", "sementes", "das sementes nativas", "germinação de sementes nativas"),
        ("tema.florestas_nativas", "Florestas", ["T11880"], "as", "florestas", "das florestas nativas", "ecologia e manejo de florestas nativas"),
    ],
    "sub.nutricao": [
        ("tema.nutricao_idosos", "Nutrição na velhice", ["T10397"], "a", "nutrição na velhice", "da nutrição de idosos", "nutrição e saúde no envelhecimento"),
        ("tema.obesidade", "Obesidade", ["T10010"], "a", "obesidade", "da obesidade", "obesidade, atividade física e dieta"),
        ("tema.bariatrica", "Cirurgia bariátrica", ["T10569"], "a", "cirurgia bariátrica", "da cirurgia bariátrica", "cirurgia bariátrica e seus resultados"),
        ("tema.comportamento_alimentar", "Comportamento alimentar", ["T12873", "T12057"], "a", "alimentação", "do comportamento alimentar", "comportamento alimentar e rotulagem"),
        ("tema.composicao_corporal", "Composição corporal", ["T12279"], "o", "corpo", "da composição corporal", "avaliação da composição corporal"),
        ("tema.nutricao_clinica", "Nutrição clínica", ["T10858"], "a", "nutrição clínica", "da nutrição clínica", "nutrição clínica e gastroenterologia"),
    ],
    "sub.parasitos": [
        ("tema.leishmaniose2", "Leishmaniose", ["T10823"], "a", "leishmaniose", "da leishmaniose", "leishmaniose"),
        ("tema.chagas", "Doença de Chagas", ["T10890"], "a", "doença de Chagas", "da doença de Chagas", "doença de Chagas e Trypanosoma cruzi"),
        ("tema.helmintos", "Verminoses", ["T11074"], "as", "verminoses", "das helmintoses", "helmintoses e controle de vermes"),
        ("tema.toxoplasmose", "Toxoplasmose", ["T11155"], "a", "toxoplasmose", "da toxoplasmose", "toxoplasmose"),
        ("tema.leptospirose", "Leptospirose", ["T12223"], "a", "leptospirose", "da leptospirose", "leptospirose"),
    ],
    "sub.poluicao": [
        ("tema.agrotoxicos", "Agrotóxicos", ["T10875", "T11423"], "os", "agrotóxicos", "dos agrotóxicos", "exposição a agrotóxicos e resíduos"),
        ("tema.solo_contaminado", "Contaminação do solo", ["T13102"], "o", "solo contaminado", "da contaminação do solo", "contaminação ambiental do solo"),
        ("tema.contaminacao_alimentos", "Contaminação de alimentos", ["T11957"], "a", "segurança dos alimentos", "da contaminação de alimentos", "contaminação e segurança de alimentos"),
    ],
    "sub.pragas": [
        ("tema.controle_pragas", "Controle de pragas", ["T11065"], "as", "pragas", "do controle de pragas", "estratégias de controle de insetos-praga"),
        ("tema.inseto_planta2", "Interação inseto-planta", ["T10135"], "as", "plantas atacadas", "das interações entre insetos-praga e plantas", "interações entre insetos-praga e plantas"),
        ("tema.controle_biologico", "Controle biológico", ["T11436"], "o", "controle biológico", "do controle biológico", "controle biológico com fungos e bactérias entomopatogênicos"),
        ("tema.feromonios", "Comportamento e feromônios", ["T12043"], "os", "feromônios", "do comportamento de insetos-praga", "comportamento de insetos-praga e feromônios"),
        ("tema.inseticidas", "Inseticidas e resistência", ["T11641"], "os", "inseticidas", "dos inseticidas", "inseticidas e resistência de insetos"),
    ],
    "sub.solos": [
        ("tema.carbono_solo", "Carbono e nitrogênio", ["T10004"], "o", "carbono do solo", "do carbono e do nitrogênio no solo", "carbono e nitrogênio no solo"),
        ("tema.manejo_solo", "Manejo e adubação", ["T12792", "T12294"], "a", "adubação", "do manejo e da adubação do solo", "manejo do solo e adubação"),
        ("tema.microbios_solo", "Micróbios do solo", ["T10076"], "os", "micróbios do solo", "dos microrganismos do solo", "microrganismos do solo e plantas"),
        ("tema.nutricao_plantas", "Nutrição de plantas", ["T12113"], "a", "nutrição de plantas", "da nutrição de plantas", "nutrição mineral de plantas"),
    ],
    "sub.vetores": [
        ("tema.aedes", "Aedes e arboviroses", ["T10166", "T14053"], "o", "Aedes", "do Aedes e das arboviroses", "Aedes aegypti e arboviroses"),
        ("tema.barbeiros", "Barbeiros e Chagas", ["T10890"], "os", "barbeiros", "dos barbeiros", "barbeiros e doença de Chagas"),
        ("tema.flebotomineos", "Flebotomíneos e leishmaniose", ["T10823"], "os", "flebotomíneos", "dos flebotomíneos", "flebotomíneos e leishmaniose"),
        ("tema.controle_vetores", "Controle de vetores", ["T11065"], "o", "controle de vetores", "do controle de vetores", "controle de mosquitos e vetores"),
    ],
    "sub.virus": [
        ("tema.arbovirus", "Arbovírus", ["T10166"], "os", "arbovírus", "dos arbovírus", "dengue, zika e chikungunya"),
        ("tema.coronavirus", "Coronavírus", ["T10118", "T10041", "T11754"], "o", "coronavírus", "do coronavírus", "SARS-CoV-2 e covid-19"),
        ("tema.retrovirus", "HTLV e retrovírus", ["T12159"], "os", "retrovírus", "do HTLV e dos retrovírus", "HTLV e retrovírus"),
        ("tema.raiva", "Raiva", ["T11780"], "a", "raiva", "da raiva", "epidemiologia e controle da raiva"),
        ("tema.antivirais", "Antivirais", ["T10211"], "os", "antivirais", "de antivirais", "descoberta de fármacos antivirais"),
    ],
    # novos sub-objetos (lacunas da auditoria)
    "sub.cuidado": [
        ("tema.seguranca_paciente", "Segurança do paciente", ["T10508"], "a", "segurança do paciente", "da segurança do paciente", "segurança do paciente e erros de medicação"),
        ("tema.lesao_pressao", "Lesões por pressão e feridas", ["T11670"], "as", "feridas", "das lesões por pressão e feridas", "prevenção de lesões por pressão e cuidado de feridas"),
        ("tema.gestao_enfermagem", "Gestão e prática de enfermagem", ["T10186", "T14316", "T11816"], "a", "enfermagem", "da gestão e da prática de enfermagem", "gestão e prática de enfermagem"),
        ("tema.informacao_saude", "Prontuário e informação em saúde", ["T10350", "T12871"], "os", "prontuários", "da informação e da qualidade em saúde", "prontuário eletrônico e qualidade em saúde"),
    ],
    "sub.envelhecimento": [
        ("tema.cuidado_idoso", "Cuidado ao idoso", ["T10312"], "os", "idosos", "do cuidado ao idoso", "cuidado de enfermagem ao idoso"),
        ("tema.violencia_idoso", "Violência contra idosos", ["T12462"], "os", "direitos dos idosos", "da violência contra idosos", "violência e negligência contra idosos"),
        ("tema.nutricao_velhice", "Nutrição na velhice", ["T10397"], "a", "nutrição na velhice", "da nutrição no envelhecimento", "nutrição e saúde no envelhecimento"),
        ("tema.demencia_idoso", "Demência e memória", ["T10009"], "a", "memória", "da demência na velhice", "demência e declínio cognitivo em idosos"),
    ],
    "sub.formacao": [
        ("tema.ensino_saude", "Ensino de medicina e saúde", ["T12413"], "o", "ensino em saúde", "do ensino em saúde", "educação médica e ensino em saúde"),
        ("tema.interprofissional", "Educação interprofissional", ["T11497"], "o", "trabalho em equipe", "da educação interprofissional", "educação e colaboração interprofissional"),
        ("tema.educacao_saude", "Educação em saúde e materiais educativos", ["T13117"], "a", "educação em saúde", "da educação em saúde", "educação em saúde e validação de materiais educativos"),
        ("tema.tecnologia_saude", "Tecnologia e IA na saúde", ["T11636"], "a", "saúde digital", "da tecnologia e da IA na saúde", "inteligência artificial e tecnologia na saúde e no ensino"),
    ],
    "sub.trabalho": [
        ("tema.burnout", "Estresse e burnout", ["T12869", "T12704"], "o", "burnout", "do estresse e do burnout", "estresse ocupacional e burnout"),
        ("tema.profissionais_saude", "Saúde dos profissionais de saúde", ["T10795"], "os", "profissionais de saúde", "da saúde dos profissionais de saúde", "estresse e saúde de profissionais de saúde"),
        ("tema.seguranca_trabalho", "Segurança no trabalho", ["T13315", "T13233"], "a", "segurança no trabalho", "da segurança no trabalho", "saúde e segurança no trabalho"),
    ],
}

# novo objeto e seus sub-objetos (lacunas: ver auditoria, seção 3)
OBJ_SERVICOS = {"id": "objeto.servicos", "rotulo": "Cuidado, serviços e formação em saúde",
                "sinais": {"topics": ["T10508", "T10186", "T10312", "T12413", "T12869"], "termos": ["nursing", "enfermagem", "patient safety", "segurança do paciente", "health services", "serviços de saúde", "occupational health", "saúde do trabalhador"],
                           "frase": "enfermagem, serviços de saúde, formação e saúde do trabalhador"},
                "metodos": ["metodo.epidemio", "metodo.clinica", "metodo.dados", "metodo.campo"]}
SUBS_SERVICOS = [
    {"id": "sub.cuidado", "rotulo": "Enfermagem e segurança do paciente",
     "sinais": {"topics": ["T10508", "T10186", "T14316", "T11816", "T11670", "T12871", "T10350"], "termos": ["nursing", "enfermagem", "nurse", "enfermeir", "patient safety", "segurança do paciente", "pressure ulcer", "lesão por pressão"],
                "frase": "enfermagem, cuidado e segurança do paciente"}, "sintagma": {"artigo": "a", "nome": "enfermagem"}, "nicho": "da enfermagem e da segurança do paciente"},
    {"id": "sub.envelhecimento", "rotulo": "Envelhecimento e idosos",
     "sinais": {"topics": ["T10312", "T12462", "T10397"], "termos": ["elderly", "idoso", "aging", "envelhecimento", "older adults", "long-term care", "longa permanência"],
                "frase": "envelhecimento e saúde do idoso"}, "sintagma": {"artigo": "os", "nome": "idosos"}, "nicho": "do envelhecimento"},
    {"id": "sub.formacao", "rotulo": "Formação e educação em saúde",
     "sinais": {"topics": ["T12413", "T11497", "T13117", "T11636"], "termos": ["medical education", "educação em saúde", "health education", "nursing students", "estudantes de", "curriculum", "currículo", "simulação clínica", "clinical simulation"],
                "frase": "formação de profissionais e educação em saúde"}, "sintagma": {"artigo": "a", "nome": "formação em saúde"}, "nicho": "da formação em saúde"},
    {"id": "sub.trabalho", "rotulo": "Trabalho e saúde do trabalhador",
     "sinais": {"topics": ["T12869", "T10795", "T12704", "T13315", "T13233"], "termos": ["burnout", "occupational health", "saúde do trabalhador", "occupational", "ocupacional", "workers", "trabalhadores"],
                "frase": "saúde do trabalhador, estresse e burnout"}, "sintagma": {"artigo": "o", "nome": "trabalho"}, "nicho": "da saúde do trabalhador"},
]
MAR_TOPICOS = ["T10230", "T12319", "T11390", "T11088", "T11505"]


def main() -> int:
    a = json.loads(ARQ_ARVORE.read_text(encoding="utf-8"))
    P = a["perguntas"]
    # 1. novo objeto e sub-objetos
    if not any(o["id"] == OBJ_SERVICOS["id"] for o in P["objeto"]["opcoes"]):
        P["objeto"]["opcoes"].append(OBJ_SERVICOS)
    P["sub_objeto"]["opcoes_por"][OBJ_SERVICOS["id"]] = SUBS_SERVICOS
    # focos de saúde também valem para o novo objeto
    for o in P["foco"]["opcoes"]:
        if "objeto.humanos" in o.get("objetos", []) and OBJ_SERVICOS["id"] not in o["objetos"]:
            o["objetos"].append(OBJ_SERVICOS["id"])
    # 2. pergunta de tema
    subs = {s["id"] for g in P["sub_objeto"]["opcoes_por"].values() for s in g}
    faltam = sorted(set(TEMAS) - subs)
    if faltam:
        print(f"sub-objetos desconhecidos em TEMAS: {faltam}", file=sys.stderr)
        return 1
    P["tema"] = {
        "bloco": "nicho", "faceta": "tema", "texto": "Qual destes temas é mais o seu?", "depende_de": "sub_objeto",
        "opcoes_por": {sub: [{"id": i, "rotulo": r, "sinais": {"topics": tp, "frase": fr}, "sintagma": {"artigo": art, "nome": nome}, "nicho": nicho}
                             for i, r, tp, art, nome, nicho, fr in lista] for sub, lista in TEMAS.items()},
    }
    if "tema" not in a["telas"]:
        a["telas"].insert(a["telas"].index("sub_objeto") + 1, "tema")
    a["pesos_faceta"]["tema"] = 2.5
    # 3. ambiente "mar" com tópicos marinhos
    for o in P["ambiente"]["opcoes"]:
        if o["id"] == "ambiente.mar":
            o["sinais"]["topics"] = list(dict.fromkeys(o["sinais"].get("topics", []) + MAR_TOPICOS))
    a["versao"] = 6
    ARQ_ARVORE.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(v) for v in TEMAS.values())
    print(f"arvore.json versão 6: {n} temas em {len(TEMAS)} sub-objetos, objeto {OBJ_SERVICOS['id']} com {len(SUBS_SERVICOS)} sub-objetos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
