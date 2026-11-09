# Etapa 11 — Mapa próprio do Nordeste

**Status:** concluída · **Código:** `apps/web/components/mapa/` · **Geometria:** `python -m ingest.carga.gerar_mapa_ne`
**Decisão:** D-025

## Requisitos (pedido do usuário)

- Mapa **só do território do Nordeste**, **próprio, sem APIs externas**, **autocontido**, simples de mostrar e fácil de estilizar.
- Modos: **densidade** de produção, **ligações** de colaboração entre universidades e **distribuição entre áreas**. Todos reagem aos filtros.
- Na tela inicial, densidade vertical por universidade, com bastante destaque; as posições são **representativas**, não em escala.
- Ao escolher uma pessoa, universidade ou programa: **rede em arco** com colaborações internas e externas.

## Como foi feito

| Arquivo | Papel |
|---|---|
| `geometria-ne.json` (19,5 KB) | Contorno dos 9 estados, já projetado para coordenadas SVG, com os parâmetros da projeção. Gerado **uma vez** a partir da malha oficial do IBGE (API de malhas v3, qualidade mínima) e versionado; o app nunca consulta o IBGE |
| `projecao.ts` | Projeção equirretangular (a mesma do gerador), espalhamento de instituições da mesma cidade num anel, arcos e fatias de rosca |
| `MapaNordeste.tsx` | Componente SVG puro: **não busca dados e não tem dependências**; desenha o que recebe |
| `mapa.css` | **Toda a aparência em variáveis CSS** (`--mn-*` para o mapa, `--area-0..9` para a paleta das áreas), com tema claro e escuro |
| `areas.ts`, `tipos.ts` | Ordem e cor fixas das áreas; contratos de dados |

Os dados vêm de `/api/mapa` (geral, com filtros) e `/api/rede` (por entidade), que leem as visões materializadas da migração 0005.

## Modos

| Modo | Desenho | Dados |
|---|---|---|
| **Produção** (padrão) | Barras verticais em cada instituição, com altura proporcional às publicações e rótulos das maiores sem sobreposição | `mv_mapa_producao` (instituição × área × ano) |
| **Colaboração** | Arcos entre instituições; espessura e opacidade proporcionais às publicações em comum (as 160 ligações mais fortes) | `mv_mapa_colaboracao` (par × área × ano) |
| **Áreas** | Rosca por estado com a divisão da produção entre as áreas; ao escolher uma área, os estados se colorem pela intensidade dela | `mv_mapa_producao` agregada por UF |
| **Rede** | Origem em destaque; arcos verdes para parceiros no NE; arcos tracejados para "Brasil, fora do NE" e para os 6 países com mais coautoria (âncoras ilustrativas fora do território) | `mv_mapa_colaboracao`, `mv_inst_externo` e autorias com `countries` |

Filtros: **área**, **estado** (destaca o estado e apaga os demais) e **período** (2022–2026).

## Layout

- **Tela inicial**: `.explorar`, com a busca à esquerda e o mapa à direita.
- **Perfis**: `.explorar.invertido`, com o mapa de rede à esquerda e o perfil à direita.
- Trocar os lados é só uma classe CSS.
- No celular, os painéis empilham.

## Conferência visual

Feita no Chrome. Problemas encontrados e corrigidos:

- o mapa estourava a área (a Bahia aparecia cortada);
- rótulos se sobrepunham em Recife;
- a legenda das áreas estava sem cores;
- a margem para as âncoras externas aparecia em todos os modos;
- o total do cabeçalho somava autorias institucionais sem dizer isso.

## Limitações

- As posições das âncoras externas são ilustrativas.
- Países "externos" incluem consórcios internacionais.
- No modo áreas, as roscas de PE, PB e RN encostam umas nas outras, porque os estados são pequenos e vizinhos.
