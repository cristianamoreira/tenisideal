#!/usr/bin/env python3
"""Confere o preço da SUA PLANILHA com o preço que a LOJA mostra agora na página dela.

(O site é gerado da planilha, então site e planilha nunca divergem entre si — o que pode
mudar é o preço na página da loja. É isso que este robô compara.)

Para evitar alarme falso, lê só os dados ESTRUTURADOS do produto (não pega qualquer "R$"
da página), ignora leituras implausíveis (parcela/produto errado) e só alerta diferença
real (> 5% e > R$15). Manda por e-mail a lista, com o link pra conferir.

Lojas que bloqueiam robô (Nike/Adidas/Netshoes) não retornam preço — ficam de fora.
Secrets: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE (opcional)
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.error
import concurrent.futures

H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36", "Accept-Language": "pt-BR"}

PCT_MIN = 0.05      # diferença mínima relativa (5%)
ABS_MIN = 15.0      # diferença mínima absoluta (R$15)
RATIO_LO = 0.6      # abaixo disso a leitura é implausível (provável parcela/erro)
RATIO_HI = 1.7      # acima disso idem


def carregar():
    c = open("frontend/shoes_data.js", encoding="utf-8").read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def _num(v):
    v = (v or "").strip()
    if "," in v and "." in v:          # 1.313,78
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:                      # 1313,78
        v = v.replace(",", ".")
    try:
        f = float(v)
    except ValueError:
        return None
    if f > 6000:                        # formato em centavos (131378 -> 1313.78)
        f = f / 100
    return f if 30 < f < 6000 else None


def preco_da_pagina(html):
    """Só preços ESTRUTURADOS do produto (ordem = mais confiável primeiro)."""
    fontes = [
        # JSON-LD / Offer: "price" colado em "priceCurrency" (os dois sentidos)
        r'"price"\s*:\s*"?([\d.,]+)"?\s*,\s*"priceCurrency"',
        r'"priceCurrency"\s*:\s*"[^"]+"\s*,\s*"price"\s*:\s*"?([\d.,]+)',
        # meta tags de preço do produto
        r'(?:product:price:amount|og:price:amount)"\s+content="([\d.,]+)"',
        r'itemprop="price"[^>]*content="([\d.,]+)"',
        # Amazon (caixa de compra)
        None,
    ]
    for pat in fontes[:-1]:
        for m in re.finditer(pat, html):
            f = _num(m.group(1))
            if f:
                return f
    # Amazon: a-price-whole + a-price-fraction dentro de priceToPay/apexPriceToPay
    m = re.search(r'(?:priceToPay|apexPriceToPay).*?a-price-whole">([\d.]+)</span>.*?a-price-fraction">(\d{2})',
                  html, re.S)
    if m:
        return _num(m.group(1).replace(".", "") + "." + m.group(2))
    return None


def checar(item):
    b, n, k, url, ps = item
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25)
        html = r.read().decode("utf-8", "ignore")
        return (b, n, k, url, ps, preco_da_pagina(html))
    except Exception:
        return (b, n, k, url, ps, None)


def e_divergencia(ps, pp):
    if not ps or not pp:
        return False
    ratio = pp / ps
    if ratio < RATIO_LO or ratio > RATIO_HI:   # leitura implausível -> ignora
        return False
    return abs(pp - ps) > max(ABS_MIN, PCT_MIN * ps)


def enviar_email(divs):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem secrets de e-mail — pulando envio.")
        return
    hoje = datetime.date.today().strftime("%d/%m")
    if divs:
        linhas = "".join(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{b} {n} <b>({k})</b></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>planilha R$ {ps:.2f}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;color:#c00'><b>loja R$ {pp:.2f}</b></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'><a href='{url}'>conferir</a></td></tr>"
            for b, n, k, url, ps, pp in divs)
        html = (f"<p style='font-family:sans-serif'>Comparei o preço da <b>sua planilha</b> com o que a "
                f"<b>loja mostra hoje</b> ({hoje}). <b>{len(divs)} divergência(s)</b> provável(is):</p>"
                f"<table style='font-family:sans-serif;font-size:14px;border-collapse:collapse'>{linhas}</table>"
                f"<p style='font-family:sans-serif;color:#666;font-size:13px'>Clique em \"conferir\" pra ver na loja "
                f"e, se confirmar, ajuste na planilha. Diferenças muito grandes (provável erro de leitura) e lojas "
                f"que bloqueiam robô (Nike/Adidas/Netshoes) ficam de fora.</p>")
        assunto = f"⚠️ {len(divs)} preço(s) pra conferir — {hoje}"
    else:
        html = f"<p style='font-family:sans-serif'>✅ Conferi os preços hoje ({hoje}) e está tudo batendo!</p>"
        assunto = f"✅ Preços conferidos, tudo certo — {hoje}"
    body = {"sender": {"email": remet, "name": "Conferência de Preços - Tênis Ideal"},
            "to": [{"email": email}], "subject": assunto, "htmlContent": html}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode(),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail enviado ({len(divs)} divergências).")


def main():
    shoes = carregar()
    items = []
    for s in shoes:
        for k, v in s.get("affiliate_links", {}).items():
            if v.get("url") and v.get("price"):
                items.append((s["brand"], s["name"], k, v["url"], v["price"]))

    res = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for x in ex.map(checar, items):
            res.append(x)

    div = [x for x in res if e_divergencia(x[4], x[5])]
    lidos = sum(1 for x in res if x[5])
    print(f"Links lidos com preço: {lidos}/{len(items)} | Divergências reais: {len(div)}")
    for b, n, k, url, ps, pp in div:
        print(f"  {b} {n} ({k}): planilha R${ps:.2f} -> loja R${pp:.2f}")
    enviar_email(div)


if __name__ == "__main__":
    main()
