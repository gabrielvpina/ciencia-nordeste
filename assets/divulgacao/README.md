# Peças de divulgação

Imagens para redes sociais no estilo dos cartões do quiz ("Registro de campo", D-049/D-050; `docs/arte-banners.md`).
Três mensagens, cinco formatos cada. Os números vêm do banco (`mv_resumo`) no dia da geração (2026-11-16).

| peça | mensagem | legenda sugerida |
|---|---|---|
| `o-que-e-*` | O que é o Ciência Nordeste: os números da base | Quem pesquisa o quê no Nordeste? Pesquisadores, publicações, instituições e programas de pós em saúde, ciências biológicas e agrárias, num só lugar e com dados abertos. ciencianordeste.com.br |
| `quiz-*` | Que cientista é você? Como funciona o quiz | Descubra o seu perfil de cientista em uns 2 minutos e veja quem no Nordeste pesquisa como você. ciencianordeste.com.br/quiz |
| `por-que-*` | Por que fazer o quiz: ciência se faz em rede | Orientação, pós-graduação e colaboração começam por saber quem pesquisa o mesmo que você. Faça o quiz e compartilhe o seu cartão. ciencianordeste.com.br/quiz |

| formato | tamanho | uso | zona segura respeitada |
|---|---|---|---|
| `instagram-post` | 1080 × 1350 (4:5) | feed do Instagram e do Facebook | margens de 64–72 px |
| `instagram-story` | 1080 × 1920 (9:16) | stories e status do WhatsApp | 230 px no topo e 210 px embaixo livres de texto |
| `tiktok` | 1080 × 1920 (9:16) | TikTok, Reels e Shorts | 190 px no topo, 430 px embaixo e 168 px à direita (botões) |
| `linkedin-quadrado` | 1200 × 1200 (1:1) | post com imagem no LinkedIn | margens de 72 px |
| `linkedin-paisagem` | 1200 × 627 (1,91:1) | imagem de link ou post horizontal no LinkedIn | margens de 44–52 px |

## Como gerar de novo

O gerador (`gerador.route.tsx`) usa as mesmas fontes, cores e o mesmo motor (next/og) dos cartões do quiz. Ele não fica
no site: para regenerar (por exemplo, com números novos), copie-o para `apps/web/app/api/divulgacao/[peca]/route.tsx`,
reconstrua o `web` localmente e baixe as imagens:

```bash
mkdir -p "apps/web/app/api/divulgacao/[peca]" && cp assets/divulgacao/gerador.route.tsx "apps/web/app/api/divulgacao/[peca]/route.tsx"
docker compose build web && docker compose up -d web
for p in o-que-e quiz por-que; do for f in instagram-post instagram-story tiktok linkedin-quadrado linkedin-paisagem; do
  curl -s -o assets/divulgacao/$p-$f.png "http://localhost:3000/api/divulgacao/$p?f=$f"; done; done
rm -r apps/web/app/api/divulgacao && docker compose build web && docker compose up -d web
```
