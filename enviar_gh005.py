#!/usr/bin/env python3
"""Envia o carrossel avulso GH-005 (6 slides + legenda) por e-mail via Brevo.

Os slides ja vem prontos e versionados em conteudo_gh005/ (slide-01..06.png) junto
com legenda-gh005.txt. Nao renderiza nada: so anexa e manda. Mesmos secrets dos
outros robos (BREVO_API_KEY / EMAIL_CUPONS / EMAIL_REMETENTE).

Disparo: workflow "Enviar GH-005 (manual)" na aba Actions.
Teste local (sem enviar): python3 enviar_gh005.py
Enviar de verdade: BREVO_API_KEY=... EMAIL_CUPONS=... python3 enviar_gh005.py
"""
import os, base64, json, datetime, urllib.request

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conteudo_gh005")
LEGENDA = os.path.join(PASTA, "legenda-gh005.txt")


def main():
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"

    slides = sorted(f for f in os.listdir(PASTA) if f.lower().endswith(".png"))
    anexos = []
    for f in slides:
        with open(os.path.join(PASTA, f), "rb") as fh:
            anexos.append({"content": base64.b64encode(fh.read()).decode(), "name": f})

    legenda = open(LEGENDA, encoding="utf-8").read() if os.path.exists(LEGENDA) else ""
    leg_html = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    if not key or not email:
        print(f"Sem BREVO_API_KEY/EMAIL_CUPONS — {len(anexos)} slides prontos, e-mail pulado.")
        return

    html = ("<p style='font-family:sans-serif'>Oi! 👋 Aqui está o carrossel <b>GH-005</b> pro "
            "<b>@tenisideal_br</b> (photo mode no TikTok / carrossel no Instagram). "
            f"São <b>{len(anexos)} slides</b> em anexo, na ordem <code>slide-01..06</code>. "
            "Poste na ordem e cole a legenda abaixo. No TikTok, escolha um <b>som em alta</b>.</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px'>{leg_html}</pre>")
    body = {"sender": {"email": remet, "name": "Conteúdo - Tênis Ideal"},
            "to": [{"email": email}],
            "subject": f"👟 Carrossel GH-005 pro TikTok/Insta — {datetime.date.today().strftime('%d/%m')}",
            "htmlContent": html, "attachment": anexos}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"✅ E-mail enviado para {email} com {len(anexos)} slides (HTTP {r.status})")


if __name__ == "__main__":
    main()
