import { redirect } from "next/navigation";

// O mapa fica no painel (D-039); os parâmetros seguem junto.
export default function PaginaMapa({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(searchParams)) for (const x of [v].flat()) if (x != null) qs.append(k, x);
  redirect(qs.toString() ? `/painel?${qs}` : "/painel");
}
