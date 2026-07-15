#!/usr/bin/env python3
"""Gera as paginas de artigo (SEO) a partir do shoes-fallback.json.

Roda DEPOIS do fetch_shoes_from_sheets.py, na mesma automacao diaria.
Assim os precos/links dos artigos ficam sempre atualizados (iguais ao quiz),
enquanto os textos editoriais (review, veredito, FAQ) ficam fixos aqui.

Saida: tenis-pisada-pronada.html, tenis-ate-300.html,
       nike-pegasus-42-vs-mizuno-wave-rider-28.html
"""
import json
import re
import os
import glob
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "shoes-fallback.json")

# ---------------------------------------------------------------- utilitarios

def fmt(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    s = f"{v:,.2f}"                       # 1,234.56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.234,56
    return "R$ " + s


def with_subid(url, sub):
    """Acrescenta o SubID de origem por rede de afiliado."""
    if not url:
        return url
    u = str(url)
    if re.search(r"amazon\.|amzn\.to|link\.amazon", u):
        if "ascsubtag=" not in u:
            u += ("&" if "?" in u else "?") + "ascsubtag=" + sub
    elif re.search(r"awin1\.com|tidd\.ly", u):
        if "clickref=" not in u:
            u += ("&" if "?" in u else "?") + "clickref=" + sub
        else:
            u = re.sub(r"clickref=[^&]*", "clickref=" + sub, u)
    elif "linksynergy.com" in u:
        if "u1=" not in u:
            u += ("&" if "?" in u else "?") + "u1=" + sub
    return u


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def offers_for(prod):
    """Ofertas do produto, ordenadas da mais barata para a mais cara."""
    links = prod.get("affiliate_links") or {}
    offers = []
    for key, o in links.items():
        if not o:
            continue
        url = o.get("url")
        if not url or url == "-":
            continue
        offers.append({
            "key": key,
            "label": o.get("label") or o.get("store") or key.title(),
            "price": float(o.get("price") or 0),
            "pix": float(o.get("preco_pix") or 0),
            "installments": str(o.get("installments") or "").strip(),
            "url": url,
        })
    offers.sort(key=lambda x: (x["price"] <= 0, x["price"] if x["price"] > 0 else 9e9))
    return offers


def best_price(prod):
    offs = offers_for(prod)
    return offs[0]["price"] if offs else 0

# ------------------------------------------------------------------- template

CSS = """
        :root{--black:#0a0a0a;--green:#c8f000;--green-dark:#a8d900;--white:#fff;--gray:#888;--border:#2a2a2a;--card-bg:#141414;}
        *{margin:0;padding:0;box-sizing:border-box;}
        body{background:var(--black);color:var(--white);font-family:'DM Sans',sans-serif;}
        header{padding:20px 40px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
        .logo{font-family:'Bebas Neue',sans-serif;font-size:26px;letter-spacing:3px;text-decoration:none;color:var(--white);}
        .logo span{color:var(--green);}
        .hero{padding:60px 40px 40px;max-width:900px;margin:0 auto;text-align:center;}
        .hero-badge{display:inline-block;background:var(--green);color:var(--black);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:5px 14px;border-radius:2px;margin-bottom:20px;}
        h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(36px,6.5vw,68px);line-height:1.05;margin-bottom:16px;}
        h1 span{color:var(--green);}
        .hero p{font-size:17px;color:var(--gray);line-height:1.7;max-width:640px;margin:0 auto 32px;}
        .brand-pills{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:32px;}
        .brand-pill{background:var(--card-bg);border:1px solid var(--border);padding:8px 20px;border-radius:30px;color:var(--white);text-decoration:none;font-size:14px;font-weight:600;transition:.2s;}
        .brand-pill:hover{border-color:var(--green);background:var(--green);color:var(--black);}
        .guide{padding:0 40px 40px;max-width:900px;margin:0 auto;}
        .guide h2{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;margin:32px 0 8px;}
        .guide p{font-size:15px;color:var(--gray);line-height:1.8;margin-bottom:14px;}
        .guide-tip{background:var(--card-bg);border-left:4px solid var(--green);padding:20px 24px;border-radius:4px;margin:24px 0;font-size:15px;color:var(--gray);line-height:1.7;}
        .guide-tip strong{color:var(--white);}
        .cmp{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px;}
        .cmp th,.cmp td{border:1px solid var(--border);padding:12px 14px;text-align:left;}
        .cmp th{background:#141414;color:var(--green);font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:.03em;}
        .cmp td:first-child{color:var(--gray);font-weight:600;}
        .cmp td{color:var(--white);}
        .products{padding:20px 40px 60px;max-width:1100px;margin:0 auto;}
        .products-label{font-size:11px;color:var(--green);letter-spacing:.15em;text-transform:uppercase;margin-bottom:8px;}
        .products-title{font-family:'Bebas Neue',sans-serif;font-size:2rem;margin-bottom:32px;}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
        .card{background:var(--card-bg);border:1px solid var(--border);border-radius:4px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .2s,transform .2s;}
        .card:hover{border-color:#3a3a3a;transform:translateY(-2px);}
        .card.best{border-color:var(--green);}
        .card-img{height:200px;background:#1a1a1a;display:flex;align-items:center;justify-content:center;}
        .card-img img{width:100%;height:100%;object-fit:contain;padding:16px;}
        .card-body{padding:16px;display:flex;flex-direction:column;gap:8px;flex:1;}
        .card-top-row{display:flex;justify-content:space-between;align-items:center;}
        .card-brand{font-size:10px;color:var(--green);font-weight:700;letter-spacing:.1em;text-transform:uppercase;}
        .card-level{font-size:10px;color:var(--gray);background:#222;padding:2px 8px;border-radius:10px;}
        .card-name{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:.03em;}
        .card-tag{display:inline-block;background:var(--green);color:var(--black);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;padding:2px 8px;border-radius:2px;width:max-content;}
        .card-reason{font-size:13px;color:var(--gray);line-height:1.5;flex:1;}
        .card-price{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:var(--green);letter-spacing:.02em;}
        .card-price.ver{font-size:1rem;color:var(--gray);}
        .card-pix{font-size:12px;color:var(--white);}
        .card-parcelas{font-size:12px;color:var(--gray);}
        .card-btns{display:flex;flex-direction:column;gap:8px;margin-top:4px;}
        .btn-amazon{display:flex;justify-content:space-between;align-items:center;background:var(--green);color:var(--black);font-weight:700;font-size:14px;padding:11px 16px;text-decoration:none;border-radius:3px;transition:.2s;}
        .btn-amazon:hover{background:var(--green-dark);}
        .btn-sec{display:flex;justify-content:space-between;align-items:center;background:transparent;border:1px solid var(--border);color:var(--gray);font-size:13px;padding:9px 16px;text-decoration:none;border-radius:3px;transition:.2s;}
        .btn-sec:hover{border-color:#555;color:var(--white);}
        .quiz-cta{margin:0 40px 60px;background:linear-gradient(135deg,#0f1800 0%,#141414 100%);border:1px solid rgba(200,240,0,0.2);border-radius:6px;padding:3rem;display:flex;align-items:center;justify-content:space-between;gap:2rem;}
        .quiz-cta h3{font-family:'Bebas Neue',sans-serif;font-size:2rem;margin-bottom:8px;}
        .quiz-cta p{font-size:14px;color:var(--gray);}
        .btn-quiz{display:inline-flex;align-items:center;gap:8px;background:transparent;border:1px solid var(--green);color:var(--green);font-family:'Bebas Neue',sans-serif;font-size:18px;padding:14px 28px;text-decoration:none;border-radius:3px;white-space:nowrap;transition:.2s;}
        .btn-quiz:hover{background:var(--green);color:var(--black);}
        .afiliado-note{text-align:center;font-size:11px;color:#444;padding:0 40px 40px;}
        footer{padding:40px;border-top:1px solid var(--border);text-align:center;font-size:12px;color:var(--gray);}
        footer a{color:var(--green);text-decoration:none;margin:0 12px;}
        @media(max-width:600px){header,.hero,.guide,.products,.quiz-cta{padding-left:20px;padding-right:20px;}.quiz-cta{flex-direction:column;text-align:center;}.cmp{font-size:12.5px;}.cmp th,.cmp td{padding:9px 8px;}}
"""


def page_head(title, desc, slugfile):
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18004382554"></script>
    <script>
        window.dataLayer=window.dataLayer||[];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js',new Date());
        gtag('config','AW-18004382554');
        gtag('config','G-GE2YJ60PPY');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(desc)}">
    <link rel="canonical" href="https://www.tenisideal.com.br/{slugfile[:-5] if slugfile.endswith('.html') else slugfile}">
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>{CSS}</style>
</head>
<body>
    <header>
        <a href="index.html" class="logo"><span>Tênis</span>ideal</a>
        <a href="index.html" style="font-size:13px;color:var(--gray);text-decoration:none;">← Voltar ao quiz</a>
    </header>
"""


def pills(items):
    h = '<div class="brand-pills">'
    for label, href in items:
        h += f'<a href="{href}" class="brand-pill">{esc(label)}</a>'
    return h + "</div>"


def footer(links):
    h = '<footer><p>&copy; 2026 Tênisideal.</p><div style="margin-top:12px;">'
    for label, href in links:
        h += f'<a href="{href}">{esc(label)}</a>'
    return h + '</div></footer>\n</body>\n</html>\n'


def render_card(prod, cfg, sub, best=False):
    offs = offers_for(prod)
    if not offs:
        return ""
    primary = offs[0]
    price = primary["price"]
    price_html = (f'<div class="card-price">{fmt(price)}</div>'
                  if price > 0 else '<div class="card-price ver">Ver preço</div>')
    # PIX: do primeiro que tiver, menor que o preco cheio
    pix = primary["pix"] if primary["pix"] > 0 else 0
    if pix <= 0:
        for o in offs:
            if 0 < o["pix"] < (price or 9e9):
                pix = o["pix"]
                break
    pix_html = f'<div class="card-pix">{fmt(pix)} no PIX</div>' if pix > 0 else ""
    parc = (f'<div class="card-parcelas">{esc(primary["installments"])}</div>'
            if primary["installments"] else "")
    name = prod.get("name", "")
    btns = '<div class="card-btns">'
    b1 = with_subid(primary["url"], sub)
    btns += (f'<a href="{b1}" target="_blank" rel="nofollow noopener" class="btn-amazon" '
             f"onclick=\"gtag('event','click_afiliado',{{store:'{esc(primary['label'])}',product:'{esc(prod['brand']+' '+name)}'}})\">Ver melhor preço →</a>")
    if len(offs) > 1:
        s = offs[1]
        b2 = with_subid(s["url"], sub)
        btns += (f'<a href="{b2}" target="_blank" rel="nofollow noopener" class="btn-sec" '
                 f"onclick=\"gtag('event','click_afiliado',{{store:'{esc(s['label'])}',product:'{esc(prod['brand']+' '+name)}'}})\">Ver na {esc(s['label'])} →</a>")
    btns += "</div>"
    tag = f'<span class="card-tag">{esc(cfg.get("tag",""))}</span>' if cfg.get("tag") else ""
    return f"""
        <div class="card{' best' if best else ''}">
          <div class="card-img"><img src="{esc(prod.get('photo',''))}" alt="{esc(prod['brand']+' '+name)}" loading="lazy" onerror="this.style.opacity=0"></div>
          <div class="card-body">
            <div class="card-top-row">
              <div class="card-brand">{esc(prod['brand'])}</div>
              <div class="card-level">{esc(cfg.get('level',''))}</div>
            </div>
            {tag}
            <div class="card-name">{esc(name)}</div>
            <div class="card-reason">{esc(cfg.get('review',''))}</div>
            {price_html}
            {pix_html}
            {parc}
            {btns}
          </div>
        </div>"""


def render_list_article(article, index):
    head = page_head(article["title"], article["desc"], article["file"])
    hero = f"""
    <div class="hero">
        <div class="hero-badge">{article['badge']}</div>
        <h1>{article['h1']}</h1>
        <p>{esc(article['lead'])}</p>
        {pills(article['pills'])}
    </div>
"""
    guide = '<div class="guide">' + article["intro_html"] + "</div>"
    cards = ""
    for i, item in enumerate(article["products"]):
        prod = index.get(item["slug"])
        if not prod:
            continue
        cards += render_card(prod, item, article["sub"], best=(i == 0))
    section = f"""
    <section class="products">
        <div class="products-label">{esc(article['products_label'])}</div>
        <h2 class="products-title">{esc(article['products_title'])}</h2>
        <div class="grid">{cards}
        </div>
    </section>
"""
    faq = '<div class="guide"><h2>Perguntas frequentes</h2>' + article["faq_html"] + "</div>"
    cta = f"""
    <div class="quiz-cta">
        <div><h3>{esc(article['cta_h3'])}</h3>
        <p>Responda 7 perguntas e descubra os modelos exatos para o seu perfil, pisada e orçamento.</p></div>
        <a href="index.html" class="btn-quiz">👟 Fazer o Quiz Grátis →</a>
    </div>
    <p class="afiliado-note">* Os links são de afiliado. Ao comprar você apoia o Tênisideal sem custo adicional. Preços e disponibilidade podem variar.</p>
"""
    return head + hero + guide + section + faq + cta + footer(article["footer"])


def render_comparison(article, index):
    a = index.get(article["a"]["slug"])
    b = index.get(article["b"]["slug"])
    pa, pb = best_price(a), best_price(b)
    head = page_head(article["title"], article["desc"], article["file"])
    hero = f"""
    <div class="hero">
        <div class="hero-badge">{article['badge']}</div>
        <h1>{article['h1']}</h1>
        <p>{esc(article['lead'])}</p>
        {pills(article['pills'])}
    </div>
"""
    rows = article["table_rows"]
    table = '<table class="cmp"><tr><th>&nbsp;</th><th>' + esc(article["a"]["name"]) + '</th><th>' + esc(article["b"]["name"]) + '</th></tr>'
    table += f'<tr><td>Preço a partir de</td><td>{fmt(pa)}</td><td><strong style="color:var(--green)">{fmt(pb)}</strong></td></tr>'
    for label, va, vb in rows:
        table += f'<tr><td>{esc(label)}</td><td>{esc(va)}</td><td>{esc(vb)}</td></tr>'
    table += "</table>"
    guide = ('<div class="guide">' + article["intro_html"] +
             '<h2>Comparativo direto</h2>' + table +
             '<h2>O veredito</h2>' + article["verdict_html"] + "</div>")
    cards = render_card(b, article["b"], article["sub"], best=True) + render_card(a, article["a"], article["sub"], best=False)
    section = f"""
    <section class="products">
        <div class="products-label">Onde comprar · Melhor preço</div>
        <h2 class="products-title">Os dois modelos</h2>
        <div class="grid">{cards}
        </div>
    </section>
"""
    faq = '<div class="guide"><h2>Perguntas frequentes</h2>' + article["faq_html"] + "</div>"
    cta = f"""
    <div class="quiz-cta">
        <div><h3>{esc(article['cta_h3'])}</h3>
        <p>Responda 7 perguntas e descubra o modelo exato para o seu perfil, pisada e orçamento.</p></div>
        <a href="index.html" class="btn-quiz">👟 Fazer o Quiz Grátis →</a>
    </div>
    <p class="afiliado-note">* Os links são de afiliado. Ao comprar você apoia o Tênisideal sem custo adicional. Preços e disponibilidade podem variar.</p>
"""
    return head + hero + guide + section + faq + cta + footer(article["footer"])

# ------------------------------------------------------------- config artigos

RELATED = [("Melhores da Corrida", "melhores-tenis-corrida.html"),
           ("Para Iniciantes", "melhores-tenis-corrida-iniciantes.html"),
           ("Dor no Joelho", "tenis-para-dor-no-joelho.html"),
           ("Pisada Pronada", "tenis-pisada-pronada.html"),
           ("Até R$ 300", "tenis-ate-300.html"),
           ("Pegasus vs Wave Rider", "nike-pegasus-42-vs-mizuno-wave-rider-28.html")]

PRONADA = {
    "file": "tenis-pisada-pronada.html", "sub": "artigo_pronada",
    "title": "Melhores Tênis para Pisada Pronada em 2026 — Guia e Comparativo",
    "desc": "Os melhores tênis de estabilidade para pisada pronada em 2026: Mizuno Wave Inspire 21, Brooks Adrenaline GTS 24, ASICS Gel-Kayano 32 e Nike Structure 26. Preços e como escolher.",
    "badge": "👟 Guia de Pisada 2026",
    "h1": "Melhores Tênis para <span>Pisada Pronada</span>",
    "lead": "Se você é pronador e usa o tênis errado, cada corrida vira risco de lesão. Veja os melhores tênis de estabilidade de 2026 à venda no Brasil — com preço e para quem cada um serve.",
    "pills": [("Pisada Supinada", "tenis-pisada-supinada.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Até R$ 300", "tenis-ate-300.html")],
    "intro_html": (
        "<h2>Antes de tudo: você é mesmo pronador?</h2>"
        "<p>A pronação excessiva acontece quando o tornozelo \"rola\" para dentro a cada passada, sobrecarregando joelho, canela e quadril. O tênis certo — os modelos de <strong>estabilidade</strong> — corrige esse movimento e reduz o risco de lesão.</p>"
        "<div class=\"guide-tip\">🦶 <strong>Teste do pé molhado:</strong> molhe a sola do pé e pise numa folha de papel. Pegada cheia e larga é um forte sinal de <strong>pisada pronada</strong>. Curva moderada indica neutra; arco muito acentuado, supinada.</div>"
        "<div class=\"guide-tip\">👉 <strong>Quer certeza em 1 minuto?</strong> <a href=\"index.html\" style=\"color:var(--green);\">Faça o quiz do Tênis Ideal</a> — ele cruza sua pisada, peso, terreno e objetivo e mostra o tênis certo, com o melhor preço.</div>"
    ),
    "products_label": "Seleção 2026 · Tênis de estabilidade",
    "products_title": "Os melhores para pisada pronada",
    "products": [
        {"slug": "mizuno-wave-inspire-21-0e67", "tag": "🏆 Melhor custo-benefício", "level": "Iniciante / Intermediário", "review": "A placa Wave dupla estabiliza sem endurecer a passada. Mais macio que os antigos Mizuno de controle e aguenta treinos longos. Estabilidade premium por um preço bem menor."},
        {"slug": "brooks-adrenaline-gts-24-ec51", "tag": "Recomendado por fisioterapeutas", "level": "Todos os níveis", "review": "O sistema GuideRails age como grades de proteção que só entram em ação quando o joelho sai do eixo. Controle inteligente, sem parecer engessado."},
        {"slug": "asics-gel-kayano-32-8bbd", "tag": "Longas distâncias", "level": "Todos os níveis", "review": "Referência em estabilidade + amortecimento para longas distâncias. Espuma FF BLAST PLUS e suporte 4D para pronadores que rodam muito ou pesam mais."},
        {"slug": "nike-structure-26-9602", "tag": "Para fãs da Nike", "level": "Todos os níveis", "review": "Suporte medial firme e solado durável, com o conforto que a Nike entrega no dia a dia. A opção de estabilidade para quem é fiel à marca."},
    ],
    "faq_html": (
        "<div class=\"guide-tip\"><strong>Tênis de estabilidade serve para pisada neutra?</strong><br>Não é o ideal — o suporte extra pode incomodar. Prefira um modelo neutro nesse caso.</div>"
        "<div class=\"guide-tip\"><strong>Dá pra correr com o tênis errado?</strong><br>Dá, mas aumenta o risco de lesão a longo prazo. Vale investir no tipo certo.</div>"
        "<div class=\"guide-tip\"><strong>Onde comprar mais barato?</strong><br>Os preços variam entre Amazon, Netshoes e loja oficial. O <a href=\"index.html\" style=\"color:var(--green);\">quiz do Tênis Ideal</a> compara os três, inclusive no PIX.</div>"
    ),
    "cta_h3": "Não sabe qual é a sua pisada?",
    "footer": [("Pisada Supinada", "tenis-pisada-supinada.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Até R$ 300", "tenis-ate-300.html"), ("Voltar ao Quiz", "index.html")],
}

ATE300 = {
    "file": "tenis-ate-300.html", "sub": "artigo_ate300",
    "title": "Melhores Tênis de Corrida até R$300 em 2026 (Custo-Benefício)",
    "desc": "Os melhores tênis de corrida até R$300 em 2026: Olympikus Orbita, Fila Speed Lite, Mizuno Wave Dynasty 7, Nike Revolution 8 e mais. Custo-benefício real e onde comprar mais barato.",
    "badge": "💸 Custo-Benefício 2026",
    "h1": "Melhores Tênis de Corrida <span>até R$300</span>",
    "lead": "Dá sim pra começar a correr sem gastar muito. Selecionamos os tênis com o melhor custo-benefício de 2026 até R$300 — leves, confortáveis e com bom amortecimento pro dia a dia.",
    "pills": [("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html"), ("Até R$ 500", "tenis-ate-500.html")],
    "intro_html": (
        "<h2>Como escolher um bom tênis barato</h2>"
        "<p>Na faixa até R$300 você não vai achar placa de carbono — e tudo bem. Para começar, o que importa é <strong>amortecimento confortável</strong>, <strong>solado durável</strong> e o <strong>ajuste no pé</strong>. As marcas nacionais (Olympikus, Fila) dominam esse segmento.</p>"
        "<div class=\"guide-tip\">💡 <strong>Dica de ouro:</strong> o mesmo tênis costuma variar de preço entre as lojas — o <a href=\"index.html\" style=\"color:var(--green);\">quiz do Tênis Ideal</a> já mostra o menor preço, inclusive no PIX.</div>"
    ),
    "products_label": "Seleção 2026 · Até R$300",
    "products_title": "Os melhores com o melhor custo-benefício",
    "products": [
        {"slug": "olympikus-orbita-3e40", "tag": "🏆 Mais barato da lista", "level": "Iniciante", "review": "Leve e versátil com tecnologia Evasense para treinos diários. Difícil achar um tênis de corrida decente por menos."},
        {"slug": "olympikus-marte-4909", "tag": "Leve pro dia a dia", "level": "Iniciante", "review": "Tecnologia EVAsense para máxima maciez e leveza. Cabedal respirável e boa tração no asfalto e esteira."},
        {"slug": "fila-tenis-fila-speed-lite-masculino-328b", "tag": "Para começar com segurança", "level": "Iniciante", "review": "Leve, confortável e com ótimo custo-benefício para treinos diários e caminhada. Ideal para quem está começando."},
        {"slug": "olympikus-challenger-5-3413", "tag": "Amortecimento nacional", "level": "Iniciante / Intermediário", "review": "Tecnologia Eleva+ com cabedal tipo meia e solado Gripper antiderrapante. Amortecimento acima da média para o preço."},
        {"slug": "mizuno-wave-dynasty-7-83eb", "tag": "Marca premium por menos", "level": "Todos os níveis", "review": "Tecnologia Mizuno Wave para estabilidade e amortecimento, com solado X10 durável. Um Mizuno de verdade por menos."},
        {"slug": "nike-revolution-8-3567-f", "tag": "Nike acessível", "level": "Iniciante", "review": "A entrada ideal no universo Nike: leve, respirável e com bom amortecimento para treinos regulares."},
    ],
    "faq_html": (
        "<div class=\"guide-tip\"><strong>Dá pra correr de verdade com tênis até R$300?</strong><br>Dá sim, principalmente para iniciantes e treinos de até 5–10 km. O que muda nos mais caros é a espuma e a leveza — importante para distâncias longas ou provas.</div>"
        "<div class=\"guide-tip\"><strong>Marca nacional é boa?</strong><br>Olympikus e Fila entregam ótimo custo-benefício e são feitas para o corredor brasileiro. Para começar, são certeiras.</div>"
        "<div class=\"guide-tip\"><strong>Como pago mais barato?</strong><br>Muitos têm desconto no PIX. O <a href=\"index.html\" style=\"color:var(--green);\">quiz do Tênis Ideal</a> mostra o menor preço entre as lojas.</div>"
    ),
    "cta_h3": "Qual desses combina com você?",
    "footer": [("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html"), ("Até R$ 500", "tenis-ate-500.html"), ("Voltar ao Quiz", "index.html")],
}

INICIANTES = {
    "file": "melhores-tenis-corrida-iniciantes.html", "sub": "artigo_iniciantes",
    "title": "Melhores Tênis de Corrida para Iniciantes em 2026 (Guia Completo)",
    "desc": "Os melhores tênis de corrida para iniciantes em 2026: Mizuno Wave Rider 28, Olympikus Orbita, Nike Revolution 8, ASICS Gel-Cumulus 26 e mais. Como escolher o primeiro tênis e onde comprar mais barato.",
    "badge": "🌱 Guia do Iniciante 2026",
    "h1": "Melhores Tênis de Corrida para <span>Iniciantes</span>",
    "lead": "Vai começar a correr? O primeiro tênis não precisa ser o mais caro — precisa ser o certo. Selecionamos os melhores tênis para iniciantes de 2026: confortáveis, com bom amortecimento e para todos os bolsos.",
    "pills": [("Até R$ 300", "tenis-ate-300.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html")],
    "intro_html": (
        "<h2>Como escolher o primeiro tênis de corrida</h2>"
        "<p>No começo, três coisas importam mais que qualquer tecnologia de ponta: <strong>amortecimento confortável</strong> (para proteger joelhos e canela), um modelo <strong>neutro e versátil</strong> (serve pra maioria das pessoas) e o <strong>ajuste no pé</strong>. Deixe placa de carbono e tênis de prova para depois — eles são feitos para quem já corre rápido.</p>"
        "<div class=\"guide-tip\">📏 <strong>Dica de tamanho:</strong> compre a corrida <strong>meio a um número maior</strong> que seu calçado normal. O pé incha ao correr, e sobrar um dedo na frente evita bolhas e unha roxa.</div>"
        "<div class=\"guide-tip\">🔁 <strong>Quanto dura?</strong> Um tênis de corrida rende de <strong>600 a 800 km</strong>. Para quem corre 3x por semana, isso dá cerca de um ano. Depois disso a espuma perde o amortecimento — hora de trocar.</div>"
        "<div class=\"guide-tip\">👉 <strong>Não sabe sua pisada nem o modelo certo?</strong> <a href=\"index.html\" style=\"color:var(--green);\">Faça o quiz do Tênis Ideal</a> — em 60 segundos ele cruza sua pisada, peso, objetivo e orçamento e mostra o tênis certo, com o melhor preço.</div>"
    ),
    "products_label": "Seleção 2026 · Para quem está começando",
    "products_title": "Os melhores tênis para iniciantes",
    "products": [
        {"slug": "mizuno-wave-rider-28-4dcc", "tag": "🏆 Melhor escolha geral", "level": "Iniciante / Todos os níveis", "review": "O primeiro tênis \"de verdade\" mais recomendado do Brasil. Neutro, estável e muito durável graças à placa Wave e ao solado X10. Conforto de sobra para evoluir do zero aos 10 km sem trocar de modelo."},
        {"slug": "olympikus-orbita-3e40", "tag": "💸 Mais barato pra começar", "level": "Iniciante", "review": "Leve, nacional e com tecnologia Evasense para treinos diários. É difícil achar um tênis de corrida decente por menos — perfeito para dar os primeiros passos sem medo de gastar."},
        {"slug": "fila-tenis-fila-speed-lite-masculino-328b", "tag": "Alternativa econômica", "level": "Iniciante", "review": "Leve e confortável, com ótimo custo-benefício para caminhada e corrida leve. Uma entrada segura para quem ainda está criando o hábito de treinar."},
        {"slug": "nike-revolution-8-3567-f", "tag": "Nike acessível", "level": "Iniciante", "review": "A porta de entrada no universo Nike: respirável, leve e com bom amortecimento para treinos regulares. Para quem quer a marca sem pagar caro."},
        {"slug": "asics-gel-cumulus-26-ffda", "tag": "Amortecimento premium", "level": "Iniciante / Intermediário", "review": "Um clássico neutro e macio: gel no calcanhar e espuma FF BLAST para absorver o impacto. Ideal para quem quer conforto extra desde o início ou pretende aumentar a quilometragem."},
        {"slug": "brooks-ghost-14-neutral-b5f9", "tag": "O conforto pra durar anos", "level": "Todos os níveis", "review": "Referência mundial em conforto neutro. Maciez equilibrada e transição suave da passada — o tipo de tênis que você compra uma vez e usa por muito tempo. Um upgrade que vale para quem levou gosto pela corrida."},
    ],
    "faq_html": (
        "<div class=\"guide-tip\"><strong>Preciso de um tênis caro para começar a correr?</strong><br>Não. Para iniciantes e treinos de até 5–10 km, um modelo nacional de R$150–300 já cumpre bem. O que muda nos mais caros é a espuma e a leveza — importantes só quando você aumentar a distância ou o ritmo.</div>"
        "<div class=\"guide-tip\"><strong>Tênis de academia ou casual serve para correr?</strong><br>Não é o ideal. Tênis de corrida têm amortecimento e drop pensados para o impacto repetido da passada. Correr com casual aumenta o risco de dor no joelho e na canela.</div>"
        "<div class=\"guide-tip\"><strong>Que tamanho devo comprar?</strong><br>Meio a um número maior que o seu normal. Deve sobrar cerca de um dedo entre o maior dedo do pé e a ponta do tênis.</div>"
        "<div class=\"guide-tip\"><strong>Como pago mais barato?</strong><br>O mesmo tênis varia de preço entre Amazon, Netshoes e loja oficial, e muitos têm desconto no PIX. O <a href=\"index.html\" style=\"color:var(--green);\">quiz do Tênis Ideal</a> mostra o menor preço entre as lojas.</div>"
    ),
    "cta_h3": "Qual é o tênis ideal pra você começar?",
    "footer": [("Até R$ 300", "tenis-ate-300.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html"), ("Voltar ao Quiz", "index.html")],
}

JOELHO = {
    "file": "tenis-para-dor-no-joelho.html", "sub": "artigo_joelho",
    "title": "Melhores Tênis para Correr com Dor no Joelho em 2026 — Guia",
    "desc": "Os melhores tênis de amortecimento e estabilidade para quem sente dor no joelho ao correr em 2026: Brooks Adrenaline GTS 24, Hoka Bondi 9, ASICS Gel-Kayano 32 e mais. Como escolher e quando procurar um profissional.",
    "badge": "🦵 Guia de Amortecimento 2026",
    "h1": "Melhores Tênis para Correr com <span>Dor no Joelho</span>",
    "lead": "Sente o joelho reclamar depois de correr? O tênis certo reduz o impacto e alinha a passada, aliviando a sobrecarga na articulação. Veja os modelos de 2026 com mais amortecimento e estabilidade — e saiba quando é hora de procurar ajuda profissional.",
    "pills": [("Pisada Pronada", "tenis-pisada-pronada.html"), ("Para Iniciantes", "melhores-tenis-corrida-iniciantes.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html")],
    "intro_html": (
        "<h2>O tênis certo ajuda — mas não substitui um diagnóstico</h2>"
        "<p>A dor no joelho ao correr tem várias causas possíveis: <strong>impacto excessivo</strong>, <strong>pronação</strong> (o tornozelo rola para dentro e desalinha o joelho), fraqueza muscular ou aumento rápido do volume de treino. Um bom tênis atua em duas delas: <strong>amortece o impacto</strong> que sobe para a articulação e <strong>estabiliza a passada</strong>. Isso alivia a sobrecarga — mas não trata a causa por trás da dor.</p>"
        "<div class=\"guide-tip\">⚠️ <strong>Aviso importante:</strong> se a dor é forte, persistente, vem com inchaço ou trava o joelho, <strong>pare e procure um médico ou fisioterapeuta</strong> antes de continuar correndo. Este guia é informativo e não substitui a avaliação de um profissional de saúde.</div>"
        "<div class=\"guide-tip\">🦵 <strong>O que procurar num tênis:</strong> <strong>amortecimento generoso</strong> (absorve o impacto no calcanhar e reduz o que chega ao joelho) e, se você for pronador, <strong>estabilidade</strong> (impede o joelho de \"cair\" para dentro a cada passada). Evite modelos duros, minimalistas ou de prova.</div>"
        "<div class=\"guide-tip\">👉 <strong>Não sabe sua pisada?</strong> <a href=\"index.html\" style=\"color:var(--green);\">Faça o quiz do Tênis Ideal</a> — em 60 segundos ele cruza sua pisada, peso e objetivo e indica o modelo com o amortecimento certo para o seu caso, no melhor preço.</div>"
    ),
    "products_label": "Seleção 2026 · Amortecimento e estabilidade",
    "products_title": "Os melhores para quem sente dor no joelho",
    "products": [
        {"slug": "brooks-adrenaline-gts-24-ec51", "tag": "🏆 Recomendado por fisioterapeutas", "level": "Estabilidade", "review": "O sistema GuideRails funciona como grades que impedem o joelho de sair do eixo, reduzindo a torção que sobrecarrega a articulação. É um dos modelos mais citados por fisioterapeutas para quem sente dor no joelho ao correr."},
        {"slug": "hoka-bondi-9-f", "tag": "Amortecimento máximo", "level": "Neutro · Max cushion", "review": "O tênis mais amortecido da Hoka. A espuma espessa absorve boa parte do impacto que sobe para o joelho a cada passada. Excelente para asfalto e para corredores mais pesados que querem poupar as articulações."},
        {"slug": "asics-gel-kayano-32-8bbd", "tag": "Estabilidade + conforto", "level": "Estabilidade · Max cushion", "review": "Une as duas frentes: gel e espuma FF BLAST PLUS para amortecer o impacto, mais suporte 4D que segura a pronação. Para pronadores que sentem o joelho e rodam distâncias maiores."},
        {"slug": "asics-gel-nimbus-27-2ecb", "tag": "Amortecimento por menos", "level": "Neutro", "review": "Amortecimento neutro macio e generoso a um preço mais acessível que os topos de linha. Boa opção para pisada neutra que quer reduzir o impacto sem gastar tanto."},
        {"slug": "mizuno-wave-inspire-21-0e67", "tag": "Estabilidade acessível", "level": "Estabilidade", "review": "A placa Wave dupla controla a pronação sem endurecer a passada. Alívio para o joelho de quem é pronador, por um preço bem mais amigável que os modelos premium."},
        {"slug": "brooks-ghost-14-neutral-b5f9", "tag": "Maciez pro dia a dia", "level": "Neutro", "review": "Transição suave e maciez neutra, com menos impacto abrupto na passada. Confortável para o dia a dia de quem quer poupar as articulações sem precisar de correção de pisada."},
    ],
    "faq_html": (
        "<div class=\"guide-tip\"><strong>Um tênis mais amortecido resolve a dor no joelho?</strong><br>Ajuda a reduzir o impacto e a sobrecarga, e muita gente sente alívio. Mas se a dor persistir ou piorar, ela pode ter outra causa (muscular, articular, excesso de treino) — nesse caso, procure um profissional.</div>"
        "<div class=\"guide-tip\"><strong>Pisada tem a ver com dor no joelho?</strong><br>Sim. A pronação excessiva desalinha o joelho a cada passada e o sobrecarrega. Tênis de estabilidade ajudam a corrigir isso. Se não sabe sua pisada, o <a href=\"index.html\" style=\"color:var(--green);\">quiz</a> indica.</div>"
        "<div class=\"guide-tip\"><strong>Posso correr sentindo dor no joelho?</strong><br>Dor leve que some ao aquecer pode ser adaptação. Dor que aumenta durante ou depois da corrida, ou que vem com inchaço, é sinal de parar e procurar avaliação. Não insista na dor.</div>"
        "<div class=\"guide-tip\"><strong>Amortecimento bom custa caro?</strong><br>Os melhores modelos de amortecimento máximo tendem a ser mais caros, mas há opções de estabilidade e conforto mais acessíveis (como o Wave Inspire). O <a href=\"index.html\" style=\"color:var(--green);\">quiz</a> mostra o menor preço entre as lojas, inclusive no PIX.</div>"
    ),
    "cta_h3": "Não sabe qual combina com o seu joelho?",
    "footer": [("Pisada Pronada", "tenis-pisada-pronada.html"), ("Para Iniciantes", "melhores-tenis-corrida-iniciantes.html"), ("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Voltar ao Quiz", "index.html")],
}

VERSUS = {
    "file": "nike-pegasus-42-vs-mizuno-wave-rider-28.html", "sub": "artigo_pegasus_rider",
    "title": "Nike Pegasus 42 vs Mizuno Wave Rider 28: qual comprar em 2026?",
    "desc": "Nike Pegasus 42 ou Mizuno Wave Rider 28? Comparamos preço, amortecimento, durabilidade e para quem cada um serve. Veja o veredito e o melhor preço em 2026.",
    "badge": "⚔️ Comparativo 2026",
    "h1": "Nike Pegasus 42 <span>vs</span> Mizuno Wave Rider 28",
    "lead": "Dois dos tênis de treino diário mais vendidos do Brasil — mas com uma diferença de preço enorme. Qual entrega mais pelo seu dinheiro? Comparamos tudo e demos o veredito.",
    "pills": [("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html"), ("Até R$ 300", "tenis-ate-300.html")],
    "intro_html": "<p>Os dois são <strong>neutros, versáteis e feitos para o treino do dia a dia</strong>. O Pegasus é o \"faz-tudo\" da Nike, mais firme e responsivo. O Wave Rider é o equivalente da Mizuno, com a placa Wave que soma estabilidade e durabilidade. A grande diferença aparece no <strong>preço</strong>.</p>",
    "a": {"slug": "nike-pegasus-42-f156-m", "name": "Nike Pegasus 42", "tag": "O clássico da Nike", "level": "Todos os níveis", "review": "O tênis de corrida mais versátil da Nike. React X responsivo com Air Zoom no antepé para qualquer distância e ritmo. Firme e durável."},
    "b": {"slug": "mizuno-wave-rider-28-4dcc", "name": "Mizuno Wave Rider 28", "tag": "🏆 Melhor custo-benefício", "level": "Todos os níveis", "review": "A placa Wave entrega estabilidade e suavidade juntas. Excelente custo-benefício e muito durável — um dos tênis mais recomendados para o dia a dia."},
    "table_rows": [
        ("Tecnologia", "React X + Air Zoom", "Enerzy + placa Wave + solado X10"),
        ("Pegada", "Mais firme e responsiva", "Equilíbrio: macio e estável"),
        ("Melhor para", "Ritmos rápidos e fãs da Nike", "Custo-benefício, iniciantes e durabilidade"),
        ("Durabilidade", "Boa", "Excelente (solado X10)"),
    ],
    "verdict_html": (
        "<div class=\"guide-tip\">🏆 <strong>Para a maioria das pessoas, o Mizuno Wave Rider 28 vence</strong> — entrega estabilidade, conforto e durabilidade de sobra por quase <strong>metade do preço</strong>. É a escolha de custo-benefício.<br><br>👟 <strong>Escolha o Nike Pegasus 42</strong> se você quer uma pegada mais responsiva para treinos de ritmo, ou se é fã da Nike.</div>"
        "<div class=\"guide-tip\">🤔 <strong>Ainda na dúvida?</strong> <a href=\"index.html\" style=\"color:var(--green);\">Faça o quiz do Tênis Ideal</a> — ele considera sua pisada, peso e objetivo e indica qual dos dois é o certo pra você.</div>"
    ),
    "faq_html": (
        "<div class=\"guide-tip\"><strong>Qual é melhor para iniciantes?</strong><br>O Mizuno Wave Rider 28 — mais estável, durável e com preço mais amigável. Ótimo primeiro tênis.</div>"
        "<div class=\"guide-tip\"><strong>Servem para pisada pronada?</strong><br>Os dois são neutros. Se você é pronador, veja o <a href=\"tenis-pisada-pronada.html\" style=\"color:var(--green);\">guia de pisada pronada</a>.</div>"
        "<div class=\"guide-tip\"><strong>Vale pagar mais no Pegasus?</strong><br>Só se você busca pegada mais responsiva para ritmos rápidos ou faz questão da Nike.</div>"
    ),
    "cta_h3": "Qual dos dois é o seu?",
    "footer": [("Melhores da Corrida", "melhores-tenis-corrida.html"), ("Pisada Pronada", "tenis-pisada-pronada.html"), ("Até R$ 300", "tenis-ate-300.html"), ("Voltar ao Quiz", "index.html")],
}

# --------------------------------------------------------------------- sitemap

SITE = "https://www.tenisideal.com.br"

# Paginas internas / utilitarias que NAO devem entrar no sitemap nem ser indexadas.
SITEMAP_EXCLUDE = {
    "calendario_editorial.html", "relatorio_oportunidades.html",
    "gerador-links-afiliado.html", "email-boas-vindas.html",
    "tenisideal-agente-instagram.html",
}

# Prioridade por pagina (index e artigos de alta intencao no topo).
SITEMAP_PRIORITY = {
    "index.html": "1.0",
    "melhores-tenis-corrida-iniciantes.html": "0.9",
    "tenis-para-dor-no-joelho.html": "0.9",
    "tenis-pisada-pronada.html": "0.9",
    "tenis-ate-300.html": "0.9",
    "nike-pegasus-42-vs-mizuno-wave-rider-28.html": "0.9",
    "melhores-tenis-corrida.html": "0.8",
}


def build_sitemap():
    """Gera sitemap.xml e robots.txt a partir das .html publicas da raiz."""
    today = datetime.date.today().isoformat()
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(BASE, "*.html")))
    urls = []
    for f in files:
        if f in SITEMAP_EXCLUDE or f.endswith((".backup", ".bak")):
            continue
        clean = "" if f == "index.html" else (f[:-5] if f.endswith(".html") else f)
        loc = SITE + "/" + clean
        prio = SITEMAP_PRIORITY.get(f, "0.6")
        urls.append(
            f"  <url>\n    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <priority>{prio}</priority>\n  </url>"
        )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(BASE, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)
    robots = ("User-agent: *\nAllow: /\n\n"
              + "".join(f"Disallow: /{f}\n" for f in sorted(SITEMAP_EXCLUDE))
              + f"\nSitemap: {SITE}/sitemap.xml\n")
    with open(os.path.join(BASE, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots)
    print(f"OK  sitemap.xml  ({len(urls)} URLs)  +  robots.txt")

# ------------------------------------------------------------------------ main

def main():
    with open(DATA, encoding="utf-8") as f:
        shoes = json.load(f)
    index = {p.get("slug"): p for p in shoes if p.get("slug")}

    outputs = {
        PRONADA["file"]: render_list_article(PRONADA, index),
        ATE300["file"]: render_list_article(ATE300, index),
        INICIANTES["file"]: render_list_article(INICIANTES, index),
        JOELHO["file"]: render_list_article(JOELHO, index),
        VERSUS["file"]: render_comparison(VERSUS, index),
    }
    for fname, html in outputs.items():
        with open(os.path.join(BASE, fname), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"OK  {fname}  ({len(html)} bytes)")

    build_sitemap()


if __name__ == "__main__":
    main()
