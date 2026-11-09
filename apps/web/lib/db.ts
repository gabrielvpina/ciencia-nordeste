import { Pool } from "pg";

// Uma pool por processo (evita abrir conexões a cada requisição em dev).
const globalForPg = globalThis as unknown as { pgPool?: Pool };

export const pool =
  globalForPg.pgPool ??
  new Pool({ connectionString: process.env.DATABASE_URL, max: 5 });

if (process.env.NODE_ENV !== "production") globalForPg.pgPool = pool;

export async function q<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  const { rows } = await pool.query(sql, params);
  return rows as T[];
}
