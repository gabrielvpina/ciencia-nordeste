# Etapa 3 — Grupos de pesquisa

**Status:** aguardando o pedido de acesso à informação (LAI) · **Documento do pedido:** [`../pedido_lai_cnpq.md`](../pedido_lai_cnpq.md)
**Decisões:** D-002 (sem scraping do Lattes/DGP), D-007 (LAI + pilotos)

## Objetivo

Trazer os grupos de pesquisa certificados do Diretório dos Grupos de Pesquisa (DGP/CNPq) do recorte, ligando cada grupo à instituição e os líderes aos pesquisadores.

## O que o diagnóstico encontrou

- **Não há download em lote oficial do DGP.** O site do CNPq não lista conjunto de dados de grupos, e `dadosabertos.cnpq.br` bloqueia tudo no robots.txt.
- **Fazer crawler do DGP ou do Lattes está fora das regras do projeto** (D-002).
- **Portais das universidades do NE**: só 2 de 10 publicam conjunto de grupos (UFRN e UFS). Pela amostra, são cerca de 56 grupos de saúde e biológicas. Isso serve como piloto, mas não cobre a região.
- A categoria de **bolsa de produtividade** dos docentes de pós já vem da CAPES (coluna `CD_CAT_BOLSA_PRODUTIVIDADE`, etapa 2).

## O que foi feito

- Pedido LAI redigido para o Fala.BR (`docs/pedido_lai_cnpq.md`). Ele pede os grupos certificados ativos do NE em Ciências da Saúde e Biológicas (mais Biotecnologia e Genética), com ID, instituição, UF, área, líderes e linhas de pesquisa, e também os bolsistas PQ/DT vigentes. O texto não pede dados pessoais sensíveis.

## Próximos passos

1. **Responsável:** enviar o pedido pelo Fala.BR e registrar o protocolo em `docs/decisoes.md`. O prazo legal é de 20 dias, prorrogáveis por mais 10.
2. Ao receber: guardar o arquivo em `ingest/dados/brutos/cnpq/` e implementar a carga, ligando grupos às instituições (nome + UF, com fila de revisão) e líderes aos pesquisadores. O ID Lattes entra só como evidência.
3. Se o pedido for negado por LGPD: recorrer citando que os nomes dos líderes já são públicos no espelho de cada grupo, ou aceitar a base sem nomes.
4. Considerar também o recorte ampliado (agrárias, alimentos, veterinária), que é posterior ao texto do pedido.
