#!/usr/bin/env python3
import json
import requests
from bs4 import BeautifulSoup
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def extrair_imagem_amazon(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            img_tags = soup.find_all('img', {'alt': True})
            for img in img_tags:
                src = img.get('src', '')
                if 'images' in src and ('amazon' in src or 'ssl' in src):
                    if '._' in src:
                        return src.split('._')[0] + '._AC_SY500_.jpg'
                    return src
        return None
    except:
        return None

def gerar_imagem_placeholder(nome):
    texto = nome[:30].replace(' ', '%20')
    return f"https://via.placeholder.com/300x300/1a1a1a/c8ff00?text={texto}"

def regenerar_imagens():
    print("=" * 60)
    print("🖼️ REGENERADOR DE IMAGENS")
    print("=" * 60 + "\n")

    with open('shoes-fallback.json', 'r', encoding='utf-8') as f:
        shoes = json.load(f)

    print(f"📋 Processando {len(shoes)} produtos...\n")

    atualizadas = 0
    placeholder_count = 0

    for idx, shoe in enumerate(shoes, 1):
        print(f"[{idx}/{len(shoes)}] {shoe['brand']} - {shoe['name']}")

        nova_imagem = None
        affiliate_links = shoe.get('affiliate_links', {})

        # Tentar Amazon
        if 'amazon' in affiliate_links:
            link_data = affiliate_links['amazon']
            url = link_data.get('url') if isinstance(link_data, dict) else link_data

            if url:
                print(f"  🔍 Buscando em Amazon...")
                nova_imagem = extrair_imagem_amazon(url)
                if nova_imagem:
                    print(f"  ✅ Encontrada")

        if not nova_imagem:
            print(f"  ⚠️ Usando placeholder")
            nova_imagem = gerar_imagem_placeholder(shoe['name'])
            placeholder_count += 1

        shoe['photo'] = nova_imagem
        atualizadas += 1
        time.sleep(0.3)

    print("\n💾 Salvando arquivos...\n")

    with open('shoes-fallback.json', 'w', encoding='utf-8') as f:
        json.dump(shoes, f, ensure_ascii=False, indent=2)

    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write("// Sincronizado de Google Sheets\nvar SHOES = ")
        f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
        f.write(";")

    print("=" * 60)
    print("✅ REGENERAÇÃO COMPLETA!")
    print("=" * 60)
    print(f"✅ Total atualizado: {atualizadas}")
    print(f"⚠️  Com placeholder: {placeholder_count}")

if __name__ == "__main__":
    regenerar_imagens()
