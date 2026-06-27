#!/usr/bin/env python3
"""Verifica se os preços da planilha (no site) batem com os das páginas das lojas.

Entra em cada link, lê o preço da página e compara com o preço cadastrado.
Manda por e-mail a lista de divergências (só as lojas que respondem; Amazon,
Mizuno e Olympikus costumam responder — Nike/Adidas/Netshoes bloqueiam robô).

Secrets: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE (opcional)
"""
import os
import re
import json
import base64  # noqa
import datetime
import urllib.parse
import urllib.request
import concurrent.futures
import urllib.error

H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36", "Accept-Language": "pt-BR"}
TOLERANCIA = 5.0  # diferença mínima (R$) para considerar divergência


def carregar():
    c = open("frontend/shoes_data.js", encoding="utf-8").read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def preco_da_pagina(html):
    for pat in [r'"price"\s*:\s*"?([\d.,]+)', r'itemprop="price"[^>]*content="([\d.,]+)',
                r'"priceAmount":([\d.]+)', r'R\$\s*([\d.]+,\d{2})']:
        m = re.search(pat, html)
        if m:
            v = m.group(1)
            if ',' in v and '.' in v:
                v = v.replace('.', '').replace(',', '.')
            elif ',' in v:
                v = v.replace(',', '.')
            try:
                f = float(v)
                if f > 5000:      # corrige formato em centavos (64999 -> 649.99)
                    f = f / 100
                if 30 < f < 5000:
                    return f
            except ValueError:
                pass
    return None


def checar(item):
    b, n, k, url, ps = item
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25)
        html = r.read().decode("utf-8", "ignore")
        pp = preco_da_pagina(html)
        return (b, n, k, ps, pp)
    except Exception:
        return (b, n, k, ps, None)


def enviar_email(divergencias):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem secrets de e-mail — pulando envio.")
        return
    hoje = datetime.date.today().strftime("%d/%m")
    if divergencias:
        linhas = "".join(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{b} {n} <b>({k})</b></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>planilha R$ {ps:.2f}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;color:#c00'><b>página R$ {pp:.2f}</b></td></tr>"
            for b, n, k, ps, pp in divergencias)
        html = (f"<p style='font-family:sans-serif'>Verifiquei os preços hoje ({hoje}). "
                f"<b>{len(divergencias)} divergência(s)</b> entre a planilha e a página da loja:</p>"
                f"<table style='font-family:sans-serif;font-size:14px;border-collapse:collapse'>{linhas}</table>"
                f"<p style='font-family:sans-serif;color:#666;font-size:13px'>Corrija na planilha os que quiser. "
                f"(Lojas que bloqueiam robô — Nike/Adidas/Netshoes — não entram nesta checagem.)</p>")
        assunto = f"⚠️ {len(divergencias)} preço(s) divergente(s) — {hoje}"
    else:
        html = f"<p style='font-family:sans-serif'>✅ Verifiquei os preços hoje ({hoje}) e está tudo batendo!</p>"
        assunto = f"✅ Preços conferidos, tudo certo — {hoje}"
    body = {
        "sender": {"email": remet, "name": "Conferência de Preços - Tênis Ideal"},
        "to": [{"email": email}],
        "subject": assunto,
        "htmlContent": html,
    }
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode(),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail enviado ({len(divergencias)} divergências).")


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

    div = [x for x in res if x[3] and x[4] and abs(x[4] - x[3]) > TOLERANCIA]
    verificados = sum(1 for x in res if x[3] and x[4])
    print(f"Links verificáveis: {verificados} | Divergências: {len(div)}")
    for b, n, k, ps, pp in div:
        print(f"  {b} {n} ({k}): R${ps:.2f} -> R${pp:.2f}")
    enviar_email(div)


if __name__ == "__main__":
    main()
