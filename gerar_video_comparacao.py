#!/usr/bin/env python3
"""Vídeo de COMPARAÇÃO (duelo) pro Instagram/TikTok — 9:16 (HTML->Chrome + ffmpeg).

Formato "esse ou esse?": dois tênis brigam em 5 rounds (peso, energia, estabilidade,
facilidade, preço). Cada cena mostra uma frase que é EXATAMENTE a legenda/narração
daquela cena (o narrador lê o que aparece na tela). Sai mudo — a voz é gravada depois.

Reaproveita os helpers do motor de rodízio (gerar_video_tiktok.py) — NÃO altera o motor.
Estilo harmoniza com o feed: grafite + Bebas/Montserrat, com as 2 cores do carrossel
Brutalism (laranja p/ Adidas, verde-lima p/ Saucony). A CAPA é composta na zona segura
4:5 (miniatura da grade do perfil sem corte).

Fundo IA (opcional): se OPENROUTER_API_KEY estiver no ambiente, gera um fundo
cinematográfico via google/gemini-2.5-flash-image p/ capa e veredito; senão usa gradiente.

Teste local:  python3 gerar_video_comparacao.py
"""
import os, sys, io, ssl, json, base64, shutil, tempfile, subprocess
import urllib.request
from PIL import Image

def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

# Reaproveita o motor sem reescrever (mesmos helpers de download/recorte/render/ffmpeg)
from gerar_video_tiktok import (
    carregar_catalogo, baixar, recortar, achar_chrome, render_frame,
)
import imageio_ffmpeg

LIMA = "#C8FF00"      # Saucony (mesmo verde do feed)
LARANJA = "#FF6A00"   # Adidas (laranja do carrossel Brutalism)

# ---------------------------------------------------------------- conteúdo (verificado em fóruns/labs)
A = dict(brand="ADIDAS", model="ADIOS PRO 4", price="R$ 2.000", cor=LARANJA, tag="A FACA")
B = dict(brand="SAUCONY", model="ENDORPHIN PRO 4", price="R$ 1.382", cor=LIMA, tag="A ESPERTA")

# Cada round: critério, valor A, valor B, vencedor ('A' ou 'B'), legenda/narração
ROUNDS = [
    dict(crit="PESO",         va="201g",        vb="218g",         win="A",
         cap="Round 1, peso: a Adidas leva, 201 contra 218 gramas."),
    dict(crit="ENERGIA",      va="80% RETORNO", vb="ALTO",         win="A",
         cap="Round 2, energia: Adidas de novo, 80% de retorno, recorde nos testes."),
    dict(crit="ESTABILIDADE", va="MACIA",       vb="FIRME",        win="B",
         cap="Round 3, estabilidade: a Saucony vira o jogo. A Adios é macia e instável."),
    dict(crit="FACILIDADE",   va="SÓ RITMO FORTE", vb="TREINO + PROVA", win="B",
         cap="Round 4, facilidade: a Saucony serve treino e prova. A Adidas é só pra ritmo forte."),
    dict(crit="PREÇO",        va="R$ 2.000",    vb="R$ 1.382",     win="B",
         cap="Round 5, preço: a Saucony ganha fácil, 600 reais mais barata."),
]
CAP_CAPA = "R$ 2 mil contra R$ 1.382. Qual super shoe de carbono vale mais a pena?"
CAP_APRE = "De um lado, a Adidas Adios Pro 4. Do outro, a Saucony Endorphin Pro 4."
CAP_VER  = "Placar 2 a 3. Mas não existe a melhor: a Adidas é pra recorde, a Saucony pra versatilidade."
CAP_CTA  = "Qual é a certa pra VOCÊ? Faça o quiz e descubra, link na bio."

# ---------------------------------------------------------------- CSS / blocos base
HEAD = ("<!doctype html><html><head><meta charset='utf-8'><style>"
        "@font-face{font-family:'Bebas';src:url('BebasNeue.ttf');}"
        "@font-face{font-family:'Mont';src:url('Montserrat.ttf');}"
        "*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1080px;height:1920px;}"
        ".c{width:1080px;height:1920px;position:relative;overflow:hidden;font-family:'Mont';text-align:center;"
        "background:radial-gradient(70% 45% at 50% 40%,#2c2d37 0%,#17171d 55%,#0a0a0e 100%);}"
        ".c.bg{background-size:cover;background-position:center;}"
        ".ov{position:absolute;inset:0;background:radial-gradient(75% 55% at 50% 42%,rgba(10,10,14,.30),rgba(10,10,14,.82) 78%);}"
        ".logo{position:absolute;top:70px;width:100%;font-family:'Bebas';font-size:52px;letter-spacing:4px;z-index:3;}"
        ".logo b{color:#fff;font-weight:400;}.logo i{color:#C8FF00;font-style:normal;}"
        ".foot{position:absolute;bottom:70px;width:100%;z-index:3;}"
        ".foot .h{font-family:'Bebas';font-size:40px;letter-spacing:3px;color:#fff;}"
        ".foot .h i{color:#C8FF00;font-style:normal;}"
        ".cap{position:absolute;left:70px;right:70px;bottom:150px;z-index:3;"
        "font-family:'Mont';font-weight:700;font-size:37px;line-height:1.32;color:#fff;"
        "text-shadow:0 3px 14px rgba(0,0,0,.8);}"
        "</style></head><body>")
TAIL = "</body></html>"
LOGO = "<div class='logo'><b>TÊNIS</b><i>IDEAL</i></div>"
FOOT = "<div class='foot'><div class='h'>@TENISIDEAL<i>_BR</i></div></div>"


def cap(txt):
    return f"<div class='cap'>{txt}</div>"


def glow(cor, cx, cy, w=760, h=420):
    return (f"<div style='position:absolute;top:{cy}px;left:{cx}px;transform:translate(-50%,-50%);"
            f"width:{w}px;height:{h}px;background:radial-gradient(ellipse at center,{cor}38,transparent 70%);"
            f"filter:blur(46px);z-index:1;'></div>")


def img(tag, cx, cy, maxw=430, maxh=360):
    return (f"<img src='{tag}' style='position:absolute;top:{cy}px;left:{cx}px;transform:translate(-50%,-50%);"
            f"width:auto;max-width:{maxw}px;max-height:{maxh}px;object-fit:contain;z-index:2;"
            f"filter:drop-shadow(0 30px 26px rgba(0,0,0,.6));'>")


def selo(cor, cx, cy):
    return (f"<div style='position:absolute;top:{cy}px;left:{cx}px;transform:translate(-50%,-50%) rotate(-8deg);"
            f"background:{cor};color:#101015;font-family:Bebas;font-size:40px;letter-spacing:2px;"
            f"padding:10px 26px 4px;border-radius:8px;z-index:4;box-shadow:0 8px 20px rgba(0,0,0,.5);'>VENCE</div>")


# ---------------------------------------------------------------- frames
def f_capa(has_bg):
    cls = "c bg" if has_bg else "c"
    bg = "style=\"background-image:url('bg_capa.png')\"" if has_bg else ""
    # tudo dentro da zona segura 4:5 (y ~300..1620) -> miniatura da grade sem corte
    return HEAD + f"<div class='{cls}' {bg}>" + ("<div class='ov'></div>" if has_bg else "") + LOGO + (
        "<div style='position:absolute;top:300px;width:100%;z-index:3;'>"
        "<div style='font-family:Mont;font-weight:800;font-size:44px;color:#b8bac4;letter-spacing:3px;'>DUELO DE SUPER SHOES</div>"
        "<div style='font-family:Bebas;font-size:150px;color:#fff;line-height:.86;margin-top:18px;letter-spacing:2px;'>R$2.000</div>"
        f"<div style='font-family:Bebas;font-size:78px;color:{LARANJA};line-height:.9;'>vs</div>"
        f"<div style='font-family:Bebas;font-size:150px;color:{LIMA};line-height:.82;letter-spacing:2px;'>R$1.382</div>"
        "</div>"
        + glow(LARANJA, 300, 1180) + glow(LIMA, 780, 1180)
        + img("shoeA.png", 300, 1180, 470, 400) + img("shoeB.png", 780, 1180, 470, 400)
        + "<div style='position:absolute;top:1470px;width:100%;z-index:3;font-family:Mont;font-weight:800;"
        "font-size:40px;color:#fff;letter-spacing:1px;padding:0 90px;'>qual vale mais a pena? 👇</div>"
    ) + FOOT + "</div>" + TAIL


def f_apresentacao():
    def side(s, tag, cx):
        return (f"<div style='position:absolute;top:360px;left:{cx}px;transform:translateX(-50%);width:470px;z-index:3;'>"
                f"<div style='font-family:Bebas;font-size:38px;letter-spacing:3px;color:{s['cor']};'>{s['tag']}</div>"
                f"<div style='font-family:Bebas;font-size:52px;color:#fff;line-height:.92;margin-top:6px;'>{s['brand']}</div>"
                f"<div style='font-family:Bebas;font-size:66px;color:{s['cor']};line-height:.9;'>{s['model']}</div></div>")
    return HEAD + "<div class='c'>" + LOGO + (
        side(A, "A", 300) + side(B, "B", 780)
        + glow(LARANJA, 300, 980) + glow(LIMA, 780, 980)
        + img("shoeA.png", 300, 980, 480, 430) + img("shoeB.png", 780, 980, 480, 430)
        + f"<div style='position:absolute;top:760px;left:50%;transform:translate(-50%,-50%);width:118px;height:118px;"
        f"border-radius:50%;background:#14141b;border:5px solid #fff;color:#fff;font-family:Bebas;font-size:60px;"
        f"line-height:118px;z-index:5;'>VS</div>"
        + f"<div style='position:absolute;top:1320px;width:100%;z-index:3;font-family:Mont;font-weight:700;font-size:34px;"
        f"color:#9a9ca7;letter-spacing:1px;'>duas placas de carbono. 5 rounds. 1 veredito.</div>"
        + cap(CAP_APRE)
    ) + FOOT + "</div>" + TAIL


def f_round(i, r):
    winA = r["win"] == "A"
    corW = A["cor"] if winA else B["cor"]

    def side(s, val, cx, is_win):
        op = "1" if is_win else ".5"
        ring = f"box-shadow:0 0 0 4px {s['cor']};" if is_win else ""
        return (f"<div style='position:absolute;top:640px;left:{cx}px;transform:translate(-50%,-50%);width:430px;"
                f"opacity:{op};z-index:2;'>"
                f"<div style='font-family:Bebas;font-size:40px;color:{s['cor']};letter-spacing:2px;'>{s['brand']}</div>"
                f"<div style='background:rgba(255,255,255,.06);{ring}border-radius:20px;padding:26px 10px;margin-top:12px;'>"
                f"<div style='font-family:Bebas;font-size:58px;color:#fff;line-height:1;'>{val}</div></div></div>")
    winglow = glow(corW, 300 if winA else 780, 640, 640, 520)
    return HEAD + "<div class='c'>" + LOGO + (
        f"<div style='position:absolute;top:290px;width:100%;z-index:3;'>"
        f"<div style='font-family:Mont;font-weight:800;font-size:40px;color:#b8bac4;letter-spacing:4px;'>ROUND {i}/5</div>"
        f"<div style='font-family:Bebas;font-size:120px;color:#fff;line-height:.86;letter-spacing:2px;margin-top:6px;'>{r['crit']}</div></div>"
        + winglow
        + side(A, r["va"], 300, winA) + side(B, r["vb"], 780, not winA)
        + selo(corW, 300 if winA else 780, 470)
        + f"<div style='position:absolute;top:640px;left:50%;transform:translate(-50%,-50%);width:96px;height:96px;"
        f"border-radius:50%;background:#14141b;border:4px solid #34343f;color:#787884;font-family:Bebas;font-size:42px;"
        f"line-height:96px;z-index:5;'>VS</div>"
        + cap(r["cap"])
    ) + FOOT + "</div>" + TAIL


def f_veredito(has_bg):
    cls = "c bg" if has_bg else "c"
    bg = "style=\"background-image:url('bg_ver.png')\"" if has_bg else ""
    return HEAD + f"<div class='{cls}' {bg}>" + ("<div class='ov'></div>" if has_bg else "") + LOGO + (
        "<div style='position:absolute;top:330px;width:100%;z-index:3;'>"
        "<div style='font-family:Mont;font-weight:800;font-size:44px;color:#b8bac4;letter-spacing:3px;'>PLACAR FINAL</div>"
        f"<div style='margin-top:26px;font-family:Bebas;font-size:150px;line-height:.9;letter-spacing:3px;'>"
        f"<span style='color:{LARANJA}'>2</span><span style='color:#5a5a66'> — </span><span style='color:{LIMA}'>3</span></div>"
        f"<div style='margin-top:8px;font-family:Bebas;font-size:40px;letter-spacing:3px;'>"
        f"<span style='color:{LARANJA}'>ADIDAS</span><span style='color:#5a5a66'>   x   </span><span style='color:{LIMA}'>SAUCONY</span></div>"
        "</div>"
        "<div style='position:absolute;top:820px;left:90px;right:90px;z-index:3;'>"
        f"<div style='background:rgba(255,255,255,.06);border-left:6px solid {LARANJA};border-radius:14px;padding:22px 26px;text-align:left;'>"
        f"<b style='font-family:Bebas;font-size:44px;color:{LARANJA};letter-spacing:1px;'>ADIOS PRO 4</b>"
        "<div style='font-family:Mont;font-weight:600;font-size:32px;color:#d6d7de;margin-top:4px;'>mais leve e explosiva — pra buscar recorde.</div></div>"
        f"<div style='background:rgba(255,255,255,.06);border-left:6px solid {LIMA};border-radius:14px;padding:22px 26px;text-align:left;margin-top:22px;'>"
        f"<b style='font-family:Bebas;font-size:44px;color:{LIMA};letter-spacing:1px;'>ENDORPHIN PRO 4</b>"
        "<div style='font-family:Mont;font-weight:600;font-size:32px;color:#d6d7de;margin-top:4px;'>estável, versátil e R$600 mais barata.</div></div>"
        "</div>"
        + cap(CAP_VER)
    ) + FOOT + "</div>" + TAIL


def f_cta():
    return HEAD + "<div class='c'>" + LOGO + (
        "<div style='position:absolute;top:520px;width:100%;z-index:3;'>"
        "<div style='font-family:Mont;font-weight:700;font-size:52px;color:#b8bac4;letter-spacing:2px;'>NÃO EXISTE A MELHOR</div>"
        "<div style='font-family:Mont;font-weight:700;font-size:44px;color:#fff;margin-top:8px;'>existe a ideal pra VOCÊ</div>"
        f"<div style='font-family:Bebas;font-size:190px;color:{LIMA};line-height:.82;margin-top:36px;letter-spacing:2px;'>FAÇA O QUIZ</div>"
        "<div style='font-family:Mont;font-weight:600;font-size:42px;color:#fff;margin-top:22px;padding:0 110px;line-height:1.3;'>"
        "descubra seu tênis ideal em 60 segundos</div>"
        f"<div style='display:inline-block;margin-top:52px;background:{LIMA};color:#14141b;font-family:Bebas;font-size:60px;"
        "letter-spacing:3px;padding:22px 60px 12px;border-radius:50px;'>LINK NA BIO →</div>"
        "</div>"
    ) + FOOT + "</div>" + TAIL


# ---------------------------------------------------------------- CAPA dedicada 4:5 (1080x1350)
HEAD_C = HEAD.replace("height:1920px", "height:1350px")


def f_cover(has_bg):
    cls = "c bg" if has_bg else "c"
    bg = "style=\"background-image:url('bg_cover.png')\"" if has_bg else ""
    return HEAD_C + f"<div class='{cls}' {bg}>" + ("<div class='ov'></div>" if has_bg else "") + (
        "<div class='logo' style='top:56px;'><b>TÊNIS</b><i>IDEAL</i></div>"
        "<div style='position:absolute;top:170px;width:100%;z-index:3;'>"
        "<div style='font-family:Mont;font-weight:800;font-size:40px;color:#b8bac4;letter-spacing:4px;'>DUELO DE SUPER SHOES</div>"
        f"<div style='margin-top:10px;font-family:Bebas;font-size:112px;line-height:.9;letter-spacing:2px;'>"
        f"<span style='color:{LARANJA}'>ADIDAS</span></div>"
        f"<div style='font-family:Bebas;font-size:60px;color:#fff;line-height:.8;'>vs</div>"
        f"<div style='font-family:Bebas;font-size:112px;line-height:.9;letter-spacing:2px;color:{LIMA}'>SAUCONY</div>"
        "</div>"
        + glow(LARANJA, 300, 800, 620, 440) + glow(LIMA, 780, 800, 620, 440)
        + img("shoeA.png", 300, 810, 460, 400) + img("shoeB.png", 780, 810, 460, 400)
        + "<div style='position:absolute;top:1130px;width:100%;z-index:3;font-family:Mont;font-weight:800;"
        "font-size:46px;color:#fff;letter-spacing:1px;'>qual vale mais a pena? 👇</div>"
        + "<div class='foot' style='bottom:52px;'><div class='h'>@TENISIDEAL<i>_BR</i></div></div>"
    ) + "</div>" + TAIL


def render_cover(wd, chrome, html, outpng):
    open(os.path.join(wd, "cv.html"), "w", encoding="utf-8").write(html)
    raw = os.path.join(wd, "cvraw.png")
    if os.path.exists(raw):
        os.remove(raw)
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--force-device-scale-factor=2",
                    "--window-size=1080,1350", "--hide-scrollbars", "--default-background-color=00000000",
                    "--virtual-time-budget=3000", "--screenshot=" + raw, "--allow-file-access-from-files",
                    "file://" + os.path.join(wd, "cv.html")], check=False, capture_output=True, timeout=120)
    if not os.path.exists(raw):
        return False
    Image.open(raw).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(outpng)
    return True


def gerar_capa(wd):
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome não encontrado.", file=sys.stderr); return None
    for f in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(f):
            shutil.copy(f, os.path.join(wd, f))
    S = carregar_catalogo()
    sa = achar(S, "adios", "pro"); sb = achar(S, "endorphin", "pro")
    for tag, s in (("shoeA", sa), ("shoeB", sb)):
        cut = recortar(baixar(s["photo"]))
        if cut is None:
            print(f"ERRO: recorte falhou ({tag}).", file=sys.stderr); return None
        cut.save(os.path.join(wd, tag + ".png"))
    bg = gerar_bg_ia(
        "Cinematic wide photo of an empty outdoor running track and dark wet asphalt at dawn, "
        "moody desaturated teal-and-charcoal tones, dramatic low light, soft fog, no people, "
        "no text, vertical composition, lots of empty dark space in the center for text overlay.",
        os.path.join(wd, "bg_cover.png"), tw=1080, th=1350)
    out = os.path.join(os.getcwd(), os.environ.get("CAPA_OUT") or "capa_reels.png")
    if not render_cover(wd, chrome, f_cover(bg), out):
        return None
    return out, bg


# ---------------------------------------------------------------- fundo IA (OpenRouter, opcional)
def gerar_bg_ia(prompt, outpath, tw=1080, th=1920):
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return False
    body = {"model": os.environ.get("OR_MODEL", "google/gemini-2.5-flash-image"),
            "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://tenisideal.com.br", "X-Title": "video-comparacao"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90, context=_ssl_ctx()) as r:
            data = json.loads(r.read())
        url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
        raw = base64.b64decode(url.split(",", 1)[1])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        # cover-crop pro alvo (tw x th)
        s = max(tw / im.width, th / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        L = (im.width - tw) // 2; T = (im.height - th) // 2
        im.crop((L, T, L + tw, T + th)).save(outpath)
        kb = os.path.getsize(outpath) // 1024
        print(f"  fundo IA ok ({kb}KB) -> {os.path.basename(outpath)}", file=sys.stderr)
        return kb > 30
    except Exception as e:
        print(f"  [fundo IA falhou -> gradiente] {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------- build
def achar(S, *words):
    for s in S:
        n = (s["brand"] + " " + s["name"]).lower()
        if all(w in n for w in words):
            return s
    return None


def build(wd):
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome não encontrado.", file=sys.stderr); return None
    for f in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(f):
            shutil.copy(f, os.path.join(wd, f))
    S = carregar_catalogo()
    sa = achar(S, "adios", "pro"); sb = achar(S, "endorphin", "pro")
    if not sa or not sb:
        print("ERRO: não achei os dois tênis no catálogo.", file=sys.stderr); return None
    for tag, s in (("shoeA", sa), ("shoeB", sb)):
        cut = recortar(baixar(s["photo"]))
        if cut is None:
            print(f"ERRO: recorte falhou ({tag}).", file=sys.stderr); return None
        cut.save(os.path.join(wd, tag + ".png"))
    # fundos IA (opcionais)
    bg_capa = gerar_bg_ia(
        "Cinematic wide photo of an empty outdoor running track and dark wet asphalt at dawn, "
        "moody desaturated teal-and-charcoal tones, dramatic low light, soft fog, no people, "
        "no text, vertical 9:16 composition, lots of empty dark space in the center for text overlay.",
        os.path.join(wd, "bg_capa.png"))
    bg_ver = gerar_bg_ia(
        "Cinematic close photo of a stadium finish line on dark asphalt at dusk, blurred, "
        "moody desaturated charcoal tones with a faint warm glow, no people, no text, "
        "vertical 9:16, dark empty space in the middle for text overlay.",
        os.path.join(wd, "bg_ver.png"))

    frames = [f_capa(bg_capa), f_apresentacao()]
    for i, r in enumerate(ROUNDS, 1):
        frames.append(f_round(i, r))
    frames += [f_veredito(bg_ver), f_cta()]
    # durações (s) — batem com o ritmo da narração.
    # DUR_SCALE encurta/alonga tudo proporcionalmente (ex.: TikTok mais ágil -> 0.78).
    try:
        scale = float(os.environ.get("DUR_SCALE") or 1.0)
    except Exception:
        scale = 1.0
    durs = [round(d * scale, 2) for d in ([3.4, 3.2] + [2.9] * len(ROUNDS) + [4.0, 3.6])]

    for idx, html in enumerate(frames):
        if not render_frame(wd, chrome, html, os.path.join(wd, f"frame{idx:02d}.png")):
            print(f"ERRO: render frame {idx}.", file=sys.stderr); return None

    lines = []
    for idx, d in enumerate(durs):
        lines += [f"file 'frame{idx:02d}.png'", f"duration {d}"]
    lines.append(f"file 'frame{len(durs)-1:02d}.png'")
    open(os.path.join(wd, "list.txt"), "w").write("\n".join(lines))

    mp4 = os.path.join(os.getcwd(), os.environ.get("VID_OUT") or "video_comparacao.mp4")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-r", "30",
                        "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4],
                       cwd=wd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ffmpeg erro:", r.stderr[-500:], file=sys.stderr); return None
    return mp4, (bg_capa or bg_ver)


def main():
    wd = tempfile.mkdtemp(prefix="ti_cmp_")
    # Modo capa: CAPA=1 gera só a imagem de capa 4:5 (1080x1350) e sai.
    if (os.environ.get("CAPA") or "").strip() in ("1", "true", "sim"):
        res = gerar_capa(wd)
        if not res:
            print("ERRO: não consegui gerar a capa.", file=sys.stderr); sys.exit(1)
        out, usou_ia = res
        print(f"🖼️  Capa 4:5 gerada: {out}  (1080x1350, fundo IA: {'sim' if usou_ia else 'não'})")
        return
    res = build(wd)
    if not res:
        sys.exit(1)
    mp4, usou_ia = res
    try:
        scale = float(os.environ.get("DUR_SCALE") or 1.0)
    except Exception:
        scale = 1.0
    total = sum([3.4, 3.2] + [2.9] * len(ROUNDS) + [4.0, 3.6]) * scale
    print(f"🎬 Vídeo de comparação gerado: {mp4}  (~{total:.0f}s, fundo IA: {'sim' if usou_ia else 'não'})")


if __name__ == "__main__":
    main()
