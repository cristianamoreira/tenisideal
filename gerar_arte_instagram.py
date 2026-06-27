#!/usr/bin/env python3
"""Gera artes 1080x1080 (Instagram) com os cupons do dia e te envia por e-mail.

Você baixa a imagem e posta no @tenisideal_br. Nada é postado automaticamente.

Variáveis de ambiente (secrets):
- AWIN_API_TOKEN : para buscar os cupons (mesmo dos outros robôs)
- BREVO_API_KEY  : para te enviar as artes por e-mail
- EMAIL_CUPONS   : seu e-mail (recebe as artes)
"""
import os
import sys
import re
import json
import base64
import datetime
import urllib.request
import urllib.error
from PIL import Image, ImageDraw, ImageFont

W = H = 1080
PRETO = (13, 13, 13)
AMARELO = (200, 255, 0)
BRANCO = (245, 245, 245)
CINZA = (150, 150, 150)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # GitHub Actions
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",          # macOS
    "/Library/Fonts/Arial Bold.ttf",
]


def fonte(tam):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, tam)
    return ImageFont.load_default()


def centro(draw, y, texto, font, cor):
    w = draw.textlength(texto, font=font)
    draw.text(((W - w) / 2, y), texto, font=font, fill=cor)


def quebrar(draw, texto, font, larg_max):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=font) <= larg_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:2]


def gerar_imagem(loja, codigo, titulo, idx):
    img = Image.new("RGB", (W, H), PRETO)
    d = ImageDraw.Draw(img)

    # borda amarela fina
    d.rectangle([18, 18, W - 18, H - 18], outline=AMARELO, width=4)

    # logo
    f_logo = fonte(58)
    txt1, txt2 = "TÊNIS", "IDEAL"
    w1 = d.textlength(txt1, font=f_logo)
    w2 = d.textlength(txt2, font=f_logo)
    x0 = (W - (w1 + w2)) / 2
    d.text((x0, 95), txt1, font=f_logo, fill=BRANCO)
    d.text((x0 + w1, 95), txt2, font=f_logo, fill=AMARELO)

    # selo "CUPOM DO DIA"
    centro(d, 235, "CUPOM DO DIA", fonte(40), AMARELO)

    # nome da loja (grande)
    centro(d, 330, loja.upper()[:16], fonte(104), BRANCO)

    # título do cupom (até 2 linhas)
    if titulo:
        f_t = fonte(38)
        linhas = quebrar(d, titulo, f_t, W - 200)
        y = 480
        for ln in linhas:
            centro(d, y, ln, f_t, CINZA)
            y += 52

    # caixa do código (amarela)
    if codigo:
        centro(d, 640, "USE O CUPOM", fonte(34), BRANCO)
        f_cod = fonte(86)
        wc = d.textlength(codigo.upper(), font=f_cod)
        bx0 = (W - wc) / 2 - 40
        bx1 = (W + wc) / 2 + 40
        d.rounded_rectangle([bx0, 700, bx1, 830], radius=18, fill=AMARELO)
        d.text(((W - wc) / 2, 716), codigo.upper(), font=f_cod, fill=PRETO)

    # rodapé
    centro(d, 905, "Aproveite no site da loja oficial", fonte(32), CINZA)
    f_rod = fonte(40)
    t1, t2 = "tenisideal.com.br   ", "@tenisideal_br"
    wr1 = d.textlength(t1, font=f_rod)
    wr2 = d.textlength(t2, font=f_rod)
    xr = (W - (wr1 + wr2)) / 2
    d.text((xr, 975), t1, font=f_rod, fill=BRANCO)
    d.text((xr + wr1, 975), t2, font=f_rod, fill=AMARELO)

    nome = f"arte_cupom_{idx}.png"
    img.save(nome, "PNG")
    return nome


def buscar_cupons():
    if not os.environ.get("AWIN_API_TOKEN"):
        return []
    try:
        from gerar_cupons_awin import buscar_promocoes
        dados = buscar_promocoes()
        promos = dados.get("data") if isinstance(dados, dict) else dados
        return promos or []
    except Exception as e:
        print(f"[cupons indisponíveis] {e}", file=sys.stderr)
        return []


def gerar_legenda(loja, codigo, titulo):
    m = re.search(r"(\d{1,2})\s*%", titulo or "")
    desconto = f"{m.group(1)}% OFF" if m else "Oferta especial"
    tag_loja = re.sub(r"[^a-z0-9]", "", loja.lower())
    return (
        f"🔥 {desconto.upper()} NA {loja.upper()}! 👟\n\n"
        f"{(titulo or '').strip()}\n\n"
        f"🎟️ Use o cupom: {codigo.upper()}\n"
        f"🛒 Compre pelo link na bio 👉 tenisideal.com.br\n\n"
        f"Corre que é por tempo limitado! 🏃💨\n\n"
        f"📲 Siga @tenisideal_br pra não perder nenhum cupom!\n\n"
        f"#tenisdecorrida #corrida #running #corredores #vidadecorredor "
        f"#cupom #desconto #ofertas #{tag_loja} #tenisideal"
    )


def enviar_email(items):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — pulando envio.", file=sys.stderr)
        return
    anexos = []
    blocos = ""
    for it in items:
        with open(it["nome"], "rb") as f:
            anexos.append({"content": base64.b64encode(f.read()).decode(), "name": it["nome"]})
        legenda = gerar_legenda(it["loja"], it["codigo"], it["titulo"])
        leg_html = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        blocos += (
            f"<p style='font-family:sans-serif;margin:20px 0 6px;'><b>📎 {it['nome']}</b> "
            f"({it['loja']}) — legenda pronta, é só copiar:</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px;'>{leg_html}</pre>"
        )
    hoje = datetime.date.today().strftime("%d/%m")
    html = ("<p style='font-family:sans-serif'>Bom dia! 👋 Aqui está a arte de hoje pro Instagram. "
            "<b>Baixe a imagem em anexo</b>, copie a legenda abaixo e poste no "
            "<b>@tenisideal_br</b> (feed ou stories).</p>" + blocos)
    body = {
        "sender": {"email": remet, "name": "Arte Instagram - Tênis Ideal"},
        "to": [{"email": email}],
        "subject": f"📸 Arte do dia {hoje} pro Instagram ({len(items)})",
        "htmlContent": html,
        "attachment": anexos,
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(body).encode("utf-8"),
        headers={"api-key": key, "Content-Type": "application/json", "accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail com {len(anexos)} arte(s) enviado para {email} (HTTP {r.status})")


def main():
    cupons = buscar_cupons()
    items = []
    for i, p in enumerate(cupons[:6], 1):
        loja = (p.get("advertiser") or {}).get("name") or p.get("advertiserName") or "Tênis Ideal"
        loja = loja.replace(" BR", "").replace(" Brasil", "").strip()
        codigo = (p.get("voucher") or {}).get("code") or p.get("code")
        titulo = (p.get("title") or p.get("description") or "").strip()
        if not codigo:
            continue
        nome = gerar_imagem(loja, codigo, titulo, i)
        items.append({"nome": nome, "loja": loja, "codigo": codigo, "titulo": titulo})

    if not items:
        print("Nenhum cupom com código hoje — nada a gerar.", file=sys.stderr)
        return

    print(f"🎨 {len(items)} arte(s) gerada(s).")
    enviar_email(items)


if __name__ == "__main__":
    main()
