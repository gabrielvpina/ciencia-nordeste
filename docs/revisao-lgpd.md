# Revisão simples de proteção de dados (LGPD)

- **Data:** 2026-11-11 (pedido do responsável; decisão D-041)
- **Alcance:** dados pessoais tratados pelo site e pelo quiz, como estão no branch `quiz`.
- **Natureza:** é uma checagem técnica feita a partir do código e da configuração, à luz da LGPD (Lei 13.709/2018). **Não é parecer jurídico.** Antes de divulgar o quiz amplamente, vale uma leitura por um profissional da área, sobretudo dos pontos marcados como "pendente".

## 1. Inventário dos dados

| Dado | De quem | Origem | Onde fica | Quem lê | Prazo |
|---|---|---|---|---|---|
| Nome, vínculos, publicações, orientações e participação em programas de pós | pesquisadores do NE (~145 mil) | fontes abertas: OpenAlex (CC0), ROR (CC0), CAPES Dados Abertos (CC-BY) | banco do site, público nas páginas | qualquer pessoa | enquanto o projeto existir |
| Foto | 43 pesquisadores | Wikimedia Commons, com licença livre | arquivos do servidor | qualquer pessoa | idem |
| Cadastro do quiz: nome, instituição, filiação, curso ou programa, data, versão do consentimento, código de remoção | quem faz o quiz | a própria pessoa, com consentimento | `quiz_participantes`, gravada pelo papel `quiz_escrita`, que só tem `INSERT` | só o responsável, via `psql` | 24 meses (expurgo automático) |
| Respostas do quiz, pesquisadores indicados (posição e índice) e código numérico da descrição (D-042) | quem conclui o quiz com cadastro | a própria pessoa, com consentimento (termos, revisão "e") | `quiz_alinhamentos` e `quiz_matches`, ligados ao cadastro (`ON DELETE CASCADE`), só `INSERT` | só o responsável | junto com o cadastro (24 meses ou até a remoção) |
| Texto da descrição livre | quem faz o quiz | a própria pessoa | **não é gravado**: vira código numérico (D-040) | — | — |
| IP | visitantes | conexão | só em memória, no limite de pedidos por minuto; o Caddyfile do guia de deploy não liga o log de acesso | — | ~1 minuto |
| Backups do banco (incluem o cadastro) | — | `scripts/backup.sh` | arquivos com permissão só do dono (`umask 077`) | só o responsável | rotação de 14 pacotes |

## 2. Achados e o que foi feito

| # | Ponto | Risco | Situação |
|---|---|---|---|
| 1 | **Transferência internacional.** O servidor fica na AWS `us-east-1` (Virgínia do Norte, EUA), conferido pela lista pública de faixas de IP da AWS. O texto do consentimento não dizia que os dados saem do Brasil. Sem decisão de adequação da ANPD para os EUA, a base mais simples é o consentimento específico e destacado (art. 33, VIII). | alto | **pendente por decisão do responsável**: a caixa de concordância chegou a dizer "num servidor nos EUA (AWS)", mas o responsável pediu um texto curto, sem citar a AWS nem os EUA (versão `2026-11-11d`). Os termos em `/sobre#termos` falam só em "prestadores de infraestrutura" (operadores). **O risco permanece**: o consentimento como base da transferência (art. 33, VIII) pressupõe informar o caráter internacional. Opção mínima: incluir nos termos "inclusive em infraestrutura localizada fora do Brasil", sem citar empresa nem país, ou mudar o servidor para `sa-east-1` (pendência C) |
| 2 | **Canal público para os direitos dos titulares.** O responsável preferiu as issues do GitHub, que são públicas: para pedir remoção, a pessoa teria de escrever o próprio nome em público. | alto | **mitigado**: o cadastro gera um **código de remoção** aleatório (ex.: `K7QM-4TZP`), mostrado uma vez; há um modelo de issue que pede só o código e avisa para não escrever dados pessoais; `scripts/quiz_remover.sh CÓDIGO` apaga o registro. Limite que permanece: pedidos de *acesso* ou *correção* não podem ser respondidos em público. Para eles, ver a pendência A |
| 3 | **Controlador não identificado.** O consentimento citava "o Ciência Nordeste", que não é pessoa jurídica. | médio | **corrigido**: `/sobre` identifica o controlador (o autor, pessoa física) e o canal; o consentimento fala em "o responsável pelo Ciência Nordeste" |
| 4 | **Menores de idade.** "Graduação" pode incluir adolescentes de 17 anos. Dados de crianças e adolescentes têm regras próprias (art. 14) e exigem atenção ao melhor interesse. | médio | **mitigado**: o consentimento inclui "Tenho 18 anos ou mais", e `/sobre` diz que o quiz é para maiores de 18. Ver a pendência B |
| 5 | **Dados dos pesquisadores no quiz.** Os cartões mostram nomes reais com um "índice de compatibilidade", uma finalidade nova (divulgação lúdica) em relação ao mapeamento. | baixo a médio | **mitigado**: só dados públicos e profissionais, títulos neutros (D-036), texto em `/sobre` explicando que o índice vem só das publicações e não avalia pessoas, e opção de ocultar o perfil (sai do site, das buscas e do quiz: `NOT is_hidden`) |
| 6 | **Base legal dos dados públicos.** Dados que o titular tornou manifestamente públicos podem ser tratados se a finalidade for compatível e os direitos, preservados (art. 7º, §§ 3º, 4º e 7º); vale também o interesse legítimo (art. 7º, IX). | baixo | **documentado** em `/sobre` (seção "Dados dos pesquisadores") |
| 7 | **Minimização.** Não há e-mail (migração 0015), IP, navegador, respostas nem resultado gravados. O texto livre não é guardado. | — | **ok** |
| 8 | **Segurança.** O papel só de escrita (o app não lê a tabela), a senha do papel fica no `.env`, há HTTPS (Caddy) e os backups são legíveis só pelo dono. | — | **ok** |
| 9 | **Retenção.** 24 meses com expurgo automático. Um cadastro removido continua nos backups até a rotação (14 pacotes). | baixo | **documentado** (o script de remoção lembra disso) |
| 10 | **Versão do consentimento.** Cadastros novos gravam a versão aceita, hoje `2026-11-11d`: a caixa curta ("Tenho 18 anos ou mais e aceito os termos…") com link para os termos em `/sobre#termos`, em linguagem jurídica neutra. | — | **ok** |
| 11 | **Fotos.** Licença livre no Commons resolve o direito autoral, mas não o direito de imagem do retratado. | baixo | **ok**: as fotos são poucas e já públicas, e a remoção pode ser pedida pelo mesmo canal |

| 12 | **Respostas e resultados guardados (D-042).** Passam a ser gravados para uma futura rede de afinidades. Isso amplia a finalidade (antes era só estatística) e liga o perfil de respostas ao nome. | médio | **mitigado**: termos e consentimento atualizados (versão `2026-11-11e`, finalidade "estatísticas e estudos de redes de afinidade, divulgados só de forma agregada ou sem identificação"); gravação só ao concluir (abrir um link não grava); o texto livre continua fora; a remoção apaga tudo junto. **Atenção para a rede de grafos:** publicar a rede com nomes de participantes exigiria novo consentimento; com nomes de pesquisadores, só dados já públicos |

## 3. Pendências (decisões do responsável)

- **A. Canal privado para acesso e correção.** Com issues públicas, a remoção por código funciona, mas pedidos de acesso ("que dados vocês têm de mim?") ou de correção exigiriam expor dados. Alternativas: um e-mail dedicado (`CONTATO_PRIVACIDADE`, já suportado pelo app) ou um formulário simples sem login. Enquanto não houver, `/sobre` orienta a pedir só a remoção e diz que combinamos um jeito de identificar o cadastro sem expor a pessoa.
- **B. Menores de 18.** Hoje quem tem menos de 18 anos não pode concordar e, portanto, não faz o quiz (o cadastro é obrigatório). Se o público de graduação incluir muitos adolescentes, uma opção é deixar o quiz sem cadastro para eles, sem gravar nada.
- **C. Região do servidor.** Migrar para `sa-east-1` (São Paulo) eliminaria a transferência internacional (achado 1) e simplificaria o consentimento, mas custa cerca de 50% a mais (guia de deploy).
- **D. Revisão por profissional** do texto de consentimento e da seção de privacidade antes de divulgar o quiz amplamente.
- **E. Registro das operações** (art. 37). Este documento e o inventário acima servem de registro simples; convém mantê-los atualizados a cada mudança no que é coletado.
