// Busca do site (D-044): só roda ao apertar o botão (ou Enter), nunca a cada letra digitada.
// Três partes: (1) nomes — pesquisadores, instituições e programas por texto (trigrama, barato);
// (2) tema — pesquisadores pela busca vetorial (embed + HNSW), pulada quando a consulta parece um nome;
// (3) trabalhos — publicações do tema e teses/dissertações cujo título ou palavras-chave trazem os termos.
// Resultados ficam num cache em memória: consultas repetidas (exemplos, links compartilhados) não recalculam nada.
import { q } from "@/lib/db";
import { colWorks } from "@/lib/qualis-filtro";
import { buscaPorTema } from "@/lib/vetorial";
import { TERMO_MAX, TERMO_MIN, type ItemNome, type ResultadoNomes, type ResultadoPesquisa, type Tese } from "@/lib/busca-tipos";

const SIM_NOME = 0.6;       // similaridade (trigrama) a partir da qual a consulta é tratada como nome de pessoa

async function buscaPorNome(termo: string, sq: boolean): Promise<ResultadoNomes & { simPesquisador: number; siglaExata: boolean }> {
  const W = colWorks(sq);
  const [pesquisadores, instituicoes, programas] = await Promise.all([
    termo.length >= 3
      ? q<ItemNome & { sim: number }>(
          `SELECT id, display_name AS nome, concat_ws(' · ', instituicao_sigla, uf, CASE WHEN ${W} > 0 THEN ${W} || ' publicações' END) AS detalhe,
                  similarity(normalized_name, upper(f_unaccent($1)))::float AS sim
             FROM mv_pesquisador_busca WHERE normalized_name % upper(f_unaccent($1))
            ORDER BY similarity(normalized_name, upper(f_unaccent($1))) DESC, ${W} DESC LIMIT 12`, [termo])
      : Promise.resolve([]),
    q<ItemNome & { sigla: boolean }>(
      `SELECT i.id, i.name AS nome, concat_ws(' · ', i.acronym, i.uf, s.${W} || ' publicações') AS detalhe,
              upper(f_unaccent(i.acronym)) = upper(f_unaccent($1)) AS sigla
         FROM institutions i JOIN mv_instituicao_stats s ON s.institution_id = i.id
        WHERE (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1)) OR lower(f_unaccent(i.name)) LIKE '%' || lower(f_unaccent($1)) || '%'
               OR lower(f_unaccent(i.name)) % lower(f_unaccent($1)))
          AND (s.${W} > 0 OR s.programas > 0)
        ORDER BY (upper(f_unaccent(i.acronym)) = upper(f_unaccent($1))) DESC, s.${W} DESC LIMIT 8`, [termo]),
    q<ItemNome>(
      `SELECT id, name AS nome, concat_ws(' · ', entity_acronym, uf, 'conceito ' || grade) AS detalhe FROM graduate_programs
        WHERE lower(f_unaccent(name)) LIKE '%' || lower(f_unaccent($1)) || '%' OR upper(entity_acronym) = upper($1)
        ORDER BY grade DESC, name LIMIT 8`, [termo]),
  ]);
  return {
    pesquisadores: pesquisadores.map(({ id, nome, detalhe }) => ({ id, nome, detalhe })),
    instituicoes: instituicoes.map(({ id, nome, detalhe }) => ({ id, nome, detalhe })),
    programas,
    simPesquisador: pesquisadores[0]?.sim ?? 0,
    siglaExata: instituicoes.some((i) => i.sigla),
  };
}

// Mesma expressão do índice da migração 0019 (theses_texto_idx). A consulta vira "palavra1 | palavra2 | …".
const VETOR_TESE = `to_tsvector('portuguese', f_unaccent(coalesce(t.title, '') || ' ' || coalesce(t.keywords, '')))`;
// Para ordenar (só nas linhas que já casaram): o título pesa mais que as palavras-chave.
const PESO_TESE = `setweight(to_tsvector('portuguese', f_unaccent(coalesce(t.title, ''))), 'A') || setweight(to_tsvector('portuguese', f_unaccent(coalesce(t.keywords, ''))), 'C')`;
async function buscaTeses(termo: string): Promise<Tese[]> {
  return q<Tese>(
    `WITH c AS (SELECT nullif(replace(plainto_tsquery('portuguese', f_unaccent($1))::text, ' & ', ' | '), '')::tsquery AS tq)
     SELECT t.id, upper(left(t.title, 1)) || lower(substr(t.title, 2)) AS titulo, initcap(lower(t.degree)) AS grau, t.year AS ano,
            concat_ws(' · ', g.entity_acronym, g.uf) AS detalhe, t.full_text_url AS url, t.program_id AS programa
       FROM theses t CROSS JOIN c LEFT JOIN graduate_programs g ON g.id = t.program_id
      WHERE c.tq IS NOT NULL AND ${VETOR_TESE} @@ c.tq AND t.degree IN ('DISSERTAÇÃO', 'TESE')
      ORDER BY ts_rank(${PESO_TESE}, c.tq) DESC, t.year DESC NULLS LAST LIMIT 8`, [termo]);
}

// ---- cache em memória (por processo): até CACHE_MAX consultas, valendo CACHE_MS ----
const CACHE_MAX = 300;
const CACHE_MS = 6 * 60 * 60 * 1000;
const cache = new Map<string, { em: number; r: Promise<ResultadoPesquisa> }>();

/** `forcarTema`: roda a busca por tema mesmo quando a consulta parece um nome (link "buscar como tema"). */
export function pesquisar(termoBruto: string, sq: boolean, forcarTema = false): Promise<ResultadoPesquisa> {
  const termo = termoBruto.trim().replace(/\s+/g, " ").slice(0, TERMO_MAX);
  const chave = `${sq ? 1 : 0}|${forcarTema ? 1 : 0}|${termo.toLowerCase()}`;
  const achado = cache.get(chave);
  if (achado && Date.now() - achado.em < CACHE_MS) {
    cache.delete(chave); cache.set(chave, achado);   // mais recente no fim (LRU)
    return achado.r;
  }
  const r = calcular(termo, sq, forcarTema);
  cache.set(chave, { em: Date.now(), r });
  r.catch(() => cache.delete(chave));                // erro não fica guardado
  while (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value!);
  return r;
}

async function calcular(termo: string, sq: boolean, forcarTema: boolean): Promise<ResultadoPesquisa> {
  const t0 = Date.now();
  const vazio = { pesquisadores: [], instituicoes: [], programas: [] };
  if (termo.length < TERMO_MIN) return { termo, nomes: vazio, tema: null, pareceNome: false, teses: [], ms: 0 };
  const { simPesquisador, siglaExata, ...nomes } = await buscaPorNome(termo, sq);
  // Parece nome: sigla exata de instituição ou nome de pessoa muito parecido. (Palavra dentro do nome de uma instituição
  // não conta: "caprinos" está em "Embrapa Caprinos e Ovinos" e é um tema.)
  const pareceNome = siglaExata || simPesquisador >= SIM_NOME;
  const rodaTema = termo.length >= 3 && (forcarTema || !pareceNome);
  const [tema, teses] = await Promise.all([
    rodaTema ? buscaPorTema(termo, "hibrido", sq) : Promise.resolve(null),
    rodaTema ? buscaTeses(termo) : Promise.resolve([]),
  ]);
  return { termo, nomes, tema, pareceNome, teses, ms: Date.now() - t0 };
}
