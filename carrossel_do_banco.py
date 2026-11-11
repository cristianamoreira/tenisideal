#!/usr/bin/env python3
"""Consome o próximo carrossel APROVADO do banco (banco_posts/) e envia por
e-mail (Brevo), marcando-o como publicado na fila — nunca repete.

Códigos de saída (o workflow conteudo-do-dia.yml depende deles):
  0 = ok (enviado, ou sem chave Brevo — nesse caso NÃO marca e avisa)
  3 = banco vazio -> o workflow cai pra geração na hora
  1 = erro real (post corrompido, slide faltando...)

Alerta de estoque: quando restarem <= 2 aprovados após o consumo, o e-mail sai
com o aviso "BANCO ACABANDO" para reabastecer com a Claude.

Teste local: python3 carrossel_do_banco.py  (sem BREVO_API_KEY só simula)
"""
import os
import sys
import json
import base64
import datetime
import urllib.request

import banco_posts as bp

ALERTA_MINIMO = 2  # <= 2 aprovados restantes -> alerta no e-mail


def montar_email(slides, legenda, assunto, restantes, anexar=True, hoje=None):
    """Monta o body Brevo. anexar=False só nos testes (não lê os PNGs).
    hoje: string ISO (YYYY-MM-DD) ou None para usar a data atual."""
    hoje = hoje or datetime.date.today().isoformat()
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    email = os.environ.get("EMAIL_CUPONS", "")
    anexos = []
    if anexar:
        for p in slides:
            with open(p, "rb") as f:
                anexos.append({"content": base64.b64encode(f.read()).decode(),
                               "name": os.path.basename(p)})
    leg = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    alerta = ""
    if restantes <= ALERTA_MINIMO:
        alerta = (f"<p style='font-family:sans-serif;background:#fff3cd;border:1px solid #ffc107;"
                  f"border-radius:8px;padding:12px'><b>⚠️ BANCO ACABANDO:</b> só restam "
                  f"<b>{restantes}</b> carrosséis aprovados. Abra o Claude e peça pra "
                  f"reabastecer o banco de posts.</p>")
    data_fmt = datetime.date.fromisoformat(hoje).strftime('%d/%m')
    html = (f"{alerta}<p style='font-family:sans-serif'>Oi! 👋 Carrossel <b>do banco</b> "
            f"(pré-aprovado) pro <b>@tenisideal_br</b> — <b>{assunto}</b>. "
            f"{len(slides)} slides em anexo (ordem slide-01..0N). Poste na ordem e cole a legenda:</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px'>{leg}</pre>")
    return {"sender": {"email": remet, "name": "Conteúdo - Tênis Ideal"},
            "to": [{"email": email}],
            "subject": f"👟 Carrossel do banco — {assunto} — {data_fmt}",
            "htmlContent": html, "attachment": anexos}


def enviar_brevo(body):
    """Envia via Brevo. Retorna True se enviou, False se não há chave/destino."""
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — e-mail pulado (fila NÃO marcada).")
        return False
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        print(f"✅ E-mail enviado (HTTP {r.status})")
    return True


def consumir(banco_dir=bp.BANCO_DIR, fila_path=bp.FILA_PADRAO, hoje=None):
    hoje = hoje or datetime.date.today().isoformat()
    fila = bp.carregar_fila(fila_path)
    item = bp.proximo_aprovado(fila)
    if not item:
        print("Banco vazio: nenhum carrossel aprovado na fila (exit 3 -> gerar na hora).")
        return 3
    try:
        slides, legenda, assunto = bp.carregar_post(item["id"], banco_dir=banco_dir)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"ERRO: post '{item['id']}' corrompido: {e}", file=sys.stderr)
        return 1
    restantes = bp.contar_aprovados(fila) - 1  # depois deste
    print(f"🎠 Carrossel do banco: {item['id']} — {assunto} ({len(slides)} slides, restarão {restantes})")
    body = montar_email(slides, legenda, assunto, restantes, hoje=hoje)
    if enviar_brevo(body):
        bp.marcar_publicado(fila, item["id"], hoje)
        bp.salvar_fila(fila, fila_path)
        print(f"📦 Fila atualizada: {item['id']} -> publicado em {hoje}")
    return 0


if __name__ == "__main__":
    sys.exit(consumir())
