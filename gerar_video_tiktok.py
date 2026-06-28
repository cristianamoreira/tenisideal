#!/usr/bin/env python3
"""Robô de VÍDEO diário pro TikTok — slideshow vertical 9:16 (HTML->Chrome + ffmpeg) por e-mail.

Cada execução monta um vídeo com TEMA diferente (rotação): Tênis dos Sonhos, Melhores até R$500,
Top Amortecimento, Leves e Rápidos, Pra quem tá começando. Estrutura: gancho → tênis (foto real
recortada) → CTA do quiz. Sai sem áudio de propósito (você adiciona um som em alta no TikTok).

Roda no GitHub Actions (Pillow + imageio-ffmpeg + Chrome do runner).
Secrets: BREVO_API_KEY, EMAIL_CUPONS, EMAIL_REMETENTE (opcional).
Teste local: TEMA_VIDEO=ate500 python3 gerar_video_tiktok.py
"""
import os, sys, re, io, ssl, json, base64, shutil, tempfile, subprocess, datetime
import urllib.request
from PIL import Image, ImageDraw, ImageFilter
import imageio_ffmpeg

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}
TRAIL_KW = ("trail", "trilha", "terrex", "hiking", "trabuco", "venture", "juniper", "peregrine",
            "hierro", "speedcross", "daichi", "shinobi", "agravic", "anylander", "wildhorse",
            "cascadia", "speedgoat", "torrent", "xodus", "rincon", "aero blaze")


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
    for y in range(int(h * 0.5), h):  # remove a sombra cinza do chão
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and (max(r, g, b) - min(r, g, b)) < 30 and 128 < min(r, g, b) < 216:
                px[x, y] = (0, 0, 0, 0)
    a = rgba.split()[3].filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))
    rgba.putalpha(a)
    bb = rgba.getbbox()
    return rgba.crop(bb) if bb else rgba


def fmt(p):
    try:
        return "R$ " + "{:,}".format(int(round(float(p)))).replace(",", ".")
    except Exception:
        return ""


def preco(s):
    ps = [v["price"] for v in (s.get("affiliate_links") or {}).values() if v.get("price")]
    return min(ps) if ps else (s.get("price") or 0)


def amazon(s):
    return "amazon" in (s.get("photo") or "").lower() and s.get("photo")


def eh_trilha(s):
    nm = (s["brand"] + " " + s["name"]).lower()
    return "trilha" in (s.get("terreno") or []) or any(k in nm for k in TRAIL_KW)


def distintas(lst):
    seen, out = set(), []
    for s in lst:
        if s["brand"] not in seen:
            out.append(s); seen.add(s["brand"])
    return out


def sel_premium(sh):
    return distintas(sorted([s for s in sh if amazon(s) and not eh_trilha(s) and s.get("price")], key=lambda s: -s["price"]))


def sel_ate500(sh):
    return distintas(sorted([s for s in sh if amazon(s) and not eh_trilha(s) and 0 < (s.get("price") or 0) <= 520], key=lambda s: -s["price"]))


def sel_tag(sh, tags):
    t = set(x.lower() for x in tags)
    cands = [s for s in sh if amazon(s) and not eh_trilha(s) and {x.lower() for x in (s.get("tags") or [])} & t]
    return distintas(sorted(cands, key=lambda s: -(s.get("price") or 0)))


def sel_amort(sh):
    return sel_tag(sh, ["Amortecimento", "Conforto", "Maxi Amortecimento", "Maciez", "Maxi-Soft"])


def sel_leves(sh):
    return sel_tag(sh, ["Leveza", "Leve", "Velocidade", "Carbono", "Super shoe", "Rápido"])


def sel_iniciante(sh):
    cands = [s for s in sh if amazon(s) and not eh_trilha(s) and "iniciante" in (s.get("levels") or []) and 0 < (s.get("price") or 0) <= 700]
    return distintas(sorted(cands, key=lambda s: s.get("price") or 0))


THEMES = [
    dict(key="sonhos", label="TÊNIS DOS SONHOS", small="QUAL É O SEU", big1="TÊNIS DOS", big2="SONHOS?",
         sub="comente o número do seu favorito 👇", select=sel_premium,
         hook="Qual é o seu TÊNIS DOS SONHOS? 👟🔥 Comenta o número 👇", tags=["supertenis", "maratona"]),
    dict(key="ate500", label="MELHORES ATÉ R$500", small="OS MELHORES", big1="TÊNIS ATÉ", big2="R$ 500",
         sub="qual vale mais a pena? comenta 👇", select=sel_ate500,
         hook="Os melhores tênis de corrida ATÉ R$500 👟💰 Qual você levaria? 👇", tags=["custobeneficio", "tenisbarato"]),
    dict(key="amort", label="MÁXIMO AMORTECIMENTO", small="OS TÊNIS DE", big1="MÁXIMO", big2="AMORTECIMENTO",
         sub="conforto pra rodar tranquilo 👇", select=sel_amort,
         hook="Tênis de MÁXIMO amortecimento pra correr sem dor 👟☁️ Comenta 👇", tags=["amortecimento", "conforto"]),
    dict(key="leves", label="LEVES E RÁPIDOS", small="OS TÊNIS MAIS", big1="LEVES E", big2="RÁPIDOS",
         sub="pra ganhar tempo nas provas 👇", select=sel_leves,
         hook="Tênis LEVES pra ganhar velocidade 👟⚡ Qual seu favorito? 👇", tags=["velocidade", "carbono"]),
    dict(key="iniciante", label="PRA QUEM TÁ COMEÇANDO", small="OS MELHORES PRA", big1="QUEM TÁ", big2="COMEÇANDO",
         sub="comece com o pé direito 👇", select=sel_iniciante,
         hook="Tá começando a correr? Esses tênis são pra você 👟🌱 Comenta 👇", tags=["iniciante", "corridainiciante"]),
]

HEAD = ("<!doctype html><html><head><meta charset='utf-8'><style>"
        "@font-face{font-family:'Bebas';src:url('BebasNeue.ttf');}"
        "@font-face{font-family:'Mont';src:url('Montserrat.ttf');}"
        "*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1080px;height:1920px;}"
        ".c{width:1080px;height:1920px;position:relative;overflow:hidden;font-family:'Mont';text-align:center;"
        "background:radial-gradient(70% 45% at 50% 42%,#2c2d37 0%,#17171d 55%,#0a0a0e 100%);}"
        ".hd{position:absolute;top:78px;width:100%;font-family:'Bebas';font-size:64px;letter-spacing:4px;}"
        ".hd b{color:#fff;font-weight:400;}.hd i{color:#C8FF00;font-style:normal;}"
        ".ft{position:absolute;bottom:86px;width:100%;}.ft .h{font-family:'Bebas';font-size:48px;letter-spacing:3px;color:#fff;}"
        ".ft .h i{color:#C8FF00;font-style:normal;}.ft .s{font-family:'Mont';font-size:27px;color:#9a9ca7;margin-top:5px;letter-spacing:1px;}"
        "</style></head><body>")
TAIL = "</body></html>"
HD = "<div class='hd'><b>TÊNIS</b><i>IDEAL</i></div>"
FT = "<div class='ft'><div class='h'>@TENISIDEAL<i>_BR</i></div><div class='s'>tenisideal.com.br</div></div>"


def hook_frame(t):
    bf = min(190, int(900 / (max(len(t["big1"]), len(t["big2"])) * 0.46)))
    return HEAD + "<div class='c'>" + HD + (
        "<div style='position:absolute;top:620px;width:100%;'>"
        f"<div style='font-family:Mont;font-weight:600;font-size:58px;color:#b8bac4;letter-spacing:3px;'>{t['small']}</div>"
        f"<div style='font-family:Bebas;font-size:{bf}px;color:#fff;line-height:.92;letter-spacing:2px;margin-top:46px;'>{t['big1']}</div>"
        f"<div style='font-family:Bebas;font-size:{bf}px;color:#C8FF00;line-height:.9;letter-spacing:2px;'>{t['big2']}</div>"
        "<div style='width:170px;height:9px;background:#C8FF00;border-radius:5px;margin:54px auto 0;'></div>"
        f"<div style='font-family:Mont;font-weight:600;font-size:44px;color:#C8FF00;margin-top:52px;padding:0 80px;'>{t['sub']}</div>"
        "</div>") + FT + "</div>" + TAIL


def shoe_frame(label, n, brand, model, price):
    mf = 86 if len(model) <= 14 else (74 if len(model) <= 20 else 62)
    return HEAD + "<div class='c'>" + HD + (
        f"<div style='position:absolute;top:178px;width:100%;font-family:Bebas;font-size:54px;color:#fff;letter-spacing:3px;opacity:.85;padding:0 60px;'>{label}</div>"
        f"<div style='position:absolute;top:308px;left:50%;transform:translateX(-50%);width:124px;height:124px;border-radius:50%;background:#C8FF00;color:#14141b;font-family:Bebas;font-size:92px;line-height:132px;'>{n}</div>"
        "<div style='position:absolute;top:790px;left:50%;transform:translateX(-50%);width:840px;height:360px;background:radial-gradient(ellipse at center,rgba(200,255,0,.18),rgba(150,170,255,.05) 45%,transparent 72%);filter:blur(42px);'></div>"
        f"<img src='shoe{n-1}.png' style='position:absolute;top:530px;left:50%;transform:translateX(-50%);width:950px;max-height:770px;object-fit:contain;filter:drop-shadow(0 40px 34px rgba(0,0,0,.55));'>"
        "<div style='position:absolute;top:1378px;width:100%;'>"
        f"<div style='font-family:Bebas;color:#C8FF00;font-size:62px;letter-spacing:2px;'>{brand}</div>"
        f"<div style='font-family:Bebas;color:#fff;font-size:{mf}px;letter-spacing:1px;line-height:.9;padding:0 70px;'>{model}</div></div>"
        f"<div style='position:absolute;top:1560px;width:100%;font-family:Mont;font-weight:700;font-size:48px;color:#b8bac4;'>{price}</div>"
    ) + FT + "</div>" + TAIL


def cta_frame():
    return HEAD + "<div class='c'>" + HD + (
        "<div style='position:absolute;top:620px;width:100%;'>"
        "<div style='font-family:Mont;font-weight:600;font-size:56px;color:#b8bac4;letter-spacing:2px;'>ACHOU O SEU?</div>"
        "<div style='font-family:Bebas;font-size:210px;color:#C8FF00;line-height:.82;margin-top:10px;letter-spacing:2px;'>FAÇA O QUIZ</div>"
        "<div style='font-family:Mont;font-weight:600;font-size:46px;color:#fff;margin-top:28px;padding:0 100px;line-height:1.3;'>e descubra o tênis ideal pro seu perfil em 60 segundos</div>"
        "<div style='display:inline-block;margin-top:58px;background:#C8FF00;color:#14141b;font-family:Bebas;font-size:64px;letter-spacing:3px;padding:22px 64px 14px;border-radius:50px;'>LINK NA BIO →</div>"
        "</div>") + FT + "</div>" + TAIL


def achar_chrome():
    for c in ["google-chrome-stable", "google-chrome", "chrome", "chromium-browser", "chromium",
              os.environ.get("CHROME_PATH", ""), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if not c:
            continue
        if os.path.sep in c:
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return c
    return None


def render_frame(wd, chrome, html, outpng):
    open(os.path.join(wd, "f.html"), "w", encoding="utf-8").write(html)
    raw = os.path.join(wd, "raw.png")
    if os.path.exists(raw):
        os.remove(raw)
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--force-device-scale-factor=2",
                    "--window-size=1080,1920", "--hide-scrollbars", "--default-background-color=00000000",
                    "--virtual-time-budget=3000", "--screenshot=" + raw, "--allow-file-access-from-files",
                    "file://" + os.path.join(wd, "f.html")], check=False, capture_output=True, timeout=120)
    if not os.path.exists(raw):
        return False
    Image.open(raw).convert("RGB").resize((1080, 1920), Image.LANCZOS).save(outpng)
    return True


def build_video(t, wd):
    chrome = achar_chrome()
    if not chrome:
        print("ERRO: Chrome não encontrado.", file=sys.stderr); return None
    for f in ("BebasNeue.ttf", "Montserrat.ttf"):
        if os.path.exists(f):
            shutil.copy(f, os.path.join(wd, f))
    shoes = t["select"](carregar_catalogo())
    chosen = []
    for s in shoes:
        try:
            shoe = recortar(baixar(s["photo"]))
        except Exception:
            shoe = None
        if shoe is None:
            continue
        shoe.save(os.path.join(wd, f"shoe{len(chosen)}.png"))
        chosen.append(s)
        if len(chosen) == 6:
            break
    if len(chosen) < 4:
        return None
    frames = [hook_frame(t)]
    for i, s in enumerate(chosen):
        frames.append(shoe_frame(t["label"], i + 1, s["brand"].upper(), s["name"].upper(), fmt(preco(s))))
    frames.append(cta_frame())
    durs = [2.4] + [1.7] * len(chosen) + [2.9]
    for idx, html in enumerate(frames):
        if not render_frame(wd, chrome, html, os.path.join(wd, f"frame{idx:02d}.png")):
            return None
    lines = []
    for idx, d in enumerate(durs):
        lines += [f"file 'frame{idx:02d}.png'", f"duration {d}"]
    lines.append(f"file 'frame{len(durs)-1:02d}.png'")
    open(os.path.join(wd, "list.txt"), "w").write("\n".join(lines))
    mp4 = "video_tiktok.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-r", "30",
                        "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        os.path.join(os.getcwd(), mp4)], cwd=wd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ffmpeg erro:", r.stderr[-500:], file=sys.stderr); return None
    legenda = (t["hook"] + "\n\n" + "\n".join(f"{i+1}️⃣ {s['brand']} {s['name']}" for i, s in enumerate(chosen)) +
               "\n\nNão sabe qual é o ideal pra VOCÊ? Faça nosso quiz em 60s e descubra — link na bio! 🔎\n\n" +
               " ".join("#" + h for h in ["tenisdecorrida", "corrida", "running", "tenis", "corridaderua",
                                          *t["tags"], "corredores", "fyp"]))
    return mp4, legenda


def enviar_email(mp4, legenda, label):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — vídeo gerado, e-mail pulado.", file=sys.stderr)
        return
    with open(mp4, "rb") as f:
        anexo = base64.b64encode(f.read()).decode()
    leg = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    hoje = datetime.date.today().strftime("%d/%m")
    html = ("<p style='font-family:sans-serif'>Bom dia! 🎬 Aqui está o <b>vídeo do dia pro TikTok</b> "
            f"— tema: <b>{label}</b>. Baixe o vídeo em anexo, poste no TikTok e <b>adicione um áudio em alta</b> "
            "(o vídeo vem sem som de propósito). Copie a legenda abaixo:</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;border:1px solid #ddd;"
            f"border-radius:8px;padding:14px;font-size:14px'>{leg}</pre>")
    body = {"sender": {"email": remet, "name": "Vídeo TikTok - Tênis Ideal"},
            "to": [{"email": email}], "subject": f"🎬 Vídeo do dia {hoje} pro TikTok — {label}",
            "htmlContent": html, "attachment": [{"content": anexo, "name": "tiktok_" + datetime.date.today().isoformat() + ".mp4"}]}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json", "accept": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"✅ E-mail enviado para {email} (HTTP {r.status})")


def main():
    chave = (os.environ.get("TEMA_VIDEO") or "").strip().lower()
    tema = next((t for t in THEMES if t["key"] == chave), None) or THEMES[datetime.date.today().timetuple().tm_yday % len(THEMES)]
    wd = tempfile.mkdtemp(prefix="ti_video_")
    res = build_video(tema, wd)
    if not res and tema["key"] != "sonhos":  # fallback
        res = build_video(THEMES[0], wd); tema = THEMES[0]
    if not res:
        print("ERRO: não consegui gerar o vídeo.", file=sys.stderr); sys.exit(1)
    mp4, legenda = res
    print(f"🎬 Vídeo gerado — tema: {tema['label']} ({mp4})")
    enviar_email(mp4, legenda, tema["label"])


if __name__ == "__main__":
    main()
