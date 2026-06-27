#!/usr/bin/env python3
"""Sincroniza a aba 'Catálogo' do Google Sheets -> frontend/shoes_data.js + shoes-fallback.json

Faz TUDO de forma correta e repetível:
- Lê os links exatos da planilha (link_loja_oficial / link_amazon / link_netshoes)
- Faz parsing de preço no formato brasileiro (R$ 1.313,78 -> 1313.78)
- Guarda o preço de CADA loja (para o comparador de preços)
- Preenche campos vazios do quiz (budget/nível/pisada/terreno/distância) de forma inteligente
"""
import json
import re
import unicodedata
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

try:
    import requests
except ImportError:
    requests = None

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"
_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'}
_STOP = {'tenis', 'de', 'corrida', 'masculino', 'feminino', 'unissex', 'para', 'nike', 'adidas',
         'mizuno', 'asics', 'new', 'balance', 'olympikus', 'fila', 'hoka', 'saucony', 'brooks',
         'wave', 'gel', 'x', 'v', 'run', 'running', 'skechers', 'under', 'armour', 'salomon'}


def _norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', s.lower())


def _official_ok(brand, name, url):
    """True se o link oficial leva ao produto certo (segue redirect)."""
    if not requests or not url:
        return None  # não dá para validar
    try:
        r = requests.get(url, headers=_UA, timeout=20, allow_redirects=True)
        if r.status_code == 404:
            return False
        final = _norm(urllib.parse.unquote(r.url))
        toks = [t for t in _norm(brand + ' ' + name).split() if t not in _STOP and len(t) >= 2]
        if not toks:
            return True
        return any(t in final for t in toks)
    except Exception:
        return None  # rede falhou → não penaliza


def dedupe(shoes):
    """Remove linhas duplicadas (mesma marca+modelo), mantendo a de melhor link oficial."""
    groups = {}
    for s in shoes:
        key = (s['brand'].strip().lower(), s['name'].strip().lower())
        groups.setdefault(key, []).append(s)

    result = []
    removidos = 0
    for key, entries in groups.items():
        if len(entries) == 1:
            result.append(entries[0])
            continue
        # Pontua cada duplicata: link oficial válido vale muito
        best, best_score = None, -999
        for e in entries:
            score = len(e.get('affiliate_links', {}))  # mais lojas = melhor
            of = e.get('affiliate_links', {}).get('oficial', {})
            if of:
                ok = _official_ok(e['brand'], e['name'], of.get('url'))
                if ok is True:
                    score += 5
                elif ok is False:
                    score -= 10  # oficial errado/quebrado → penaliza forte
            if score > best_score:
                best, best_score = e, score
        result.append(best)
        removidos += len(entries) - 1
        print(f"   🔁 Duplicata '{best['brand']} {best['name']}': "
              f"{len(entries)} linhas → mantida 1 (a de melhor link)")
    if removidos:
        print(f"   🧹 {removidos} linha(s) duplicada(s) removida(s) do site (planilha intacta)")
    return result


def parse_price(val):
    """R$ 1.313,78 -> 1313.78 (formato brasileiro)."""
    if not val:
        return 0
    s = str(val).replace('R$', '').replace('\xa0', '').strip()
    if not s or s == '-':
        return 0
    if ',' in s and '.' in s:        # 1.313,78
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:                    # 1313,78
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0


def budget_by_price(p):
    if p <= 0:
        return ''
    if p < 300:
        return 'ate300'
    if p < 600:
        return '300a600'
    if p < 1000:
        return '600a1000'
    return 'acima1000'


# Padrões por marca para preencher quiz quando a planilha não tem
BRAND_DEFAULTS = {
    'NIKE': {'levels': ['iniciante', 'intermediario', 'avancado'], 'pisada': ['neutra', 'pronada', 'supinada'], 'terreno': ['asfalto', 'pista', 'mista']},
    'ADIDAS': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra', 'pronada'], 'terreno': ['asfalto', 'pista', 'mista']},
    'ASICS': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra', 'pronada', 'supinada'], 'terreno': ['asfalto', 'trilha', 'mista']},
    'BROOKS': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra'], 'terreno': ['asfalto', 'pista']},
    'NEW BALANCE': {'levels': ['iniciante', 'intermediario', 'avancado'], 'pisada': ['neutra'], 'terreno': ['asfalto', 'mista']},
    'MIZUNO': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra', 'pronada'], 'terreno': ['asfalto', 'trilha', 'mista']},
    'HOKA': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra'], 'terreno': ['asfalto', 'trilha']},
    'SAUCONY': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra', 'pronada'], 'terreno': ['asfalto']},
    'FILA': {'levels': ['iniciante', 'intermediario'], 'pisada': ['neutra'], 'terreno': ['asfalto']},
    'OLYMPIKUS': {'levels': ['iniciante', 'intermediario'], 'pisada': ['neutra'], 'terreno': ['asfalto']},
    'SALOMON': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra'], 'terreno': ['trilha', 'mista']},
    'SKECHERS': {'levels': ['iniciante', 'intermediario'], 'pisada': ['neutra'], 'terreno': ['asfalto']},
    'UNDER ARMOUR': {'levels': ['intermediario', 'avancado'], 'pisada': ['neutra'], 'terreno': ['asfalto', 'pista']},
}


def split_pipe(val):
    return [x.strip() for x in str(val or '').split('|') if x.strip()]


def fetch_shoes():
    print("=" * 60)
    print("📥 Sincronizando Google Sheets → shoes_data.js")
    print("=" * 60 + "\n")

    creds = Credentials.from_service_account_file(
        'credenciais.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)
    ws = sheet.worksheet('Catálogo')

    rows = ws.get_all_values()
    headers = rows[0]

    shoes = []
    for row in rows[1:]:
        d = {h: (row[i] if i < len(row) else '') for i, h in enumerate(headers) if h}
        if d.get('ativo', '').lower() != 'sim' or not d.get('nome'):
            continue

        brand = d.get('marca', '').upper()
        name = d.get('nome', '')

        # Preço de cada loja (normal) e PIX
        p_of = parse_price(d.get('preco_loja_oficial'))
        p_am = parse_price(d.get('preco_amazon'))
        p_ns = parse_price(d.get('preco_netshoes'))
        p_pix_of = parse_price(d.get('preco_pix_oficial'))
        p_pix_ns = parse_price(d.get('preco_pix_netshoes'))
        # Preço principal = menor preço disponível
        precos = [p for p in (p_of, p_am, p_ns) if p > 0]
        price = min(precos) if precos else 0

        # Links de afiliado (exatos da planilha) com preço, PIX e parcelas reais
        links = {}
        if d.get('link_loja_oficial') and d['link_loja_oficial'].strip() not in ('', '-'):
            links['oficial'] = {'url': d['link_loja_oficial'].strip(), 'price': p_of,
                                'preco_pix': p_pix_of, 'store': brand, 'label': brand,
                                'installments': (d.get('parcelas_loja_oficial') or '').strip()}
        if d.get('link_amazon') and d['link_amazon'].strip() not in ('', '-'):
            links['amazon'] = {'url': d['link_amazon'].strip(), 'price': p_am,
                               'store': 'Amazon', 'label': 'Amazon',
                               'installments': (d.get('parcelas_amazon') or '').strip()}
        if d.get('link_netshoes') and d['link_netshoes'].strip() not in ('', '-'):
            links['netshoes'] = {'url': d['link_netshoes'].strip(), 'price': p_ns,
                                 'preco_pix': p_pix_ns, 'store': 'Netshoes', 'label': 'Netshoes',
                                 'installments': (d.get('parcelas_netshoes') or '').strip()}

        # Campos do quiz (preenche se a planilha estiver vazia)
        defaults = BRAND_DEFAULTS.get(brand, BRAND_DEFAULTS['NIKE'])
        levels = split_pipe(d.get('nível')) or defaults['levels']
        pisada = split_pipe(d.get('pisada')) or defaults['pisada']
        terreno = split_pipe(d.get('terreno')) or list(defaults['terreno'])
        if 'esteira' not in [t.lower() for t in terreno]:
            terreno.append('esteira')   # esteira serve para qualquer tênis
        # sempre recalcula pelo preço atual (não desatualiza se o preço mudar)
        budget = budget_by_price(price) or d.get('budget', '').strip()

        shoes.append({
            "brand": brand,
            "name": name,
            "slug": d.get('product_id', ''),
            "sexo": split_pipe(d.get('sexo')) or ['unissex'],
            "budget": budget,
            "price": price,
            "price_formatted": ("R$ %.2f" % price).replace(',', '@').replace('.', ',').replace('@', '.'),
            "levels": levels,
            "pisada": pisada,
            "terreno": terreno,
            "distancia": ['curta', 'media', 'longa'],
            "photo": d.get('img', ''),
            "affiliate_links": links,
            "tags": split_pipe(d.get('tags')),
            "description": d.get('razão', ''),
            "reason": d.get('razão', ''),
        })

    # Remove duplicatas (mantém a de melhor link oficial)
    print("\n🔎 Verificando duplicatas...")
    shoes = dedupe(shoes)

    out = "// Sincronizado de Google Sheets (Catálogo)\nvar SHOES = " + \
          json.dumps(shoes, ensure_ascii=False, indent=2) + ";"
    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write(out)
    with open('shoes-fallback.json', 'w', encoding='utf-8') as f:
        json.dump(shoes, f, ensure_ascii=False, indent=2)

    # Resumo
    com_oficial = sum(1 for s in shoes if 'oficial' in s['affiliate_links'])
    com_amazon = sum(1 for s in shoes if 'amazon' in s['affiliate_links'])
    com_netshoes = sum(1 for s in shoes if 'netshoes' in s['affiliate_links'])
    sem_preco = sum(1 for s in shoes if s['price'] <= 0)
    print(f"✅ {len(shoes)} produtos sincronizados")
    print(f"   links: oficial={com_oficial}  amazon={com_amazon}  netshoes={com_netshoes}")
    print(f"   sem preço: {sem_preco}")
    print("\n✅ SUCESSO!")


if __name__ == "__main__":
    fetch_shoes()
