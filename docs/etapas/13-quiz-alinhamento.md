# Etapa 13 — Quiz "Que cientista é você?" e alinhamento a pesquisadores do Nordeste

**Status:** em construção (estrutura, match e rascunho dos banners prontos; cadastro e interface em andamento) · **Branch:** `quiz`
**Código até agora:** `apps/web/lib/quiz/arvore.json` (v1), `ingest/carga/validar_arvore_quiz.py`
**Decisões:** D-036 (quiz), D-037 (cadastro dos participantes), D-038 (FUNED fora da base)

## Objetivo

Um quiz de múltipla escolha, pensado para o celular, que termina com **dois banners para compartilhar**:

1. **"Que cientista você é"**: um **título descontraído** (ex.: "Magia dos dados", "Fominha de bancada", "Fã nº 1 dos insetos"), sempre em forma neutra, e o **nicho científico** da pessoa (ex.: "Bioinformática de vírus de plantas"). Por enquanto o visual usa só cores e elementos simples, sem ilustração.
2. **"Seus 5 pesquisadores de afinidade no Nordeste"**: os mais alinhados ao nicho, **de fora da instituição da pessoa** e das ligadas a ela, num mini mapa do NE.

Antes das perguntas, a pessoa faz um **cadastro curto** (D-037), que fica numa tabela própria com consentimento explícito. O resultado é calculado no servidor a partir dos ids das respostas, e as respostas não são gravadas.

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
| 1 | Cadastro | **Quem é você?** nome completo · instituição por extenso (sugestões da base) · tipo de filiação · e-mail (opcional) · curso ou programa (sugestões dos programas da base) · consentimento | ver "Cadastro" | a instituição, quando casada com a base, exclui os colegas do resultado; o resto só vai para `quiz_participantes` |
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

## Implementação do match (passo 2)

**Banco (migração `0012_quiz_perfis`):**
- `researcher_embeddings`: perfil temático de **35.806 pesquisadores** (todos os ativos, com 3 ou mais publicações; média de 8 publicações por perfil), índice HNSW por cosseno.
  - Calculado por `ingest/sql/perfis_tematicos.sql` em cerca de 70 s, idempotente.
  - O pgvector 0.8.6 soma e tira média de `halfvec`, mas não multiplica por escalar. A soma ponderada é feita em `vector`, com um vetor de pesos.
  - Peso de cada publicação = recência (1,0 no último ano, −0,1 por ano) × autoria (1,0 como primeiro, último ou correspondente; 0,6 no meio) × equipe (1,0 até 10 autores; √(10/n) acima).
- `quiz_sinal` e `quiz_opcao_work`: os sinais de cada opção de nicho e quanto cada publicação casa cada opção. São 710 mil pares, pré-calculados por `python3 -m ingest.carga.quiz_preparar` em cerca de 20 s.
  - O script é só biblioteca padrão + psql, então roda no servidor.
  - É chamado pelo `carregar_banco.sh` e pelo `publicar.sh` quando o `arvore.json` muda.
- `quiz_meta`: a versão da estrutura carregada.

**App:**
- `lib/quiz/estrutura.ts` interpreta as respostas e recusa ids desconhecidos ou incoerentes (ex.: um sub-objeto de outro objeto, um método não oferecido para o objeto).
- `lib/quiz/alinhamento.ts` faz o match, só com as facetas de nicho.
- `POST /api/quiz/resultado` não grava nada e responde com `cache-control: no-store`.

**Índice de compatibilidade (0–100)** = 100 × (0,30 cobertura + 0,20 concentração + 0,20 volume + 0,30 afinidade):
- **cobertura:** para cada faceta respondida fora do núcleo, a fração das publicações do nicho que a casa, ponderada pelo peso da faceta;
- **concentração:** publicações no nicho ÷ produção no recorte, cheia a partir de 50%;
- **volume:** ln(1 + publicações no nicho) ÷ ln(16), cheio a partir de 15;
- **afinidade:** cosseno do perfil com a frase do nicho, posicionado entre os percentis 90 (0) e 99,9 (1) da população inteira para aquela frase. Os cossenos do e5 ficam espremidos entre 0,84 e 0,91, e o percentil puro dava quase 1 a qualquer candidato.

Sem o serviço `embed`, os outros três componentes se renormalizam. Para entrar, o pesquisador precisa de 2 ou mais publicações no núcleo e índice de pelo menos 35. A proeminência (produção, h-index, docência, PQ) só soma até 3 pontos **na ordem**, nunca no índice. No banner entram no máximo 2 pesquisadores por instituição; na lista, 3.

**Avaliação** (`python -m ingest.carga.avaliar_quiz`, 15 caminhos × instituição, filtro Qualis ligado; relatório em `ingest/relatorios/avaliacao_quiz.md`):

| Item | Resultado |
|---|---|
| Exclusão da instituição e das ligadas | ok nos 15 |
| Máximo por instituição no banner | 2 |
| Separação perfil × match (mesmos nomes, ordem e índices) | ok nos 15 |
| Coerência temática (exemplo com termo esperado) | média 89%, mínima 60% |
| Índice do 1º do banner | mediana 78 (de 56 a 99) |
| Índice do 5º do banner | mediana 71 (de 53 a 97) |
| Latência no servidor | mediana 400 ms; 4 nichos muito amplos entre 1,1 e 2,1 s |

**Problemas de desempenho resolvidos:**
- **exclusões:** a visão de vínculos era recalculada para cada candidato. Agora a lista de instituições excluídas é calculada antes.
- **similaridade:** os percentis da população eram refeitos por candidato. Agora as âncoras saem numa consulta à parte (~100 ms).
- **filtro Qualis:** o `EXISTS` linha a linha virou um `JOIN`.
- **cobertura:** a agregação era refeita por candidato. Agora é materializada.

**Pendências do match:**
- latência dos nichos muito amplos (Epidemiologia × infecções, Química × plantas medicinais, Clínica × boca e dentes, Clínica × movimento), com cerca de 27 mil publicações no nicho;
- a primeira chamada depois de reiniciar o app leva 1 a 2 s, porque aquece o modelo.

## Cadastro dos participantes (D-037)

A primeira tela do quiz é um formulário curto, pensado para o celular:

| Campo | Obrigatório | Como |
|---|---|---|
| Nome completo | sim | texto (2 a 120 caracteres) |
| Instituição | sim | texto por extenso, com sugestões das instituições do NE da base (`/api/quiz/instituicoes`). Escolhendo uma sugestão, grava-se também o id. Sem sugestão, vale o texto livre. |
| Tipo de filiação | sim | graduação · mestrado · doutorado · docente · pesquisador(a) · profissional do mercado |
| E-mail | não | validado; usado só para contato sobre o projeto |
| Curso ou programa | sim | para mestrado, doutorado, docente e pesquisador(a): sugestões dos programas de pós da base (`/api/quiz/programas`), priorizando os da instituição escolhida; para graduação e profissional do mercado: texto livre |
| Consentimento | sim | caixa não marcada por padrão, com a finalidade escrita e um link para `/sobre#privacidade-quiz` |

**Armazenamento** (migração `0014_quiz_participantes`):
- **Tabela `quiz_participantes`:** id, data, nome, instituição (id e texto), filiação, e-mail, programa (id e texto), versão do consentimento e versão da estrutura do quiz.
- **Papel `quiz_escrita`:** só `INSERT` na tabela. O app usa `DATABASE_URL_QUIZ` com esse papel. A senha vem de `QUIZ_DB_PASSWORD` no `.env` e é aplicada pelo `scripts/migrar.sh`.
- **O app nunca lê a tabela.**
- **Retenção de 24 meses** (expurgo automático).
- **Não se grava:** IP, navegador, respostas do quiz, resultado.

Se o cadastro falhar no servidor (banco fora do ar, papel não configurado), a pessoa vê um aviso e pode tentar de novo. O quiz não segue sem o cadastro, porque esse é o pedido do responsável.

## Cartões dos banners (neo-brutalismo do site)

Os cartões dos pesquisadores no banner de afinidades ganham um layout mais criativo, ainda só com cores e formas:
- **posição como selo:** um número grande num quadrado inclinado na cor de acento, com borda e sombra dura;
- **cartões levemente rotacionados**, alternando −1,5° e +1,5°, como figurinhas coladas;
- **índice num "ticket":** caixa lima com borda grossa, separada do cartão;
- **barra de compatibilidade em blocos** (10 segmentos), à maneira de um medidor;
- iniciais num círculo com contorno e sombra dura.

## Privacidade

- As respostas do quiz e o resultado não são gravados. As URLs de resultado e dos banners levam só ids de opções e da instituição, e o servidor recalcula tudo.
- O cadastro segue a D-037: consentimento, mínimo necessário, papel só de escrita, retenção de 24 meses e pedidos de remoção pelo contato de `/sobre`.

## Pendências desta etapa

- [x] Estrutura v2 por facetas, validada (280 pares)
- [x] Migração `0012`, perfis temáticos, match e avaliação
- [x] Rascunho dos banners com cores e formas
- [ ] FUNED fora da base (D-038) e lista de bloqueio na ingestão
- [ ] Cadastro dos participantes (D-037): migração `0014`, papel só de escrita, APIs de sugestões e de cadastro
- [ ] Cartões neo-brutalistas nos banners
- [ ] Interface do quiz (`/quiz`: cadastro, perguntas com barra de progresso, voltar pelo histórico) e página de resultado com compartilhamento
- [ ] Fontes do site nos banners (Lexend e DM Sans em `.ttf`; aguardando autorização para baixar)
- [ ] Nova tela inicial e painel (seção 6 do pedido original)
- [ ] Atualizar o `SCHEME.md` e o `README.md` com os números finais
