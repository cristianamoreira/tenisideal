#!/usr/bin/env python3
"""Gera TODOS os carrosséis do rodízio e manda por e-mail num pacote só.

Diferente do gerar_carrossel_instagram.py (que manda 1 tema por dia), este junta
os 3 temas (pronada, ate300, versus) — todos no mesmo estilo brutalism verde-lima,
pra o feed ficar harmônico — e envia num único e-mail, com os slides agrupados por
tema e a legenda pronta de cada um.

Feito pra ser disparado à mão pelo workflow "Enviar conteúdo (manual)" no GitHub
(botão "Run workflow"). Precisa dos secrets BREVO_API_KEY / EMAIL_CUPONS.

Teste local (sem enviar): python3 enviar_carrosseis_todos.py
Enviar de verdade:        CUPOM_ENVIAR=1 BREVO_API_KEY=... EMAIL_CUPONS=... python3 enviar_carrosseis_todos.py
"""
import os
import base64
import json
import tempfile
import datetime
import urllib.request

import gerar_carrossel_instagram as cr


def gerar_tema(tema, wd):
    """Renderiza os slides de um tema e devolve (lista_de_pngs, legenda, assunto)."""
    cfg = cr.TEMAS[tema]
    catalogo = cr.carregar_catalogo()
    pngs = []
    for i, s in enumerate(cfg["slides"], 1):
        s = dict(s)
        if s.get("slug"):
            p = cr.fmt(cr.preco_min(catalogo.get(s["slug"])))
            s["titulo"] = s["titulo"].replace("{preco}", p)
            s["corpo"] = s["corpo"].replace("{preco}", p or "consultar")
        out = os.path.join(os.getcwd(), f"carrossel_{tema}_{i:02d}.png")
        if cr.render(wd, cr.slide_html(s), out):
            pngs.append(out)
    return pngs, cfg["legenda"], cfg["assunto"]


def enviar_pacote(temas):
    """temas: lista de (pngs, legenda, assunto). Manda 1 e-mail com tudo."""
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    anexos, blocos = [], []
    for pngs, legenda, assunto in temas:
        for p in pngs:
            with open(p, "rb") as f:
                anexos.append({"content": base64.b64encode(f.read()).decode(),
                               "name": os.path.basename(p)})
        leg_html = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        blocos.append(
            f"<h3 style='font-family:sans-serif;margin:26px 0 6px'>🎠 {assunto} "
            f"<span style='font-weight:400;color:#888'>({len(pngs)} slides)</span></h3>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px'>{leg_html}</pre>")

    if not key or not email:
        print(f"Sem BREVO_API_KEY/EMAIL_CUPONS — {len(anexos)} slides gerados, e-mail pulado.")
        return
    html = ("<p style='font-family:sans-serif'>Oi! 👋 Aqui está o <b>pacote de carrosséis</b> pro "
            "<b>@tenisideal_br</b> — os 3 temas no mesmo estilo (verde-lima), pra o feed ficar harmônico. "
            "Os anexos estão nomeados <code>carrossel_&lt;tema&gt;_01..05</code>; poste cada tema na ordem.</p>"
            + "".join(blocos))
    body = {"sender": {"email": remet, "name": "Conteúdo - Tênis Ideal"},
            "to": [{"email": email}],
            "subject": f"🎠 Pacote de carrosséis harmônicos — {datetime.date.today().strftime('%d/%m')}",
            "htmlContent": html, "attachment": anexos}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"✅ E-mail enviado para {email} com {len(anexos)} slides (HTTP {r.status})")


def main():
    wd = tempfile.mkdtemp(prefix="carrosseis_todos_")
    temas = []
    for tema in cr.RODIZIO:
        print(f"🎠 Gerando {tema}...")
        temas.append(gerar_tema(tema, wd))
    total = sum(len(t[0]) for t in temas)
    print(f"Total de slides gerados: {total}")
    enviar_pacote(temas)


if __name__ == "__main__":
    main()
