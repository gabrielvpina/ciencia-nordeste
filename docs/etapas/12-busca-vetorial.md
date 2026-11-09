# Etapa 12 — Busca vetorial por tema de pesquisa

**Status:** concluída · **Código:** `ingest/carga/parte8_embeddings.py`, `ingest/carga/avaliar_busca_tema.py`, `servicos/embed/`, `apps/web/lib/vetorial.ts`, `apps/web/app/api/tema/`
**Decisão:** D-028 · **Migração:** `0007_busca_vetorial`

## Objetivo

Permitir buscar por **tema** em português ("resistência bacteriana a antibióticos", "fruticultura irrigada no semiárido") e encontrar as publicações, a maioria em inglês, os pesquisadores, as instituições e os programas que trabalham com ele.

## Como rodar

```bash
python -m ingest.carga.parte8_embeddings coletar-keywords   # palavras-chave do OpenAlex (~1.100 chamadas)
python -m ingest.carga.parte8_embeddings benchmark          # velocidade e memória antes de rodar tudo
# feche o Docker Desktop antes do próximo passo se a máquina tiver 8 GB (ver "Memória")
python -m ingest.carga.parte8_embeddings embeddings         # vetores (incremental; retoma do último checkpoint)
./scripts/carregar_banco.sh                                 # inclui work_keywords
python -m ingest.carga.parte8_embeddings carregar           # vetores no Postgres + índice HNSW
docker compose up -d embed web
python -m ingest.carga.avaliar_busca_tema                   # avaliação PT -> PT/EN
```

Dependências pesadas em `ingest/requirements-embeddings.txt` (torch 2.14.1, sentence-transformers 6.2.0, psycopg 3.3.6).

## Arquitetura

| Peça | Detalhe |
|---|---|
| Texto embutido | `passage: <título>. Palavras-chave: <até 6>. Tópicos: <até 3>.` (formato do e5) |
| Modelo | `intfloat/multilingual-e5-base` (MIT, 768 dim.), commit `d128750`, safetensors |
| Lote (publicações) | GPU do Mac (MPS); vetores normalizados em `ingest/dados/processados/embeddings/` (171 MB, meia precisão), com hash do texto para recalcular só o que mudou |
| Banco | `pgvector/pgvector:0.8.6-pg16`; `work_embeddings (halfvec(768))` com índice HNSW por cosseno; `work_keywords` (1,08 milhão) |
| Consultas | Serviço `embed` (Python, CPU, sem portas publicadas, offline): `POST /embed` → vetor `query:` em ~120 ms; o texto das consultas não é registrado em log |
| Busca (`/api/tema`) | Híbrida (RRF): vizinhos HNSW **balanceados por idioma** (inglês e demais) + coincidência no título e nas palavras-chave; soma por pesquisador, instituição e programa; se o `embed` cair, segue só pelo texto |
| Interface | Seção "Por tema de pesquisa" na barra lateral da tela inicial (a partir de 4 letras) |

## Resultado

| Item | Valor |
|---|---|
| Publicações com palavras-chave | 110.973 de 111.164 (99,8%); 1.082.256 palavras-chave |
| Vetores | 111.143 (todas as publicações com título) |
| Tamanho no banco | 655 MB (tabela + índice HNSW) |
| Custo no OpenAlex | 1.353 créditos ≈ US$ 0,14 |

Avaliação com 20 consultas em português; uma publicação conta como relevante se o título ou as palavras-chave têm algum termo esperado em PT ou EN:

| Modo | Precisão nos 8 primeiros | Publicações em inglês | Consultas sem resultado | Latência média |
|---|---|---|---|---|
| Só texto | 70% | 6% | 6 de 20 | 87 ms |
| Vetor | **100%** | **50%** | 0 | 464 ms |
| **Híbrido** (padrão) | **100%** | 34% | 0 | 235 ms |

O critério de relevância é conservador e aproximado (sinônimos fora da lista contam como erro). Ele serve para comparar modos e versões, não como medida absoluta.

## Problemas encontrados

- **Viés de idioma:** antes do balanceamento, só 1 de 40 resultados vinha em inglês. Resolvido buscando vizinhos por idioma e intercalando.
- **Memória (8 GB):** com o Docker aberto, o cálculo caiu para ~15 textos/s (swap de 9,5 GB). Com o Docker fechado, voltou a ~31/s. O script agora grava checkpoints a cada ~16 mil textos.
- **`/dev/shm` de 64 MB** impedia criar o índice HNSW em paralelo: `shm_size: 1gb` no banco.
- **`EMBED_URL` ausente** no app por uma edição do compose que não se aplicou. Corrigida; o app caía, como previsto, no modo só texto.
- **`.venv` quebrado** pela renomeação da pasta (scripts com caminho absoluto): recriado.

## Pendências e ideias

- Reduzir a imagem do serviço `embed` (3,7 GB) com ONNX.
- Incluir resumos no texto embutido (exige recoletar `abstract_inverted_index`).
- Perfil temático por pesquisador (média dos vetores) para "pesquisadores parecidos" e para a compatibilidade de pesquisa.
- Página de resultados completa por tema (hoje: os primeiros resultados na barra lateral).
