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

# Bebas Neue (títulos condensados, = logo do site) + Montserrat (corpo limpo)
FONTES_BEBAS = ["BebasNeue.ttf", "/tmp/BebasNeue.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
FONTES_MONT = ["Montserrat.ttf", "/tmp/Montserrat.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _carregar(paths, tam):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, tam)
            except Exception:
                pass
    return ImageFont.load_default()


def bebas(tam):
    return _carregar(FONTES_BEBAS, tam)


def mont(tam):
    return _carregar(FONTES_MONT, tam)


def fonte(tam):   # compat
    return bebas(tam)


def centro(draw, y, texto, font, cor):
    w = draw.textlength(texto, font=font)
    draw.text(((W - w) / 2, y), texto, font=font, fill=cor)


# ───── identidade visual compartilhada (mesma em todos os posts) ─────
def desenhar_header(d):
    f = bebas(78)
    t1, t2 = "TÊNIS", "IDEAL"
    w1 = d.textlength(t1, font=f)
    w2 = d.textlength(t2, font=f)
    x0 = (W - (w1 + w2)) / 2
    d.text((x0, 54), t1, font=f, fill=BRANCO)
    d.text((x0 + w1, 54), t2, font=f, fill=AMARELO)


def desenhar_chip(d, y, texto):
    f = bebas(40)
    w = d.textlength(texto, font=f)
    x0 = (W - w) / 2 - 30
    x1 = (W + w) / 2 + 30
    d.rounded_rectangle([x0, y, x1, y + 62], radius=31, fill=AMARELO)
    d.text(((W - w) / 2, y + 9), texto, font=f, fill=PRETO)


def desenhar_rodape(d):
    d.rectangle([0, 950, W, H], fill=AMARELO)
    centro(d, 968, "@TENISIDEAL_BR", bebas(50), PRETO)
    centro(d, 1028, "tenisideal.com.br", mont(23), (35, 35, 35))


def gerar_imagem(loja, codigo, titulo, idx):
    img = Image.new("RGB", (W, H), PRETO)
    d = ImageDraw.Draw(img)
    desenhar_header(d)
    desenhar_chip(d, 168, "CUPOM DO DIA")

    # selo de desconto (círculo, canto superior direito)
    m = re.search(r"(\d{1,2})\s*%", titulo or "")
    if m:
        cx, cy, r0 = W - 158, 200, 96
        d.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], fill=AMARELO)
        fp = bebas(70)
        pct = m.group(1) + "%"
        wp = d.textlength(pct, font=fp)
        d.text((cx - wp / 2, cy - 62), pct, font=fp, fill=PRETO)
        fo = bebas(36)
        wo = d.textlength("OFF", font=fo)
        d.text((cx - wo / 2, cy + 12), "OFF", font=fo, fill=PRETO)

    # nome da loja (grande, condensada)
    centro(d, 318, loja.upper()[:18], bebas(140), BRANCO)

    # descrição (Montserrat, limpa)
    y = 512
    for ln in quebrar_linhas(d, sem_emoji(titulo), mont(30), W - 200, 3):
        centro(d, y, ln, mont(30), CINZA)
        y += 46

    # caixa do código
    centro(d, 700, "USE O CUPOM", mont(26), BRANCO)
    fc = bebas(100)
    wc = d.textlength(codigo.upper(), font=fc)
    bx0 = (W - wc) / 2 - 46
    bx1 = (W + wc) / 2 + 46
    d.rounded_rectangle([bx0, 748, bx1, 880], radius=22, fill=AMARELO)
    d.text(((W - wc) / 2, 762), codigo.upper(), font=fc, fill=PRETO)

    desenhar_rodape(d)
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


def sem_emoji(s):
    return re.sub(r'[\U0001F000-\U0001FAFF☀-➿️←-⇿]', '', s or '').strip()


def quebrar_linhas(d, texto, font, larg, maxn):
    palavras, linhas, atual = (texto or '').split(), [], ""
    for p in palavras:
        t = (atual + " " + p).strip()
        if d.textlength(t, font=font) <= larg:
            atual = t
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:maxn]


def conteudo_do_dia():
    try:
        from gerar_campanha_email import CONTEUDO
    except Exception:
        CONTEUDO = [{"titulo": "Qual é o seu tênis ideal?",
                     "texto": "Faça o teste e descubra o tênis perfeito pro seu perfil em 60 segundos."}]
    idx = datetime.date.today().timetuple().tm_yday % len(CONTEUDO)
    b = CONTEUDO[idx]
    return b["titulo"], re.sub(r"<[^>]+>", "", b["texto"])


def gerar_imagem_info(titulo, texto, idx):
    img = Image.new("RGB", (W, H), PRETO)
    d = ImageDraw.Draw(img)
    desenhar_header(d)
    desenhar_chip(d, 168, "DICA DO DIA")

    # título (Bebas condensada — cabe bastante)
    ft = bebas(86)
    y = 300
    for ln in quebrar_linhas(d, sem_emoji(titulo), ft, W - 130, 2):
        centro(d, y, ln, ft, BRANCO)
        y += 82

    # divisor amarelo curto
    y += 18
    d.rectangle([(W / 2) - 40, y, (W / 2) + 40, y + 5], fill=AMARELO)
    y += 38

    # texto (Montserrat)
    for ln in quebrar_linhas(d, sem_emoji(texto), mont(34), W - 180, 6):
        centro(d, y, ln, mont(34), CINZA)
        y += 50

    centro(d, 884, "DESCUBRA O SEU NO NOSSO QUIZ", bebas(40), AMARELO)
    desenhar_rodape(d)
    nome = f"arte_info_{idx}.png"
    img.save(nome, "PNG")
    return nome


def legenda_info(titulo, texto):
    return (
        f"{titulo}\n\n{texto}\n\n"
        f"👟 Descubra o tênis ideal pro seu perfil no nosso quiz (link na bio)!\n"
        f"📲 Siga @tenisideal_br pra mais dicas de corrida.\n\n"
        f"#tenisdecorrida #corrida #running #corredores #vidadecorredor "
        f"#dicasdecorrida #treino #maratona #pisada #tenisideal"
    )


def enviar_email(posts):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — pulando envio.", file=sys.stderr)
        return
    anexos = []
    blocos = ""
    for p in posts:
        with open(p["nome"], "rb") as f:
            anexos.append({"content": base64.b64encode(f.read()).decode(), "name": p["nome"]})
        leg_html = p["legenda"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        blocos += (
            f"<p style='font-family:sans-serif;margin:22px 0 6px;'><b>{p['label']}</b> "
            f"&nbsp;·&nbsp; arquivo <b>{p['nome']}</b> — legenda pronta, é só copiar:</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px;'>{leg_html}</pre>"
        )
    hoje = datetime.date.today().strftime("%d/%m")
    html = ("<p style='font-family:sans-serif'>Bom dia! 👋 Aqui estão os <b>2 posts de hoje</b> pro "
            "Instagram (1 cupom + 1 informativo). Baixe as imagens em anexo, copie a legenda de cada "
            "uma e poste no <b>@tenisideal_br</b>.</p>" + blocos)
    body = {
        "sender": {"email": remet, "name": "Posts Instagram - Tênis Ideal"},
        "to": [{"email": email}],
        "subject": f"📸 Posts do dia {hoje} pro Instagram ({len(posts)})",
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
    posts = []

    # 1) POST DE CUPOM (o melhor cupom do dia)
    for p in buscar_cupons():
        loja = (p.get("advertiser") or {}).get("name") or p.get("advertiserName") or "Tênis Ideal"
        loja = loja.replace(" BR", "").replace(" Brasil", "").strip()
        codigo = (p.get("voucher") or {}).get("code") or p.get("code")
        titulo = (p.get("title") or p.get("description") or "").strip()
        if codigo:
            nome = gerar_imagem(loja, codigo, titulo, 1)
            posts.append({"nome": nome, "legenda": gerar_legenda(loja, codigo, titulo),
                          "label": f"🎟️ POST 1 — Cupom ({loja})"})
            break   # 1 cupom por dia

    # 2) POST INFORMATIVO (gira a cada dia)
    tit, txt = conteudo_do_dia()
    nome_info = gerar_imagem_info(tit, txt, 1)
    posts.append({"nome": nome_info, "legenda": legenda_info(tit, txt),
                  "label": "💡 POST 2 — Informativo"})

    print(f"🎨 {len(posts)} post(s) gerado(s).")
    enviar_email(posts)


if __name__ == "__main__":
    main()
