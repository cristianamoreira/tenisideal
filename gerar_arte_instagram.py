#!/usr/bin/env python3
"""Gera a arte diária "Destaque do Tênis" (HTML -> screenshot via Chrome) e envia por e-mail.

Estilo inspirado no @teniscerto: fundo escuro premium, foto real do tênis recortada
("flutuando"), título marca+modelo, preço e a identidade TÊNIS IDEAL. A cada dia destaca
um tênis diferente do catálogo (rotação), com legenda pronta pra postar no @tenisideal_br.

Roda no GitHub Actions (o runner ubuntu-latest já vem com o Google Chrome).
Secrets: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE (opcional).
"""
import os
import sys
import re
import io
import ssl
import json
import base64
import shutil
import tempfile
import subprocess
import datetime
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'Bebas';src:url('BebasNeue.ttf');}
@font-face{font-family:'Mont';src:url('Montserrat.ttf');}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:1080px;height:1080px;}
.canvas{width:1080px;height:1080px;position:relative;overflow:hidden;
 background:radial-gradient(72% 56% at 50% 63%,#2c2d37 0%,#17171d 52%,#0a0a0e 100%);font-family:'Mont',sans-serif;}
.accent-glow{position:absolute;width:640px;height:640px;left:-170px;top:-220px;
 background:radial-gradient(circle,rgba(200,255,0,.15),transparent 65%);filter:blur(10px);}
.header{position:absolute;top:50px;left:64px;font-family:'Bebas';font-size:44px;letter-spacing:3px;}
.header b{color:#fff;font-weight:400;}.header i{color:#C8FF00;font-style:normal;}
.chip{position:absolute;top:114px;left:64px;background:rgba(200,255,0,.13);
 border:1.5px solid rgba(200,255,0,.55);color:#C8FF00;font-family:'Bebas';font-size:24px;
 letter-spacing:3px;padding:9px 22px 7px;border-radius:30px;}
.title{position:absolute;top:192px;left:64px;}
.brand{font-family:'Bebas';font-size:80px;color:#C8FF00;line-height:.9;letter-spacing:1px;}
.model{font-family:'Bebas';font-size:114px;color:#fff;line-height:.85;letter-spacing:1px;
 text-shadow:0 4px 34px rgba(0,0,0,.45);max-width:940px;}
.subtitle{font-family:'Mont';font-weight:500;font-size:25px;color:#c3c5d0;margin-top:18px;
 max-width:500px;line-height:1.36;}
.bar{width:120px;height:7px;background:#C8FF00;border-radius:4px;margin-top:22px;}
.price{position:absolute;top:56px;right:58px;text-align:center;background:#C8FF00;color:#14141b;
 border-radius:22px;padding:12px 26px 14px;box-shadow:0 14px 34px rgba(200,255,0,.22);}
.price .lbl{font-family:'Mont';font-weight:700;font-size:14px;letter-spacing:2px;opacity:.65;}
.price .val{font-family:'Bebas';font-size:60px;line-height:.8;margin-top:2px;}
.shoe-glow{position:absolute;bottom:250px;left:50%;transform:translateX(-50%);width:720px;height:230px;
 background:radial-gradient(ellipse at center,rgba(200,255,0,.16),rgba(150,170,255,.05) 45%,transparent 72%);
 filter:blur(34px);}
.shoe{position:absolute;bottom:182px;left:50%;transform:translateX(-50%);width:802px;
 filter:drop-shadow(0 34px 28px rgba(0,0,0,.55));}
.footer{position:absolute;bottom:46px;left:0;width:100%;text-align:center;}
.cta{display:inline-block;background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:28px;
 letter-spacing:2px;padding:11px 32px 9px;border-radius:30px;margin-bottom:14px;}
.handle{font-family:'Bebas';font-size:34px;letter-spacing:2px;color:#fff;}.handle i{color:#C8FF00;font-style:normal;}
.site{font-family:'Mont';font-size:19px;color:#9a9ca7;margin-top:3px;letter-spacing:1px;}
</style></head><body><div class="canvas">
<div class="accent-glow"></div>
<div class="header"><b>TÊNIS</b><i>IDEAL</i></div>
<div class="chip">@@CHIP@@</div>
<div class="title"><div class="brand">@@BRAND@@</div><div class="model">@@MODEL@@</div>
<div class="subtitle">@@SUB@@</div><div class="bar"></div></div>
<div class="price"><div class="lbl">A PARTIR DE</div><div class="val">@@PRICE@@</div></div>
<div class="shoe-glow"></div><img class="shoe" src="shoe.png">
<div class="footer"><div class="cta">FAÇA O QUIZ • LINK NA BIO</div>
<div class="handle">@TENISIDEAL<i>_BR</i></div><div class="site">tenisideal.com.br</div></div>
</div></body></html>"""


def carregar_catalogo():
    c = open("frontend/shoes_data.js", encoding="utf-8").read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def baixar(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        return urllib.request.urlopen(req, timeout=25).read()
    except Exception:
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(req, context=ctx, timeout=25).read()


def recortar(raw):
    from PIL import Image, ImageDraw
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    corners = [img.getpixel(p) for p in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]]
    if not all(sum(c) / 3 > 200 for c in corners):
        return None
    SENT = (255, 0, 255)
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        try:
            ImageDraw.floodfill(img, xy, SENT, thresh=46)
        except Exception:
            pass
    rgba = img.convert("RGBA"); px = rgba.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 250 and g < 6 and b > 250:
                px[x, y] = (0, 0, 0, 0)
    bb = rgba.getbbox()
    return rgba.crop(bb) if bb else rgba


def fmt_preco(p):
    try:
        return "R$ " + "{:,}".format(int(round(float(p)))).replace(",", ".")
    except Exception:
        return ""


def melhor_link(s):
    """Retorna (preco, parcelas) do link mais barato com preço."""
    melhor = None
    for v in (s.get("affiliate_links") or {}).values():
        if v.get("price"):
            if melhor is None or v["price"] < melhor["price"]:
                melhor = v
    if melhor:
        return melhor["price"], (melhor.get("installments") or "").strip()
    return s.get("price") or 0, ""


def escolher_tenis(shoes):
    """Pool com foto da Amazon (fundo branco = recorte limpo). Rotaciona por dia."""
    pool = [s for s in shoes if "amazon" in (s.get("photo") or "").lower() and s.get("photo")]
    if not pool:
        pool = [s for s in shoes if s.get("photo")]
    dia = datetime.date.today().timetuple().tm_yday
    # tenta o do dia; se o recorte falhar, vai pro próximo
    n = len(pool)
    for k in range(n):
        yield pool[(dia + k) % n]


def achar_chrome():
    cands = ["google-chrome-stable", "google-chrome", "chrome", "chromium-browser", "chromium",
             os.environ.get("CHROME_PATH", ""),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    for c in cands:
        if os.path.sep in c:
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return c
    return None


def gerar_arte(s, workdir):
    """Monta o HTML + foto recortada e renderiza via Chrome. Retorna caminho do PNG ou None."""
    shoe = recortar(baixar(s["photo"]))
    if shoe is None:
        return None
    shoe.save(os.path.join(workdir, "shoe.png"))
    for f in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(f):
            shutil.copy(f, os.path.join(workdir, f))
    preco, parc = melhor_link(s)
    sub = (s.get("reason") or s.get("description") or "").split(".")[0].strip()
    html = (HTML.replace("@@CHIP@@", "TÊNIS EM DESTAQUE")
                .replace("@@BRAND@@", s["brand"].upper())
                .replace("@@MODEL@@", s["name"].upper())
                .replace("@@SUB@@", sub)
                .replace("@@PRICE@@", fmt_preco(preco) or "—"))
    open(os.path.join(workdir, "art.html"), "w", encoding="utf-8").write(html)
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome não encontrado.", file=sys.stderr)
        return None
    out2x = os.path.join(workdir, "out2x.png")
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--force-device-scale-factor=2", "--window-size=1080,1080", "--hide-scrollbars",
                    "--default-background-color=00000000", "--virtual-time-budget=3500",
                    "--screenshot=" + out2x, "--allow-file-access-from-files",
                    "file://" + os.path.join(workdir, "art.html")],
                   check=False, capture_output=True, timeout=120)
    if not os.path.exists(out2x):
        print("ERRO: screenshot não gerado.", file=sys.stderr)
        return None
    from PIL import Image
    final = "arte_destaque.png"
    Image.open(out2x).convert("RGB").resize((1080, 1080), Image.LANCZOS).save(final, "PNG")
    return final


def gerar_legenda(s):
    preco, parc = melhor_link(s)
    brand, name = s["brand"], s["name"]
    reason = (s.get("reason") or s.get("description") or "").strip()
    tag = re.sub(r"[^a-z0-9]", "", brand.lower())
    linha_preco = f"💰 A partir de {fmt_preco(preco)}" + (f" ({parc})" if parc else "")
    return (
        f"🔥 {brand.upper()} {name.upper()} 👟\n\n"
        f"{reason}\n\n"
        f"{linha_preco}\n"
        f"🔎 Faça nosso quiz e descubra o tênis ideal pro seu perfil — link na bio 👉 tenisideal.com.br\n\n"
        f"📲 Siga @tenisideal_br pra mais dicas de corrida!\n\n"
        f"#tenisdecorrida #corrida #running #corredores #vidadecorredor "
        f"#{tag} #tenisideal #tenis #corridaderua"
    )


def enviar_email(png, legenda, s):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — arte gerada, e-mail pulado.", file=sys.stderr)
        return
    with open(png, "rb") as f:
        anexo = base64.b64encode(f.read()).decode()
    leg_html = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    hoje = datetime.date.today().strftime("%d/%m")
    html = ("<p style='font-family:sans-serif'>Bom dia! 👋 Aqui está a <b>arte do dia</b> pro Instagram "
            f"— hoje em destaque: <b>{s['brand']} {s['name']}</b>. Baixe a imagem em anexo, copie a "
            "legenda abaixo e poste no <b>@tenisideal_br</b>.</p>"
            "<p style='font-family:sans-serif;margin:18px 0 6px'><b>📸 Legenda pronta (é só copiar):</b></p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;border:1px solid #ddd;"
            f"border-radius:8px;padding:14px;font-size:14px'>{leg_html}</pre>")
    body = {
        "sender": {"email": remet, "name": "Arte do dia - Tênis Ideal"},
        "to": [{"email": email}],
        "subject": f"📸 Arte do dia {hoje} — {s['brand']} {s['name']}",
        "htmlContent": html,
        "attachment": [{"content": anexo, "name": png}],
    }
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail enviado para {email} (HTTP {r.status})")


def main():
    shoes = carregar_catalogo()
    workdir = tempfile.mkdtemp(prefix="ti_arte_")
    escolhido = None
    for s in escolher_tenis(shoes):
        png = gerar_arte(s, workdir)
        if png:
            escolhido = s
            break
    if not escolhido:
        print("ERRO: não consegui gerar a arte de nenhum tênis.", file=sys.stderr)
        sys.exit(1)
    print(f"🎨 Arte gerada: {escolhido['brand']} {escolhido['name']}")
    enviar_email("arte_destaque.png", gerar_legenda(escolhido), escolhido)


if __name__ == "__main__":
    main()
