#!/usr/bin/env python3
"""Gerador LOCAL de carrossel FOTO para o banco de pré-aprovados (banco_posts/).

Uso: python3 _banco_gerar_foto.py <spec.json>

O spec traz id, copy (escrita/aprovada na sessão com a Claude) e a lista de
tênis (brand+name exatos do catálogo). Reaproveita o motor do repo:
seleção/recorte (gerar_video_tiktok + gerar_carrossel_foto) e o engine
carrossel_estilos/render.js (estilo brutalism, arquétipos fotocapa/foto/cta).

Não envia e-mail e não mexe na fila — só gera banco_posts/<id>/ com
slide-NN.png + post.json. A fila é atualizada na aprovação, pelo fluxo da sessão.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess

import gerar_video_tiktok as vid
import gerar_carrossel_foto as gcf
import revisor_copy

RAIZ = os.path.dirname(os.path.abspath(__file__))


def achar_tenis(catalogo, brand, name):
    for s in catalogo:
        if s.get("brand", "").lower() == brand.lower() and s.get("name", "").lower() == name.lower():
            return s
    raise SystemExit(f"ERRO: tênis não encontrado no catálogo: {brand} {name}")


def main(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    catalogo = vid.carregar_catalogo()
    tenis = [achar_tenis(catalogo, t["brand"], t["name"]) for t in spec["tenis"]]

    wd = tempfile.mkdtemp(prefix="banco_foto_")
    print(f"[wd] {wd}")

    # fotos recortadas
    imgs = []
    for i, s in enumerate(tenis, 1):
        p = gcf.preparar_tenis(s, wd, i)
        if not p:
            raise SystemExit(f"ERRO: falha ao preparar foto de {s['brand']} {s['name']}")
        imgs.append(p)
        print(f"  foto {i}: {s['brand']} {s['name']} ok")

    # capa (fallback commitado — sem IA local)
    capa = os.path.join(wd, "capa.png")
    from PIL import Image
    Image.open(gcf.CAPA_FALLBACK).convert("RGB").save(capa)

    # saneamento de toda a copy (sem IA local; regras duras do revisor)
    cap_tit = revisor_copy.sanear_campo(spec["capa_titulo"], "titulo")
    cap_cor = revisor_copy.sanear_campo(spec["capa_corpo"], "corpo")
    legenda = revisor_copy.sanear_campo(spec["legenda"], "legenda")

    slides = [dict(type="fotocapa", titulo=cap_tit, corpo=cap_cor, img="capa.png")]
    for i, (s, t) in enumerate(zip(tenis, spec["tenis"]), 1):
        slides.append(dict(type="foto", kicker=f"{i:02d}",
                           titulo=f"{s['brand']} {s['name']}",
                           corpo=revisor_copy.sanear_campo(t["blurb"], "corpo"),
                           img=os.path.basename(imgs[i - 1])))
    slides.append(dict(gcf.CTA))

    roteiro = dict(estilo="brutalism", formato="carrossel", outDir="out", slides=slides)
    open(os.path.join(wd, "roteiro.json"), "w", encoding="utf-8").write(
        json.dumps(roteiro, ensure_ascii=False))
    r = subprocess.run(["node", gcf.RENDER_JS, os.path.join(wd, "roteiro.json")],
                       capture_output=True, text=True)
    print(r.stdout[-300:])
    if r.returncode != 0:
        raise SystemExit("render.js erro: " + r.stderr[-500:])

    outdir = os.path.join(wd, "out")
    pngs = sorted(f for f in os.listdir(outdir) if f.endswith(".png"))

    destino = os.path.join(RAIZ, "banco_posts", spec["id"])
    os.makedirs(destino, exist_ok=True)
    for i, f in enumerate(pngs, 1):
        shutil.copyfile(os.path.join(outdir, f), os.path.join(destino, f"slide-{i:02d}.png"))
    meta = dict(assunto=spec["assunto"], legenda=legenda,
                tema=spec.get("tema", ""), estilo="brutalism-foto")
    open(os.path.join(destino, "post.json"), "w", encoding="utf-8").write(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ {len(pngs)} slides em {destino}")


if __name__ == "__main__":
    main(sys.argv[1])
