// Match do quiz (etapa 13, D-036): das respostas de NICHO aos pesquisadores mais alinhados do Nordeste.
// Este módulo não lê as respostas de perfil (habitat, estilo, vínculo), que só montam o título do banner:
// as mesmas respostas de nicho dão sempre os mesmos pesquisadores, na mesma ordem e com os mesmos índices.
import { q } from "@/lib/db";
import { embedConsulta } from "@/lib/vetorial";
import { ARVORE, type Opcao } from "./estrutura";

// ---------------------------------------------------------------- constantes (documentadas na D-036)
/** Peso de cada componente no índice de compatibilidade (0–100). Somam 1. */
export const PESO_INDICE = {
  cobertura: 0.3,       // facetas respondidas fora do núcleo (objeto, foco, escala, ambiente, impacto): fração das publicações do nicho
                        // que casa cada uma, ponderada pelo peso da faceta (contínua; o núcleo já é exigido para entrar)
  concentracao: 0.2,    // parte da produção do pesquisador que cai no nicho
  volume: 0.2,          // quantas publicações no nicho (satura em VOLUME_CHEIO)
  afinidade: 0.3,       // similaridade do perfil temático com a frase do nicho, entre o percentil 90 (0) e o 99,9 (1) da população
} as const;
export const CONCENTRACAO_CHEIA = 0.5;   // metade da produção no nicho = concentração máxima
export const VOLUME_CHEIO = 15;          // publicações no nicho que dão o volume máximo
export const MIN_NICHO = 2;              // publicações que casam o núcleo (método e sub-objeto) para entrar
export const MIN_INDICE = 35;            // abaixo disto, não aparece (o banner mostra "até 5")
export const PESO_PROEMINENCIA = 3;      // pontos de ordenação (não do índice) dados pela proeminência (0–1)
export const POR_INSTITUICAO = { banner: 2, lista: 3 };   // diversidade
export const N = { banner: 5, lista: 15 };

export type Filtro = { tipo: "ne" } | { tipo: "uf" } | { tipo: "raio"; km: number };

export type Alinhado = {
  id: string; nome: string; indice: number; ordem: number;
  instituicao_id: string | null; sigla: string | null; instituicao: string | null; municipio: string | null; uf: string | null;
  lat: number | null; lon: number | null; distancia_km: number | null;
  n_nicho: number; desde: number | null; facetas: string[]; programa: string | null; programa_id: string | null;
  exemplos: { titulo: string; ano: number; doi: string | null }[];
};

export type Resultado = {
  versao: number; nucleo: string[]; vetorial: boolean; candidatos: number; tempos?: Record<string, number>;
  banner: Alinhado[]; lista: Alinhado[];
  instituicoes: { id: string; nome: string; sigla: string | null; uf: string; n: number }[];
  programas: { id: string; nome: string; sigla: string | null; uf: string; n: number }[];
  origem: { id: string; uf: string } | null;
};

/** A instituição do usuário e as ligadas a ela (parent/child do ROR e vínculo de subunidade, D-030). */
async function instituicoesExcluidas(inst: string | null): Promise<string[]> {
  if (!inst) return [];
  const r = await q<{ id: string }>(
    `SELECT $1::uuid AS id
     UNION SELECT related_institution_id FROM institution_relations WHERE institution_id = $1 AND relation IN ('parent', 'child') AND related_institution_id IS NOT NULL
     UNION SELECT institution_id FROM institution_relations WHERE related_institution_id = $1 AND relation IN ('parent', 'child')
     UNION SELECT institution_id FROM v_instituicao_vinculo WHERE parent_id = $1
     UNION SELECT parent_id FROM v_instituicao_vinculo WHERE institution_id = $1`, [inst]);
  return r.map((x) => x.id);
}

/** O núcleo: método e sub-objeto (ou objeto, se o sub-objeto foi pulado). Se faltar um, o outro sozinho. */
function nucleo(nicho: Map<string, Opcao>): Opcao[] {
  const alvo = nicho.get("sub_objeto") ?? nicho.get("objeto");
  return [nicho.get("metodo"), alvo].filter((o): o is Opcao => !!o?.sinais && Object.keys(o.sinais).length > 0);
}

export async function alinhar(nicho: Map<string, Opcao>, opts: { instituicao: string | null; soQualis: boolean; filtro?: Filtro }): Promise<Resultado> {
  const facetas = [...nicho.entries()].filter(([, o]) => o.sinais && (o.sinais.topics || o.sinais.subfields || o.sinais.fields || o.sinais.termos));
  const nuc = nucleo(nicho);
  const vazio: Resultado = { versao: ARVORE.versao, tempos: {}, nucleo: nuc.map((o) => o.id), vetorial: false, candidatos: 0, banner: [], lista: [], instituicoes: [], programas: [], origem: null };
  if (!nuc.length) return vazio;

  const ids = facetas.map(([, o]) => o.id);
  const pesos = facetas.map(([f]) => ARVORE.pesos_faceta[f] ?? 1);
  const frase = facetas.map(([, o]) => o.sinais?.frase).filter(Boolean).join(" · ");
  const t0 = Date.now();
  const vetor = frase ? await embedConsulta(frase) : null;
  const t1 = Date.now();
  const pA = vetor ? PESO_INDICE.afinidade : 0;
  const soma = PESO_INDICE.cobertura + PESO_INDICE.concentracao + PESO_INDICE.volume + pA;   // sem vetor, os outros se renormalizam
  const filtro = opts.filtro ?? { tipo: "ne" };
  const excluidas = await instituicoesExcluidas(opts.instituicao);
  // âncoras da afinidade: percentis 90 e 99,9 da similaridade entre a frase e TODOS os perfis (uma vez por consulta)
  const [anc] = vetor ? await q<{ p90: number; p999: number }>(
    `SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY s) AS p90, percentile_cont(0.999) WITHIN GROUP (ORDER BY s) AS p999
       FROM (SELECT 1 - (embedding <=> $1::halfvec) AS s FROM researcher_embeddings) x`, [vetor]) : [{ p90: 0, p999: 1 }];
  // filtro Qualis (D-035): JOIN direto, para o plano não testar publicação a publicação
  const juntaQualis = opts.soQualis ? "JOIN mv_work_qualis mq ON mq.work_id = qw.work_id" : "";

  const linhas = await q<Alinhado & { inst_ok: boolean }>(
    `WITH sel AS (SELECT * FROM unnest($1::text[], $2::real[]) AS s(opcao_id, peso)),
     origem AS (SELECT latitude AS lat, longitude AS lon, uf FROM institutions WHERE id = $3),
     ow AS MATERIALIZED (SELECT qw.work_id, qw.opcao_id, qw.v * s.peso AS v, s.peso FROM quiz_opcao_work qw JOIN sel s USING (opcao_id) ${juntaQualis}),
     nicho AS (SELECT work_id, sum(v) AS v FROM ow GROUP BY work_id
                HAVING count(*) FILTER (WHERE opcao_id = ANY($4::text[])) = cardinality($4::text[])),
     nr AS MATERIALIZED (SELECT DISTINCT a.researcher_id AS rid, n.work_id, n.v FROM nicho n JOIN work_authorships a ON a.work_id = n.work_id WHERE a.researcher_id IS NOT NULL),
     cand AS MATERIALIZED (SELECT rid, count(*)::int AS n_nicho, sum(v) AS soma FROM nr GROUP BY rid HAVING count(*) >= ${MIN_NICHO}),
     cob AS MATERIALIZED (SELECT x.rid, sum(x.peso_faceta * x.n / c.n_nicho) FILTER (WHERE NOT x.opcao_id = ANY($4::text[])) AS cobertos,
                    array_agg(x.opcao_id) AS ops
               FROM (SELECT nr.rid, ow.opcao_id, ow.peso AS peso_faceta, count(*)::real AS n
                       FROM nr JOIN cand USING (rid) JOIN ow ON ow.work_id = nr.work_id GROUP BY 1, 2, 3) x
               JOIN cand c ON c.rid = x.rid GROUP BY x.rid),   -- quanto das publicações do nicho casa cada faceta fora do núcleo
     tot AS (SELECT researcher_id AS rid, n_works AS n FROM researcher_embeddings),   -- produção no recorte (perfil temático, 0012)
     sims AS MATERIALIZED (SELECT e.researcher_id AS rid,
                      least(1, greatest(0, (1 - (e.embedding <=> $6::halfvec) - $10::float8) / nullif($11::float8 - $10::float8, 0))) AS pct
                 FROM researcher_embeddings e JOIN cand c ON c.rid = e.researcher_id WHERE $6::halfvec IS NOT NULL),
     base AS (
       SELECT r.id, r.display_name AS nome, c.n_nicho, c.soma, t.n AS n_total, cb.cobertos, cb.ops, coalesce(sm.pct, 0) AS afin,
              i.id AS instituicao_id, i.acronym AS sigla, i.name AS instituicao, m.name AS municipio, i.uf, i.latitude AS lat, i.longitude AS lon,
              (SELECT 6371 * 2 * asin(sqrt(power(sin(radians(i.latitude - o.lat) / 2), 2)
                      + cos(radians(o.lat)) * cos(radians(i.latitude)) * power(sin(radians(i.longitude - o.lon) / 2), 2))) FROM origem o) AS distancia_km,
              (0.4 * least(1, ln(1 + coalesce(s.works_count_period, 0)) / ln(51)) + 0.3 * least(1, coalesce(s.h_index_openalex, 0) / 30.0)
                 + 0.15 * r.is_capes_faculty::int + 0.15 * (r.pq_category_latest IS NOT NULL)::int) AS proeminencia
         FROM cand c JOIN researchers r ON r.id = c.rid AND NOT r.is_hidden
         JOIN tot t ON t.rid = c.rid JOIN cob cb ON cb.rid = c.rid
         LEFT JOIN sims sm ON sm.rid = c.rid
         LEFT JOIN researcher_openalex_stats s ON s.researcher_id = r.id
         LEFT JOIN institutions i ON i.id = r.main_institution_id
         LEFT JOIN municipalities m ON m.ibge_code = i.municipality_ibge
        WHERE r.main_institution_id IS NULL OR r.main_institution_id <> ALL($5::uuid[]))
     SELECT *, round(100 * (${PESO_INDICE.cobertura} * CASE WHEN $7::real = 0 THEN 1 ELSE least(1, coalesce(cobertos, 0) / $7::real) END
                            + ${PESO_INDICE.concentracao} * least(1, (n_nicho::real / greatest(n_total, 1)) / ${CONCENTRACAO_CHEIA})
                            + ${PESO_INDICE.volume} * least(1, ln(1 + n_nicho) / ln(${1 + VOLUME_CHEIO}))
                            + ${pA} * afin) / ${soma})::int AS indice
       FROM base
      WHERE ($8 = 'ne') OR ($8 = 'uf' AND uf = (SELECT uf FROM origem)) OR ($8 = 'raio' AND distancia_km <= $9::real)
      ORDER BY indice DESC, proeminencia DESC LIMIT 300`,
    [ids, pesos, opts.instituicao, nuc.map((o) => o.id), excluidas, vetor,
      facetas.reduce((t, [f, o]) => t + (nuc.some((n) => n.id === o.id) ? 0 : ARVORE.pesos_faceta[f] ?? 1), 0), filtro.tipo,
      filtro.tipo === "raio" ? filtro.km : null, anc.p90, anc.p999]);

  const t2 = Date.now();
  const elegiveis = linhas
    .filter((l) => l.indice >= MIN_INDICE)
    .map((l) => ({ ...l, ordem: l.indice + PESO_PROEMINENCIA * Number((l as unknown as { proeminencia: number }).proeminencia) }))
    .sort((a, b) => b.ordem - a.ordem);
  const diverso = (max: number, n: number) => {
    const conta = new Map<string, number>(), out: typeof elegiveis = [];
    for (const l of elegiveis) {
      const k = l.instituicao_id ?? `sem-${l.id}`;
      if ((conta.get(k) ?? 0) >= max) continue;
      conta.set(k, (conta.get(k) ?? 0) + 1);
      out.push(l);
      if (out.length >= n) break;
    }
    return out;
  };
  const lista = diverso(POR_INSTITUICAO.lista, N.lista);
  const banner = diverso(POR_INSTITUICAO.banner, N.banner);

  // detalhes só de quem vai aparecer: exemplos de publicações do nicho, programa de pós e "desde"
  const ids_mostrar = [...new Set([...banner, ...lista].map((l) => l.id))];
  const detalhes = ids_mostrar.length ? await q<{ rid: string; exemplos: Alinhado["exemplos"]; desde: number | null; programa: string | null; programa_id: string | null }>(
    `WITH sel AS (SELECT * FROM unnest($2::text[], $3::real[]) AS s(opcao_id, peso)),
     nicho AS (SELECT qw.work_id, sum(qw.v * s.peso) AS v FROM quiz_opcao_work qw JOIN sel s USING (opcao_id) GROUP BY 1
                HAVING count(*) FILTER (WHERE qw.opcao_id = ANY($4::text[])) = cardinality($4::text[]))
     SELECT r.rid,
            (SELECT json_agg(json_build_object('titulo', w.title, 'ano', w.year, 'doi', w.doi) ORDER BY n.v DESC, w.year DESC)
               FROM (SELECT DISTINCT a.work_id FROM work_authorships a WHERE a.researcher_id = r.rid) aw JOIN nicho n ON n.work_id = aw.work_id
               JOIN works w ON w.id = aw.work_id WHERE NOT $5 OR EXISTS (SELECT 1 FROM mv_work_qualis mq WHERE mq.work_id = w.id)
              LIMIT 2) AS exemplos,
            (SELECT min(w.year) FROM work_authorships a JOIN nicho n ON n.work_id = a.work_id JOIN works w ON w.id = a.work_id WHERE a.researcher_id = r.rid) AS desde,
            (SELECT g.name FROM program_faculty f JOIN graduate_programs g ON g.id = f.program_id WHERE f.researcher_id = r.rid ORDER BY f.base_year DESC LIMIT 1) AS programa,
            (SELECT g.id::text FROM program_faculty f JOIN graduate_programs g ON g.id = f.program_id WHERE f.researcher_id = r.rid ORDER BY f.base_year DESC LIMIT 1) AS programa_id
       FROM unnest($1::uuid[]) AS r(rid)`,
    [ids_mostrar, ids, pesos, nuc.map((o) => o.id), opts.soQualis]) : [];
  const t3 = Date.now();
  const det = new Map(detalhes.map((d) => [d.rid, d]));
  const rotulo = new Map(facetas.map(([, o]) => [o.id, o.rotulo]));
  const completar = (l: (typeof elegiveis)[number]): Alinhado => {
    const d = det.get(l.id);
    const ops = (l as unknown as { ops: string[] }).ops ?? [];
    return {
      id: l.id, nome: l.nome, indice: l.indice, ordem: Math.round(l.ordem * 10) / 10, instituicao_id: l.instituicao_id, sigla: l.sigla,
      instituicao: l.instituicao, municipio: l.municipio, uf: l.uf, lat: l.lat, lon: l.lon,
      distancia_km: l.distancia_km == null ? null : Math.round(Number(l.distancia_km)),
      n_nicho: l.n_nicho, desde: d?.desde ?? null, facetas: [...new Set(ops)].map((x) => rotulo.get(x) ?? x),
      programa: d?.programa ?? null, programa_id: d?.programa_id ?? null, exemplos: (d?.exemplos ?? []).slice(0, 2),
    };
  };

  // instituições e programas mais alinhados (soma dos índices dos 60 primeiros), fora da instituição do usuário
  const topo = elegiveis.slice(0, 60);
  const instMap = new Map<string, { id: string; nome: string; sigla: string | null; uf: string; n: number }>();
  for (const l of topo) if (l.instituicao_id && l.instituicao) {
    const x = instMap.get(l.instituicao_id) ?? { id: l.instituicao_id, nome: l.instituicao, sigla: l.sigla, uf: l.uf ?? "", n: 0 };
    x.n += 1; instMap.set(l.instituicao_id, x);
  }
  const programas = topo.length ? await q<Resultado["programas"][number]>(
    `SELECT g.id, g.name AS nome, g.entity_acronym AS sigla, g.uf, count(DISTINCT f.researcher_id)::int AS n
       FROM program_faculty f JOIN graduate_programs g ON g.id = f.program_id
      WHERE f.researcher_id = ANY($1::uuid[]) AND (g.institution_id IS NULL OR g.institution_id <> ALL($2::uuid[]))
      GROUP BY g.id ORDER BY n DESC, g.name LIMIT 6`,
    [topo.map((l) => l.id), opts.instituicao ? [opts.instituicao] : []]) : [];
  const origem = opts.instituicao ? (await q<{ id: string; uf: string }>(`SELECT id, uf FROM institutions WHERE id = $1`, [opts.instituicao]))[0] ?? null : null;

  return {
    versao: ARVORE.versao, nucleo: nuc.map((o) => o.id), vetorial: !!vetor, candidatos: elegiveis.length,
    tempos: { embed: t1 - t0, ranking: t2 - t1, detalhes: t3 - t2, resto: Date.now() - t3 },
    banner: banner.map(completar), lista: lista.map(completar),
    instituicoes: [...instMap.values()].sort((a, b) => b.n - a.n).slice(0, 6), programas, origem,
  };
}
