#!/usr/bin/env python3
"""
buscar_imagens_avancado.py
---------------------------
🖼️  Busca imagens dos sapatos usando múltiplas estratégias:
1. Web Scraping direto dos links de afiliado
2. Google Images busca automática
3. Fallback para placeholders
"""

import json
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote
import gspread
from google.oauth2.service_account import Credentials

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def expandir_url_encurtada(url_encurtada):
    """Expande URLs encurtadas para obter URL real"""
    try:
        response = requests.head(url_encurtada, allow_redirects=True, timeout=5, headers=HEADERS)
        return response.url
    except:
        return url_encurtada

def buscar_imagem_amazon(url):
    """Tenta extrair imagem do Amazon"""
    try:
        url_real = expandir_url_encurtada(url)
        response = requests.get(url_real, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Tentar vários seletores
            selectors = [
                'img#landingImage',
                'img.a-dynamic-image',
                'div.a-section.a-spacing-none.a-spacing-top-small img',
                'img[alt*="product"]',
            ]

            for selector in selectors:
                try:
                    img = soup.select_one(selector)
                    if img and img.get('src'):
                        src = img.get('src')
                        # Melhorar resolução
                        if '._' in src:
                            return src.split('._')[0] + '._AC_SY500_.jpg'
                        return src
                except:
                    pass
        return None
    except Exception as e:
        return None

def buscar_imagem_loja_oficial(url):
    """Tenta extrair imagem da loja oficial"""
    try:
        url_real = expandir_url_encurtada(url)
        response = requests.get(url_real, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Procurar por imagem principal
            img_selectors = [
                'img.product-image',
                'img.product-img',
                'img[data-src*=product]',
                'picture img',
                'img[alt*=product]',
                'div.product-image img',
            ]

            for selector in img_selectors:
                try:
                    img = soup.select_one(selector)
                    if img:
                        src = img.get('src') or img.get('data-src')
                        if src and src.startswith('http'):
                            return src
                        elif src:
                            return url_real.split('/')[0] + '//' + url_real.split('/')[2] + src
                except:
                    pass
        return None
    except:
        return None

def buscar_no_google_images(brand, name):
    """Busca imagem no Google usando bing (alternativa mais rápida)"""
    try:
        # Usar Bing Image Search como alternativa ao Google (mais rápido)
        search_term = f"{brand} {name} shoe"
        bing_url = f"https://www.bing.com/images/search?q={quote(search_term)}"

        response = requests.get(bing_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            # Procurar por imagem no HTML
            match = re.search(r'"imgUrl":"([^"]+)"', response.text)
            if match:
                return match.group(1)

        return None
    except:
        return None

def gerar_placeholder(nome):
    """Gera placeholder bonito com o nome do produto"""
    return f"https://via.placeholder.com/400x300/1a1a1a/c8ff00?text={quote(nome[:30])}"

def buscar_imagens_com_fallback():
    """Busca imagens com múltiplas estratégias de fallback"""
    print("=" * 80)
    print("🖼️  BUSCADOR AVANÇADO DE IMAGENS - TENIS IDEAL")
    print("=" * 80 + "\n")

    # Carregar dados
    with open('shoes-fallback.json', 'r') as f:
        shoes = json.load(f)

    print(f"📋 Processando {len(shoes)} produtos...\n")

    atualizadas = 0
    amazon_sucesso = 0
    oficial_sucesso = 0
    google_sucesso = 0
    placeholder = 0

    for idx, shoe in enumerate(shoes, 1):
        # Se já tem imagem real, pular
        if shoe.get('photo') and 'placeholder' not in shoe.get('photo', ''):
            continue

        brand = shoe['brand']
        name = shoe['name']

        print(f"[{idx:3d}/103] {brand:15} | {name:35} ", end='', flush=True)

        nova_imagem = None

        # 1️⃣ Tentar Amazon
        affiliate_links = shoe.get('affiliate_links', {})
        if affiliate_links.get('amazon'):
            link = affiliate_links['amazon']
            url = link.get('url') if isinstance(link, dict) else link

            if url and 'amzn.to' in url:
                print("🔍Amazon ", end='', flush=True)
                nova_imagem = buscar_imagem_amazon(url)
                if nova_imagem:
                    print("✅ ", end='', flush=True)
                    amazon_sucesso += 1
                else:
                    print("❌ ", end='', flush=True)

        # 2️⃣ Tentar Loja Oficial
        if not nova_imagem and affiliate_links.get('oficial'):
            link = affiliate_links['oficial']
            url = link.get('url') if isinstance(link, dict) else link

            if url and 'tidd.ly' in url:
                print("🔍Oficial ", end='', flush=True)
                nova_imagem = buscar_imagem_loja_oficial(url)
                if nova_imagem:
                    print("✅ ", end='', flush=True)
                    oficial_sucesso += 1
                else:
                    print("❌ ", end='', flush=True)

        # 3️⃣ Tentar Google Images
        if not nova_imagem:
            print("🔍Google ", end='', flush=True)
            nova_imagem = buscar_no_google_images(brand, name)
            if nova_imagem:
                print("✅ ", end='', flush=True)
                google_sucesso += 1
            else:
                print("❌ ", end='', flush=True)

        # 4️⃣ Usar Placeholder se tudo falhar
        if not nova_imagem:
            nova_imagem = gerar_placeholder(name)
            print("🔲Placeholder")
            placeholder += 1
        else:
            print()

        shoe['photo'] = nova_imagem
        atualizadas += 1
        time.sleep(0.5)  # Rate limiting

    # Salvar
    print("\n💾 Salvando arquivos...\n")

    with open('shoes-fallback.json', 'w', encoding='utf-8') as f:
        json.dump(shoes, f, ensure_ascii=False, indent=2)

    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write("// Sincronizado de Google Sheets\nvar SHOES = ")
        f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
        f.write(";")

    print("=" * 80)
    print("✅ BUSCA DE IMAGENS COMPLETA!")
    print("=" * 80)
    print(f"✅ Total processado: {atualizadas}")
    print(f"  📷 Amazon: {amazon_sucesso}")
    print(f"  🏪 Loja Oficial: {oficial_sucesso}")
    print(f"  🔍 Google Images: {google_sucesso}")
    print(f"  🔲 Placeholder: {placeholder}")
    print(f"\n📊 Taxa de sucesso: {(atualizadas - placeholder) / atualizadas * 100:.1f}%")

if __name__ == "__main__":
    buscar_imagens_com_fallback()
