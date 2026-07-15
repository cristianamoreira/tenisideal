#!/usr/bin/env python3
"""Gera um carrossel de um TEMA num ESTILO à escolha (engine carrossel_estilos).

Diferente do gerar_carrossel_instagram.py (que só faz o estilo brutalism verde-lima),
este deixa você ESCOLHER o estilo na hora, entre os 10 do catálogo:
  glassmorphism-ibeia, ticket-zerotoui, editorial-magazine, swiss-grid, brutalism,
  claymorphism, neo-newspaper, sticker-cutout, terminal-mono, flat-editorial-colorido

Reusa os roteiros dos temas (pronada / ate300 / versus) do gerar_carrossel_instagram,
injeta os preços ao vivo, renderiza com a engine Node/Playwright (carrossel_estilos/)
e manda os slides por e-mail via Brevo (mesma função dos outros robôs).

Uso:
    ESTILO_CARROSSEL=swiss-grid TEMA_CARROSSEL=pronada python3 gerar_carrossel_estilo.py

Sem BREVO_API_KEY/EMAIL_CUPONS só gera os PNGs (não envia).
"""
import os
import sys
import json
import glob
import tempfile
import subprocess

import gerar_carrossel_instagram as cr

AQUI = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(AQUI, "carrossel_estilos")

ESTILOS = ["glassmorphism-ibeia", "ticket-zerotoui", "editorial-magazine", "swiss-grid",
           "brutalism", "claymorphism", "neo-newspaper", "sticker-cutout",
           "terminal-mono", "flat-editorial-colorido"]

ESTILO = (os.environ.get("ESTILO_CARROSSEL") or "brutalism").strip()
TEMA = (os.environ.get("TEMA_CARROSSEL") or "pronada").strip().lower()


def montar_slides(tema):
    """Converte o roteiro do tema (kind/kicker/titulo/corpo/slug) pro formato da engine."""
    cfg = cr.TEMAS[tema]
    catalogo = cr.carregar_catalogo()
    slides = []
    for s in cfg["slides"]:
        preco = cr.fmt(cr.preco_min(catalogo.get(s["slug"]))) if s.get("slug") else ""
        slide = {
            "type": s["kind"],
            "kicker": s.get("kicker", ""),
            "titulo": s["titulo"].replace("{preco}", preco),
            "corpo": s.get("corpo", "").replace("{preco}", preco or "consultar"),
        }
        if s["kind"] == "cta":
            slide["cta"] = "tenisideal.com.br"
            slide["plug"] = "Link na bio"
        slides.append(slide)
    return slides


def main():
    if ESTILO not in ESTILOS:
        sys.exit(f"ERRO: estilo '{ESTILO}' invalido.\nDisponiveis: {', '.join(ESTILOS)}")
    tema = TEMA if TEMA in cr.TEMAS else "pronada"
    cfg = cr.TEMAS[tema]
    print(f"🎨 Estilo: {ESTILO} | 🎠 Tema: {tema} -> {cfg['assunto']}")

    jobdir = tempfile.mkdtemp(prefix=f"estilo_{ESTILO}_")
    job = {"estilo": ESTILO, "outDir": "saida", "slides": montar_slides(tema)}
    jobpath = os.path.join(jobdir, "job.json")
    with open(jobpath, "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)

    # resolve o playwright: usa o node_modules da engine (workflow, após npm i);
    # se não existir (rodando local sem instalar), cai no node_modules da skill.
    env = dict(os.environ)
    if not os.path.isdir(os.path.join(ENGINE, "node_modules")):
        skill_nm = os.path.expanduser("~/.claude/skills/carrossel-estilos/node_modules")
        if os.path.isdir(skill_nm):
            env["NODE_PATH"] = skill_nm

    r = subprocess.run(["node", os.path.join(ENGINE, "render.js"), jobpath],
                       env=env, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        sys.exit(f"ERRO: engine falhou (código {r.returncode}).")

    pngs = sorted(glob.glob(os.path.join(jobdir, "saida", "slide-*.png")))
    if not pngs:
        sys.exit("ERRO: nenhum slide gerado.")
    print(f"✅ {len(pngs)} slides em {os.path.join(jobdir, 'saida')}")

    # copia pra raiz (backup/artefato do workflow) e envia
    finais = []
    for i, p in enumerate(pngs, 1):
        dest = os.path.join(AQUI, f"carrossel_{i:02d}.png")
        with open(p, "rb") as src, open(dest, "wb") as out:
            out.write(src.read())
        finais.append(dest)
    cr.enviar_email(finais, cfg["legenda"], f"{cfg['assunto']} · estilo {ESTILO}")


if __name__ == "__main__":
    main()
