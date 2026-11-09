# Etapa 10 — Aplicação web (Fases B e C)

**Status:** núcleo concluído, rodando localmente em http://localhost:3000 · **Comando:** `docker compose up -d web`
**Código:** `apps/web/` (Next.js 14.2.35, TypeScript, App Router) · **Decisões:** D-019, D-021, D-023, D-024, D-025

## Arquitetura

- O app **só lê** do Postgres, pelo driver `pg` com consultas parametrizadas.
- Roda inteiro no Docker (a máquina não tem Node instalado). O build roda o typecheck e gera uma imagem *standalone* que executa com usuário sem privilégio.
- O Next.js foi atualizado de 14.2.15 para **14.2.35**, porque o npm sinalizou a versão anterior como vulnerável (aviso de 11/12/2025).

## Telas

| Rota | Conteúdo |
|---|---|
| `/` | **Tela inicial**: barra lateral à esquerda com busca unificada (pesquisador, instituição, programa), modos do mapa e filtros (área, estado, período); **mapa próprio do NE** à direita ([etapa 11](11-mapa-proprio.md)) |
| `/pesquisador/<id>` | Mapa de **rede em arco** à esquerda e perfil à direita: instituição, selos (docente de pós, bolsa PQ, ORCID), tópicos, programas, coautores no NE, orientações, publicações. Foto com crédito ou avatar de iniciais. Um UUID que virou alias redireciona (307) para o perfil canônico |
| `/instituicao/<id>` | Rede em arco; números, publicações por área, programas, principais pesquisadores, instituições parceiras |
| `/programa/<id>` | Rede dos docentes; conceito e área CAPES, docentes do último ano, teses recentes com link para o orientador |
| `/instituicoes`, `/programas` | Listas com filtros por estado, tipo e área de avaliação |
| `/sobre` | Fontes e licenças, como os perfis são montados, LGPD |
| `/api/busca`, `/api/mapa`, `/api/rede` | APIs JSON da busca e do mapa |
| `/sitemap.xml`, `/sitemaps/<n>`, `/robots.txt` | SEO: sitemap em blocos de 40 mil URLs, gerado sob demanda; metadados por página |
| `/foto/<id>` | Serve o WebP da etapa 7 |

## Login

**Desligado até a produção** (D-024): não há tela nem botão de login. A chave `LOGIN_HABILITADO` (`apps/web/lib/recursos.ts`) prepara a ativação com o ORCID. URL de retorno prevista: `https://<domínio>/api/auth/callback/orcid`.

## Histórico

1. **Esqueleto**: home com números e busca por nome; página de pesquisador.
2. **Fase C**:
   - busca com filtros e paginação;
   - páginas de instituição e programa;
   - mapa com Leaflet e tiles do OSM, depois substituído;
   - sitemap, página "Sobre" e fotos.
3. **Redesenho pedido pelo usuário** (D-025): mapa próprio sem serviços externos, tela inicial com mapa e busca lateral, perfis com rede em arco. Leaflet removido.

## Desempenho medido

| Página | Antes | Depois |
|---|---|---|
| Home | 2,5 s | 0,2–0,35 s (visões materializadas) |
| Instituição grande (UFPB) | 2,5 s | 0,2 s |
| Pesquisador | 4,4 s | ~0,02 s (índice de coautoria) |

## Pendências (Fase C)

- Busca por tema/tópico (ver a proposta de busca vetorial) e filtro por município.
- Rede de coautoria pessoa × pessoa como grafo.
