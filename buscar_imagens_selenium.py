#!/usr/bin/env python3
"""
buscar_imagens_selenium.py
---------------------------
🖼️  Busca avançada de imagens usando Selenium (navegador real)
Para contornar bloqueios de scraping e extrair imagens dinamicamente
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os

def expandir_url_encurtada(url_encurtada):
    """Expande URLs encurtadas"""
    try:
        import requests
        response = requests.head(url_encurtada, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url_encurtada

def buscar_imagem_amazon_selenium(url, driver):
    """Busca imagem do Amazon usando Selenium"""
    try:
        url_real = expandir_url_encurtada(url)

        # Adicionar parâmetros para evitar bloqueios
        if 'amazon.com' in url_real:
            driver.get(url_real)

            # Aguardar imagem carregar
            time.sleep(3)

            # Procurar por imagem principal
            try:
                img = driver.find_element(By.ID, "landingImage")
                src = img.get_attribute("src")
                if src:
                    return src
            except:
                pass

            try:
                img = driver.find_element(By.CSS_SELECTOR, "img.a-dynamic-image")
                src = img.get_attribute("src")
                if src:
                    return src
            except:
                pass

            # Tentar extrair do script JavaScript (dados do produto)
            try:
                script_result = driver.execute_script("""
                    var imgs = [];
                    document.querySelectorAll('img[alt*="product"]').forEach(el => {
                        var src = el.src || el.getAttribute('data-src');
                        if (src && src.includes('images')) {
                            imgs.push(src);
                        }
                    });
                    return imgs.length > 0 ? imgs[0] : null;
                """)
                if script_result:
                    return script_result
            except:
                pass

        return None
    except Exception as e:
        return None

def buscar_imagens_com_selenium():
    """Busca imagens usando Selenium"""
    print("=" * 80)
    print("🖼️  BUSCADOR COM SELENIUM - TENIS IDEAL")
    print("=" * 80 + "\n")

    # Carregar dados
    with open('shoes-fallback.json', 'r') as f:
        shoes = json.load(f)

    # Configurar Chrome (headless para rodar em background)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    print("🌐 Iniciando navegador Chrome...\n")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    except Exception as e:
        print(f"❌ Erro ao iniciar Chrome: {e}")
        print("   Verifique se o Chrome está instalado\n")
        return False

    found = 0
    failed = 0

    print("📋 Processando produtos sem imagem...\n")

    for idx, shoe in enumerate(shoes, 1):
        # Se já tem imagem real, pular
        if shoe.get('photo') and 'placeholder' not in shoe.get('photo', ''):
            continue

        brand = shoe['brand']
        name = shoe['name']

        print(f"[{idx:3d}] {brand:15} | {name:35} ", end='', flush=True)

        nova_imagem = None
        affiliate_links = shoe.get('affiliate_links', {})

        # Tentar Amazon com Selenium
        if affiliate_links.get('amazon'):
            link = affiliate_links['amazon']
            url = link.get('url') if isinstance(link, dict) else link

            if url and 'amzn.to' in url:
                print("🔍Selenium ", end='', flush=True)
                nova_imagem = buscar_imagem_amazon_selenium(url, driver)
                if nova_imagem:
                    print("✅")
                    found += 1
                else:
                    print("❌")
                    failed += 1
            else:
                print("❌ (sem link)")
                failed += 1
        else:
            print("❌ (sem dados)")
            failed += 1

        if nova_imagem:
            shoe['photo'] = nova_imagem

        time.sleep(1)  # Rate limiting

    driver.quit()
    print("\n" + "=" * 80)
    print("✅ BUSCA COM SELENIUM COMPLETA!")
    print("=" * 80)
    print(f"✅ Encontradas: {found}")
    print(f"❌ Não encontradas: {failed}")

    # Salvar
    with open('shoes-fallback.json', 'w', encoding='utf-8') as f:
        json.dump(shoes, f, ensure_ascii=False, indent=2)

    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write("// Sincronizado de Google Sheets\nvar SHOES = ")
        f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
        f.write(";")

    return True

if __name__ == "__main__":
    buscar_imagens_com_selenium()
