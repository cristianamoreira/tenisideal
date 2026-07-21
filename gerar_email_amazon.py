#!/usr/bin/env python3
"""E-mail 'Achados da Amazon' (campanha de 30 dias p/ destravar a PA-API).

Cria um RASCUNHO de campanha no Brevo — nada é enviado automaticamente.
Você revisa no painel do Brevo e clica em "Enviar".

Diferente da newsletter semanal (gerar_campanha_email.py), aqui TODOS os botões
apontam direto para os links de afiliada da AMAZON, e há um bloco de acessórios
baratos com links de busca já com a sua tag. Objetivo: concentrar cliques/vendas
na Amazon (qualquer compra em até 24h após o clique conta como venda sua).

Variáveis de ambiente (secrets):
- BREVO_API_KEY   : chave da API do Brevo (obrigatória)
- BREVO_LIST_ID   : id da lista de assinantes (padrão 3)
- EMAIL_REMETENTE : remetente verificado (padrão cupons@tenisideal.com.br)
- MAX_PRODUTOS    : quantos tênis destacar (padrão 4)
"""
import os
import sys
import json
import datetime
import ssl
import urllib.parse
import urllib.request
import urllib.error

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
SENDER_EMAIL = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
MAX_PRODUTOS = int(os.environ.get("MAX_PRODUTOS", "4"))
SITE = "https://tenisideal.com.br"

YELLOW = "#c8ff00"
DARK = "#1a1a1a"
AMZ_ORANGE = "#ff9900"


def amazon_tag():
    try:
        return json.load(open("config_afiliados.json", encoding="utf-8"))["amazon"]["tag"]
    except Exception:
        return "tenisideal26-20"


TAG = amazon_tag()


def carregar_shoes():
    with open("frontend/shoes_data.js", "r", encoding="utf-8") as f:
        c = f.read()
    i = c.find("var SHOES = ")
    return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))


def link_amazon(s):
    """URL de afiliada REAL da Amazon (ou None se for placeholder/inexistente)."""
    a = (s.get("affiliate_links") or {}).get("amazon") or {}
    u = (a.get("url") or "")
    low = u.lower()
    if u and ("amzn.to" in low or "amazon." in low):
        return u, (a.get("price") or s.get("price"))
    return None, None


def busca_amazon(termo):
    """Link de busca na Amazon já com a sua tag de afiliada."""
    q = urllib.parse.urlencode({"k": termo, "tag": TAG})
    return f"https://www.amazon.com.br/s?{q}"


def foto_ok(url):
    """True só se a foto responde 200 e é uma imagem — evita imagem quebrada no e-mail.

    Desligue com CHECAR_FOTOS=0 (ex.: rodar offline). Se a checagem falhar por rede,
    assume que está OK pra não bloquear o envio à toa (só o 404 explícito reprova).
    """
    if os.environ.get("CHECAR_FOTOS", "1") == "0":
        return True
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=12)
        tipo = (r.headers.get("Content-Type") or "").lower()
        return r.status == 200 and tipo.startswith("image")
    except urllib.error.HTTPError:
        return False  # 404/403 etc → foto quebrada, pula
    except Exception as e:
        print(f"  [checagem de foto inconclusiva, mantendo] {url[:60]}… ({type(e).__name__})", file=sys.stderr)
        return True


def brl(v):
    try:
        return ("R$ %.2f" % float(v)).replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return "Ver preço"


def selecionar(shoes, n):
    """Tênis com link real da Amazon + foto; rotaciona a seleção a cada dia."""
    bons = []
    for s in shoes:
        url, preco = link_amazon(s)
        if url and s.get("photo", "").startswith("http"):
            bons.append((s, url, preco))
    if not bons:
        return []
    dia = datetime.date.today().timetuple().tm_yday
    inicio = (dia * n) % len(bons)
    girado = bons[inicio:] + bons[:inicio]
    # variedade de marcas primeiro, validando a foto de cada candidato
    seen, out, marcas_pulei = set(), [], []
    for item in girado:
        b = item[0].get("brand")
        if b in seen:
            continue
        if not foto_ok(item[0]["photo"]):
            marcas_pulei.append(f"{item[0]['brand']} {item[0]['name']}")
            continue
        out.append(item); seen.add(b)
        if len(out) == n:
            break
    # completa (aceitando repetir marca) se ainda faltar, sempre checando a foto
    if len(out) < n:
        for item in girado:
            if item in out:
                continue
            if not foto_ok(item[0]["photo"]):
                continue
            out.append(item)
            if len(out) == n:
                break
    if marcas_pulei:
        print(f"[fotos quebradas puladas] {', '.join(marcas_pulei)}", file=sys.stderr)
    return out[:n]


def card_produto(s, url, preco):
    nome = (s.get("brand", "") + " " + s.get("name", "")).strip()
    foto = s.get("photo")
    return f"""
    <tr><td style="padding:10px 0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #eee;border-radius:10px;overflow:hidden;">
        <tr>
          <td width="120" style="padding:12px;background:#f7f7f7;text-align:center;">
            <img src="{foto}" alt="{nome}" width="96" style="max-width:96px;height:auto;display:block;margin:0 auto;">
          </td>
          <td style="padding:12px 16px;vertical-align:middle;">
            <div style="font-size:16px;font-weight:700;color:#1a1a1a;line-height:1.2;">{nome}</div>
            <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin:6px 0;">{brl(preco)}</div>
            <a href="{url}" style="display:inline-block;background:{AMZ_ORANGE};color:#1a1a1a;text-decoration:none;font-size:13px;font-weight:800;padding:9px 16px;border-radius:6px;">Ver na Amazon →</a>
          </td>
        </tr>
      </table>
    </td></tr>"""


# Acessórios baratos de impulso — cada link já leva com a sua tag de afiliada.
ACESSORIOS = [
    ("🧦 Meias de compressão", "meia de compressao corrida"),
    ("👣 Palmilhas de amortecimento", "palmilha amortecimento corrida"),
    ("💧 Garrafa / cinto de hidratação", "cinto hidratacao corrida"),
    ("⌚ Faixa de braço p/ celular", "braçadeira celular corrida"),
]


def secao_acessorios():
    linhas = ""
    for titulo, termo in ACESSORIOS:
        url = busca_amazon(termo)
        linhas += f"""
        <tr><td style="padding:9px 0;border-bottom:1px solid #f0f0f0;">
          <a href="{url}" style="font-size:15px;font-weight:700;color:#1a1a1a;text-decoration:none;">{titulo}
            <span style="color:{AMZ_ORANGE};">→</span></a>
        </td></tr>"""
    return f"""
    <tr><td style="padding:18px 28px 4px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border:1px solid #eee;border-radius:10px;">
        <tr><td style="padding:18px 20px;">
          <div style="display:inline-block;background:{YELLOW};color:#1a1a1a;font-size:11px;font-weight:800;
               text-transform:uppercase;letter-spacing:.5px;padding:3px 10px;border-radius:12px;">Extras baratinhos</div>
          <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin:10px 0 4px;">Complete o kit do corredor 🏃</div>
          <div style="font-size:14px;color:#555;line-height:1.5;margin-bottom:8px;">
            Itens que fazem diferença no treino — e cabem no bolso:
          </div>
          <table width="100%" cellpadding="0" cellspacing="0">{linhas}</table>
        </td></tr>
      </table>
    </td></tr>"""


def montar_html(itens):
    cards = "".join(card_produto(s, u, p) for s, u, p in itens)
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
      <div style="font-size:22px;font-weight:800;color:#1a1a1a;">🛒 Achados da Amazon</div>
      <div style="font-size:15px;color:#555;line-height:1.6;margin-top:8px;">
        Separamos uma seleção rápida de tênis de corrida com bom custo-benefício na Amazon —
        e uns acessórios baratinhos que fazem diferença no treino. Quem é Prime ainda tem
        frete grátis. 😉
      </div>
    </td></tr>
    <!-- produtos -->
    <tr><td style="padding:8px 28px;">
      <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">👟 Tênis em destaque</div>
      <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
    </td></tr>
    <!-- acessórios -->
    {secao_acessorios()}
    <!-- CTA quiz -->
    <tr><td style="padding:28px;text-align:center;">
      <div style="font-size:16px;color:#555;margin-bottom:14px;">Não sabe qual combina com a sua pisada? Faça o teste em 60 segundos:</div>
      <a href="{SITE}" style="display:inline-block;background:{YELLOW};color:#1a1a1a;text-decoration:none;font-size:17px;font-weight:800;padding:15px 34px;border-radius:8px;">DESCOBRIR MEU TÊNIS IDEAL →</a>
    </td></tr>
    <!-- footer -->
    <tr><td style="background:#fafafa;padding:20px 28px;border-top:1px solid #eee;text-align:center;">
      <div style="font-size:12px;color:#999;line-height:1.6;">
        Você recebe este e-mail porque se cadastrou no quiz do Tênis Ideal.<br>
        <a href="{SITE}" style="color:#999;">tenisideal.com.br</a> · Os links são de afiliado da Amazon.
      </div>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def criar_rascunho_brevo(html):
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    body = {
        "name": f"Achados da Amazon — {hoje}",
        "subject": "👟 Achados da Amazon: os tênis (e acessórios) que separamos pra você",
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
    shoes = carregar_shoes()
    itens = selecionar(shoes, MAX_PRODUTOS)
    if not itens:
        print("ERRO: nenhum tênis com link real da Amazon encontrado.", file=sys.stderr)
        sys.exit(1)
    html = montar_html(itens)

    with open("email_amazon.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 HTML salvo em email_amazon.html ({len(itens)} tênis + {len(ACESSORIOS)} acessórios).")

    if not BREVO_API_KEY:
        print("[sem BREVO_API_KEY — rascunho no Brevo pulado; abra o HTML pra pré-visualizar]", file=sys.stderr)
        return
    try:
        r = criar_rascunho_brevo(html)
        print(f"✅ Rascunho criado no Brevo (id {r.get('id')}).")
        print("   Vá em Brevo → Campanhas → revise e clique em Enviar.")
    except urllib.error.HTTPError as e:
        print(f"ERRO HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
