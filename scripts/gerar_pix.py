"""Gera o Pix de apoio ao site: o código "copia e cola" (BR Code estático do Banco Central) e o QR code em SVG.

  python3 scripts/gerar_pix.py

Escreve apps/web/lib/pix.ts (constantes usadas por components/Apoio.tsx). Sem dependências: o codificador de QR code
abaixo segue a norma ISO/IEC 18004 (modo byte, correção de erros nível M), no estilo da implementação de referência de
Nayuki (MIT). Rode de novo só se a chave, o nome ou a cidade mudarem.
"""
from __future__ import annotations

import pathlib

CHAVE = "eb5df9d2-590c-4b18-af73-21af03a7b883"   # chave aleatória
NOME = "CIENCIA NORDESTE"      # até 25 caracteres, sem acento (o app do banco mostra o titular real da chave)
CIDADE = "BRASIL"              # até 15 caracteres
DESCRICAO = "Apoio ao Ciencia Nordeste"
SAIDA = pathlib.Path(__file__).resolve().parent.parent / "apps/web/lib/pix.ts"


# ---------- BR Code (manual do BR Code, Banco Central) ----------
def campo(id_: str, valor: str) -> str:
    assert len(valor) <= 99, (id_, valor)
    return f"{id_}{len(valor):02d}{valor}"


def crc16(s: str) -> str:
    crc = 0xFFFF
    for b in s.encode():
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def br_code() -> str:
    conta = campo("00", "br.gov.bcb.pix") + campo("01", CHAVE) + campo("02", DESCRICAO)
    s = (campo("00", "01") + campo("26", conta) + campo("52", "0000") + campo("53", "986") + campo("58", "BR")
         + campo("59", NOME) + campo("60", CIDADE) + campo("62", campo("05", "***")) + "6304")
    return s + crc16(s)


# ---------- QR code (modo byte, nível M) ----------
ECC_POR_BLOCO = [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26]
BLOCOS = [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16]
FORMATO_M = 0


def modulos_brutos(v: int) -> int:
    r = (16 * v + 128) * v + 64
    if v >= 2:
        n = v // 7 + 2
        r -= (25 * n - 10) * n - 55
        if v >= 7:
            r -= 36
    return r


def codewords_dados(v: int) -> int:
    return modulos_brutos(v) // 8 - ECC_POR_BLOCO[v] * BLOCOS[v]


def gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_divisor(grau: int) -> list[int]:
    r = [0] * (grau - 1) + [1]
    raiz = 1
    for _ in range(grau):
        for j in range(grau):
            r[j] = gf_mul(r[j], raiz)
            if j + 1 < grau:
                r[j] ^= r[j + 1]
        raiz = gf_mul(raiz, 0x02)
    return r


def rs_resto(dados: list[int], div: list[int]) -> list[int]:
    r = [0] * len(div)
    for b in dados:
        f = b ^ r.pop(0)
        r.append(0)
        for i, c in enumerate(div):
            r[i] ^= gf_mul(c, f)
    return r


def posicoes_alinhamento(v: int, tam: int) -> list[int]:
    if v == 1:
        return []
    n = v // 7 + 2
    passo = (v * 8 + n * 3 + 5) // (n * 4 - 4) * 2
    return [6] + [tam - 7 - i * passo for i in reversed(range(n - 1))]


def qr(texto: str) -> list[list[bool]]:
    dados = texto.encode()
    for v in range(1, len(BLOCOS)):
        bits_contagem = 8 if v <= 9 else 16
        if 4 + bits_contagem + 8 * len(dados) <= codewords_dados(v) * 8:
            break
    else:
        raise ValueError("texto longo demais")
    cap = codewords_dados(v) * 8
    bits: list[int] = []
    def put(val: int, n: int) -> None:
        bits.extend((val >> i) & 1 for i in reversed(range(n)))
    put(0b0100, 4); put(len(dados), bits_contagem)
    for b in dados:
        put(b, 8)
    put(0, min(4, cap - len(bits)))
    put(0, -len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap:
        put(pad, 8); pad ^= 0xEC ^ 0x11
    cw = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    # correção de erros e intercalação dos blocos
    nb, ecl = BLOCOS[v], ECC_POR_BLOCO[v]
    brutos = modulos_brutos(v) // 8
    curtos = nb - brutos % nb
    tam_curto = brutos // nb
    div = rs_divisor(ecl)
    blocos, k = [], 0
    for i in range(nb):
        d = cw[k:k + tam_curto - ecl + (0 if i < curtos else 1)]
        k += len(d)
        e = rs_resto(d, div)
        if i < curtos:
            d = d + [0]
        blocos.append(d + e)
    final = [blk[i] for i in range(len(blocos[0])) for j, blk in enumerate(blocos) if i != tam_curto - ecl or j >= curtos]

    tam = v * 4 + 17
    m = [[False] * tam for _ in range(tam)]
    fn = [[False] * tam for _ in range(tam)]
    def pos(x: int, y: int, escuro: bool) -> None:
        m[y][x] = escuro; fn[y][x] = True
    for i in range(tam):
        pos(6, i, i % 2 == 0); pos(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (tam - 4, 3), (3, tam - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                if 0 <= cx + dx < tam and 0 <= cy + dy < tam:
                    pos(cx + dx, cy + dy, max(abs(dx), abs(dy)) not in (2, 4))
    al = posicoes_alinhamento(v, tam)
    for i, ax in enumerate(al):
        for j, ay in enumerate(al):
            if (i, j) in ((0, 0), (0, len(al) - 1), (len(al) - 1, 0)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    pos(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
    def formato(mask: int) -> None:
        d = FORMATO_M << 3 | mask
        r = d
        for _ in range(10):
            r = (r << 1) ^ ((r >> 9) * 0x537)
        b = (d << 10 | r) ^ 0x5412
        bit = lambda i: (b >> i) & 1 == 1
        for i in range(6):
            pos(8, i, bit(i))
        pos(8, 7, bit(6)); pos(8, 8, bit(7)); pos(7, 8, bit(8))
        for i in range(9, 15):
            pos(14 - i, 8, bit(i))
        for i in range(8):
            pos(tam - 1 - i, 8, bit(i))
        for i in range(8, 15):
            pos(8, tam - 15 + i, bit(i))
        pos(8, tam - 8, True)
    formato(0)   # reserva as áreas
    if v >= 7:
        r = v
        for _ in range(12):
            r = (r << 1) ^ ((r >> 11) * 0x1F25)
        b = v << 12 | r
        for i in range(18):
            bt = (b >> i) & 1 == 1
            a, c = tam - 11 + i % 3, i // 3
            pos(a, c, bt); pos(c, a, bt)
    i = 0
    for direita in range(tam - 1, 0, -2):
        if direita <= 6:
            direita -= 1
        for vert in range(tam):
            for j in range(2):
                x = direita - j
                subindo = ((direita + 1) & 2) == 0
                y = tam - 1 - vert if subindo else vert
                if not fn[y][x] and i < len(final) * 8:
                    m[y][x] = (final[i >> 3] >> (7 - (i & 7))) & 1 == 1
                    i += 1

    mascaras = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
                lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
                lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
                lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]
    def aplicar(k: int) -> None:
        for y in range(tam):
            for x in range(tam):
                if not fn[y][x] and mascaras[k](x, y):
                    m[y][x] = not m[y][x]
    def penalidade() -> int:
        p = 0
        linhas = m + [list(c) for c in zip(*m)]
        for ln in linhas:
            run = 1
            for a, b in zip(ln, ln[1:]):
                if a == b:
                    run += 1
                else:
                    if run >= 5: p += run - 2
                    run = 1
            if run >= 5: p += run - 2
            s = "".join("1" if c else "0" for c in ln)
            p += 40 * (s.count("10111010000") + s.count("00001011101"))
        for y in range(tam - 1):
            for x in range(tam - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    p += 3
        escuros = sum(map(sum, m))
        p += abs(escuros * 20 - tam * tam * 10) // (tam * tam) * 10
        return p
    melhor = None
    for k in range(8):
        aplicar(k); formato(k)
        pen = penalidade()
        if melhor is None or pen < melhor[0]:
            melhor = (pen, k)
        aplicar(k)   # desfaz
    aplicar(melhor[1]); formato(melhor[1])
    return m


def caminho_svg(m: list[list[bool]], borda: int = 4) -> tuple[str, int]:
    partes = []
    for y, ln in enumerate(m):
        x = 0
        while x < len(ln):
            if ln[x]:
                ini = x
                while x < len(ln) and ln[x]:
                    x += 1
                partes.append(f"M{ini + borda} {y + borda}h{x - ini}v1h-{x - ini}z")
            else:
                x += 1
    return "".join(partes), len(m) + 2 * borda


def main() -> None:
    codigo = br_code()
    matriz = qr(codigo)
    d, lado = caminho_svg(matriz)
    SAIDA.write_text(
        "// Gerado por scripts/gerar_pix.py — não edite à mão.\n"
        f"export const PIX_CHAVE = {CHAVE!r};\n"
        f"export const PIX_COPIA_COLA = {codigo!r};\n"
        f"export const PIX_QR = {{ lado: {lado}, d: {d!r} }};\n".replace("'", '"'))
    print(codigo)
    print(f"QR {len(matriz)}×{len(matriz)} → {SAIDA}")


if __name__ == "__main__":
    main()
