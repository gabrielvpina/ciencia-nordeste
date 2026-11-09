import { readFile } from "node:fs/promises";
import path from "node:path";

const UUID = /^[0-9a-f-]{36}$/i;
const DIR = process.env.FOTOS_DIR ?? "/app/fotos";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  if (!UUID.test(params.id)) return new Response("not found", { status: 404 });
  try {
    const dados = await readFile(path.join(DIR, `${params.id}.webp`));
    return new Response(dados, { headers: { "content-type": "image/webp", "cache-control": "public, max-age=86400" } });
  } catch {
    return new Response("not found", { status: 404 });
  }
}
