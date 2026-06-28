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

    # selo de desconto (canto superior direito) se o título tiver %
    mdesc = re.search(r"(\d{1,2})\s*%", titulo or "")
    if mdesc:
        cx, cy, r0 = W - 165, 165, 100
        d.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], fill=AMARELO)
        ftxt = fonte(58)
        t_pct = mdesc.group(1) + "%"
        wt = d.textlength(t_pct, font=ftxt)
        d.text((cx - wt / 2, cy - 50), t_pct, font=ftxt, fill=PRETO)
        foff = fonte(30)
        wo = d.textlength("OFF", font=foff)
        d.text((cx - wo / 2, cy + 14), "OFF", font=foff, fill=PRETO)

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
    d.rectangle([18, 18, W - 18, H - 18], outline=AMARELO, width=4)
    # logo
    fl = fonte(54)
    t1, t2 = "TÊNIS", "IDEAL"
    w1 = d.textlength(t1, font=fl)
    w2 = d.textlength(t2, font=fl)
    x0 = (W - (w1 + w2)) / 2
    d.text((x0, 90), t1, font=fl, fill=BRANCO)
    d.text((x0 + w1, 90), t2, font=fl, fill=AMARELO)
    centro(d, 205, "DICA DO DIA", fonte(36), AMARELO)
    # título
    ft = fonte(56)
    y = 310
    for ln in quebrar_linhas(d, sem_emoji(titulo), ft, W - 150, 2):
        centro(d, y, ln, ft, BRANCO)
        y += 68
    # texto
    fx = fonte(37)
    y = max(y + 40, 480)
    for ln in quebrar_linhas(d, sem_emoji(texto), fx, W - 170, 6):
        centro(d, y, ln, fx, CINZA)
        y += 52
    # CTA
    centro(d, 880, "Descubra o seu no nosso quiz:", fonte(32), BRANCO)
    fr = fonte(40)
    a, bb = "tenisideal.com.br   ", "@tenisideal_br"
    wa = d.textlength(a, font=fr)
    wb = d.textlength(bb, font=fr)
    xr = (W - (wa + wb)) / 2
    d.text((xr, 945), a, font=fr, fill=BRANCO)
    d.text((xr + wa, 945), bb, font=fr, fill=AMARELO)
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
