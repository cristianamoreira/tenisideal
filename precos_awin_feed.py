#!/usr/bin/env python3
"""Lê o Feed de Produtos da Awin e casa com o catálogo para pegar preços oficiais.

MODO DIAGNÓSTICO (este v1): baixa o feed, mostra as colunas, exemplos e a taxa
de casamento com seus 84 tênis. Ainda NÃO grava nada — primeiro a gente valida
o casamento, depois eu ligo a atualização de preços.

Variável de ambiente (secret):
- AWIN_FEED_URL : a URL de download do feed gerada no "Create-a-Feed" da Awin
                  (contém sua chave — por isso vai como secret, nunca no código)
"""
import os
import sys
import io
import csv
import gzip
import re
import json
import unicodedata
import urllib.request

FEED_URL = os.environ.get("AWIN_FEED_URL", "")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


STOP = {"tenis", "de", "corrida", "masculino", "feminino", "unissex", "running",
        "shoes", "shoe", "running", "para", "com"}


def tokens(*partes):
    t = norm(" ".join(p for p in partes if p)).split()
    return set(x for x in t if x not in STOP and len(x) >= 2)


def carregar_catalogo():
    with open("frontend/shoes_data.js", "r", encoding="utf-8") as f:
        c = f.read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def baixar_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": "tenisideal-feed/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
    # tenta descompactar (Awin entrega gzip)
    try:
        raw = gzip.decompress(raw)
    except Exception:
        pass
    return raw.decode("utf-8", "ignore")


def parse_csv(texto):
    # detecta delimitador (vírgula ou pipe)
    primeira = texto.split("\n", 1)[0]
    delim = "|" if primeira.count("|") > primeira.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto), delimiter=delim)), delim


def achar_coluna(cols, *candidatas):
    low = {c.lower(): c for c in cols}
    for cand in candidatas:
        if cand in low:
            return low[cand]
    return None


def main():
    if not FEED_URL:
        print("ERRO: AWIN_FEED_URL não definida.", file=sys.stderr)
        sys.exit(1)

    print("Baixando feed da Awin...", file=sys.stderr)
    texto = baixar_feed(FEED_URL)
    produtos, delim = parse_csv(texto)
    if not produtos:
        print("ERRO: feed vazio ou ilegível.", file=sys.stderr)
        sys.exit(1)

    cols = list(produtos[0].keys())
    print("=" * 70)
    print(f"FEED LIDO: {len(produtos)} produtos | delimitador '{delim}'")
    print("=" * 70)
    print("Colunas disponíveis:")
    for c in cols:
        print(f"   - {c}")

    col_nome = achar_coluna(cols, "product_name", "product name", "name")
    col_marca = achar_coluna(cols, "brand_name", "brand", "merchant_name")
    col_loja = achar_coluna(cols, "merchant_name", "advertiser")
    col_preco = achar_coluna(cols, "search_price", "store_price", "price", "saving_amount")
    col_link = achar_coluna(cols, "aw_deep_link", "deep_link", "merchant_deep_link", "aw_image_url")

    print(f"\nMapeamento detectado:")
    print(f"   nome  → {col_nome}")
    print(f"   marca → {col_marca}")
    print(f"   loja  → {col_loja}")
    print(f"   preço → {col_preco}")
    print(f"   link  → {col_link}")

    print("\n--- 3 exemplos do feed ---")
    for p in produtos[:3]:
        print(f"   {p.get(col_marca,'')} | {p.get(col_nome,'')[:50]} | "
              f"R$ {p.get(col_preco,'')} | {(p.get(col_link,'') or '')[:40]}")

    # Tentativa de casamento com o catálogo
    catalogo = carregar_catalogo()
    feed_idx = []
    for p in produtos:
        nome = p.get(col_nome, "")
        marca = p.get(col_marca, "") or p.get(col_loja, "")
        feed_idx.append((tokens(marca, nome), p))

    casados = 0
    exemplos = []
    for s in catalogo:
        alvo = tokens(s.get("brand", ""), s.get("name", ""))
        if not alvo:
            continue
        melhor, score = None, 0
        for toks_feed, p in feed_idx:
            inter = len(alvo & toks_feed)
            if inter > score:
                score, melhor = inter, p
        # exige casar pelo menos metade dos tokens do nome do tênis
        if melhor and score >= max(2, len(alvo) // 2):
            casados += 1
            if len(exemplos) < 12:
                exemplos.append((f"{s['brand']} {s['name']}",
                                 melhor.get(col_nome, ""), melhor.get(col_preco, "")))

    print("\n" + "=" * 70)
    print(f"CASAMENTO: {casados}/{len(catalogo)} tênis encontrados no feed")
    print("=" * 70)
    for cat, feed_nome, preco in exemplos:
        print(f"   ✅ {cat:32} → {feed_nome[:34]:34} R$ {preco}")


if __name__ == "__main__":
    main()
