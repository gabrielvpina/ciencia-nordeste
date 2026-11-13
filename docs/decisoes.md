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

## D-032 — Atualização periódica dos dados em um comando

- **Script:** `scripts/atualizar_dados.sh` executa a ordem completa da ingestão (Partes 1 → 2 → 5 → 4 → revisão → 6 → 7 → 8), recarrega o Postgres e grava os vetores. Faz backup antes e depois.
- **Fontes sempre frescas:** por padrão o cache HTTP é ignorado. A nova variável `INGEST_SEM_CACHE=1`, lida em `carregar_config`, vale para todas as partes, mesmo as que não têm `--sem-cache`. Os lotes do OpenAlex são recoletados com `--recoletar`.
- **Retomada e recorte:** `--a-partir-de` retoma de uma etapa, e `--so` roda só algumas. Uma trava impede duas execuções ao mesmo tempo.
- **Conferência automática:**
  - contagens antes/depois (publicações, pesquisadores, instituições, programas, teses, vetores e último ano);
  - alerta para quedas acima de 2%;
  - teste das rotas `/`, `/api/mapa`, `/api/busca` e `/api/tema`.
  - Relatório em `ingest/relatorios/atualizacao-<data>.md`.
- **Período dinâmico no app:** `ANO_MIN` vem de `ANO_INICIO` (padrão 2022) e o fim é o ano corrente. A tela inicial lê o período real do banco (`min`/`max` de `works.year`), então seletor de período, colunas de Produção por ano e textos acompanham a base sem mudar o código.
- **Revisão de identidade:** continua humana. O script aplica a regra D-018 aos pares novos e exporta os pendentes.

## D-033 — Qualis Periódicos 2021-2024 na produção de pesquisadores e programas

- **Fonte:** planilha da consulta pública de periódicos do Qualis na Plataforma Sucupira (evento "Classificações de periódicos quadriênio 2021-2024"), exportada à mão e guardada em `ingest/dados/brutos/capes/qualis/qualis-2021-2024.xlsx`. Não há download em lote nem API, e a coleta não raspa o formulário (D-002). É informação pública da CAPES; a fonte é citada na tela.
- **Achado que simplifica:** no 2021-2024 cada ISSN tem **um só estrato**, repetido em todas as áreas de avaliação que listam a revista (33.347 ISSNs, nenhum conflito). O estrato não depende da área do programa. A carga confere isso a cada execução e, se aparecer conflito, fica o melhor estrato e o caso vai ao relatório.
- **Casamento por ISSN:** o Qualis lista o ISSN impresso ou o eletrônico; o banco só tinha o ISSN-L. A Parte 9 (`ingest/carga/parte9_qualis.py`) extrai todos os ISSNs de cada revista dos brutos do OpenAlex já coletados (sem chamadas novas) para `venue_issns`. Com isso, 92.112 de 111.164 publicações (83%) têm estrato, contra 87.712 só pelo ISSN-L. O restante é anais de iniciação científica, preprints, livros e revistas fora da lista.
- **Banco (migração 0010):** `qualis_periodicos` (evento, issn, estrato, título, áreas), `venue_issns` e a visão `mv_work_qualis` (estrato de cada publicação; havendo mais de um ISSN classificado, vale o melhor). Publicações de 2025 em diante usam o 2021-2024, a classificação mais recente. Um novo quadriênio entra por uma nova migração que recria a visão com o evento novo.
- **App:** programas e pesquisadores ganham duas abas na coluna principal: **Rede de colaboração** (o mapa de antes) e **Produção** (`?ver=producao`). A produção mostra colunas empilhadas por ano (altura = volume, segmentos = faixa Qualis A1–A2, A3–A4, B1–B2, B3–B4, C e "sem Qualis"), a distribuição pelos nove estratos, as revistas mais usadas com o estrato e uma tabela com os números. No programa, conta a produção dos docentes do último ano-base, o mesmo critério do mapa de rede.
- **Cores:** rampa ordinal de um só azul (A1–A2 mais escuro no tema claro, mais claro no escuro) e cinza para "sem Qualis", validadas com o validador de paletas (`--ordinal`) contra os cards dos dois temas. Ficam fixas em `--qualis-*` e não seguem a troca de paleta do site.
- **Uso responsável:** o Qualis classifica revistas para a avaliação de programas, não artigos nem pessoas. A tela diz isso, e o site não faz ranking de pesquisadores por estrato.

## D-034 — Site só no tema claro

- **Decisão:** o site tem um único tema, o claro. Saem o seletor claro/escuro do cabeçalho (`components/SeletorTema.tsx`), o script que aplicava a escolha salva (`cn-tema` no `localStorage`) e todos os estilos do tema escuro (`prefers-color-scheme: dark` e `data-theme="dark"` em `app/tokens.css` e `app/globals.css`).
- **Sistema em modo escuro:** o site continua claro. `color-scheme: light` no `:root` mantém também os controles nativos do navegador (barras de rolagem, campos) no claro.
- **Cabeçalho:** fica só o link para o repositório no GitHub.
- **Revoga** a parte de tema escuro das decisões de interface anteriores (D-031). A paleta (`data-palette`) e os tokens claros não mudam. As telas do README passam a ser só claras; o logo do README mantém a variante escura, que segue o tema do GitHub do leitor, não o do site.

## D-035 — Filtro "só revistas com Qualis" no site inteiro

- **O quê:** um card pequeno acima de **Áreas**, na tela inicial, com a caixa "Só publicações em revistas com Qualis", **marcada por padrão**. Com ela marcada, todo o site conta só as publicações cuja revista está no Qualis Periódicos 2021-2024 (D-033): mapa (produção, colaboração, áreas), produção por ano, totais, busca por nome e por tema, listas e perfis de instituição, programa e pesquisador (números, publicações, coautores, rede e a aba Produção).
- **Onde fica a escolha:** no cookie `cn-qualis` (sem cookie = ligado; `0` = desligado), para valer em todas as páginas e o servidor ler na hora de montar cada uma. As chamadas do navegador às APIs levam `ql=0|1` na URL, para o cache do navegador não misturar as duas versões. O rodapé avisa quando o filtro está ligado.
- **Banco (migração 0011):** as visões de contagem (`mv_resumo`, `mv_pesquisador_busca`, `mv_instituicao_stats`, `mv_instituicao_areas`, `mv_mapa_producao`, `mv_mapa_colaboracao`, `mv_inst_externo`, `mv_uf_ano_area`) foram recriadas com uma coluna `works_qualis` ao lado de `works`; o app escolhe a coluna. Nenhum dado novo: tudo vem de `mv_work_qualis`, que agora é a primeira do REFRESH em `carga.sql`.
- **Contado na hora com o filtro:** coautores do pesquisador e parceiras da instituição (as tabelas `coauthorships` e `institution_collaborations` da ingestão não separam Qualis).
- **Não muda:** número de pesquisadores, programas, teses e orientações (não são publicações em revista). A avaliação da busca por tema (`avaliar_busca_tema.py`) usa `ql=0`, a base inteira.

## D-036 — Quiz "Que cientista é você?": estrutura por facetas, match e banners

- **Data:** 2026-11-11 · **Branch:** `quiz` · **Etapa:** [13](etapas/13-quiz-alinhamento.md)
- **Estrutura:** dado versionado em `apps/web/lib/quiz/arvore.json`. São 10 perguntas mais a instituição.
  - **Nicho**, que alimenta o match: método, objeto, sub-objeto (42 opções), foco, escala, ambiente e impacto.
  - **Perfil**, que só monta o título: habitat, estilo e vínculo.
  - **Filtros:** cada objeto lista os métodos que fazem sentido para ele, e os pares método × sub-objeto sem pesquisadores saem. Ficam 280 pares no núcleo.
- **Match e banner são processos separados.** O match (`lib/quiz/alinhamento.ts`) só lê as facetas de nicho e a instituição. O título e o nicho escrito (`lib/quiz/titulo.ts`) não alteram quem aparece. Um teste garante que trocar só as respostas de perfil não muda nomes, ordem nem índices.
- **Match:**
  - **Núcleo obrigatório:** 2 ou mais publicações que casem método e sub-objeto, sem alargar o nicho para completar a lista. Por isso o banner mostra **até 5** pesquisadores.
  - **Índice de 0 a 100, em escala fixa** = 0,30 cobertura das demais facetas + 0,20 concentração no nicho + 0,20 volume + 0,30 afinidade. A afinidade é o cosseno do perfil temático com a frase do nicho, entre os percentis 90 e 99,9 da população.
  - **Ordem (pedido do responsável):** entre os que passam no índice mínimo, quem tem **mais produção** vem antes. A ordem soma índice + 20 × produção total no período (escala log, cheia em 100 publicações) + 3 × proeminência (h-index, docência na pós, bolsa PQ). O índice mostrado não muda, então a ordem nem sempre segue o índice.
  - **Exclusão:** fica de fora a instituição do usuário e as ligadas a ela (parent/child do ROR e vínculo de subunidade).
  - **Diversidade:** o banner traz **instituições diferentes**. Só repete uma instituição (até 2 pessoas) se faltar gente para completar 5. A lista estendida aceita até 3 por instituição.
  - **Filtro Qualis:** respeita o D-035.
- **Perfil temático** (`researcher_embeddings`, migração 0012): média dos vetores das publicações, ponderada por recência × autoria × tamanho da equipe, para 35.806 pesquisadores.
- **Ambiente no título e no nicho:** só entra quando a pessoa diz que um lugar é essencial na pesquisa (pergunta "Algum ambiente é essencial na sua pesquisa?"). Com "Não, minha pesquisa não depende de um lugar", o título e o nicho ficam gerais (ex.: "Bioinformática de vírus"; "Sentinela dos anfíbios e répteis" em vez de "Sentinela da mata atlântica").
- **Títulos:** sempre neutros e sem nomes licenciados, a pedido do responsável. São 25 arquétipos (habitat × estilo) mais os vínculos ("Fã nº 1 dos vírus", "Detetive do cérebro", "Sentinela da caatinga"). O validador barra marcas de gênero e nomes proibidos.
- **Visual:** nesta fase, só cores e formas simples, sem ilustração SVG. Fundo pelo habitat, acento pelo ambiente, cartões neo-brutalistas e mini mapa do NE. PNG gerado no servidor (`next/og`), em 1080 × 1920 e 1080 × 1350.

## D-037 — Cadastro dos participantes do quiz (primeira escrita do app)

- **Data:** 2026-11-11 (pedido do responsável)
- **Decisão:** antes das perguntas, o quiz pede:
  - **nome completo**;
  - **instituição** por extenso, com sugestões das instituições do NE da base; aceita texto livre;
  - **tipo de filiação:** graduação, mestrado, doutorado, docente, pesquisador(a) ou profissional do mercado;
  - **curso ou programa:** para quem está na pós, sugestões dos programas da base; senão, texto livre.

  Os dados ficam numa tabela própria, `quiz_participantes`. É a **primeira escrita do app**: até aqui ele só lia (D-022).
- **Como, pela LGPD** (base legal: consentimento, art. 7º, I):
  - **Consentimento explícito:** caixa obrigatória, não marcada por padrão, com a finalidade escrita na tela e um link para a seção de privacidade em `/sobre`. Grava-se também a data e a versão do texto aceito.
  - **Finalidade:** só estatísticas agregadas sobre quem usa o quiz (filiação, instituições, programas). **Não se pede e-mail nem outro contato** (o campo opcional de e-mail foi retirado a pedido do responsável, para reduzir riscos jurídicos; migração `0015`). **Os dados não entram no match.** A instituição escolhida na lista só serve para excluir os colegas dela do resultado, como antes.
  - **Mínimo necessário:** não se grava IP, navegador, respostas do quiz nem o resultado. As URLs de resultado e dos banners continuam levando só ids de opções e da instituição.
  - **Acesso restrito:** o app grava com um papel próprio do Postgres, `quiz_escrita`, que só tem `INSERT` na tabela. O app não lê esses dados. Leitura e exportação só pelo responsável, via `psql`.
  - **Retenção de 24 meses:** registros mais antigos são apagados pelo `scripts/publicar.sh` e pelo `scripts/carregar_banco.sh`.
  - **Pedidos de acesso, correção ou remoção** vão pelo contato indicado em `/sobre` (variável `CONTATO_PRIVACIDADE`).
  - **Backups:** os pacotes de `scripts/backup.sh` passam a conter dados pessoais. Já são legíveis só pelo dono, e isso fica explícito no guia.
- **Proteção contra abuso:** campo-isca invisível para robôs, limites de tamanho e no máximo 10 cadastros por minuto por origem (em memória).

## D-038 — FUNED fora da base (geocodificação errada no ROR)

- **Data:** 2026-11-11 (pedido do responsável)
- **Problema:** a Fundação Ezequiel Dias (FUNED, ROR `01qgvp179`) fica em Belo Horizonte (MG). O ROR a localiza em "Gameleira", e o nome foi casado com o município de Gameleira (PE). Com isso, ela entrou no recorte do NE com 303 pesquisadores vinculados, 415 publicações e 381 publicações que só estavam na base por causa dela.
- **Correção:**
  - **Ingestão:** a Parte 1 ganhou `ROR_EXCLUIDOS`, uma lista de ids do ROR fora do recorte, cada um com o motivo. A FUNED não volta numa próxima atualização.
  - **Banco** (migração `0013_remover_funed`, idempotente):
    - remove a FUNED das autorias;
    - apaga as publicações que ficaram sem nenhuma instituição do NE;
    - desvincula os pesquisadores (sem apagá-los; os que ficarem sem produção saem na próxima ingestão);
    - apaga a instituição.
  - **Depois:** visões materializadas, perfis temáticos e sinais do quiz são recalculados.

## D-039 — Nova tela inicial: busca e dois caminhos (painel e quiz)

- **Data:** 2026-11-11 (branch `quiz`)
- **O quê:** a tela inicial (`/`) fica mais leve: o título, a **busca unificada** (nomes e temas, como antes) e dois cartões grandes:
  - **"Ver o painel"** leva a `/painel`;
  - **"Descobrir meu perfil de cientista"** leva ao quiz (`/quiz`, etapa 13).

  Abaixo, os números da base (pesquisadores, publicações, instituições, programas), que respeitam o filtro Qualis (D-035).
- **Painel (`/painel`):** é a antiga tela inicial inteira (D-031): busca com destaque no mapa, filtro "só revistas com Qualis", áreas, produção por ano, mapa, instituição selecionada, seletores e KPIs.
  - Os filtros agora vão na URL (`?uf=PE&area=…&de=…&ate=…`, via `replaceState`, sem criar histórico), então o link do painel abre já filtrado.
  - Endereços antigos com parâmetros (`/?uf=…`) e `/mapa` redirecionam para `/painel` com os mesmos parâmetros.
- **Código:** a busca saiu para `components/BuscaGeral.tsx`, usada nas duas telas. `components/Inicio.tsx` virou `components/Painel.tsx`.
- **Navegação:**
  - o menu "Mapa" virou **"Painel"** e ganhou o item **"Quiz"**;
  - no celular, a marca e o GitHub ficam na primeira linha e o menu numa segunda linha, que rola de lado;
  - o aviso do rodapé sobre o filtro Qualis aponta para o painel;
  - os links "← mapa geral" dos perfis levam ao painel;
  - o sitemap troca `/mapa` por `/painel` e inclui `/quiz`.
- **Por quê:** o mapa é rico, mas pesado como primeira impressão no celular. A maioria chega querendo buscar alguém ou, agora, fazer o quiz. A busca continua no topo das duas telas.

## D-040 — Descrição livre da pesquisa no quiz, só como código no link

- **Data:** 2026-11-11 (pedido do responsável)
- **O quê:** uma última tela opcional no quiz: "Descreva a sua pesquisa em poucas palavras" (até 160 caracteres). Serve para refinar o match dentro do nicho escolhido nas respostas.
- **Restrições:** o resultado precisa continuar reproduzível pelo link (D-036), e nada do quiz pode ser gravado (D-037). Pôr o texto na URL o deixaria no histórico, nos logs do Caddy e em todo link compartilhado. Guardá-lo no servidor quebraria a regra de não gravar.
- **Como:**
  - O servidor (`POST /api/quiz/texto`) transforma o texto em vetor (e5, 768 dimensões) e o projeta na **base PCA dos perfis temáticos**: 128 componentes, 79% da variância.
  - Cada coeficiente é quantizado em 6 bits (±3σ), o que dá um caractere base64url. O código tem 129 caracteres: 1 de versão mais 128.
  - O texto não é gravado, não vai para log e não volta ao navegador. O link leva `&t=<código>`.
  - Página e banners reconstroem o vetor aproximado sem o serviço de embedding.
- **Fidelidade:** com 30 consultas, Spearman de 0,991 entre as similaridades exatas e as reconstruídas, e 82% dos 100 perfis mais próximos em comum. Também foram testados 64 componentes × 8 bits (0,983), 96 × 8 (0,989) e 192 × 4 (0,991, mas com o mesmo tamanho e mais código).
- **Peso:** a similaridade com o texto, ancorada como a afinidade, entra com 0,40, somado aos 1,00 das respostas; com texto, o texto vale ~29% do índice. Numa avaliação com 8 nichos amplos e descrições específicas, a aderência da lista de 15 subiu 25 pontos em média, sem nenhum caso pior. Com peso 0,25, o ganho era de 18 pontos.
- **Estabilidade:** `apps/web/lib/quiz/base-texto-v1.json` não pode mudar, porque links compartilhados dependem dela. O script `ingest/carga/quiz_base_texto.py` se recusa a sobrescrevê-la. Uma base nova (por exemplo, com outro modelo de embedding) ganha outra versão, e o app passa a aceitar as duas.
- **Junto:** o vetor da frase do nicho passou a ficar em memória. Antes, uma lentidão do serviço de embedding (limite de 4 s) fazia o mesmo link dar resultados diferentes; foi o que aconteceu na avaliação logo após reiniciar o app.
- **Privacidade:** do código não se recuperam as palavras, só o tema aproximado. O aviso está na própria tela e em `/sobre#privacidade-quiz`.
- **Posição e pergunta (revisão do mesmo dia):** a tela passou do fim do quiz para **logo depois de "especificamente?"**, com a pergunta "Qual organismo, doença ou sistema, exatamente?". A decisão veio de um experimento com 20 casos (`ingest/carga/experimento_quiz_textos.py`), que comparou textos sobre o objeto, a técnica e o objetivo da metodologia, sozinhos e combinados:
  - **objeto:** maior ganho (aderência ao objeto na lista de 49% para 65%; no banner, de 54% para 72%) e nenhum caso pior;
  - **técnica ou objetivo, somados ao objeto:** de 1 a 4 pontos a mais, dentro do ruído de 20 casos;
  - **objetivo sozinho:** piorou 4 casos. A linguagem de objetivos é genérica ("melhorar a qualidade", "prevenir") e pode tirar a lista do nicho.

  Por isso o quiz tem **uma** tela de texto, e não várias intercaladas, que também aumentariam a desistência no celular.

## D-041 — Revisão de proteção de dados, código de remoção e escolha única no quiz

- **Data:** 2026-11-11 (pedido do responsável)
- **Revisão LGPD simples:** em `docs/revisao-lgpd.md`, com inventário, achados e pendências. Não é parecer jurídico. Mudanças que saíram dela:
  - **Transferência internacional:** o servidor fica na AWS `us-east-1` (EUA). O consentimento passa a dizer isso (art. 33, VIII).
  - **Controlador identificado** em `/sobre` (o autor, pessoa física), com a base legal de cada tratamento, a seção "Dados dos pesquisadores" e o link para a ANPD.
  - **Maiores de 18:** a caixa de concordância começa por "Tenho 18 anos ou mais".
  - **Versão do consentimento:** `2026-11-11c`.
- **Canal dos titulares:** continuam as issues do GitHub (`CONTATO_PRIVACIDADE` vazio, a pedido do responsável). Como são públicas:
  - o cadastro gera um **código de remoção** aleatório de 8 caracteres (migração `0016`), mostrado uma vez numa tela após o cadastro;
  - o modelo de issue `.github/ISSUE_TEMPLATE/privacidade.md` pede só o código e avisa para não escrever dados pessoais;
  - `scripts/quiz_remover.sh CÓDIGO` apaga o registro.
- **Termos (revisão do mesmo dia, versão `2026-11-11d`):** a caixa de concordância ficou curta: "Tenho 18 anos ou mais e aceito os termos de uso e compartilhamento de dados", com link para `/sobre#termos`. Os termos, em linguagem jurídica neutra, tratam de objeto, controlador, dados, finalidade (só estatística), base legal, compartilhamento (só operadores de infraestrutura), prazo de 24 meses, segurança, direitos, idade mínima e alterações. A pedido do responsável, nenhum texto cita a AWS nem os EUA; o risco quanto ao art. 33 fica registrado em `docs/revisao-lgpd.md` (achado 1).
- **Escolha única:** as perguntas do quiz continuam aceitando uma resposta cada (decisão do responsável). A múltipla escolha alargaria o núcleo do match e tenderia a reduzir a precisão.

## D-042 — Guardar o alinhamento de quem fez o quiz (base da futura rede de afinidades)

- **Data:** 2026-11-11 (pedido do responsável)
- **O quê:** para cada quiz concluído por alguém com cadastro, grava-se o perfil de respostas e com quais pesquisadores houve match. Isso substitui a regra inicial de não gravar respostas (pedido original da etapa 13, D-037). O objetivo é uma futura rede (grafo) participante → pesquisador, que pode juntar instituições e programas de pós dos dois lados.
- **Tabelas** (migrações `0017` e `0018`):
  - **`quiz_alinhamentos`:** as respostas (ids na ordem das telas), o código do texto livre (D-040, nunca o texto), a instituição excluída, o filtro Qualis, o núcleo, o número de candidatos e uma `chave` (sha256 das respostas, do código e da instituição).
  - **`quiz_matches`:** uma aresta por pesquisador da lista de 15 ou do banner de 5, com índice, posição em cada um e publicações no nicho.
- **Como:**
  - O cadastro devolve o id do participante, que fica só na memória do navegador.
  - Ao concluir, o quiz chama `POST /api/quiz/alinhamento` uma vez, sem esperar a resposta. A rota recalcula o match como a página de resultado e grava.
  - A página de resultado e os banners continuam sem gravar nada, porque são abertos também por quem recebe o link.
  - Repetições (toque duplo, reenvio) são descartadas no navegador e no banco: chave única por participante e conjunto de respostas, com `ON CONFLICT DO NOTHING` sem alvo, que o papel só de `INSERT` pode usar. Quem volta e muda as respostas gera outro registro.
- **Privacidade:**
  - O papel `quiz_escrita` só insere; o app não lê nenhuma das tabelas (testado: leitura recusada).
  - Remover o cadastro (`scripts/quiz_remover.sh`) ou o expurgo de 24 meses apagam alinhamentos e arestas (`ON DELETE CASCADE`, testado).
  - Termos e consentimento revistos (versão `2026-11-11e`): dados coletados e finalidade passam a incluir "estudos sobre redes de afinidade científica, divulgados só de forma agregada ou sem identificação dos usuários".
  - A página de resultado avisa que abrir o link não grava nada.

## D-043 — Sem código de remoção; o cadastro leva direto ao quiz

- **Data:** 2026-11-11 (pedido do responsável)
- **O quê:** sai a tela "Guarde o seu código" (D-041). Depois do cadastro, o quiz começa direto. O cadastro não gera mais o código: a coluna `codigo_remocao` (migração `0016`) fica nula, porque migrações aplicadas não são editadas (D-022). Saem também o `scripts/quiz_remover.sh` e as menções ao código nos termos, em `/sobre` e no modelo de issue.
- **Revogação:** o responsável vai definir outro jeito de revogar o cadastro. Até lá, os pedidos chegam pelas issues (sem dados pessoais, segundo o modelo), e a remoção é feita por `psql`, levando junto os alinhamentos (`ON DELETE CASCADE`).
- **Risco:** sem um identificador que não exponha a pessoa, a remoção por um canal público fica difícil. Registrado como pendente no achado 2 de `docs/revisao-lgpd.md`.
- **Versão do consentimento:** `2026-11-11f` (os termos deixam de citar o código).

## D-044 — Busca só pelo botão, página de resultados em três partes e painel numa tela

- **Data:** 2026-11-13 (pedido do responsável)
- **Por quê:** reduzir o custo da busca vetorial (cada pausa na digitação chamava o `embed` e o HNSW) e fazer o painel caber numa tela 16:9 sem rolagem.
- **Busca:**
  - A barra só busca ao apertar **Buscar** ou Enter; não há mais sugestões a cada letra. Na tela inicial, leva para `/busca?q=…`; no painel, os resultados ocupam o lugar dos cards de filtro (`/painel?q=…`).
  - Três colunas (`components/ResultadosBusca.tsx`, `lib/busca.ts`):
    1. **Nomes:** pesquisadores, instituições e programas por texto (trigrama), sem vetor.
    2. **Pesquisadores no tema:** busca vetorial híbrida (D-028), mais as instituições do tema.
    3. **Trabalhos:** artigos do tema e teses e dissertações (CAPES) cujo título ou palavras-chave trazem algum termo da consulta, com índice de texto em português (migração `0019`) e título pesando mais que as palavras-chave.
  - **Consulta que parece nome** (sigla exata de instituição ou similaridade ≥ 0,6 com o nome de um pesquisador): as colunas 2 e 3 não rodam, e um botão permite "buscar como tema" (`&tema=1`). Palavra dentro do nome de instituição não conta, porque "caprinos" está em "Embrapa Caprinos e Ovinos".
  - **Cache em memória** de até 300 consultas por 6 h (reinicia a cada publicação, quando os dados mudam). Os exemplos e os links repetidos não recalculam nada.
  - `/api/busca` passa a devolver o resultado completo. `/api/tema` continua igual, porque é usado na avaliação (`avaliar_busca_tema.py`).
- **Painel:**
  - Sai o título "Painel da pesquisa no Nordeste" (fica só para leitores de tela) e saem os KPIs.
  - À esquerda: busca compacta e, abaixo, os cards em duas colunas (áreas e instituição selecionada | seletores, Qualis e produção por ano). À direita: o mapa na altura da janela.
  - Em janelas a partir de 1100 × 620, a página tem a altura da janela, sem rolagem: quem rola, se precisar, é a área dos cards ou cada coluna de resultados. Conferido em 1920 × 1080 e 1366 × 768. No celular, tudo fica empilhado.
- **Medido (local, depois de aquecer):** a busca de tema levou de 60 a 900 ms na primeira vez e cerca de 10 ms no cache; a de nome, de 6 a 300 ms; as teses, de 2 a 15 ms com o índice.
