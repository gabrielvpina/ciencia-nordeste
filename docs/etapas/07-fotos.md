# Etapa 7 — Fotos de pesquisadores

**Status:** concluída para o Wikimedia Commons (o upload próprio fica para a Fase D) · **Comando:** `python -m ingest.carga.parte7_fotos`
**Código:** `ingest/carga/parte7_fotos.py` · **Relatório:** `ingest/relatorios/parte7_fotos.md`
**Decisões:** D-008

## Regras

- Nada de Lattes nem Google Acadêmico.
- **Padrão de todo perfil: avatar com as iniciais.**
- Fotos externas só do Wikimedia Commons, **com licença livre** (CC0, domínio público, CC BY, CC BY-SA), exibidas com **autor e licença**.
- Conversão para **WebP**, lado máximo de **400 px**, qualidade ~80, **sem EXIF** (verificado nos arquivos gerados).
- O upload pelo próprio pesquisador entra com a reivindicação de perfil (Fase D).

## Como funciona

1. Toma os 82.901 ORCIDs dos pesquisadores do recorte.
2. Consulta o Wikidata (P496 + P18) em **lotes de 200 ORCIDs com `VALUES`**, que são consultas leves.
   - A primeira tentativa, uma consulta global ("todas as pessoas com ORCID e foto"), estourava o tempo do serviço; foi interrompida em vez de insistir.
3. Busca os metadados no Commons (licença, autor, miniatura de 400 px) em lotes de 50.
4. Filtra as licenças livres, baixa a miniatura, converte e grava.

## Resultado

| Item | Valor |
|---|---|
| ORCIDs consultados | 82.901 |
| **Fotos gravadas** | **43** (588 KB no total) |
| Licenças | CC BY-SA 4.0: 25 · CC BY 2.0: 5 · CC BY 4.0: 4 · CC0: 2 · CC BY-SA 3.0: 2 · CC BY-SA 2.0: 2 · CC BY 3.0: 2 · CC BY 3.0 BR: 1 |
| Com marca "personality rights" | 6. Pede cuidado com uso comercial da imagem da pessoa; o uso informativo é aceitável, mas revisar no lançamento |

## Saídas

Fotos em `ingest/dados/fotos/<researcher_id>.webp` (fora do git), servidas pelo app em `/foto/<id>`. Créditos em `researcher_photos.csv`, que vai para a tabela `researcher_photos`.
