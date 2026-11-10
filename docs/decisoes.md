# Registro de decisões técnicas

Formato: cada decisão tem um ID, data, contexto, decisão e consequências. Decisões novas vão no fim.

---

## D-001 — Escopo da camada de dados: Brasil inteiro, produção desde `YEAR_START`

- **Data:** 2026-11-09
- **Contexto:** o SCHEME.md propõe começar pela Bahia. Para a etapa de dados, o objetivo passou a ser mapear todo o Brasil, com produção de `YEAR_START` (padrão 2020) até o ano atual.
- **Decisão:** a ingestão é parametrizada por `YEAR_START` (.env ou `--year-start`) e cobre instituições brasileiras de todo o país. O recorte regional pode ser aplicado depois, na aplicação.
- **Consequências:** volumes maiores (ver `ingest/relatorios/diagnostico_fontes.md`). O SCHEME.md (§3.4, §7) precisa ser atualizado para refletir o novo escopo quando a Fase 1 começar.

## D-002 — Só fontes abertas; sem Lattes e sem Google Acadêmico

- **Data:** 2026-11-09
- **Decisão:** nada de scraping da Plataforma Lattes, do DGP (dgp.cnpq.br) ou do Google Acadêmico. Lattes e Scholar só entram como identificador informado pelo próprio pesquisador (`researcher_identifiers.scheme in ('lattes','scholar_url')`).
- **Consequências:** grupos de pesquisa e bolsistas PQ completos dependem de pedido LAI ou acordo com o CNPq (ver D-007).

## D-003 — robots.txt × APIs oficiais documentadas

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Contexto:** os robots.txt de `pub.orcid.org` (`Disallow: /`) e `query.wikidata.org` (`Disallow: /sparql`) bloqueiam robôs, mas são APIs oficiais documentadas para uso programático, com termos próprios. O robots.txt de `servicodados.ibge.gov.br` não responde (timeout), o que pela RFC 9309 equivale a bloqueio total.
- **Decisão:** o cliente HTTP (`ingest/diagnostico/http.py`) respeita robots.txt em tudo, **exceto** nos hosts listados em `EXCECOES_ROBOTS` (`ingest/diagnostico/config.py`), cada um com justificativa e link para os termos da API: `pub.orcid.org`, `query.wikidata.org`, `commons.wikimedia.org` (API MediaWiki) e `servicodados.ibge.gov.br`. Nesses hosts seguimos os termos da própria API (limite de taxa, User-Agent identificado, chamadas seriais).
- **Onde há rota permitida, ela é usada:** CAPES (`/api/` bloqueado, `Crawl-delay: 10`) → lemos a página HTML do conjunto + HEAD/Range nos arquivos, com 10 s entre chamadas; Zenodo (`/api` bloqueado) → DOI-conceito + `/records/{id}/export/json` + download do arquivo.
- **Consequências:** qualquer host novo bloqueado no robots.txt precisa de decisão explícita antes de entrar na lista de exceções.

## D-004 — Cliente HTTP comum com cache, retry, limite de tamanho e certificados do sistema

- **Data:** 2026-11-09
- **Decisão:** todas as chamadas passam por `ClienteHttp`: cache em disco (`ingest/.cache/`, chave = método + URL sem `api_key` + Range), intervalo mínimo por host (o maior entre a configuração e o `Crawl-delay`), retry com backoff exponencial (até 5 tentativas; respeita `Retry-After`; desiste se `Retry-After` > 120 s, que indica cota diária esgotada), timeout de 45 s, trava de 50 MB por download nesta parte. A verificação TLS usa o repositório de certificados do sistema (`truststore`), porque sites gov.br (ex.: `download.inep.gov.br`) não validam com o bundle do certifi. A verificação nunca é desligada.
- **Consequências:** quem rodar em Linux/Docker precisa dos certificados de CA do sistema instalados (`ca-certificates`).

## D-005 — Diagnóstico sem baixar bases completas

- **Data:** 2026-11-09
- **Decisão:** a Parte 0 usa só contagens (`per_page=1` + `meta.count`, `group_by`), HEAD, manifests do S3, a página/export dos repositórios e leituras parciais: diretório central de ZIPs remotos e primeiros 256 KB de CSVs (via `Range`), com descompressão parcial de entradas do ZIP para ler o cabeçalho do CSV. O datastore CKAN da CAPES tem só uma prévia de 1.000 linhas, então o número de linhas é **estimado** pelo tamanho do arquivo ÷ bytes médios por linha na amostra.
- **Servidor que ignora Range:** parte dos arquivos da CAPES responde `200` com o arquivo inteiro a um pedido `Range: bytes=0-N`. Nesse caso o cliente lê só os N bytes pedidos e fecha a conexão (sem baixar o resto). Range de sufixo ignorado gera erro.
- **Consequências:** contagens da CAPES e do INEP são aproximadas (erro típico < 10%); as partes seguintes calculam os números exatos.

## D-006 — OpenAlex: API com chave para o recorte BR; snapshot como plano B

- **Data:** 2026-11-09
- **Contexto (documentação conferida em 2026-11-09):** list+filter e group_by custam 1 crédito = US$ 0,0001 por chamada; `per_page` máximo é 100; sem chave há US$ 0,10/dia compartilhado por IP e o cursor paging não funciona; com chave gratuita, US$ 1/dia (≈ 10.000 chamadas) e cursor paging. O snapshot público (S3, sem login) é trimestral e particionado por `updated_date`, não por país ou ano; works ocupa ~615 GB comprimidos.
- **Decisão:** puxar o recorte brasileiro (works, authors, institutions) pela **API com chave** e cursor paging, usando `select=` para trazer só os campos necessários. Atualização incremental por data de atualização. O snapshot fica para reprocessamentos completos ou se o recorte crescer muito.
- **Consequências:** é preciso criar a chave (`OPENALEX_API_KEY`). Os números de custo e tempo estão na seção final do relatório da Parte 0.

## D-007 — Grupos de pesquisa: pedido LAI + pilotos em portais de universidades

- **Data:** 2026-11-09
- **Decisão:** abrir pedido via Fala.BR ao CNPq pela base de grupos certificados (e bolsistas PQ/DT). Enquanto isso, usar portais de dados abertos de universidades apenas como piloto/validação. A categoria PQ dos docentes de pós vem da coluna `CD_CAT_BOLSA_PRODUTIVIDADE` do conjunto de docentes da CAPES.

## D-008 — Fotos: upload próprio, avatar com iniciais e Commons só com licença livre

- **Data:** 2026-11-09
- **Decisão:** a foto padrão é um avatar gerado com as iniciais. A fonte principal é o upload feito pelo próprio pesquisador ao reivindicar o perfil. Wikidata (P18) / Commons só com licença livre e crédito exibido. Nada de Lattes ou Scholar.

## D-009 — Novo escopo: Integra Nordeste (substitui D-001)

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Contexto:** o projeto deixou de ser uma plataforma nacional e passou a ser o **Integra Nordeste**: repositório da pesquisa e produção biomédica, em saúde, biotecnologia, genética e áreas afins dos **últimos 5 anos**, de universidades, pesquisadores, docentes e autores com vínculo em instituições dos 9 estados do Nordeste.
- **Decisão:** o recorte fica centralizado em `ingest/diagnostico/recorte.py` (UFs, período, áreas, termos de busca). Período padrão = ano atual e os 4 anteriores (2022–2026 em 2026), sobrescrevível por `YEAR_START`. O diagnóstico nacional anterior foi arquivado em `ingest/relatorios/arquivo/`.
- **Consequências:** o SCHEME.md (nome, visão, §3.4, §7) precisa ser reescrito para o novo projeto antes da Parte 1. O User-Agent passou a ser `integra-nordeste-diagnostico/0.1`.

## D-010 — Como o recorte é aplicado em cada fonte

- **Data:** 2026-11-09
- **Região:**
  - OpenAlex: filtros por `geo.region` com os nomes dos estados (`authorships.institutions.geo.region` em works, `last_known_institutions.geo.region` em authors). Como nem toda instituição tem `geo.region`, a lista do ROR por UF (`country_subdivision_code`) é usada para medir a perda e, nas próximas partes, para filtrar por lista de IDs de instituições.
  - INEP: `SG_UF_IES`. CAPES: `SG_UF_PROGRAMA`. IBGE: prefixo do código do município.
  - BDTD/Oasisbr: soma das contagens por sigla de instituição do NE (cada registro tem uma instituição só).
  - Wikidata: organização localizada (P131, transitivo) num estado com ISO 3166-2 BR-MA…BR-BA.
- **Área:**
  - OpenAlex: works pelo `primary_topic.field.id` nos fields 27 Medicine, 13 Biochemistry/Genetics/Molecular Biology (inclui Biotechnology), 24 Immunology and Microbiology, 28 Neuroscience, 30 Pharmacology/Toxicology/Pharmaceutics, 29 Nursing, 35 Dentistry e 36 Health Professions. Authors por `topics.field.id` (mais amplo).
  - Ficam fora da contagem principal, mas são medidos à parte: Veterinary (34) e o subfield Biomedical Engineering (2204).
  - CAPES: áreas de avaliação Medicina I–III, Enfermagem, Odontologia, Farmácia, Saúde Coletiva, Nutrição, Educação Física (fisioterapia, fonoaudiologia, TO), Ciências Biológicas I–III e Biotecnologia.
  - INEP: cursos CINE 09 (Saúde e bem-estar) e 051 (Ciências biológicas).
  - BDTD/Oasisbr: termos de busca. Grupos de universidades: palavras-chave.
- **Estimativas:** programas CAPES são contados exatamente (CSVs pequenos). Docentes, teses e produção da CAPES (arquivos > 50 MB) são estimados como linhas no período × fração de programas do recorte; o número exato sai na Parte 2.

## D-011 — IBICT (BDTD/Oasisbr): firewall bloqueou consultas booleanas longas

- **Data:** 2026-11-09
- **O que aconteceu:** na API VuFind do BDTD e do Oasisbr, uma busca com 18 termos unidos por OR (e uma frase entre aspas) recebeu HTTP 403. Na sequência, durante testes manuais com o curl para isolar a causa, os servidores passaram a recusar conexões do nosso IP. Foram poucas requisições, com intervalo de 1 a 2 s.
- **Decisão:** não insistir nem contornar. Busca limitada a 11 termos (versão que respondeu 200), 5 s entre chamadas a `bdtd.ibict.br` e `oasisbr.ibict.br`, e nova tentativa só depois de o bloqueio expirar (`--fonte bdtd --fonte oasisbr --sem-cache`). Para a coleta real (Parte 6), preferir OAI-PMH (`oasisbr.ibict.br/vufind/OAI/Server`) ou contato formal com o IBICT.

## D-012 — Instituições: política de cruzamento INEP ↔ ROR

- **Data:** 2026-11-09
- **Decisão:** o ROR é a lista-base das organizações do NE (225). IES do INEP sem correspondente viram instituições próprias (751 no total). O cruzamento segue três níveis:
  1. **Identificador comum** (confiança 1): Wikidata com ROR (P6782) e e-MEC (P5148). A P5148 guarda o código **em base64**, como nas URLs do e-MEC (`NTg2` → 586).
  2. **Automático forte** (confiança 0,9): nome idêntico, ou sigla igual com similaridade ≥ 0,5, **e** mesmo município, sem candidato concorrente e com o ROR ainda livre. Vale para organizações (não pessoas). O vínculo é listado no relatório para conferência, e a chave `emec:` não entra no registro de IDs (se o vínculo cair, nenhum UUID fica preso a ele).
  3. **Fila de revisão** (`institution_review_queue.csv`): todo o resto com similaridade ≥ 0,5 ou sigla igual.
- A similaridade ignora palavras genéricas ("Universidade", "Centro Universitário"...) e nomes de lugar do NE. Sem isso a fila enchia de falsos pares.
- **Consequências:** natureza jurídica fica desconhecida para organizações só do ROR (hospitais, institutos). As unidades da Fiocruz no NE aparecem na CAPES com o e-MEC da Fiocruz nacional e ficam na fila até alguém decidir. Decisões manuais devem virar uma tabela de mapeamentos versionada (próximo passo).

## D-013 — IDs estáveis e saída em CSV

- **Data:** 2026-11-09
- **Decisão:** os UUIDs internos (instituição, programa, pesquisador) vêm de um registro persistente, só de acréscimo: `ingest/dados/ids/<entidade>.csv`, com chaves `esquema:valor`. Nunca são derivados de hash, para não mudarem quando a chave preferida muda. Se uma execução liga chaves que já pertencem a UUIDs diferentes, o conflito é registrado e **não há mescla**.
- Até o banco existir, as cargas gravam CSVs em `ingest/dados/processados/`. `ingest/sql/schema.sql` e `ingest/sql/carga.sql` levam esses CSVs para o Postgres (upsert, idempotente). O registro de IDs entra no backup.
- **Ocorrido em 2026-11-09:** o registro de instituições foi apagado e recriado uma única vez, porque tinha sido gerado minutos antes por uma execução com o bug do base64 e nada o consumia. Fora dessa situação, o arquivo não deve ser apagado.

## D-014 — CAPES: dados pessoais minimizados e pesquisador nasce do ID_PESSOA

- **Data:** 2026-11-09
- **Decisão:** de docentes, não gravamos `NR_DOCUMENTO_DOCENTE` (CPF mascarado), `TP_DOCUMENTO_DOCENTE`, `AN_NASCIMENTO_DOCENTE` nem `DS_FAIXA_ETARIA`. Cada `ID_PESSOA` da CAPES recebe um UUID de pesquisador (chave `capes_id_pessoa`, confiança 1). Na Parte 4, OpenAlex e ORCID se ligam a esses mesmos UUIDs quando houver evidência por identificador; sem identificador comum, vai para a fila.
- O programa é ligado à instituição pelo código e-MEC da CAPES (`CD_ENTIDADE_EMEC`). Se não houver, por nome exato na mesma UF; senão, fila. A instituição ganha o identificador `capes_entidade`.

## D-015 — Pesquisadores: quem entra e como as identidades se resolvem

- **Data:** 2026-11-09
- **Quem entra:** todo autor OpenAlex com ao menos uma autoria vinculada a instituição do NE (lista da Parte 1, via `lineage`) em works do recorte, mais os docentes CAPES do recorte (Parte 2). Coautores de fora do NE ficam só em `work_authorships` (nome e ID OpenAlex, sem `researcher_id`). Autorias com `author.id` nulo no OpenAlex não geram pesquisador.
- **Identidade:**
  - Perfis OpenAlex com o mesmo ORCID (primário do perfil ou, na falta, o mais frequente nas autorias) recebem o mesmo UUID. É identificador comum, então confiança 1.
  - Docente CAPES × autor OpenAlex: não há identificador comum. Pares com sobrenome igual, primeiro nome compatível e instituição em comum vão para `researcher_review_queue.csv`, com score = 0,75 × similaridade do nome + 0,2 (teto 0,95). **Nada é mesclado automaticamente**; a decisão é humana ou vem da reivindicação via ORCID.
- **ORCID:** não é consultado em massa; fica para a reivindicação de perfil (sob demanda), como recomendado no diagnóstico.
- **Coautoria:** arestas só de works com até 50 autores, para que consórcios (GBD e similares, com milhares de autores) não criem cliques artificiais. Esses works continuam no perfil de cada autor.

## D-016 — Produção: filtro por lista de instituições, não por estado

- **Data:** 2026-11-09
- **Decisão:** a coleta usa `authorships.institutions.lineage` com os IDs OpenAlex das 225 instituições do NE (3 lotes de até 100 IDs, deduplicados localmente) × `primary_topic.field.id` × ano. Isso corrige a perda medida na Parte 0: 111 instituições, entre elas a UFPB, não têm `geo.region` no OpenAlex. Coleta por cursor paging com chave; works brutos em `ingest/dados/brutos/openalex/works_loteNN.jsonl.gz` (um `.ok` por lote concluído, para retomar sem rebaixar).

## D-017 — Recorte ampliado ("opção D"): ciências agrárias, biológicas e veterinária

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Contexto:** a pergunta "agrárias, biotecnologia e microbiologia estão incluídas?" mostrou que:
  - microbiologia já estava (field 24);
  - a biotecnologia estava só na parte de saúde e molecular (subfield 1305 e área CAPES Biotecnologia). A biotecnologia vegetal e agrícola fica no field 11;
  - agrárias, veterinária e biodiversidade estavam fora.
- **Decisão:**
  - OpenAlex: entram o field 11 inteiro (Agricultural and Biological Sciences, que inclui também ecologia, zoologia e botânica) e o field 34 (Veterinary). Biomedical Engineering (subfield 2204) continua medido à parte.
  - CAPES: entram Biodiversidade, Ciências Agrárias I, Ciência de Alimentos, Zootecnia / Recursos Pesqueiros e Medicina Veterinária.
  - INEP: entra o CINE 08.
  - O nome do recorte passa a ser "ciências da vida".
- **Consequências:**
  - Partes 2, 5 e 4 refeitas. Os UUIDs existentes se mantêm (registro só de acréscimo); entram novos programas, works e pesquisadores.
  - Os termos de busca do BDTD/Oasisbr continuam limitados a 11 por causa do firewall do IBICT (D-011). As agrárias, nessas fontes, terão de ser buscadas em consultas separadas na Parte 6.

## D-018 — Aceite em lote de pares docente × autor (regra aprovada pelo responsável)

- **Data:** 2026-11-09 (aprovado pelo usuário na conversa)
- **Regra:** um par docente CAPES × autor OpenAlex é aceito se: (1) o docente tem **um único** candidato; (2) o nome é idêntico depois de normalizado (score de nome 1,0); (3) há instituição em comum; (4) o autor não é candidato único de outro docente.
- **Resultado em 2026-11-09:** 2.653 aceites. Ficaram de fora 2.068 docentes com mais de um candidato, 111 sem nome idêntico e 9 casos de autor disputado por dois docentes. Restam 5.336 pares de pesquisadores e 53 de instituições para revisão manual (`ingest/dados/revisao/pendentes_*.csv`).
- **Mecânica:**
  - As decisões ficam em `ingest/dados/revisao/decisoes.csv` (só acréscimo, com regra, quem decidiu e quando).
  - Aceitar cria um **alias**: o UUID do docente passa a apontar para o UUID do autor OpenAlex. Nenhum UUID é apagado, e o app redireciona o UUID antigo.
  - O identificador `capes_id_pessoa` do docente aliasado entra com confiança 0,95 (regra) ou 0,99 (revisão humana), nunca 1.
  - Rejeitar depois desfaz o alias na próxima consolidação.
- **Exceção ao modelo original:** o modelo dizia que cruzamentos sem identificador comum nunca mesclam automaticamente. Esta regra é uma exceção autorizada explicitamente pelo responsável, limitada aos casos sem ambiguidade e reversível.

## D-019 — Fase B: banco e app locais

- **Data:** 2026-11-09
- **Decisão:**
  - `docker-compose.yml` com Postgres 16.4 publicado só em `127.0.0.1:5432` e o app Next.js 14 (standalone) em `127.0.0.1:3000`. `docker-compose.prod.yml` remove todas as portas.
  - Credenciais do banco em `POSTGRES_*` no `.env`. A senha local foi gerada aleatoriamente.
  - `scripts/carregar_banco.sh` aplica `ingest/sql/schema.sql` e `ingest/sql/carga.sql` (idempotente; testado com duas cargas seguidas).
- **Achados do primeiro teste real do SQL:**
  - `unaccent()` não é IMMUTABLE e não pode ir em índice: criado o invólucro `f_unaccent`.
  - Alguns perfis OpenAlex têm `display_name` em cirílico. A Parte 4 agora prefere um nome em alfabeto latino entre as alternativas.
  - A fila tinha pares repetidos entre fontes, agora deduplicados na carga.
- **App:**
  - Node não está instalado na máquina; o app é instalado e compilado só no Docker. O typecheck roda no build.
  - Telas mínimas: números e busca por nome (pg_trgm sem acento) e página de pesquisador (programas, coautores, publicações), com redirecionamento de UUID aliasado.
  - Sem CI por enquanto: o projeto ainda não é um repositório git.

## D-020 — Repositório git: o que é versionado

- **Data:** 2026-11-09
- **Decisão:** versionar código, SQL, documentação, relatórios e dois tipos de dado que **não são regeneráveis**:
  - o registro de UUIDs estáveis (`ingest/dados/ids/`, ~30 MB);
  - as decisões de revisão (`ingest/dados/revisao/decisoes.csv`).
  Contêm só identificadores públicos (OpenAlex, ORCID, ID CAPES, e-MEC, ROR) mapeados para UUID, sem nomes nem dados pessoais.
- Ficam fora: `.env`, caches, `ingest/dados/brutos/` (1,8 GB) e `ingest/dados/processados/` (618 MB), que se regeneram rodando as partes, e as planilhas de pendentes.
- **Atenção:** se o repositório for publicado, revisar antes se o mapeamento ID CAPES ↔ UUID deve continuar público. Considerar Git LFS se `ingest/dados/ids/` passar de ~100 MB.

## D-021 — Nome do projeto: Ciência Nordeste

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Decisão:** o projeto passa a se chamar **Ciência Nordeste** (antes "Integra Nordeste"). Identificador técnico: `ciencia-nordeste` (User-Agent `ciencia-nordeste-diagnostico/0.1`, pacote `ciencia-nordeste-web`).
- **Consequências:** código, SCHEME, README e app atualizados. As decisões anteriores e os relatórios já gerados mantêm o nome antigo, por serem registro histórico (o User-Agent que de fato foi enviado nas coletas de 2026-11-09 era `integra-nordeste-...`).

## D-022 — Migrações SQL numeradas em vez de Drizzle

- **Data:** 2026-11-09
- **Decisão:** o schema evolui por arquivos SQL numerados em `ingest/sql/migracoes/` (`0001_schema_inicial` … `0004_instituicao_areas`). `scripts/migrar.sh` aplica, numa transação cada, só as que faltam, e registra em `schema_migrations`. O banco criado pelo antigo `schema.sql` foi marcado como baseline (0001).
- **Por quê:** o schema nasceu em SQL, a ingestão é Python e o app só lê, então um ORM no Node não traria ganho agora. Se a Fase D trouxer escrita pelo app (reivindicação, edição de perfil), dá para adotar Drizzle com `introspect` a partir do banco.
- **Regras:**
  - nunca editar uma migração já aplicada;
  - toda migração deve poder rodar duas vezes (`IF NOT EXISTS`). A CI testa isso num Postgres vazio.

## D-023 — Fase C: escolhas do app

- **Data:** 2026-11-09
- **Desempenho:** a home e a busca leem visões materializadas (`mv_resumo`, `mv_pesquisador_busca`, `mv_instituicao_stats`, `mv_instituicao_areas`), atualizadas no fim de `carga.sql`. Home de 2,5 s para 0,35 s; página de instituição grande de 2,5 s para 0,2 s.
- **Segurança:** o Next 14.2.15 constava como vulnerável no npm (aviso de 11/12/2025); atualizado para 14.2.35 (tag `next-14`, sem aviso). Rever a linha 15/16 antes do lançamento público.
- **Sitemap:** índice dinâmico `/sitemap.xml` com blocos `/sitemaps/<n>` de 40 mil URLs; nada depende do banco no build.
- **Mapa:** Leaflet 1.9.4 com tiles do OpenStreetMap, ok para desenvolvimento e uso leve com atribuição. Em produção, trocar por um provedor de tiles (política de uso do OSM).
- **Fotos:** servidas por `/foto/<id>` a partir de `ingest/dados/fotos/`, montado só leitura no container. Crédito e licença aparecem sob a foto. Sem foto, o perfil mostra o avatar com iniciais.

## D-024 — Login com ORCID adiado até a produção

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Decisão:** o login não é uma funcionalidade enquanto o site não estiver em produção (o sandbox do ORCID não está disponível). O app não mostra nenhuma tela ou chamada de login. A chave `LOGIN_HABILITADO` (`apps/web/lib/recursos.ts`, padrão desligado) prepara a ativação. URL de retorno prevista: `https://<domínio>/api/auth/callback/orcid`.

## D-025 — Mapa próprio do Nordeste e nova navegação

- **Data:** 2026-11-09 (pedido do usuário)
- **Mapa:** componente SVG autocontido em `apps/web/components/mapa/`, sem tiles, bibliotecas ou chamadas externas. Os contornos dos 9 estados vêm uma vez da malha do IBGE (`python -m ingest.carga.gerar_mapa_ne`) e ficam versionados em `geometria-ne.json`. O componente só desenha o que recebe; toda a aparência está em variáveis CSS (`mapa.css`).
- **Modos:**
  - **produção**: barras verticais por instituição, com posições representativas, não em escala;
  - **colaboração**: arcos entre instituições do NE;
  - **áreas**: rosca por estado e, ao escolher uma área, estados coloridos por ela;
  - **rede**: arcos de uma pessoa, instituição ou programa para parceiros do NE e para âncoras externas (Brasil fora do NE e países).
  Todos respondem aos filtros de área, estado e período via `/api/mapa`. O Leaflet foi removido.
- **Layout:** na home, busca unificada à esquerda (pesquisador, instituição, programa) e mapa à direita. Nas páginas de entidade, o mapa de rede fica à esquerda e o perfil à direita (classe `.explorar.invertido`, fácil de trocar).
- **Dados:** migração 0005 (países por autoria; visões `mv_work_inst`, `mv_mapa_producao`, `mv_mapa_colaboracao`, `mv_inst_externo`) e 0006 (índices do perfil).

## D-026 — Git só com código e documentação (substitui D-020)

- **Data:** 2026-11-09 (decidido pelo usuário)
- **Decisão:** o repositório versiona apenas código (Python, SQL, TypeScript, scripts, configs) e documentação (`SCHEME.md`, `README.md`, `docs/`).
  - Saem do git: os relatórios gerados (`ingest/relatorios/`), o registro de UUIDs estáveis (`ingest/dados/ids/`) e as decisões de revisão (`ingest/dados/revisao/decisoes.csv`).
  - Os arquivos continuam no disco; só deixaram de ser rastreados (`git rm --cached`). As versões anteriores seguem no histórico dos commits já feitos.
- **Consequência importante:** o registro de UUIDs e as decisões **não são regeneráveis** e agora não têm cópia no git. Precisam de backup próprio (cópia externa periódica, junto com o `pg_dump` previsto na seção 12 do SCHEME). Até haver esse backup, perder o disco quebra a estabilidade dos IDs e perde as revisões feitas.

## D-027 — Nome fixo do projeto no Docker, backup local e incidente com o git

- **Data:** 2026-11-09
- **Docker:** a pasta do projeto foi renomeada (`ache-um-pesquisador` → `ciencia-nordeste`), e o Compose usa o nome da pasta para nomear containers e volumes. O `docker-compose.yml` agora fixa `name: ciencia-nordeste`.
  - Os containers antigos foram removidos. O banco foi recriado do zero (6 migrações + carga), o primeiro teste real de banco vazio → banco cheio, sem erros.
  - O volume antigo `ache-um-pesquisador_pgdata` foi preservado até o responsável decidir apagá-lo.
- **Backup:**
  - `scripts/backup.sh` gera um pacote datado em `BACKUP_DIR` (padrão `~/Backups/ciencia-nordeste`), legível só pelo dono. O pacote contém o registro de UUIDs, as decisões de revisão, o `pg_dump` do banco, um manifesto e checksums SHA-256.
  - Retenção padrão de 14 pacotes e cópia extra opcional (`BACKUP_COPIA_EXTRA`). O `.env` não entra no pacote.
  - `scripts/restaurar.sh` verifica o pacote, restaura os IDs (com proteção contra sobrescrever) e restaura o banco (só com `--forcar`).
  - Tudo foi testado, inclusive a restauração completa do banco num banco descartável, com contagens idênticas.
- **Incidente (D-026):**
  - **O que aconteceu:** depois do `git rm --cached`, o merge direto do `main` para o commit que deixa de rastrear `ingest/dados/ids/`, `decisoes.csv` e `ingest/relatorios/` **apagou esses arquivos do disco**. Para o git, avançar para um commit que remove um arquivo rastreado significa removê-lo também da pasta.
  - **Recuperação:** os arquivos foram restaurados do commit `a8e6428` (`git restore --source=a8e6428 --worktree`) e conferidos byte a byte, sem perda, porque não tinham mudado desde aquele commit.
  - **Lição:** fazer `checkout` de commits **anteriores** a `f9451a7` escreve versões antigas desses arquivos por cima das atuais, e voltar ao `main` apaga os arquivos do disco. Antes de qualquer `checkout` de commit antigo, rodar `./scripts/backup.sh`. Se for preciso olhar código antigo, usar `git show <commit>:<arquivo>` ou um `git worktree` separado, nunca `checkout` na pasta de trabalho.

## D-028 — Busca vetorial por tema (multilíngue, híbrida e balanceada por idioma)

- **Data:** 2026-11-09
- **Decisão:**
  - **Modelo:** `intfloat/multilingual-e5-base` (MIT, 768 dimensões), fixado no commit `d128750` e carregado em safetensors. O mesmo modelo calcula os vetores das publicações (em lote, nesta máquina, com a GPU do Mac via MPS) e os das consultas (serviço `embed`, CPU, só na rede interna do Docker e offline em execução). Texto de cada publicação: `passage: título. Palavras-chave: … Tópicos: …`; consulta: `query: …`.
  - **Banco:** imagem `pgvector/pgvector:0.8.6-pg16` (Postgres 16.15, mesmo volume). A migração 0007 cria `work_keywords` e `work_embeddings` (`halfvec(768)`, índice HNSW por cosseno). O banco ganhou `shm_size: 1gb`, porque a construção paralela do índice estoura os 64 MB padrão.
  - **Busca:** híbrida, com fusão de rankings (RRF, k = 60) entre os vizinhos vetoriais e a coincidência textual no título e nas palavras-chave. Os resultados são somados por pesquisador, instituição e programa. Se o serviço `embed` cair, a busca continua só pelo texto.
  - **Balanceamento por idioma:** o modelo multilíngue prefere textos no idioma da consulta (só 1 de 40 resultados vinha em inglês, embora 55% das publicações sejam em inglês). Os vizinhos passaram a ser buscados separadamente entre publicações em inglês e nas demais línguas, com `hnsw.iterative_scan = relaxed_order`, e intercalados.
- **Avaliação** (`python -m ingest.carga.avaliar_busca_tema`, 20 consultas em português com termos esperados em PT/EN):

  | Modo | Precisão nos 8 primeiros | Em inglês | Sem resultado | Latência |
  |---|---|---|---|---|
  | Texto | 70% | 6% | 6 de 20 | 87 ms |
  | Vetor | 100% | 50% | 0 | 464 ms |
  | Híbrido (padrão) | 100% | 34% | 0 | 235 ms |

- **Custos e recursos:**
  - Palavras-chave do OpenAlex: 1.353 créditos (US$ 0,14); 99,8% das publicações têm palavras-chave.
  - Vetores: 111.143 em 171 MB (meia precisão); 655 MB no banco, com o índice.
  - Imagem do serviço `embed`: 3,7 GB (torch); usa 1,1 GB de RAM.
- **Lição de memória (máquina com 8 GB):** com o Docker Desktop aberto, o cálculo em lote caiu de 51 para ~15 textos/s por causa do swap (9,5 GB em uso). Com o Docker fechado, voltou a ~31 textos/s. O cálculo em lote deve rodar com o Docker desligado. O script grava o progresso a cada ~16 mil textos e retoma de onde parou.
- **Próximos passos possíveis:**
  - reduzir a imagem do `embed` com ONNX;
  - incluir resumos no texto;
  - perfil temático por pesquisador (média dos vetores) para "pesquisadores parecidos" e compatibilidade.

## D-029 — Identidade visual: paleta Mangue derivada por tokens

- **Decisão:** o app usa um sistema de tokens em `apps/web/app/tokens.css`. Cada paleta é definida por três números (matiz `--h`, saturação `--s`, matiz de destaque `--h2`), e todos os tons do tema claro e do escuro derivam deles em HSL. A paleta padrão é **Mangue** (verde-água 172°, âmbar 36° nos destaques). Atlântico, Lavanda e Sertão ficam prontas via `data-palette` no `<html>`.
- **Papéis das cores:**
  - `--accent` é a estrutura: barras, arcos internos e controles ativos;
  - `--flow` (âmbar) fica reservado ao que merece atenção: a origem da rede, a coautoria fora do Nordeste e a busca por tema;
  - o mapa (`mapa.css`) só referencia tokens.
- **Mapa:** passa a ser uma "placa" com espessura (quatro cópias deslocadas) e sombra; no escuro, a sombra vira brilho.
- **Contraste:** `--accent` do tema claro ficou mais escuro que o da inspiração (32% de luminosidade em vez de 47%) para links legíveis. Os preenchimentos usam `--accent-vivo`.
- **Tipografia:** Sora (títulos e números) e Inter (texto), via `next/font`. As fontes são baixadas no build e servidas pelo próprio site, sem chamadas ao Google em tempo de execução (coerente com D-025).
- **Tema:** segue o sistema; `data-theme="light|dark"` no `<html>` força um tema. Ainda não há botão de troca na interface.

## D-030 — Interface: busca em destaque, mapa interativo com subunidades recolhidas, páginas em gráficos

- **Tela inicial:**
  - Busca no topo, com exemplos clicáveis. Os resultados aparecem em colunas: pesquisadores, instituições, programas e tema.
  - Abaixo, um painel em três colunas:
    - à esquerda, filtros e áreas (barras clicáveis, que também são a legenda do modo Áreas);
    - no centro, o mapa;
    - à direita, o ranking.
  - **Retiradas por redundância:**
    - o título repetido "Ciência Nordeste" e a descrição no cabeçalho;
    - o número de publicações nos rótulos do mapa (está no ranking e na dica);
    - o total de publicações no cabeçalho da rede (está no perfil).
- **Mapa:**
  - **Dica (tooltip) em HTML** em barras, nós, arcos, fatias e estados, com toque em celular.
  - **Clique seleciona a instituição:** abre um cartão com o link para o perfil e esmaece as demais. Sem seleção possível (perfis), o clique abre o perfil.
  - **Mouse sobre um nome:** no ranking ou nos resultados, realça a instituição no mapa. No modo Colaboração, isola a rede dela.
  - **Altura das barras em escala de raiz quadrada** (antes, linear): diminui a diferença visual entre as grandes e as pequenas sem inverter a ordem.
  - **Rótulos:** só sigla e posição no ranking (selo numerado; top 3 na cor de destaque).
- **Subunidades recolhidas:**
  - A migração 0008 cria `v_instituicao_vinculo` (subunidade → instituição principal) com três regras, em ordem de confiança: ROR parent/child; ROR related entre universidade e hospital/instituto; sigla ou nome da universidade dentro da subunidade, na mesma UF.
  - Resultado atual: 12 vínculos (ex.: HC-UFPE → UFPE, HUWC → UFC, HUOL → UFRN, HUUFMA → UFMA). O ROR quase não tem departamentos no NE, e o OpenAlex trabalha no nível de instituição.
  - No mapa, as subunidades ficam ocultas e entram num leque abaixo da principal quando ela é selecionada. Pelo mesmo mecanismo, em cada cidade só as 4 maiores (ou as que têm ≥ 20% da maior) ficam sempre visíveis; as demais entram no leque da maior da cidade.
  - Ligações de instituições ocultas são somadas à instituição que as representa.
- **Instituições:** treemap agrupado por estado ou por tipo, com o tamanho por publicações, pesquisadores ou programas. Clicar no grupo filtra. Abaixo, cards com números e a barra de áreas, mais filtros por estado, tipo e texto (tudo no navegador; cerca de 190 itens).
- **Programas:** matriz área de avaliação × conceito CAPES, com círculos proporcionais, que funciona como filtro. Abaixo, cards com o conceito em destaque, agrupáveis por área, instituição ou estado, e filtros por estado e nível.
- **Perfis:**
  - áreas, subunidades e parceiras em barras horizontais;
  - pesquisadores, docentes e coautores em nuvem (tamanho = publicações);
  - programas em cards;
  - publicações e teses numa linha do tempo por ano.
- **Cores:** as cores categóricas (`--area-0…9`) passaram para `tokens.css`, para valerem fora do mapa (treemap, cards, perfis).

## D-031 — Estética "neo-brutalismo suave e sóbrio" e nova tela inicial (branch `ui`)

- **Base visual** (`apps/web/app/tokens.css`):
  - fundo liso levemente tingido pela paleta (distinto dos cards) e tinta azul-marinho;
  - cards com borda de 2 px, cantos de 14 px e sombra dura de 3 px, sem desfoque;
  - divisórias tracejadas; etiquetas em azul-claro com contorno fino.
- **Controles em pílula:** o item ativo vira uma pílula na cor de destaque, com contorno.
- **Paleta Azul** (`--h: 222`): azul para dados e controles; lima como marca-texto só no que merece atenção (top 3 e seleção). Lavanda, Coral e Verde ficam disponíveis via `data-palette`.
- **Tipografia:** Lexend nos títulos e números, DM Sans no texto, via `next/font` (servidas pelo próprio site). Marca "Ciência **Nordeste**" com contraste de peso.
- **Ícone e favicon:** na paleta (azul, marinho e lima). O ícone do cabeçalho é desenhado com os tokens e acompanha o tema.
- **Tela inicial:**
  - busca no topo, com até 4 sugestões por grupo ("mais N") e altura máxima;
  - três colunas: **Áreas** (270 px) e **Produção por ano** | **mapa** | **KPIs** (pesquisadores e publicações), **Seletores do mapa** e **Instituição selecionada**;
  - o card do mapa tem a largura do desenho (o desenho é limitado pela altura), e a área do mapa ocupa a altura da janela;
  - Produção por ano: publicações únicas de cada ano no filtro de estado e área, a partir de `mv_uf_ano_area` (migração 0009); clicar num ano filtra o período;
  - Instituição selecionada: números no filtro e no total, pesquisadores, programas, áreas principais e subunidades (`/api/instituicao-resumo`); substitui a barra que ficava sobre o mapa.
- **Mapa:**
  - sombra dura em tinta no lugar do relevo e do brilho;
  - fundo com anéis estáticos e gride de latitude/longitude rotulado;
  - escala gráfica e seta do norte;
  - no modo Produção, **bolhas** (padrão; área ∝ publicações, menores por cima, raio mínimo clicável) ou **cilindros** (altura comprimida; vizinhos próximos em tons diferentes; área de clique ampliada);
  - selos do ranking como círculos com contorno, com o top 3 em lima;
  - sem callouts fixos;
  - legenda abaixo do mapa e dica com borda e sombra dura.
- **Filtro de estado:** isola o estado escolhido e o amplia na área do mapa. Só as posições são reescaladas (cilindros, bolhas, rótulos e bordas mantêm o tamanho); o gride (1°/2°) e a escala gráfica acompanham o zoom.
- **Programas:** linhas tracejadas e fundo alternado separando cada área na matriz área × conceito, com cabeçalho alinhado.
