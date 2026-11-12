#!/usr/bin/env python3
"""Gerador LOCAL de carrossel de TEXTO para o banco (banco_posts/).

Uso: python3 _banco_gerar_texto.py <spec.json>

Spec: {id, estilo, assunto, tema, slides: [{type: capa|conteudo|cta, ...}], legenda}
Renderiza com carrossel_estilos/render.js (formato carrossel 1080x1350) e grava
banco_posts/<id>/slide-NN.png + post.json. Copy saneada pelo revisor (regras duras).
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess

import revisor_copy

RAIZ = os.path.dirname(os.path.abspath(__file__))
RENDER_JS = os.path.join(RAIZ, "carrossel_estilos", "render.js")


def sanear_slide(s):
    out = dict(s)
    for campo, tipo in (("titulo", "titulo"), ("corpo", "corpo"), ("cta", "corpo")):
        if out.get(campo):
            out[campo] = revisor_copy.sanear_campo(out[campo], tipo)
    return out


def main(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    wd = tempfile.mkdtemp(prefix="banco_texto_")
    slides = [sanear_slide(s) for s in spec["slides"]]
    legenda = revisor_copy.sanear_campo(spec["legenda"], "legenda")

    roteiro = dict(estilo=spec["estilo"], formato="carrossel", outDir="out", slides=slides)
    open(os.path.join(wd, "roteiro.json"), "w", encoding="utf-8").write(
        json.dumps(roteiro, ensure_ascii=False))
    r = subprocess.run(["node", RENDER_JS, os.path.join(wd, "roteiro.json")],
                       capture_output=True, text=True)
    print(r.stdout[-200:])
    if r.returncode != 0:
        raise SystemExit("render.js erro: " + r.stderr[-500:])

    outdir = os.path.join(wd, "out")
    pngs = sorted(f for f in os.listdir(outdir) if f.endswith(".png"))
    destino = os.path.join(RAIZ, "banco_posts", spec["id"])
    os.makedirs(destino, exist_ok=True)
    for i, f in enumerate(pngs, 1):
        shutil.copyfile(os.path.join(outdir, f), os.path.join(destino, f"slide-{i:02d}.png"))
    meta = dict(assunto=spec["assunto"], legenda=legenda,
                tema=spec.get("tema", ""), estilo=spec["estilo"])
    open(os.path.join(destino, "post.json"), "w", encoding="utf-8").write(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ {len(pngs)} slides em {destino}")


if __name__ == "__main__":
    main(sys.argv[1])
