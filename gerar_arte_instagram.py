#!/usr/bin/env python3
"""Robô de arte diária do Instagram — RODÍZIO de 4 formatos (HTML -> screenshot via Chrome).

Cada dia manda 1 formato diferente, com legenda pronta, no e-mail:
  Seg=Destaque · Ter=Comparativo · Qua=Tênis dos Sonhos · Qui=Destaque
  Sex=Cupom (se houver) · Sáb=Comparativo · Dom=Tênis dos Sonhos
Estilo inspirado no @teniscerto: fundo escuro premium, fotos reais recortadas, identidade.
O site é um QUIZ (não loja) — o CTA sempre leva pro quiz.

Roda no GitHub Actions (ubuntu-latest já tem o Chrome).
Secrets: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE, AWIN_API_TOKEN (p/ o cupom).
Teste local: FORMATO_ARTE=destaque|comparativo|sonhos|cupom python3 gerar_arte_instagram.py
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

SCHEDULE = ["destaque", "comparativo", "sonhos", "destaque", "cupom", "comparativo", "sonhos"]  # Seg..Dom

# nomes que indicam trilha/hiking (pra o comparativo não misturar trilha com rua)
TRAIL_KW = ("trail", "trilha", "terrex", "hiking", "trabuco", "venture", "juniper", "peregrine",
            "hierro", "speedcross", "daichi", "shinobi", "agravic", "anylander", "wildhorse",
            "cascadia", "speedgoat", "torrent", "xodus", "rincon", "aero blaze")

# Bloco de <style> comum a todas as artes
CSS = """<style>
@font-face{font-family:'Bebas';src:url('BebasNeue.ttf');}
@font-face{font-family:'Mont';src:url('Montserrat.ttf');}
*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1080px;height:1080px;}
.canvas{width:1080px;height:1080px;position:relative;overflow:hidden;font-family:'Mont',sans-serif;}
.darkbg{background:radial-gradient(72% 56% at 50% 50%,#2c2d37 0%,#17171d 54%,#0a0a0e 100%);}
.gn{color:#C8FF00;}.wh{color:#fff;}
</style>"""

HTML_DESTAQUE = CSS + """<div class="canvas darkbg" style="background:radial-gradient(72% 56% at 50% 63%,#2c2d37 0%,#17171d 52%,#0a0a0e 100%);">
<div style="position:absolute;width:640px;height:640px;left:-170px;top:-220px;background:radial-gradient(circle,rgba(200,255,0,.15),transparent 65%);filter:blur(10px);"></div>
<div style="position:absolute;top:50px;left:64px;font-family:'Bebas';font-size:44px;letter-spacing:3px;"><span class="wh">TÊNIS</span><span class="gn">IDEAL</span></div>
<div style="position:absolute;top:114px;left:64px;background:rgba(200,255,0,.13);border:1.5px solid rgba(200,255,0,.55);color:#C8FF00;font-family:'Bebas';font-size:24px;letter-spacing:3px;padding:9px 22px 7px;border-radius:30px;">TÊNIS EM DESTAQUE</div>
<div style="position:absolute;top:192px;left:64px;">
 <div style="font-family:'Bebas';font-size:80px;color:#C8FF00;line-height:.9;letter-spacing:1px;">@@BRAND@@</div>
 <div style="font-family:'Bebas';font-size:114px;color:#fff;line-height:.85;letter-spacing:1px;text-shadow:0 4px 34px rgba(0,0,0,.45);max-width:940px;">@@MODEL@@</div>
 <div style="font-family:'Mont';font-weight:500;font-size:25px;color:#c3c5d0;margin-top:18px;max-width:500px;line-height:1.36;">@@SUB@@</div>
 <div style="width:120px;height:7px;background:#C8FF00;border-radius:4px;margin-top:22px;"></div></div>
<div style="position:absolute;top:56px;right:58px;text-align:center;background:#C8FF00;color:#14141b;border-radius:22px;padding:12px 26px 14px;box-shadow:0 14px 34px rgba(200,255,0,.22);">
 <div style="font-family:'Mont';font-weight:700;font-size:14px;letter-spacing:2px;opacity:.65;">A PARTIR DE</div>
 <div style="font-family:'Bebas';font-size:60px;line-height:.8;margin-top:2px;">@@PRICE@@</div></div>
<div style="position:absolute;bottom:250px;left:50%;transform:translateX(-50%);width:720px;height:230px;background:radial-gradient(ellipse at center,rgba(200,255,0,.16),rgba(150,170,255,.05) 45%,transparent 72%);filter:blur(34px);"></div>
<img src="shoe.png" style="position:absolute;bottom:182px;left:50%;transform:translateX(-50%);width:802px;filter:drop-shadow(0 34px 28px rgba(0,0,0,.55));">
<div style="position:absolute;bottom:46px;left:0;width:100%;text-align:center;">
 <div style="display:inline-block;background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:28px;letter-spacing:2px;padding:11px 32px 9px;border-radius:30px;margin-bottom:14px;">FAÇA O QUIZ • LINK NA BIO</div>
 <div style="font-family:'Bebas';font-size:34px;letter-spacing:2px;color:#fff;">@TENISIDEAL<span class="gn">_BR</span></div>
 <div style="font-family:'Mont';font-size:19px;color:#9a9ca7;margin-top:3px;letter-spacing:1px;">tenisideal.com.br</div></div>
</div>"""

HTML_CUPOM = CSS + """<div class="canvas" style="background:radial-gradient(70% 55% at 50% 46%,#2c2d37 0%,#17171d 52%,#0a0a0e 100%);text-align:center;">
<div style="position:absolute;width:760px;height:760px;left:50%;top:120px;transform:translateX(-50%);background:radial-gradient(circle,rgba(200,255,0,.14),transparent 62%);filter:blur(20px);"></div>
<div style="position:absolute;top:56px;width:100%;font-family:'Bebas';font-size:46px;letter-spacing:3px;"><span class="wh">TÊNIS</span><span class="gn">IDEAL</span></div>
<div style="position:absolute;top:150px;left:50%;transform:translateX(-50%);background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:30px;letter-spacing:4px;padding:10px 30px 7px;border-radius:30px;">CUPOM DO DIA</div>
<div style="position:absolute;top:236px;width:100%;"><span style="font-family:'Bebas';font-size:300px;color:#C8FF00;line-height:.78;letter-spacing:2px;text-shadow:0 10px 60px rgba(200,255,0,.25);">@@PCT@@</span><span style="font-family:'Bebas';font-size:120px;color:#fff;letter-spacing:4px;margin-left:10px;">OFF</span></div>
<div style="position:absolute;top:566px;width:100%;font-family:'Bebas';font-size:118px;color:#fff;letter-spacing:2px;line-height:.9;">@@STORE@@</div>
<div style="position:absolute;top:702px;width:100%;font-family:'Mont';font-weight:500;font-size:27px;color:#c3c5d0;">@@DESC@@</div>
<div style="position:absolute;top:770px;width:100%;"><div style="font-family:'Mont';font-weight:700;font-size:22px;letter-spacing:3px;color:#fff;opacity:.8;">USE O CUPOM</div>
 <div style="display:inline-block;margin-top:14px;background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:96px;letter-spacing:4px;padding:14px 52px 8px;border-radius:24px;box-shadow:0 16px 40px rgba(200,255,0,.22);">@@CODE@@</div></div>
<div style="position:absolute;bottom:54px;width:100%;"><div style="font-family:'Bebas';font-size:32px;letter-spacing:2px;color:#fff;">Use o cupom na loja · @TENISIDEAL<span class="gn">_BR</span></div>
 <div style="font-family:'Mont';font-size:19px;color:#9a9ca7;margin-top:3px;letter-spacing:1px;">tenisideal.com.br</div></div>
</div>"""

HTML_GRID = CSS + """<div class="canvas" style="background:radial-gradient(80% 60% at 50% 42%,#2c2d37 0%,#17171d 55%,#0a0a0e 100%);text-align:center;">
<div style="position:absolute;top:46px;width:100%;font-family:'Bebas';font-size:42px;letter-spacing:3px;"><span class="wh">TÊNIS</span><span class="gn">IDEAL</span></div>
<div style="position:absolute;top:104px;width:100%;font-family:'Bebas';font-size:80px;color:#fff;letter-spacing:2px;line-height:.9;">TÊNIS DOS SONHOS</div>
<div style="position:absolute;top:194px;width:100%;font-family:'Mont';font-weight:600;font-size:25px;color:#C8FF00;letter-spacing:1px;">Comente o número do seu favorito 👇</div>
<div style="position:absolute;top:258px;left:54px;width:972px;height:680px;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:6px;">@@CELLS@@</div>
<div style="position:absolute;bottom:40px;width:100%;"><div style="font-family:'Bebas';font-size:30px;letter-spacing:2px;color:#fff;">@TENISIDEAL<span class="gn">_BR</span></div>
 <div style="font-family:'Mont';font-size:18px;color:#9a9ca7;margin-top:2px;letter-spacing:1px;">tenisideal.com.br</div></div>
</div>"""

CELL = """<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;">
<div style="position:absolute;top:6px;left:78px;width:46px;height:46px;border-radius:50%;background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:34px;line-height:50px;">@@N@@</div>
<div style="height:150px;display:flex;align-items:center;justify-content:center;"><img src="grid/shoe@@I@@.png" style="max-width:84%;max-height:150px;object-fit:contain;filter:drop-shadow(0 18px 16px rgba(0,0,0,.5));"></div>
<div style="font-family:'Bebas';font-size:30px;color:#fff;letter-spacing:1px;line-height:.95;margin-top:8px;"><span class="gn">@@BRAND@@</span> @@MODEL@@</div>
<div style="font-family:'Mont';font-weight:700;font-size:19px;color:#b8bac4;margin-top:3px;">@@PRICE@@</div></div>"""

HTML_CMP = CSS + """<div class="canvas" style="background:radial-gradient(82% 60% at 50% 30%,#2c2d37 0%,#17171d 58%,#0a0a0e 100%);text-align:center;">
<div style="position:absolute;top:40px;width:100%;font-family:'Bebas';font-size:40px;letter-spacing:3px;"><span class="wh">TÊNIS</span><span class="gn">IDEAL</span></div>
<div style="position:absolute;top:92px;width:100%;font-family:'Bebas';font-size:62px;color:#fff;letter-spacing:3px;">COMPARATIVO</div>
<div style="position:absolute;top:168px;left:46px;width:430px;height:220px;display:flex;align-items:center;justify-content:center;"><img src="cmp/a.png" style="max-width:98%;max-height:220px;object-fit:contain;filter:drop-shadow(0 20px 18px rgba(0,0,0,.55));"></div>
<div style="position:absolute;top:168px;right:46px;width:430px;height:220px;display:flex;align-items:center;justify-content:center;"><img src="cmp/b.png" style="max-width:98%;max-height:220px;object-fit:contain;filter:drop-shadow(0 20px 18px rgba(0,0,0,.55));"></div>
<div style="position:absolute;left:50%;top:236px;transform:translate(-50%,-50%);width:94px;height:94px;border-radius:50%;background:#C8FF00;color:#14141b;font-family:'Bebas';font-size:50px;line-height:98px;box-shadow:0 10px 30px rgba(200,255,0,.3);">VS</div>
<div style="position:absolute;top:398px;left:2%;width:46%;font-family:'Bebas';line-height:.92;"><div style="color:#C8FF00;font-size:34px;letter-spacing:1px;">@@BRANDA@@</div><div style="color:#fff;font-size:44px;letter-spacing:1px;">@@MODELA@@</div></div>
<div style="position:absolute;top:398px;right:2%;width:46%;font-family:'Bebas';line-height:.92;"><div style="color:#C8FF00;font-size:34px;letter-spacing:1px;">@@BRANDB@@</div><div style="color:#fff;font-size:44px;letter-spacing:1px;">@@MODELB@@</div></div>
<div style="position:absolute;top:506px;left:54px;width:972px;">@@ROWS@@</div>
<div style="position:absolute;bottom:118px;width:100%;font-family:'Mont';font-weight:600;font-size:23px;color:#c3c5d0;">@@NOTE@@</div>
<div style="position:absolute;bottom:46px;width:100%;"><div style="font-family:'Bebas';font-size:30px;letter-spacing:2px;color:#fff;">@TENISIDEAL<span class="gn">_BR</span></div>
 <div style="font-family:'Mont';font-size:18px;color:#9a9ca7;margin-top:2px;letter-spacing:1px;">tenisideal.com.br</div></div>
</div>"""

ROW = """<div style="display:grid;grid-template-columns:1fr 220px 1fr;align-items:center;height:68px;border-radius:8px;@@ALT@@">
<div style="text-align:right;padding-right:28px;font-family:'Bebas';font-size:34px;letter-spacing:.5px;color:@@CA@@;">@@VA@@</div>
<div style="text-align:center;font-family:'Mont';font-weight:700;font-size:17px;letter-spacing:2px;color:#8d8f9a;">@@LBL@@</div>
<div style="text-align:left;padding-left:28px;font-family:'Bebas';font-size:34px;letter-spacing:.5px;color:@@CB@@;">@@VB@@</div></div>"""


# ───────────────────── utilidades ─────────────────────
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
    if not all(sum(img.getpixel(p)) / 3 > 200 for p in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]):
        return None
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        try:
            ImageDraw.floodfill(img, xy, (255, 0, 255), thresh=46)
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


def baixar_recortar(url, dest):
    try:
        shoe = recortar(baixar(url))
    except Exception as e:
        print(f"  [foto falhou] {e}", file=sys.stderr)
        return False
    if shoe is None:
        return False
    shoe.save(dest)
    return True


def fmt_preco(p):
    try:
        return "R$ " + "{:,}".format(int(round(float(p)))).replace(",", ".")
    except Exception:
        return ""


def melhor_link(s):
    melhor = None
    for v in (s.get("affiliate_links") or {}).values():
        if v.get("price") and (melhor is None or v["price"] < melhor["price"]):
            melhor = v
    if melhor:
        return melhor["price"], (melhor.get("installments") or "").strip()
    return s.get("price") or 0, ""


def achar_chrome():
    cands = ["google-chrome-stable", "google-chrome", "chrome", "chromium-browser", "chromium",
             os.environ.get("CHROME_PATH", ""),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    for c in cands:
        if not c:
            continue
        if os.path.sep in c:
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return c
    return None


def preparar_fontes(workdir):
    for f in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(f):
            shutil.copy(f, os.path.join(workdir, f))


def render(workdir, html, outname):
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome não encontrado.", file=sys.stderr)
        return None
    open(os.path.join(workdir, "art.html"), "w", encoding="utf-8").write(html)
    out2x = os.path.join(workdir, "out2x.png")
    if os.path.exists(out2x):
        os.remove(out2x)
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
    Image.open(out2x).convert("RGB").resize((1080, 1080), Image.LANCZOS).save(outname, "PNG")
    return outname


def hashtags(*extra):
    base = ["tenisdecorrida", "corrida", "running", "corredores", "vidadecorredor", "tenisideal", "corridaderua"]
    return " ".join("#" + h for h in list(dict.fromkeys([*[e for e in extra if e], *base])))


def cta_quiz():
    return "🔎 Faça nosso quiz e descubra o tênis ideal pro seu perfil — link na bio 👉 tenisideal.com.br"


# ───────────────────── formatos ─────────────────────
def build_destaque(shoes, wd):
    pool = [s for s in shoes if "amazon" in (s.get("photo") or "").lower()]
    dia = datetime.date.today().timetuple().tm_yday
    for k in range(len(pool)):
        s = pool[(dia + k) % len(pool)]
        if not baixar_recortar(s["photo"], os.path.join(wd, "shoe.png")):
            continue
        preco, parc = melhor_link(s)
        sub = (s.get("reason") or s.get("description") or "").split(".")[0].strip()
        html = (HTML_DESTAQUE.replace("@@BRAND@@", s["brand"].upper()).replace("@@MODEL@@", s["name"].upper())
                .replace("@@SUB@@", sub).replace("@@PRICE@@", fmt_preco(preco) or "—"))
        png = render(wd, html, "arte_destaque.png")
        if not png:
            return None
        tag = re.sub(r"[^a-z0-9]", "", s["brand"].lower())
        leg = (f"🔥 {s['brand'].upper()} {s['name'].upper()} 👟\n\n{(s.get('reason') or '').strip()}\n\n"
               f"💰 A partir de {fmt_preco(preco)}" + (f" ({parc})" if parc else "") + "\n"
               f"{cta_quiz()}\n\n📲 Siga @tenisideal_br pra mais dicas de corrida!\n\n" + hashtags(tag, "tenis"))
        return png, leg, f"{s['brand']} {s['name']}"
    return None


def build_grid(shoes, wd):
    cand = [s for s in shoes if "amazon" in (s.get("photo") or "").lower() and s.get("price")]
    cand.sort(key=lambda s: -(s.get("price") or 0))
    seen, prem = set(), []
    for s in cand:
        if s["brand"] not in seen:
            prem.append(s); seen.add(s["brand"])
    if len(prem) < 6:
        prem = cand
    if len(prem) < 6:
        return None
    prem = prem[:8]   # só os mais premium (combina com o tema "tênis dos sonhos")
    os.makedirs(os.path.join(wd, "grid"), exist_ok=True)
    dia = datetime.date.today().timetuple().tm_yday
    chosen = []
    for k in range(len(prem)):
        s = prem[(dia + k) % len(prem)]
        if any(c is s for c in chosen):
            continue
        if baixar_recortar(s["photo"], os.path.join(wd, "grid", f"shoe{len(chosen)}.png")):
            chosen.append(s)
        if len(chosen) == 6:
            break
    if len(chosen) < 6:
        return None
    cells, linhas = "", []
    for i, s in enumerate(chosen):
        cells += (CELL.replace("@@N@@", str(i + 1)).replace("@@I@@", str(i))
                  .replace("@@BRAND@@", s["brand"].upper()).replace("@@MODEL@@", s["name"].upper())
                  .replace("@@PRICE@@", fmt_preco(s.get("price"))))
        linhas.append(f"{i + 1}. {s['brand']} {s['name']}")
    png = render(wd, HTML_GRID.replace("@@CELLS@@", cells), "arte_sonhos.png")
    if not png:
        return None
    leg = ("💭 TÊNIS DOS SONHOS 👟🔥\n\nQual desses é o SEU? Comenta o número 👇\n\n" + "\n".join(linhas) +
           f"\n\n{cta_quiz()}\n\n📲 Siga @tenisideal_br\n\n" + hashtags("supertenis", "maratona"))
    return png, leg, "Tênis dos Sonhos"


def build_comparativo(shoes, wd):
    def _road(s):
        nm = (s["brand"] + " " + s["name"]).lower()
        return "trilha" not in (s.get("terreno") or []) and not any(k in nm for k in TRAIL_KW)
    pool = [s for s in shoes if "amazon" in (s.get("photo") or "").lower() and s.get("price")
            and 350 <= s["price"] <= 1500 and "neutra" in (s.get("pisada") or [])
            and "intermediario" in (s.get("levels") or []) and _road(s)]
    if len(pool) < 2:
        return None
    pool.sort(key=lambda s: (s["brand"], s["name"]))
    n = len(pool)
    dia = datetime.date.today().timetuple().tm_yday
    os.makedirs(os.path.join(wd, "cmp"), exist_ok=True)
    for attempt in range(n):
        a = pool[(dia + attempt) % n]
        b = next((pool[(dia + attempt + k) % n] for k in range(1, n) if pool[(dia + attempt + k) % n]["brand"] != a["brand"]), None)
        if not b:
            continue
        if not (baixar_recortar(a["photo"], os.path.join(wd, "cmp", "a.png"))
                and baixar_recortar(b["photo"], os.path.join(wd, "cmp", "b.png"))):
            continue

        def niv(s):
            L = s.get("levels") or []
            return ("Inic." if "iniciante" in L else "Interm.") + " a " + ("Avançado" if "avancado" in L else "Interm.")

        def terr(s):
            t = [x for x in (s.get("terreno") or []) if x != "esteira"]
            return "Asfalto/Rua" if "asfalto" in t else (", ".join(x.capitalize() for x in t) or "Rua")

        def dist(s):
            return "Até longas" if "longa" in (s.get("distancia") or []) else "Curtas/médias"

        def dest(s):
            return (s.get("tags") or ["Versátil"])[0]
        pa, pb = a.get("price") or 0, b.get("price") or 0
        ca = "#C8FF00" if pa < pb else "#fff"
        cb = "#C8FF00" if pb < pa else "#fff"
        dados = [("PREÇO", fmt_preco(pa), fmt_preco(pb), ca, cb),
                 ("PISADA", "Neutra/Supinada", "Neutra/Supinada", "#fff", "#fff"),
                 ("NÍVEL", niv(a), niv(b), "#fff", "#fff"),
                 ("DISTÂNCIA", dist(a), dist(b), "#fff", "#fff"),
                 ("TERRENO", terr(a), terr(b), "#fff", "#fff"),
                 ("DESTAQUE", dest(a), dest(b), "#fff", "#fff")]
        rows = ""
        for idx, (lbl, va, vb, cca, ccb) in enumerate(dados):
            rows += (ROW.replace("@@ALT@@", "background:rgba(255,255,255,.04);" if idx % 2 else "")
                     .replace("@@LBL@@", lbl).replace("@@VA@@", va).replace("@@VB@@", vb)
                     .replace("@@CA@@", cca).replace("@@CB@@", ccb))
        barato = a if pa < pb else b
        html = (HTML_CMP.replace("@@BRANDA@@", a["brand"].upper()).replace("@@MODELA@@", a["name"].upper())
                .replace("@@BRANDB@@", b["brand"].upper()).replace("@@MODELB@@", b["name"].upper())
                .replace("@@ROWS@@", rows)
                .replace("@@NOTE@@", f"Mais em conta: {barato['brand']} {barato['name']}. Faça o quiz e ache o seu 👇"))
        png = render(wd, html, "arte_comparativo.png")
        if not png:
            return None
        ta, tb = (re.sub(r"[^a-z0-9]", "", a["brand"].lower()), re.sub(r"[^a-z0-9]", "", b["brand"].lower()))
        leg = (f"⚔️ {a['brand'].upper()} {a['name'].upper()} x {b['brand'].upper()} {b['name'].upper()}: qual escolher?\n\n"
               f"Os dois são ótimos pro dia a dia. O mais em conta é o {barato['brand']} {barato['name']} ({fmt_preco(barato.get('price'))}).\n\n"
               f"{cta_quiz()}\n\n📲 Siga @tenisideal_br\n\n" + hashtags("comparativo", ta, tb))
        return png, leg, f"{a['brand']} {a['name']} x {b['brand']} {b['name']}"
    return None


def melhor_cupom():
    if not os.environ.get("AWIN_API_TOKEN"):
        return None
    try:
        from gerar_cupons_awin import buscar_promocoes, campo
        dados = buscar_promocoes()
        promos = dados if isinstance(dados, list) else (dados.get("data") or dados.get("promotions") or dados.get("offers") or [])
        for p in promos:
            voucher = p.get("voucher") or {}
            code = campo(voucher, "code") or campo(p, "code")
            title = campo(p, "title", "description", default="")
            m = re.search(r"(\d{1,2})\s*%", title or "")
            if code and m:
                loja = campo(p, "advertiserName") or campo(p.get("advertiser", {}), "name", default="Loja")
                return {"loja": loja.replace(" BR", "").strip(), "code": code, "pct": m.group(1),
                        "desc": " ".join((title or "").split())[:54]}
    except Exception as e:
        print(f"[cupom indisponível] {e}", file=sys.stderr)
    return None


def build_cupom(shoes, wd):
    c = melhor_cupom()
    if not c:
        return None
    html = (HTML_CUPOM.replace("@@PCT@@", c["pct"] + "%").replace("@@STORE@@", c["loja"].upper()[:16])
            .replace("@@DESC@@", c["desc"] or "em produtos selecionados").replace("@@CODE@@", c["code"].upper()))
    png = render(wd, html, "arte_cupom.png")
    if not png:
        return None
    tag = re.sub(r"[^a-z0-9]", "", c["loja"].lower())
    leg = (f"🎟️ {c['pct']}% OFF na {c['loja'].upper()}! 👟\n\nUse o cupom *{c['code'].upper()}* na loja e economize.\n\n"
           f"{cta_quiz()}\n\n📲 Siga @tenisideal_br pra não perder nenhum cupom!\n\n" + hashtags("cupom", "desconto", "ofertas", tag))
    return png, leg, f"Cupom {c['loja']}"


# ───────────────────── envio ─────────────────────
def enviar_email(png, legenda, assunto):
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
            f"— <b>{assunto}</b>. Baixe a imagem em anexo, copie a legenda abaixo e poste no <b>@tenisideal_br</b>.</p>"
            "<p style='font-family:sans-serif;margin:18px 0 6px'><b>📸 Legenda pronta (é só copiar):</b></p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;border:1px solid #ddd;"
            f"border-radius:8px;padding:14px;font-size:14px'>{leg_html}</pre>")
    body = {"sender": {"email": remet, "name": "Arte do dia - Tênis Ideal"},
            "to": [{"email": email}], "subject": f"📸 Arte do dia {hoje} — {assunto}",
            "htmlContent": html, "attachment": [{"content": anexo, "name": png}]}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json", "accept": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"✅ E-mail enviado para {email} (HTTP {r.status})")


def main():
    shoes = carregar_catalogo()
    wd = tempfile.mkdtemp(prefix="ti_arte_")
    preparar_fontes(wd)
    formato = (os.environ.get("FORMATO_ARTE") or SCHEDULE[datetime.date.today().weekday()]).lower()
    builders = {"destaque": build_destaque, "comparativo": build_comparativo,
                "sonhos": build_grid, "cupom": build_cupom}
    res = builders.get(formato, build_destaque)(shoes, wd)
    if not res:
        print(f"[formato '{formato}' indisponível — caindo pro Destaque]", file=sys.stderr)
        res = build_destaque(shoes, wd)
    if not res:
        print("ERRO: nenhuma arte gerada.", file=sys.stderr)
        sys.exit(1)
    png, legenda, assunto = res
    print(f"🎨 Formato do dia: {formato} → {assunto} ({png})")
    enviar_email(png, legenda, assunto)


if __name__ == "__main__":
    main()
