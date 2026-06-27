#!/usr/bin/env python3
"""Gera um e-mail (novidades + ofertas) e cria um RASCUNHO de campanha no Brevo.

Você só precisa revisar e clicar em "Enviar" no painel do Brevo.
Nada é enviado automaticamente — sempre vira rascunho.

Variáveis de ambiente (secrets):
- BREVO_API_KEY   : chave da API do Brevo (obrigatória)
- BREVO_LIST_ID   : id da lista de assinantes (padrão 3)
- EMAIL_REMETENTE : remetente verificado (padrão cupons@tenisideal.com.br)
- AWIN_API_TOKEN  : opcional — se presente, inclui cupons da Awin no e-mail
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
SENDER_EMAIL = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
SITE = "https://tenisideal.com.br"

YELLOW = "#c8ff00"
DARK = "#1a1a1a"


def carregar_shoes():
    with open("frontend/shoes_data.js", "r", encoding="utf-8") as f:
        c = f.read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def link_compra(s):
    al = s.get("affiliate_links", {}) or {}
    for k in ("oficial", "amazon", "netshoes"):
        if al.get(k) and al[k].get("url"):
            return al[k]["url"]
    return SITE


def brl(v):
    try:
        return ("R$ %.2f" % float(v)).replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return "Ver preço"


def destaques(shoes, n=3):
    bons = [s for s in shoes
            if s.get("photo") and s["photo"].startswith("http")
            and s.get("price", 0) and float(s["price"]) > 0
            and s.get("affiliate_links")]
    if not bons:
        return shoes[:n]
    semana = datetime.date.today().isocalendar()[1]  # rotaciona a cada semana
    inicio = (semana * 3) % len(bons)
    girado = bons[inicio:] + bons[:inicio]
    return girado[:n]


def buscar_cupons():
    if not os.environ.get("AWIN_API_TOKEN"):
        return []
    try:
        from gerar_cupons_awin import buscar_promocoes
        dados = buscar_promocoes()
        promos = dados.get("data") if isinstance(dados, dict) else dados
        return (promos or [])[:4]
    except Exception as e:
        print(f"[cupons indisponíveis] {e}", file=sys.stderr)
        return []


def card_produto(s):
    nome = (s.get("brand", "") + " " + s.get("name", "")).strip()
    preco = brl(s.get("price"))
    foto = s.get("photo")
    url = link_compra(s)
    return f"""
    <tr><td style="padding:10px 0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eee;border-radius:10px;overflow:hidden;">
        <tr>
          <td width="120" style="padding:12px;background:#f7f7f7;text-align:center;">
            <img src="{foto}" alt="{nome}" width="96" style="max-width:96px;height:auto;display:block;margin:0 auto;">
          </td>
          <td style="padding:12px 16px;vertical-align:middle;">
            <div style="font-size:16px;font-weight:700;color:#1a1a1a;line-height:1.2;">{nome}</div>
            <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin:6px 0;">{preco}</div>
            <a href="{url}" style="display:inline-block;background:{DARK};color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:9px 16px;border-radius:6px;">Ver na loja →</a>
          </td>
        </tr>
      </table>
    </td></tr>"""


def secao_cupons(cupons):
    if not cupons:
        return ""
    linhas = ""
    for p in cupons:
        adv = (p.get("advertiser") or {}).get("name") or p.get("advertiserName") or "Loja"
        voucher = (p.get("voucher") or {})
        code = voucher.get("code") or p.get("code")
        title = (p.get("title") or p.get("description") or "").strip()
        if len(title) > 70:
            title = title[:70].rsplit(" ", 1)[0] + "…"
        url = p.get("urlTracking") or p.get("url") or SITE
        code_html = f'<span style="background:{YELLOW};color:#1a1a1a;font-weight:800;padding:2px 8px;border-radius:5px;">{code}</span>' if code else ""
        linhas += f"""
        <tr><td style="padding:8px 0;border-bottom:1px solid #f0f0f0;">
          <div style="font-size:14px;font-weight:700;color:#1a1a1a;">{adv} {code_html}</div>
          <div style="font-size:13px;color:#666;margin-top:2px;">{title}</div>
          <a href="{url}" style="font-size:13px;color:#1a7f00;font-weight:700;text-decoration:none;">Aproveitar →</a>
        </td></tr>"""
    return f"""
    <tr><td style="padding:24px 0 8px;">
      <div style="font-size:18px;font-weight:800;color:#1a1a1a;">🎟️ Cupons ativos</div>
    </td></tr>
    <tr><td><table width="100%" cellpadding="0" cellspacing="0">{linhas}</table></td></tr>"""


def montar_html(shoes_sel, cupons):
    hoje = datetime.date.today().strftime("%d/%m")
    cards = "".join(card_produto(s) for s in shoes_sel)
    cupons_html = secao_cupons(cupons)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f3f3f3;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f3f3;padding:24px 0;">
<tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:14px;overflow:hidden;">
    <!-- header -->
    <tr><td style="background:{DARK};padding:22px 28px;">
      <span style="font-size:24px;font-weight:800;letter-spacing:2px;color:#fff;">TÊNIS<span style="color:{YELLOW};">IDEAL</span></span>
    </td></tr>
    <!-- hero -->
    <tr><td style="padding:28px 28px 8px;">
      <div style="font-size:22px;font-weight:800;color:#1a1a1a;">👟 Novidades da semana — {hoje}</div>
      <div style="font-size:15px;color:#555;line-height:1.6;margin-top:8px;">
        Separamos alguns destaques pra você e as melhores ofertas do momento. Bora correr? 🏃
      </div>
    </td></tr>
    <!-- produtos -->
    <tr><td style="padding:8px 28px;">
      <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">⭐ Destaques</div>
      <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
    </td></tr>
    <!-- cupons -->
    <tr><td style="padding:0 28px;"><table width="100%" cellpadding="0" cellspacing="0">{cupons_html}</table></td></tr>
    <!-- CTA quiz -->
    <tr><td style="padding:28px;text-align:center;">
      <div style="font-size:16px;color:#555;margin-bottom:14px;">Ainda não sabe qual é o seu? Faça o teste em 60 segundos:</div>
      <a href="{SITE}" style="display:inline-block;background:{YELLOW};color:#1a1a1a;text-decoration:none;font-size:17px;font-weight:800;padding:15px 34px;border-radius:8px;">DESCOBRIR MEU TÊNIS IDEAL →</a>
    </td></tr>
    <!-- footer -->
    <tr><td style="background:#fafafa;padding:20px 28px;border-top:1px solid #eee;text-align:center;">
      <div style="font-size:12px;color:#999;line-height:1.6;">
        Você recebe este e-mail porque se cadastrou no quiz do Tênis Ideal.<br>
        <a href="{SITE}" style="color:#999;">tenisideal.com.br</a> · Os links podem ser de afiliado.
      </div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def criar_rascunho_brevo(html):
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    body = {
        "name": f"Novidades Tênis Ideal — {hoje}",
        "subject": "👟 Novidades e ofertas da semana — Tênis Ideal",
        "sender": {"name": "Tênis Ideal", "email": SENDER_EMAIL},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [LIST_ID]},
        # SEM scheduledAt → fica como RASCUNHO (você envia manualmente)
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/emailCampaigns",
        data=json.dumps(body).encode("utf-8"),
        headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if not BREVO_API_KEY:
        print("ERRO: BREVO_API_KEY não definida.", file=sys.stderr)
        sys.exit(1)

    shoes = carregar_shoes()
    sel = destaques(shoes, 3)
    cupons = buscar_cupons()
    html = montar_html(sel, cupons)

    with open("email_campanha.html", "w", encoding="utf-8") as f:
        f.write(html)

    try:
        r = criar_rascunho_brevo(html)
        cid = r.get("id")
        print(f"✅ Rascunho de campanha criado no Brevo (id {cid}).")
        print(f"   {len(sel)} produtos em destaque, {len(cupons)} cupons.")
        print("   Vá em Brevo → Campanhas → revise e clique em Enviar.")
    except urllib.error.HTTPError as e:
        print(f"ERRO HTTP {e.code}: {e.read().decode('utf-8','ignore')[:300]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
