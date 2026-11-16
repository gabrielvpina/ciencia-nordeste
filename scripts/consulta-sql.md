docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

Dentro dele, estas consultas ajudam:

-- quantas pessoas e quantos resultados
SELECT (SELECT count(*) FROM quiz_participantes) AS pessoas,
       (SELECT count(*) FROM quiz_alinhamentos)  AS resultados;

-- os últimos 20 cadastros
SELECT criado_em::date, nome, instituicao_texto, filiacao, curso_texto
  FROM quiz_participantes ORDER BY criado_em DESC LIMIT 20;

-- cadastros por dia
SELECT criado_em::date AS dia, count(*) FROM quiz_participantes GROUP BY 1 ORDER BY 1 DESC;

-- por vínculo (graduação, docente…)
SELECT filiacao, count(*) FROM quiz_participantes GROUP BY 1 ORDER BY 2 DESC;

-- respostas mais escolhidas
SELECT r AS opcao, count(*) FROM quiz_alinhamentos, unnest(respostas) r GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

-- pesquisadores mais indicados
SELECT x.display_name, count(*) AS vezes
  FROM quiz_matches m JOIN researchers x ON x.id = m.researcher_id
 GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

Para sair, use \q. Se as linhas ficarem largas demais, \x alterna para a exibição em lista, um campo por linha.

Para uma olhada rápida sem entrar no psql, um comando só resolve:

docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT criado_em::date, nome, instituicao_texto, filiacao FROM quiz_participantes ORDER BY criado_em DESC LIMIT 20;"'
