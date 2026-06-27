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


# Conteúdo editorial (dicas/reviews) — gira a cada semana, pra não ser só cupom
CONTEUDO = [
    {"titulo": "Você sabe qual é a sua pisada? 👣",
     "texto": "Pisada neutra, pronada ou supinada muda totalmente o tênis ideal pra você — "
              "e correr com o errado aumenta o risco de lesão. Na dúvida, o teste do nosso site "
              "identifica em segundos."},
    {"titulo": "Quando trocar seu tênis de corrida? ⏱️",
     "texto": "A regra geral é a cada <b>600 a 800 km</b>. Depois disso, o amortecimento perde a "
              "eficiência mesmo que o tênis pareça novo por fora. Anote a quilometragem do seu par!"},
    {"titulo": "Placa de carbono vale a pena? 🏅",
     "texto": "Tênis com placa de carbono (como Adizero Adios Pro e Vaporfly) devolvem energia e "
              "aceleram seu ritmo — mas são feitos pra prova, com durabilidade menor. Pra treino "
              "diário, um daily trainer rende muito mais."},
    {"titulo": "Daily trainer x tênis de prova 🥇",
     "texto": "O daily trainer (Pegasus, Ghost, Gel-Cumulus) aguenta o dia a dia com conforto e "
              "durabilidade. O de prova é leve e rápido, pra momentos especiais. O ideal é ter um "
              "de cada pra cada propósito."},
    {"titulo": "O que é o 'drop' do tênis? 📐",
     "texto": "Drop é a diferença de altura entre o calcanhar e a ponta. Drop alto (10–12mm) "
              "favorece quem pisa de calcanhar; drop baixo (0–6mm) puxa a passada pro meio do pé. "
              "Não existe certo ou errado — existe o que combina com você."},
    {"titulo": "Amortecimento máximo x responsivo 🛋️",
     "texto": "Max cushion (Hoka Bondi, Gel-Nimbus) é macio e protege nas longas distâncias. "
              "Responsivo (Boston, Endorphin Speed) devolve energia pra ritmos rápidos. Depende do "
              "seu treino e do seu corpo."},
    {"titulo": "Duelo: Nike Pegasus x Brooks Ghost 🥊",
     "texto": "Os dois são os daily trainers mais vendidos do mundo. O <b>Pegasus</b> é um pouco "
              "mais firme e versátil; o <b>Ghost</b> é mais macio na passada. Ambos acertam pra quem "
              "quer um par confiável pro dia a dia."},
    {"titulo": "Asfalto, esteira ou trilha? 🏞️",
     "texto": "Tênis de rua não foi feito pra trilha (e vice-versa). Pra trilha, procure solado com "
              "cravos (Speedgoat, Terrex). Pra asfalto e esteira, foque em amortecimento e leveza. "
              "Usar o certo previne escorregões e lesões."},
    {"titulo": "Review: Pegasus 42 x Gel-Cumulus 🆚",
     "texto": "Dois daily trainers neutros e versáteis. O <b>Pegasus 42</b> é mais firme e ágil; o "
              "<b>Gel-Cumulus</b> é mais macio e protetor. Pra ritmos variados, Pegasus. Pra conforto "
              "no volume, Cumulus."},
    {"titulo": "Review: Kayano x Adrenaline (estabilidade) 🦶",
     "texto": "Os reis da <b>pisada pronada</b>. O <b>Gel-Kayano</b> entrega estabilidade premium e "
              "amortecimento alto; o <b>Brooks Adrenaline GTS</b> tem suporte 'GuideRails' mais "
              "discreto e passada suave. Os dois seguram a pisada sem parecer 'duro'."},
    {"titulo": "Review: Clifton x 1080 (almofada macia) ☁️",
     "texto": "Pra quem ama maciez no dia a dia: o <b>Hoka Clifton</b> é leve e fofo; o <b>New Balance "
              "Fresh Foam 1080</b> é mais encorpado e premium. Clifton pra leveza, 1080 pra conforto "
              "de luxo nas longas."},
    {"titulo": "Super sapatilhas: Vaporfly x Alphafly x Adios Pro 🚀",
     "texto": "As armas de prova com placa de carbono. <b>Vaporfly</b>: leve e ágil pra 5k–21k. "
              "<b>Alphafly</b>: máximo retorno pra maratona. <b>Adizero Adios Pro</b>: equilíbrio "
              "entre os dois. Todas pra ritmo forte — não pro treino diário."},
    {"titulo": "Começando a correr? Por aqui 🌱",
     "texto": "Pra iniciante, fuja das sapatilhas de prova. Procure um <b>daily trainer</b> com bom "
              "amortecimento e estabilidade (Pegasus, Ghost, Olympikus Corre). Conforto e durabilidade "
              "importam mais que leveza no começo."},
    {"titulo": "Nacional vale a pena? Olympikus x Mizuno 🇧🇷",
     "texto": "Pra custo-benefício, sim! O <b>Olympikus</b> evoluiu muito (tecnologia EVAsense, leve e "
              "macio) e custa bem menos. A <b>Mizuno</b> entrega a clássica tecnologia Wave com mais "
              "durabilidade. Ambas ótimas pra quem não quer gastar muito."},
]


def secao_conteudo():
    bloco = CONTEUDO[datetime.date.today().isocalendar()[1] % len(CONTEUDO)]
    return f"""
    <tr><td style="padding:18px 28px 4px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border:1px solid #eee;border-radius:10px;">
        <tr><td style="padding:18px 20px;">
          <div style="display:inline-block;background:{YELLOW};color:#1a1a1a;font-size:11px;font-weight:800;
               text-transform:uppercase;letter-spacing:.5px;padding:3px 10px;border-radius:12px;">Dica da semana</div>
          <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin:10px 0 6px;">{bloco['titulo']}</div>
          <div style="font-size:14px;color:#555;line-height:1.6;">{bloco['texto']}</div>
        </td></tr>
      </table>
    </td></tr>"""


def montar_html(shoes_sel, cupons):
    hoje = datetime.date.today().strftime("%d/%m")
    cards = "".join(card_produto(s) for s in shoes_sel)
    cupons_html = secao_cupons(cupons)
    conteudo_html = secao_conteudo()
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
        Uma dica rápida, os destaques da semana e as melhores ofertas do momento. Bora correr? 🏃
      </div>
    </td></tr>
    <!-- produtos -->
    <tr><td style="padding:8px 28px;">
      <div style="font-size:18px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">⭐ Destaques</div>
      <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
    </td></tr>
    <!-- conteúdo / review da semana -->
    {conteudo_html}
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
        "subject": "👟 Dica da semana + ofertas — Tênis Ideal",
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
