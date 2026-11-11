# Etapa 13 — Quiz "Que cientista é você?" e alinhamento a pesquisadores do Nordeste

**Status:** em desenho (aguardando aprovação da estrutura v2) · **Branch:** `quiz`
**Código até agora:** `apps/web/lib/quiz/arvore.json` (v1), `ingest/carga/validar_arvore_quiz.py`
**Decisão:** D-036 (a registrar quando a estrutura for aprovada)

## Objetivo

Um quiz de múltipla escolha, pensado para o celular, que termina com **dois banners para compartilhar**:

1. **"Que cientista você é"**: um **título descontraído** (ex.: "Magia dos dados", "Fominha de bancada", "Fã nº 1 dos insetos"), sempre em forma neutra, e o **nicho científico** da pessoa (ex.: "Bioinformática de vírus de plantas"). Por enquanto o visual usa só cores e elementos simples, sem ilustração.
2. **"Seus 5 pesquisadores de afinidade no Nordeste"**: os mais alinhados ao nicho, **de fora da instituição da pessoa** e das ligadas a ela, num mini mapa do NE.

A única entrada de texto é a instituição. O resultado é calculado no servidor a partir dos ids das respostas; nada é gravado (D-022, LGPD).

## Histórico do desenho

### v1 — árvore de decisão (validada, substituída)

Primeira proposta: uma árvore de 3 ou 4 perguntas (modo de trabalho → objeto → grupo ou foco), com 29 perguntas e 230 caminhos.

Para validá-la contra o banco, o encaixe de cada pesquisador foi calculado assim:
- **Ativos:** só entram pesquisadores com 3 ou mais publicações no período (35.806 no recorte).
- **Termos:** casam no início de uma palavra.
- **Folha:** um pesquisador entra numa folha com 2 ou mais publicações que casam as duas últimas respostas ao mesmo tempo.

Resultado da validação:
- 0 ids inexistentes;
- 0 folhas com menos de 15 pesquisadores sem a maior instituição do tema;
- 0 pares de folhas irmãs com Jaccard dos top 10 acima de 0,5 (máximo 0,43).

Relatórios em `ingest/relatorios/quiz_levantamento.md` e `quiz_validacao.md`, fora do git.

Lições da v1, que valem para a v2:
- **O modo de trabalho não existe no banco.** Ele vira tópicos típicos, termos no título (as palavras-chave do OpenAlex descrevem o conteúdo, não o método) e a frase do vetor.
- **Termos casam só no início de palavra.** Sem isso, `app` casa com "approach" e `ave` com "have".
- **O encaixe exige combinação de respostas, não respostas isoladas.** Uma resposta ampla ("Saúde humana") sozinha devolve milhares de pessoas e não distingue nada.
- **Perguntas que não distinguem aparecem na validação** (Jaccard alto entre irmãs) e devem ser fundidas ou trocadas.

### v2 — nichos por combinação de facetas (proposta atual)

Pedido do responsável: chegar a **nichos mais específicos** com **10 a 12 perguntas** e barra de progresso, combinando **metodologia × objeto de estudo** (ex.: Bioinformática + vírus/plantas/humanos; Genética + vegetal/animal/humana). Também pediu **títulos descontraídos por combinação**, definidos por 2 ou 3 perguntas de perfil pessoal.

A árvore deixa de ser uma árvore pura e passa a ser uma **sequência fixa de facetas**. Algumas facetas mostram opções que dependem de respostas anteriores. O número de perguntas é sempre o mesmo, o que deixa a barra de progresso exata.

## Estrutura v2

### As 11 telas

| # | Bloco | Pergunta | Opções (resumo) | Para que serve |
|---|---|---|---|---|
| 1 | — | **Sua instituição** (autocomplete) | instituições do NE · "outra / sem vínculo" | exclusões e distância |
| 2 | Perfil | **Num dia perfeito de trabalho, onde você está?** | no campo, de botas · na bancada, de jaleco · no computador, entre códigos e planilhas · com pessoas (pacientes, comunidades) · entre coleções, acervos e artigos | **habitat** do título (não entra no match) |
| 3 | Nicho | **Qual é a sua ferramenta principal?** | campo e observação · experimentos de bancada · genética e biologia molecular · bioinformática e genômica · estatística, modelos e IA · química e compostos · clínica e intervenções · epidemiologia e saúde coletiva | faceta **método** (núcleo) |
| 4 | Nicho | **O que você estuda?** | plantas · insetos e outros invertebrados · animais de produção · fauna silvestre e ecossistemas · microrganismos e parasitos · seres humanos · alimentos · solo, água e clima | faceta **objeto** |
| 5 | Nicho | **Mais especificamente?** (depende da 4) | ex.: microrganismos → vírus · bactérias · fungos · parasitos · microbiota; plantas → frutíferas e hortaliças · grãos e grandes culturas · forrageiras · nativas · medicinais; humanos → coração e metabolismo · cérebro e mente · infecções · câncer e sangue · mulher e criança · boca e dentes · movimento e reabilitação | faceta **sub-objeto** (núcleo) |
| 6 | Perfil | **Quando aparece um problema novo, você…** | testa uma hipótese na hora · junta todos os dados primeiro · monta um modelo · chama gente para pensar junto · vai atrás do que ninguém viu | **estilo** do título (não entra no match) |
| 7 | Nicho | **Qual é o seu foco?** (opções filtradas pelo objeto) | melhoramento e genética · doenças e pragas · manejo e produção · produtos e compostos · diversidade e conservação · diagnóstico e tratamento · prevenção e vigilância | faceta **foco** |
| 8 | Nicho | **Em que escala?** | moléculas e genes · células e tecidos · organismos inteiros · populações e comunidades · paisagens e ecossistemas | faceta **escala** |
| 9 | Nicho | **Onde o seu objeto vive ou acontece?** | caatinga e semiárido · mata atlântica e brejos · mar, mangues e estuários · lavouras e fazendas · cidades, hospitais e serviços · tanto faz | faceta **ambiente** (o sabor do Nordeste) |
| 10 | Perfil | **O seu objeto de estudo é…** | minha paixão, falo dele até em festas · um mistério que quero desvendar · algo que preciso proteger · uma ferramenta para resolver problemas reais | **vínculo** do título (não entra no match) |
| 11 | Nicho | **O seu trabalho serve principalmente para…** | produzir alimento melhor · cuidar da saúde das pessoas · conservar a natureza · criar produtos e tecnologias · entender como a vida funciona | faceta **impacto** |

- **Toda pergunta tem "Nenhuma dessas / prefiro pular".** A faceta pulada simplesmente não entra no cálculo, e o quiz segue.
- **As perguntas de perfil (2, 6 e 10) ficam intercaladas** com as de nicho, para quebrar a sequência técnica e manter o tom de jogo. A primeira tela depois da instituição já é divertida.
- **Até 8 opções por tela**, em grade de 2 colunas no celular, com cartões de pelo menos 48 px de altura. Assim cabe a lista de métodos sem rolagem.
- **Cliques:** 11 no máximo, contando a instituição.

### Dois processos separados: o match e o banner

O resultado sai de **dois processos independentes**, que só compartilham as respostas de entrada:

```
respostas ─┬─► MATCH  (só as facetas de nicho: telas 3, 4, 5, 7, 8, 9 e 11 + instituição)
           │      └─► até 5 pesquisadores, cada um com um índice de compatibilidade
           │
           └─► BANNER (título, nicho escrito e arte: telas de perfil 2, 6, 10 e 12 + os rótulos das facetas)
                  └─► texto e camadas de arte; nunca altera quem aparece nem a ordem
```

- **O match não lê** habitat, estilo nem vínculo. Duas pessoas com as mesmas respostas de nicho recebem **os mesmos pesquisadores, na mesma ordem e com os mesmos índices**, qualquer que seja o título.
- **O banner não influencia o match.** Ele recebe a lista pronta e só a desenha. O título e a frase do nicho são montados a partir dos rótulos e dos sintagmas das opções, não do resultado.
- No código, são módulos separados: `lib/quiz/alinhamento.ts` (match) e `lib/quiz/titulo.ts` (título e nicho escrito). A camada de arte vive com o banner. Um teste garante que mudar só as respostas de perfil não muda a saída do match.

### O match

**Nichos específicos de propósito.** O nicho é a combinação das facetas respondidas. Cada opção de nicho traz `sinais` no formato da v1: `topics`, `subfields`, `fields`, `termos` e `frase`.

| Método | × Sub-objeto | × Foco/escala/ambiente | Nicho |
|---|---|---|---|
| Bioinformática e genômica | vírus | plantas · caatinga | Bioinformática de vírus de plantas da caatinga |
| Genética e biologia molecular | caprinos e ovinos | melhoramento | Genética e melhoramento de caprinos |
| Campo e observação | anfíbios e répteis | diversidade · mata atlântica | Ecologia de anfíbios da mata atlântica |
| Química e compostos | plantas medicinais | produtos | Química de produtos naturais de plantas medicinais |
| Epidemiologia | infecções | vigilância · cidades | Vigilância de doenças infecciosas urbanas |

**Encaixe de um pesquisador.** Uma publicação casa uma faceta se casa algum sinal dela. O peso de cada faceta reflete a especificidade: método e sub-objeto, mais altos; foco, escala, ambiente e impacto, mais baixos. O encaixe soma as facetas casadas em cada publicação.

**Afinidade temática.** O texto da consulta vetorial junta as `frase`s das facetas respondidas (ex.: "bioinformática, genomas e sequenciamento · vírus · plantas da caatinga"). Ele é comparado com o perfil temático do pesquisador (`researcher_embeddings`, migração `0012`).

**Quem entra.** O pesquisador precisa de pelo menos **2 publicações que casem método e sub-objeto juntos**, e a combinação de encaixe e afinidade precisa passar de um mínimo de compatibilidade. **Não há relaxamento:** o nicho não é alargado para completar a lista. Por isso o banner mostra **até 5** pesquisadores. Num nicho raro podem vir menos, e o banner diz isso ("3 pesquisadores no seu nicho no Nordeste"). Se não houver nenhum, a tela de resultado sugere pular uma das facetas mais estreitas e refazer.

**Índice de compatibilidade (0–100).** Ele é calculado com uma escala fixa, não em relação ao primeiro colocado, para que os números signifiquem a mesma coisa em qualquer nicho e não apareça 99% para todo mundo. Entram:
- a **fração das facetas respondidas** que o pesquisador cobre;
- a **concentração** das publicações dele no nicho (encaixe ÷ produção);
- a **similaridade vetorial** do perfil temático, convertida em percentil da distribuição real de similaridades.

Os pesos e a fórmula ficam no topo de `lib/quiz/alinhamento.ts`, e a calibração é feita no script de avaliação, com caminhos fictícios. A proeminência (produção, h-index, docência na pós, PQ, Qualis) **não entra no índice**. Ela só desempata a ordem entre índices iguais e decide quem são os "principais" na lista estendida.

**Exclusões, distância e diversidade** seguem o pedido original:
- fora a instituição do usuário e as ligadas a ela;
- perfis ocultos ficam de fora;
- filtro opcional de distância só na página de resultado;
- no máximo 2 pesquisadores por instituição entre os 5;
- respeita o filtro "só revistas com Qualis" (D-035);
- se o serviço `embed` cair, segue só com o encaixe.

### O banner: títulos por combinação

Processo só de apresentação. O título principal sai das três perguntas de perfil; o nicho escrito (a partir dos rótulos das facetas) vira a segunda linha. Nada daqui volta para o match.

**1. Arquétipo = habitat (tela 2) × estilo (tela 6), uma matriz de 5 × 5 = 25 títulos.** Exemplos:

| habitat \ estilo | testa na hora | junta os dados | monta um modelo | chama gente | vai atrás do inédito |
|---|---|---|---|---|---|
| campo | Faz-tudo de campo | Mochila cheia de amostras | Estrategista de campo | Mutirão em pessoa | **Desbrava-trilhas** |
| bancada | **Fominha de bancada** | Caderno de protocolos ambulante | Engenharia de bancada | Alma do laboratório | Caça-moléculas |
| computador | Hacker de hipóteses | Garimpo de dados | **Magia dos dados** | Ponte entre dados e gente | Radar de padrões |
| pessoas | Plantonista de ideias | Escuta da comunidade | Estrategista do cuidado | **Elo da comunidade** | Sentinela da saúde |
| coleções | Curadoria inquieta | Arquivo vivo | Mapa-múndi das espécies | Biblioteca ambulante | Caça-raridades |

**2. Vínculo (tela 10) decide se o título fala do objeto.**

| Vínculo | Título principal | Exemplos |
|---|---|---|
| paixão | **Fã nº 1 d{objeto}** | Fã nº 1 dos insetos · Fã nº 1 das bactérias · Fã nº 1 dos caprinos |
| mistério | **Detetive d{objeto}** | Detetive dos vírus · Detetive do cérebro |
| proteger | **Sentinela d{ambiente ou objeto}** | Sentinela da caatinga · Sentinela dos mangues |
| ferramenta | **o arquétipo** | Magia dos dados · Fominha de bancada |

Quando o vínculo usa o objeto, o arquétipo desce para a segunda linha, junto com o nicho:

> **Fã nº 1 dos insetos**
> Fominha de bancada · Genética de abelhas da caatinga

Cada sub-objeto e cada ambiente traz o seu sintagma com artigo, para o texto sair correto: `{"artigo": "os", "nome": "insetos"}`, `{"artigo": "a", "nome": "caatinga"}`.

**Quantos títulos:** 25 arquétipos + 3 vínculos × cerca de 45 objetos e ambientes ≈ **160 títulos principais**. Combinados com os nichos, dão milhares de banners diferentes.

**Sempre neutros (decisão do responsável).** Não há forma feminina ou masculina, nem pergunta sobre isso. Os títulos usam só:
- substantivos comuns de dois gêneros (Fã, Detetive, Sentinela, Fominha, Estrategista, Hacker, Plantonista, Faz-tudo);
- compostos invariáveis (Caça-moléculas, Desbrava-trilhas);
- epítetos que descrevem a pessoa sem marcar gênero (Magia dos dados, Alma do laboratório, Arquivo vivo).

Nenhum adjetivo com flexão de gênero e nenhum "(a)". **Nenhum nome licenciado** (personagens, marcas, obras): o validador recusa uma lista de nomes proibidos e as marcas de gênero.

### Visual (por enquanto, sem ilustração)

Decisão do responsável: **nada de arte em SVG nesta fase**, para não gastar esforço antes da hora. Os banners usam só **cores e elementos simples**:
- **cor de fundo pelo habitat** (campo, bancada, computador, pessoas, coleções), a partir dos tokens do site (tema claro, paleta Azul, D-031 e D-034);
- **cor de acento pelo ambiente** (caatinga, mata atlântica, mar, lavouras, cidades);
- **formas geométricas básicas:** faixas, círculos e cartões, com bordas e sombra dura da estética do site;
- o título e o nicho em tipografia grande (Lexend);
- as iniciais dos pesquisadores em círculos e um mini mapa do NE com os pontos, reaproveitando a geometria do site.

Cada opção de perfil e de ambiente guarda só a **chave de cor** (`visual.cor`), não desenhos. Uma ilustração em camadas pode entrar depois, como evolução, sem mudar o match.

### Validação da v2

As combinações completas são milhões, então não dá para percorrer todas, como na v1. O validador (`validar_arvore_quiz.py banco`) passa a checar:

1. **Ids:** todo id de topic, subfield e field existe.
2. **Núcleo:** quantos pesquisadores cada par **método × sub-objeto** tem sem a maior instituição. Pares vazios indicam combinações que a pergunta não deveria oferecer (ou que precisam de sinais melhores); pares com menos de 5 são listados para revisão, já que o banner mostra "até 5".
3. **Amostra:** em 1.000 combinações completas sorteadas, mede a distribuição de quantos pesquisadores aparecem (0 a 5) e do índice de compatibilidade do primeiro e do quinto.
4. **Distinção:** dentro de um mesmo método, os top 10 de sub-objetos irmãos têm Jaccard menor que 0,5. O mesmo vale para métodos irmãos com o mesmo sub-objeto.
5. **Separação:** trocar só as respostas de perfil não muda nenhum resultado do match.
6. **Títulos:** todas as combinações de habitat × estilo × vínculo × objeto geram um título neutro (sem "(a)", sem palavras marcadas como de gênero e sem nomes licenciados), que cabe no banner.

A checagem estática continua no `scripts/verificar.sh`. Ela confere estrutura, ids, opções por tela (por objeto, quando filtradas) e sintagmas. Também confere os títulos (completos, neutros, sem nomes licenciados, até 42 caracteres) e que as perguntas de perfil não têm sinais de match.

**Filtros por método (versão 4, pedido do responsável):** cada objeto lista os métodos que fazem sentido para ele (`metodos`); por exemplo, Campo não oferece Saúde humana nem Alimentos, e Clínica só oferece humanos, animais de produção, microrganismos e alimentos. Os pares sem nenhum pesquisador saem (`sem_metodos` no sub-objeto; hoje, Estatística e IA × Cavalos). Resultado: **280 pares**, 0 vazios, 15 raros (1 a 4 pesquisadores), mediana de 83 por par, Jaccard máximo entre sub-objetos irmãos de 0,43 — **validação OK**.

**Primeira validação da v2** (`arvore.json` versão 3, antes dos filtros):

| Item | Resultado |
|---|---|
| Telas | 11, contando a instituição |
| Sub-objetos | 42 |
| Pares do núcleo (método × sub-objeto) | 336 |
| Títulos principais | 115 |
| ids inexistentes | 0 |
| Pesquisadores por par, sem a maior instituição | mediana 74 (mínimo 0, máximo 3.700) |
| Pares vazios | 1 (Estatística, modelos e IA × Cavalos) |
| Pares com 1 a 4 pesquisadores | 20 (ex.: Bioinformática × Plantas medicinais, Clínica × Aranhas e ácaros) |
| Sub-objetos irmãos com Jaccard > 0,5 | 1 (Campo × Grãos e farinhas vs. Campo × Ingredientes funcionais: 0,54; 22 e 18 pesquisadores) |
| Métodos diferentes no mesmo sub-objeto | Jaccard mediano 0,00, máximo 0,64 (só aviso: Genética e Bioinformática se sobrepõem em bovinos, por exemplo) |

Ajustes feitos durante a validação:
- um foco novo, "Monitoramento e mapeamento", porque Solo, água e clima tinha um foco só;
- sinais mais específicos para farinhas e para ingredientes funcionais;
- a ordem do encaixe passou a usar **só as publicações do nicho** (que casam método e sub-objeto), e não toda a produção do pesquisador naquela área. É também o que o match vai usar.

## Privacidade

- Nada é gravado na primeira versão.
- A URL do resultado leva só ids de opções e o id da instituição, e o servidor recalcula tudo.
- Se valer guardar contagens anônimas por ramo, isso será proposto antes, com consentimento, sem instituição, tabela própria, papel só com `INSERT` e prazo de retenção.

## Pendências desta etapa

- Aprovação da estrutura v2 (perguntas, títulos e formas).
- Migração `0012` (`researcher_embeddings`), API de resultado, ranking e script de avaliação.
- Visual dos banners com cores e formas simples (2 ou 3 rascunhos para aprovação).
- Banners (1080 × 1920 e 1080 × 1350), quiz, página de resultado e nova tela inicial com o painel.
- Decisão D-036 e atualização do `SCHEME.md`.
