# Otimizações da busca vetorial e do servidor

Levantamento de 2026-11-16 (ainda não implementado). Objetivo: gastar menos CPU e memória na VPS na busca por tema
(`apps/web/lib/vetorial.ts`, `/api/tema`, `/busca`) e no quiz, que usa o mesmo serviço de embedding.

## Onde o processamento vai hoje

Cada busca por tema faz três coisas:

1. **Calcula o vetor da frase** no serviço `embed` (modelo multilingual-e5-base em PyTorch, na CPU). Provavelmente é a parte
   mais cara: algumas centenas de milissegundos de CPU por consulta.
2. **Faz duas varreduras no índice HNSW**, uma para publicações em inglês e outra para as demais línguas. O idioma (e o
   filtro de Qualis) é aplicado *durante* a varredura (`hnsw.iterative_scan`), o que percorre muito mais nós do que o
   necessário.
3. **Cria uma tabela temporária** (`_tema`) e roda 4 agregações sobre ela. Criar tabela temporária escreve no catálogo
   do Postgres a cada busca, o que gera inchaço e trabalho para o autovacuum.

Nada disso é guardado: a mesma busca repetida refaz tudo.

---

## A. Sem alteração no banco de dados

### A1. Só código: `git pull` e `./scripts/publicar.sh`

O `publicar.sh` reconstrói e reinicia só o que mudou (`web` e, se for o caso, `embed`).

| # | Otimização | Onde muda | Ganho esperado | Risco |
|---|---|---|---|---|
| 1 | **Cache do vetor da consulta** (LRU em memória, chave = frase normalizada) | `apps/web/lib/vetorial.ts` (`embedVetor`) | Evita rodar o modelo em buscas repetidas e no quiz. É o maior corte de CPU | Baixo |
| 2 | **Cache do resultado da busca por tema** (LRU por termo + modo + Qualis, validade de algumas horas, como no quiz, D-052) | `apps/web/lib/vetorial.ts` (`buscaPorTema`) | Busca repetida não toca no banco nem no modelo. Os dados só mudam na atualização mensal | Baixo |
| 3 | **Consulta única com CTE**, sem tabela temporária, devolvendo as 4 listas em JSON | `apps/web/lib/vetorial.ts` | Sem escrita no catálogo a cada busca, menos autovacuum e 5 idas ao banco a menos | Baixo (conferir que o resultado é idêntico) |
| 4 | **`hnsw.ef_search` de 120 para 64** | `apps/web/lib/vetorial.ts` | Varredura menor no índice | Médio: medir a qualidade (os 10 primeiros resultados em ~50 consultas) |
| 5 | **Uma inferência por vez no `embed`** (trava em volta do `modelo.encode`) | `servicos/embed/app.py` (rebuild do `embed`, ~5 min) | Buscas simultâneas deixam de disputar a CPU (hoje cada uma abre 2 threads do torch) | Baixo |
| 6 | **`Disallow: /busca` e `/api/` no robots.txt** | `apps/web` (robots) | Robôs de busca deixam de disparar o modelo ao visitar `/busca?q=…` | Baixo |
| 7 | **ONNX Runtime com o modelo quantizado em int8** no lugar do PyTorch | `servicos/embed/` (Dockerfile e app.py) | 2–4× mais rápido e cerca de 1/3 da RAM (~1,5 GB → ~400 MB) | Médio: o vetor da consulta muda um pouco; validar a qualidade antes (comparar os 10 primeiros em ~50 consultas) |

Recomendação: implementar 1, 2, 3, 5 e 6 juntos, medir antes e depois, e só então avaliar 4 e 7.

### A2. Configuração do Postgres: `git pull` e reiniciar o banco

São parâmetros no `docker-compose.yml` (por exemplo `command: postgres -c jit=off -c shared_buffers=…`). Não mudam
tabelas nem dados. Entram com o `git pull`, e o `docker compose up -d db` reinicia o Postgres (o site fica alguns
segundos fora do ar).

| # | Parâmetro | Valor sugerido | Por quê |
|---|---|---|---|
| 8 | `jit` | `off` | Em consultas curtas, o JIT gasta mais CPU compilando do que economiza. Ganho comum e sem risco |
| 9 | `shared_buffers` | ~25% da RAM da VPS | O índice HNSW precisa estar na memória, senão cada busca lê do disco |
| 10 | `effective_cache_size` | ~70% da RAM | Ajuda o planejador a preferir os índices |
| 11 | `max_parallel_workers_per_gather` | 0–1 em VPS de 2 vCPUs | Evita que uma consulta ocupe todos os núcleos |
| 12 | `work_mem` | 16–32 MB | Agregações e ordenações sem usar o disco |

Os valores exatos dependem da VPS (`free -h` e `nproc`).

### A3. Fora do repositório (configuração do servidor)

| # | Otimização | Observação |
|---|---|---|
| 13 | **Limite de requisições por IP** para `/busca` e `/api/tema` | Precisa de um plugin do Caddy (a imagem padrão não tem) e o `Caddyfile` está fora do git (`deploy/`). Alternativa: limitar no próprio app |
| 14 | **Conferir os logs do Caddy** à procura de robôs abrindo `/busca` | Se houver muito tráfego automático, os itens 6 e 13 resolvem |

---

## B. Com alteração no banco de dados

Exigem migração nova (`ingest/sql/migracoes/0021_…`, com `IF NOT EXISTS`, D-022) e, em alguns casos, reconstruir
índices. Na VPS: `git pull` e `./scripts/publicar.sh` (aplica a migração), com mais tempo de manutenção.

| # | Otimização | O que muda no banco | Ganho esperado | Custo |
|---|---|---|---|---|
| 15 | **Índices HNSW parciais por idioma** | Coluna `ingles boolean` em `work_embeddings` + dois índices: `… WHERE ingles` e `… WHERE NOT ingles` | Cada uma das duas varreduras vira busca direta, sem filtro iterativo | Reconstruir os índices (minutos a dezenas de minutos, com memória extra); atualizar `parte8_embeddings.py` |
| 16 | **Índice HNSW parcial para "só Qualis"** | Coluna `qualis boolean` em `work_embeddings` (ou tabela separada) + índice parcial | O filtro Qualis, ligado por padrão, deixa de forçar varredura iterativa longa | Mais um índice para manter (espaço em disco e RAM) |
| 17 | **Tabela de cache de consultas** (frase normalizada → vetor) | Tabela nova, com limpeza periódica | O cache sobrevive a reinícios e é compartilhado | Pequeno. Atenção à privacidade: guardaria o texto das buscas (hoje nada é registrado); preferir o cache em memória (item 1) |
| 18 | **Visão materializada dos agregados por pesquisador** usados na busca | Nova `mv_…` atualizada na carga mensal | Menos junções por busca | Médio: mais uma visão para atualizar no `atualizar_dados.sh` |

Recomendação: deixar o grupo B para depois de medir o efeito do grupo A. O item 15 é o de maior ganho entre eles.
