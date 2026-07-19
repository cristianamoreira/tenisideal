#!/usr/bin/env python3
"""Robô de CARROSSEL do Instagram (estilo brutalism verde-lima do @tenisideal_br).

Gera um carrossel (5 slides, 1080x1350) a partir de um dos temas em rodizio,
com PRECOS ao vivo da planilha (shoes-fallback.json), e manda TODOS os slides
por e-mail via Brevo (mesmo caminho da arte/video), com legenda pronta.

Rodizio de temas (por dia): pronada -> ate300 -> versus.
Teste local:  TEMA_CARROSSEL=pronada python3 gerar_carrossel_instagram.py

Secrets no GitHub Actions: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE.
"""
import os
import sys
import re
import json
import base64
import shutil
import tempfile
import datetime
import subprocess
import urllib.request

VERDE = "#84CC16"     # verde-lima da marca
LARANJA = "#ff5a1f"   # realce
PRETO = "#0a0a0a"

# ----------------------------------------------------------------- dados

def carregar_catalogo():
    with open("shoes-fallback.json", encoding="utf-8") as f:
        arr = json.load(f)
    return {p.get("slug"): p for p in arr if p.get("slug")}


def fmt(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def preco_min(prod):
    links = (prod or {}).get("affiliate_links") or {}
    precos = [float(o.get("price") or 0) for o in links.values() if o and float(o.get("price") or 0) > 0]
    return min(precos) if precos else 0

# ----------------------------------------------------------------- temas
# Cada tema: lista de slides. {kind, kicker, titulo, corpo}. Se o slide tem
# "slug", o preco e injetado ao vivo no {preco} do titulo/corpo.

TEMAS = {
    "pronada": {
        "assunto": "Pisada pronada",
        "legenda": ("Você pode estar correndo com o tênis errado. 👟\n\n"
                    "Se o seu tornozelo rola pra dentro a cada passada (pisada pronada) e você usa um tênis neutro, "
                    "cada corrida vira risco de dor no joelho e na canela.\n\n"
                    "Arrasta pro lado e descubra sua pisada em casa + o melhor custo-benefício de 2026.\n\n"
                    "🔎 Não sabe a sua pisada? Faça o quiz grátis (link na bio) e receba os 3 tênis certos pra você."),
        "slides": [
            {"kind": "capa", "kicker": "CORRIDA", "titulo": "Você corre com o tênis *errado*?",
             "corpo": "Se você é pronador e não sabe, cada corrida é risco de lesão."},
            {"kind": "conteudo", "kicker": "01", "titulo": "O que é pisada *pronada*",
             "corpo": "O tornozelo rola pra dentro a cada passada. Isso sobrecarrega joelho, canela e quadril."},
            {"kind": "conteudo", "kicker": "02", "titulo": "Teste do *pé molhado*",
             "corpo": "Molhe a sola do pé e pise numa folha. Pegada cheia e larga é forte sinal de pisada pronada."},
            {"kind": "conteudo", "kicker": "03", "titulo": "Melhor custo-benefício: *Wave Inspire 21*",
             "corpo": "Estabilidade de tênis premium por bem menos. A partir de {preco}.",
             "slug": "mizuno-wave-inspire-21-0e67"},
            {"kind": "cta", "kicker": "SEU TÊNIS IDEAL", "titulo": "Descubra o *seu* em 1 minuto",
             "corpo": "Faça o quiz grátis e receba os 3 modelos certos pra sua pisada, com o melhor preço."},
        ],
    },
    "ate300": {
        "assunto": "Tenis ate R$300",
        "legenda": ("Dá pra começar a correr sem gastar muito. 💸\n\n"
                    "Separamos os tênis com o melhor custo-benefício de 2026 até R$300 — leves, confortáveis e com bom amortecimento.\n\n"
                    "Arrasta pro lado e veja os campeões.\n\n"
                    "🔎 Quer o certo pro seu perfil? Faça o quiz grátis (link na bio) e compare o preço entre Amazon, Netshoes e loja oficial."),
        "slides": [
            {"kind": "capa", "kicker": "CUSTO-BENEFICIO", "titulo": "Melhores tênis até *R$300*",
             "corpo": "Dá pra começar a correr sem gastar muito. Veja os campeões de 2026."},
            {"kind": "conteudo", "kicker": "01", "titulo": "Não precisa de *carbono*",
             "corpo": "Pra começar, o que importa é amortecimento confortável, solado durável e bom ajuste no pé."},
            {"kind": "conteudo", "kicker": "02", "titulo": "Mais barato: *Olympikus Orbita*",
             "corpo": "Leve e versátil pra treinos diários. A partir de {preco}.",
             "slug": "olympikus-orbita-3e40"},
            {"kind": "conteudo", "kicker": "03", "titulo": "Marca premium por menos: *Wave Dynasty 7*",
             "corpo": "Um Mizuno de verdade, com solado X10 durável. A partir de {preco}.",
             "slug": "mizuno-wave-dynasty-7-83eb"},
            {"kind": "cta", "kicker": "SEU TÊNIS IDEAL", "titulo": "Qual combina com *você*?",
             "corpo": "Faça o quiz grátis e receba os 3 modelos certos pro seu perfil e bolso."},
        ],
    },
    "versus": {
        "assunto": "Pegasus 42 vs Wave Rider 28",
        "legenda": ("Nike Pegasus 42 ou Mizuno Wave Rider 28? 🤔\n\n"
                    "Dois dos tênis de treino diário mais vendidos do Brasil — mas com uma diferença de preço enorme.\n\n"
                    "Arrasta pro lado e veja o veredito.\n\n"
                    "🔎 Na dúvida entre os dois? Faça o quiz grátis (link na bio) e descubra qual é o certo pra sua pisada."),
        "slides": [
            {"kind": "capa", "kicker": "COMPARATIVO", "titulo": "Pegasus 42 *vs* Wave Rider 28",
             "corpo": "Dois campeões de treino diário. Qual entrega mais pelo seu dinheiro?"},
            {"kind": "conteudo", "kicker": "01", "titulo": "Nike *Pegasus 42*",
             "corpo": "Mais firme e responsivo, com React X e Air Zoom. A partir de {preco}.",
             "slug": "nike-pegasus-42-f156-m"},
            {"kind": "conteudo", "kicker": "02", "titulo": "Mizuno *Wave Rider 28*",
             "corpo": "Equilíbrio de macio e estável, muito durável. A partir de {preco}.",
             "slug": "mizuno-wave-rider-28-4dcc"},
            {"kind": "conteudo", "kicker": "03", "titulo": "O *veredito*",
             "corpo": "Pra maioria, o Wave Rider vence: estabilidade e durabilidade por quase metade do preço."},
            {"kind": "cta", "kicker": "SEU TÊNIS IDEAL", "titulo": "Qual dos dois é o *seu*?",
             "corpo": "Faça o quiz grátis e descubra o modelo certo pra sua pisada e objetivo."},
        ],
    },
}

RODIZIO = ["pronada", "ate300", "versus"]

# ----------------------------------------------------------------- HTML

def hl(txt):
    txt = (txt or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*(.+?)\*", r'<span style="color:%s">\1</span>' % LARANJA, txt)


def quebra(corpo):
    corpo = (corpo or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    partes = re.split(r"(?<=[.?!])\s+", corpo.strip())
    return "<br>".join(p for p in partes if p)


CSS = """<style>
@font-face{font-family:'Bebas';src:url('BebasNeue.ttf');}
@font-face{font-family:'Mont';src:url('Montserrat.ttf');}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:1080px;height:1350px;}
.canvas{width:1080px;height:1350px;background:__VERDE__;position:relative;overflow:hidden;padding:90px 80px;display:flex;flex-direction:column;justify-content:center;}
.chip{align-self:flex-start;background:__PRETO__;color:__VERDE__;font-family:'Mont';font-weight:800;font-size:30px;letter-spacing:4px;padding:14px 26px;margin-bottom:34px;text-transform:uppercase;}
.card{background:#fff;border:5px solid __PRETO__;box-shadow:18px 18px 0 __PRETO__;padding:44px 46px;}
.card .t{font-family:'Bebas';color:__PRETO__;line-height:.92;letter-spacing:1px;text-transform:uppercase;}
.sub{font-family:'Mont';font-weight:600;color:__PRETO__;line-height:1.4;margin-top:40px;}
.urlbox{align-self:flex-start;background:__PRETO__;color:__VERDE__;font-family:'Mont';font-weight:800;font-size:40px;letter-spacing:1px;padding:22px 34px;margin-top:40px;}
.plug{font-family:'Mont';font-weight:700;color:__PRETO__;font-size:26px;margin-top:22px;letter-spacing:1px;}
.logo{position:absolute;top:56px;left:80px;font-family:'Bebas';font-size:44px;letter-spacing:3px;color:__PRETO__;}
</style>""".replace("__VERDE__", VERDE).replace("__PRETO__", PRETO)


def slide_html(s):
    kind = s["kind"]
    tsize = 108 if kind == "capa" else 84
    logo = '<div class="logo">TÊNIS<span style="color:#fff">IDEAL</span></div>'
    chip = '<div class="chip">%s</div>' % (s.get("kicker", "") or "")
    card = '<div class="card"><div class="t" style="font-size:%dpx">%s</div></div>' % (tsize, hl(s.get("titulo", "")))
    sub = '<div class="sub" style="font-size:%dpx">%s</div>' % (34 if kind == "capa" else 30, quebra(s.get("corpo", "")))
    extra = ""
    if kind == "cta":
        extra = ('<div class="urlbox">tenisideal.com.br</div>'
                 '<div class="plug">👉 Link na bio</div>')
    return CSS + '<div class="canvas">%s%s%s%s%s</div>' % (logo, chip, card, sub, extra)

# ----------------------------------------------------------------- render

def achar_chrome():
    for c in [os.environ.get("CHROME_PATH", ""),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"),
              shutil.which("chrome")]:
        if c and os.path.exists(c):
            return c
    return None


def render(workdir, html, outname):
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome nao encontrado.", file=sys.stderr)
        return None
    for fnt in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(fnt):
            shutil.copy(fnt, os.path.join(workdir, fnt))
    open(os.path.join(workdir, "s.html"), "w", encoding="utf-8").write(html)
    out2x = os.path.join(workdir, "o.png")
    if os.path.exists(out2x):
        os.remove(out2x)
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--force-device-scale-factor=2", "--window-size=1080,1350", "--hide-scrollbars",
                    "--virtual-time-budget=3500", "--screenshot=" + out2x,
                    "--allow-file-access-from-files",
                    "file://" + os.path.join(workdir, "s.html")],
                   check=False, capture_output=True, timeout=120)
    if not os.path.exists(out2x):
        print("ERRO: screenshot nao gerado.", file=sys.stderr)
        return None
    from PIL import Image
    Image.open(out2x).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(outname, "PNG")
    return outname

# ----------------------------------------------------------------- e-mail

def enviar_email(pngs, legenda, assunto):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — carrossel gerado, e-mail pulado.", file=sys.stderr)
        return
    anexos = []
    for p in pngs:
        with open(p, "rb") as f:
            anexos.append({"content": base64.b64encode(f.read()).decode(), "name": os.path.basename(p)})
    leg_html = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    hoje = datetime.date.today().strftime("%d/%m")
    html = ("<p style='font-family:sans-serif'>Bom dia! 👋 Aqui esta o <b>carrossel do dia</b> pro Instagram "
            f"— <b>{assunto}</b>. Baixe os {len(pngs)} slides em anexo (na ordem), copie a legenda abaixo e poste no <b>@tenisideal_br</b>.</p>"
            "<p style='font-family:sans-serif;margin:18px 0 6px'><b>📸 Legenda pronta (é só copiar):</b></p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;border:1px solid #ddd;"
            f"border-radius:8px;padding:14px;font-size:14px'>{leg_html}</pre>")
    body = {"sender": {"email": remet, "name": "Carrossel do dia - Tênis Ideal"},
            "to": [{"email": email}], "subject": f"🎠 Carrossel do dia {hoje} — {assunto}",
            "htmlContent": html, "attachment": anexos}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json", "accept": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail enviado para {email} (HTTP {r.status})")

# ----------------------------------------------------------------- main

def main():
    catalogo = carregar_catalogo()
    tema = (os.environ.get("TEMA_CARROSSEL") or RODIZIO[datetime.date.today().timetuple().tm_yday % len(RODIZIO)]).lower()
    if tema not in TEMAS:
        tema = "pronada"
    cfg = TEMAS[tema]
    print(f"🎠 Tema do carrossel: {tema} → {cfg['assunto']}")

    wd = tempfile.mkdtemp(prefix="carrossel_")
    pngs = []
    for i, s in enumerate(cfg["slides"], 1):
        s = dict(s)
        if s.get("slug"):
            p = fmt(preco_min(catalogo.get(s["slug"])))
            s["titulo"] = s["titulo"].replace("{preco}", p)
            s["corpo"] = s["corpo"].replace("{preco}", p or "consultar")
        out = os.path.join(os.getcwd(), f"carrossel_{i:02d}.png")
        if render(wd, slide_html(s), out):
            pngs.append(out)
            print(f"  ok slide {i:02d}")
    if not pngs:
        print("ERRO: nenhum slide gerado.", file=sys.stderr)
        sys.exit(1)
    enviar_email(pngs, cfg["legenda"], cfg["assunto"])


if __name__ == "__main__":
    main()
