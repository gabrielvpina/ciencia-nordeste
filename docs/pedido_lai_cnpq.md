# Pedido de acesso à informação — CNPq (grupos de pesquisa e bolsistas de produtividade)

Rascunho para enviar pela plataforma **Fala.BR** (https://falabr.cgu.gov.br/), escolhendo "Acesso à Informação" e o órgão **CNPq — Conselho Nacional de Desenvolvimento Científico e Tecnológico**. Prazo legal de resposta: 20 dias, prorrogáveis por mais 10 (Lei 12.527/2011, art. 11). Se for negado, cabe recurso em 10 dias (art. 15).

Antes de enviar, ajuste: nome do solicitante, instituição (se houver) e se o pedido sai em nome pessoal ou de um projeto/instituição.

---

**Assunto:** Base de dados dos grupos de pesquisa certificados (DGP) do Nordeste nas áreas da saúde e ciências biológicas, e lista de bolsistas de produtividade vigentes, em formato aberto

**Texto do pedido:**

Prezados,

Com base na Lei nº 12.527/2011 (Lei de Acesso à Informação) e no Decreto nº 7.724/2012, solicito, em formato eletrônico aberto e legível por máquina (CSV ou planilha), as informações abaixo, que estão no Diretório dos Grupos de Pesquisa no Brasil (DGP) e nos sistemas de fomento do CNPq e que já são, em sua maior parte, exibidas publicamente nos espelhos dos grupos no site do DGP.

1. **Grupos de pesquisa certificados e ativos** cuja instituição fica num dos estados do Nordeste (MA, PI, CE, RN, PB, PE, AL, SE, BA) e cuja **grande área predominante** seja Ciências da Saúde ou Ciências Biológicas. Incluir também os grupos de outras grandes áreas cuja área predominante seja Biotecnologia, Genética, Bioquímica, Farmacologia, Imunologia, Microbiologia, Parasitologia ou Saúde Coletiva. Para cada grupo:
   - código/identificador do grupo no DGP e link do espelho;
   - nome do grupo;
   - instituição, sigla, UF e município;
   - grande área e área predominante (e área secundária, se houver);
   - ano de formação e situação (certificado/ativo) com data da última atualização;
   - nome dos líderes e identificador público do currículo Lattes dos líderes (o mesmo exibido no espelho do grupo);
   - linhas de pesquisa (nome);
   - número de pesquisadores, estudantes e técnicos.

2. **Bolsistas de produtividade (PQ e DT) com bolsa vigente** em instituições do Nordeste, nas mesmas áreas: nome, modalidade e nível/categoria, instituição, UF, área e subárea do conhecimento, e vigência (início e término).

Se o volume for grande, aceito o recebimento por link de download. Se houver custo de reprodução, peço que seja informado antes.

Esclareço que **não** solicito dados pessoais sensíveis nem de contato (CPF, endereço, telefone, e-mail). Peço apenas informações relativas à atividade científica financiada ou certificada pelo poder público, de interesse coletivo (art. 8º da Lei 12.527/2011). Se algum campo for considerado restrito, peço a entrega parcial com os demais campos e a indicação do fundamento legal da restrição (art. 7º, § 2º).

Finalidade (informada voluntariamente, não obrigatória pelo art. 10, § 3º): compor um repositório público e sem fins lucrativos da pesquisa em saúde, biotecnologia e genética do Nordeste (projeto Ciência Nordeste), com citação do CNPq como fonte.

Atenciosamente,
[nome do solicitante]

---

## Notas internas

- **Por que pedir assim:** o diagnóstico (Parte 0) não encontrou download em lote oficial do DGP, e fazer crawler do site do DGP ou do Lattes está fora das regras do projeto (D-002).
- **Enquanto a resposta não chega:**
  - A categoria PQ dos docentes de pós já vem na coluna `CD_CAT_BOLSA_PRODUTIVIDADE` do conjunto de docentes da CAPES (Parte 2).
  - Os portais de dados abertos da UFRN e da UFS publicam seus grupos de pesquisa.
- **Quando a resposta chegar:**
  - Registrar a data e o número do protocolo em `docs/decisoes.md`.
  - Guardar o arquivo recebido em `ingest/dados/brutos/cnpq/`.
  - Implementar a Parte 3 ligando grupos às instituições (nome e UF → fila de revisão) e os líderes aos pesquisadores. O ID Lattes entra só como evidência, nunca como identificador exibido sem consentimento.
- **Possível negativa por LGPD dos nomes dos líderes:** recorrer citando que os nomes já são públicos no espelho do grupo, ou aceitar a base sem nomes (os grupos ainda são úteis por instituição e área).
