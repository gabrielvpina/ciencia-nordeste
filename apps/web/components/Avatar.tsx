// Foto (Commons, licença livre) ou avatar com iniciais — o padrão de todo perfil (SCHEME §13).
export type Foto = { license: string; author: string | null; source_page_url: string | null } | null;

function iniciais(nome: string) {
  const partes = nome.replace(/[^\p{L}\s-]/gu, "").split(/\s+/).filter((p) => p.length > 2 || /^\p{Lu}/u.test(p));
  return ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
}

export default function Avatar({ id, nome, foto, tamanho = 96 }: { id: string; nome: string; foto?: Foto; tamanho?: number }) {
  if (foto) {
    return (
      <figure className="avatar-fig" style={{ width: tamanho }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/foto/${id}`} alt={`Foto de ${nome}`} width={tamanho} height={tamanho} className="avatar" />
        <figcaption>
          {foto.source_page_url ? <a href={foto.source_page_url} rel="noopener">Foto</a> : "Foto"}: {foto.author || "autor no Commons"} · {foto.license}
        </figcaption>
      </figure>
    );
  }
  return (
    <div className="avatar avatar-ini" style={{ width: tamanho, height: tamanho, fontSize: tamanho / 2.6 }} aria-hidden>
      {iniciais(nome)}
    </div>
  );
}
