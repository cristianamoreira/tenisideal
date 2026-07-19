#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera um POST de imagem (grade de tênis por marca) no estilo "os melhores de cada
marca" — 1080x1350 (4:5) pro feed/TikTok do Tênis Ideal. Reaproveita o download +
recorte de fundo por IA do motor de vídeo (gerar_video_tiktok.py). Sai como PNG."""
import os, sys, tempfile, subprocess, base64, io
from PIL import Image

import gerar_video_tiktok as motor  # reaproveita baixar(), recortar(), achar_chrome()

# Marcas e modelos preferidos (na ordem). O script casa pelo nome no catálogo e,
# se não achar, cai pros primeiros modelos com foto daquela marca.
PLANO = [
    ("NIKE",        ["Vomero Plus", "Winflo 12", "Revolution 8"]),
    ("ASICS",       ["Gel-Nimbus 28", "Gel-Cumulus 26", "Gel-Kayano 32"]),
    ("ADIDAS",      ["Adizero Adios Pro 4", "Adizero Boston 13", "Ultraboost 5"]),
    ("MIZUNO",      ["Wave Rider 28", "Wave Inspire 21", "Wave Sky 9"]),
    ("NEW BALANCE", ["Fresh Foam X 1080 V14", "FuelCell SuperComp Elite v5", "Rebel v5"]),
]

TITULO_1 = "OS MELHORES"
TITULO_2 = "DE CADA MARCA"
SUB = "tênis de corrida que valem cada real 👟"


def escolher(cat):
    from collections import defaultdict
    by = defaultdict(list)
    for s in cat:
        if s.get("photo") and "Trilha" not in (s.get("tags") or []):
            by[s.get("brand")].append(s)
    linhas = []
    for marca, prefs in PLANO:
        pool = by.get(marca, [])
        escolhidos, usados = [], set()
        for nome in prefs:
            for s in pool:
                if s.get("name") == nome and id(s) not in usados:
                    escolhidos.append(s); usados.add(id(s)); break
        for s in pool:  # completa o que faltar (pula lifestyle)
            if len(escolhidos) >= 3:
                break
            if id(s) not in usados and "Estilo" not in (s.get("tags") or []):
                escolhidos.append(s); usados.add(id(s))
        if len(escolhidos) >= 3:
            linhas.append((marca, escolhidos[:3]))
    return linhas


def data_uri(png_path):
    with open(png_path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def build(wd):
    chrome = motor.achar_chrome()
    if not chrome:
        print("Chrome não encontrado", file=sys.stderr); sys.exit(1)
    cat = motor.carregar_catalogo()
    linhas = escolher(cat)
    if len(linhas) < 4:
        print("Poucas marcas com 3 modelos", file=sys.stderr); sys.exit(1)

    # baixa + recorta cada tênis
    imgs = {}  # (li, ci) -> data uri
    for li, (marca, tenis) in enumerate(linhas):
        for ci, s in enumerate(tenis):
            try:
                raw = motor.baixar(s["photo"])
                rec = motor.recortar(raw)
                p = os.path.join(wd, f"s{li}_{ci}.png")
                rec.save(p)
                imgs[(li, ci)] = data_uri(p)
                print(f"  ok {marca} {s['name']}")
            except Exception as e:
                print(f"  falhou {marca} {s.get('name')}: {e}", file=sys.stderr)
                imgs[(li, ci)] = ""

    # monta HTML da grade
    rows = ""
    for li, (marca, tenis) in enumerate(linhas):
        cells = ""
        for ci, s in enumerate(tenis):
            nome = s.get("name", "")
            uri = imgs.get((li, ci), "")
            cells += (
                "<div class='cell'>"
                f"<div class='ph'><img src='{uri}'></div>"
                f"<div class='mdl'>{marca}<span>{nome}</span></div>"
                "</div>")
        rows += f"<div class='row'><div class='brand'>{marca}</div><div class='cells'>{cells}</div></div>"

    bebas = "file://" + os.path.abspath("BebasNeue.ttf")
    mont = "file://" + os.path.abspath("Montserrat.ttf")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
@font-face{{font-family:'Bebas';src:url('{bebas}');}}
@font-face{{font-family:'Mont';src:url('{mont}');}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
.c{{width:1080px;height:1350px;font-family:'Mont';overflow:hidden;
background:radial-gradient(75% 45% at 50% 26%,#2c2d37 0%,#17171d 55%,#0a0a0e 100%);
padding:50px 46px 34px;color:#fff;display:flex;flex-direction:column;}}
.top{{flex:none;text-align:center;margin-bottom:6px;}}
.kick{{font-family:'Bebas';font-size:32px;letter-spacing:5px;color:#C8FF00;}}
.t1{{font-family:'Bebas';font-size:86px;line-height:.9;letter-spacing:2px;}}
.t2{{font-family:'Bebas';font-size:86px;line-height:.9;letter-spacing:2px;color:#C8FF00;}}
.sub{{font-size:25px;color:#b8bac4;margin-top:10px;font-weight:600;letter-spacing:.5px;}}
.grid{{flex:1;display:flex;flex-direction:column;justify-content:space-between;padding:6px 0;}}
.row{{flex:1;display:flex;align-items:center;gap:14px;
border-top:1px solid rgba(255,255,255,.09);}}
.brand{{width:148px;flex:none;font-family:'Bebas';font-size:38px;letter-spacing:2px;
line-height:1;color:#fff;text-align:left;}}
.cells{{flex:1;display:flex;gap:10px;height:100%;}}
.cell{{flex:1;display:flex;flex-direction:column;justify-content:center;text-align:center;}}
.ph{{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;}}
.ph img{{max-width:100%;max-height:118px;object-fit:contain;
filter:drop-shadow(0 12px 11px rgba(0,0,0,.55));}}
.mdl{{flex:none;font-family:'Bebas';font-size:21px;letter-spacing:1.5px;color:#8f9199;line-height:1.05;padding-top:4px;}}
.mdl span{{display:block;color:#fff;font-size:22px;letter-spacing:1px;}}
.foot{{flex:none;text-align:center;padding-top:10px;}}
.foot .h{{font-family:'Bebas';font-size:38px;letter-spacing:3px;}}
.foot .h i{{color:#C8FF00;font-style:normal;}}
.foot .s{{font-size:21px;color:#9a9ca7;margin-top:2px;letter-spacing:1px;}}
</style></head><body><div class='c'>
<div class='top'><div class='kick'>TÊNIS IDEAL</div>
<div class='t1'>{TITULO_1}</div><div class='t2'>{TITULO_2}</div>
<div class='sub'>{SUB}</div></div>
<div class='grid'>{rows}</div>
<div class='foot'><div class='h'>@TENISIDEAL<i>_BR</i></div><div class='s'>tenisideal.com.br</div></div>
</div></body></html>"""

    fhtml = os.path.join(wd, "post.html")
    open(fhtml, "w", encoding="utf-8").write(html)
    raw = os.path.join(wd, "raw.png")
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--force-device-scale-factor=2", "--window-size=1080,1350",
                    "--hide-scrollbars", "--virtual-time-budget=4000",
                    "--screenshot=" + raw, "--allow-file-access-from-files",
                    "file://" + fhtml], check=False, capture_output=True, timeout=120)
    if not os.path.exists(raw):
        print("Falha ao renderizar", file=sys.stderr); sys.exit(1)
    out = "post_marcas.png"
    Image.open(raw).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(out)
    print("Gerado:", out)


if __name__ == "__main__":
    # o motor precisa rodar a partir da raiz (acha fontes e catálogo por caminho relativo)
    with tempfile.TemporaryDirectory() as wd:
        # o Chrome lê as fontes por caminho relativo ao html; copiamos o html pra raiz
        # via caminho absoluto do wd, então referenciamos fontes por caminho absoluto.
        build(wd)
