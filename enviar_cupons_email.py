#!/usr/bin/env python3
"""Envia a mensagem de cupons (cupons_hoje.txt) por e-mail via Brevo.

Variáveis de ambiente (secrets do GitHub):
- BREVO_API_KEY : sua chave de API do Brevo
- EMAIL_CUPONS  : seu e-mail (recebe a mensagem; também usado como remetente)
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

API_KEY = os.environ.get("BREVO_API_KEY", "")
EMAIL = os.environ.get("EMAIL_CUPONS", "")                       # destinatário (você recebe aqui)
# remetente: precisa ser do seu domínio autenticado no Brevo (senão o Gmail bloqueia)
REMETENTE = os.environ.get("EMAIL_REMETENTE", "") or "cupons@tenisideal.com.br"


def main():
    if not API_KEY or not EMAIL:
        print("ERRO: defina os secrets BREVO_API_KEY e EMAIL_CUPONS.", file=sys.stderr)
        sys.exit(1)

    try:
        with open("cupons_hoje.txt", "r", encoding="utf-8") as f:
            mensagem = f.read().strip()
    except FileNotFoundError:
        print("ERRO: cupons_hoje.txt não encontrado (o script de cupons rodou?).", file=sys.stderr)
        sys.exit(1)

    if not mensagem:
        print("Mensagem vazia — nada a enviar.", file=sys.stderr)
        return

    hoje = datetime.datetime.now().strftime("%d/%m")
    # HTML simples: um aviso no topo + a mensagem dentro de um bloco fácil de copiar
    html = (
        "<p style='font-family:sans-serif;color:#444'>"
        "👇 <b>Copie o texto abaixo e cole no seu Canal do WhatsApp:</b></p>"
        "<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
        "border:1px solid #ddd;border-radius:8px;padding:16px;font-size:15px'>"
        + (mensagem.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        + "</pre>"
    )

    body = {
        "sender": {"email": REMETENTE, "name": "Cupons Tênis Ideal"},
        "to": [{"email": EMAIL}],
        "subject": f"🔥 Cupons e ofertas do dia {hoje} — cole no WhatsApp",
        "htmlContent": html,
        "textContent": mensagem,
    }

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(body).encode("utf-8"),
        headers={"api-key": API_KEY, "Content-Type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"✅ E-mail enviado para {EMAIL} (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        print(f"ERRO HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
