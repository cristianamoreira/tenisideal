import os
import time
import shutil
import requests
import json
from playwright.sync_api import sync_playwright

def main():
    produtos = [
        {"arquivo": "nimbus.jpg", "url": "https://amzn.to/4r8SXEQ"},
        {"arquivo": "react.jpg", "url": "https://amzn.to/4cYE30i"},
        {"arquivo": "ultraboost.jpg", "url": "https://amzn.to/4cKN7pN"},
        {"arquivo": "nb1080.jpg", "url": "https://amzn.to/4rcfUHd"},
        {"arquivo": "waverider.jpg", "url": "https://amzn.to/4d7fOgq"},
        {"arquivo": "kayano.jpg", "url": "https://amzn.to/4b8n1uk"},
        {"arquivo": "adrenaline.jpg", "url": "https://amzn.to/4u7e6Sr"},
        {"arquivo": "nb860.jpg", "url": "https://amzn.to/47lOeZa"},
        {"arquivo": "vaporfly.jpg", "url": "https://amzn.to/46AElXp"},
        {"arquivo": "adizero.jpg", "url": "https://amzn.to/4l8FKKD"},
        {"arquivo": "clifton.jpg", "url": "https://amzn.to/4u9y3YW"},
        {"arquivo": "speedcross.jpg", "url": "https://amzn.to/4rcFN9T"},
        {"arquivo": "trabuco.jpg", "url": "https://amzn.to/3NhE4Cb"},
        {"arquivo": "speedgoat.jpg", "url": "https://amzn.to/3Pe4Age"},
        {"arquivo": "olympikus.jpg", "url": "https://amzn.to/3NiTshD"},
        {"arquivo": "nb411.jpg", "url": "https://amzn.to/4b9gSht"},
        {"arquivo": "saucony.jpg", "url": "https://amzn.to/3MHdmmn"},
        {"arquivo": "wave-inspire.jpg", "url": "https://amzn.to/4sjsN31"},
        {"arquivo": "pegasus.jpg", "url": "https://amzn.to/4bnDb44"},
        {"arquivo": "ghost.jpg", "url": "https://amzn.to/4aYytsk"},
        {"arquivo": "bondi.jpg", "url": "https://amzn.to/409HQk0"},
        {"arquivo": "cumulus.jpg", "url": "https://amzn.to/477x4ys"},
        {"arquivo": "puma-velocity.jpg", "url": "https://amzn.to/4csjpWe"},
        {"arquivo": "ultra-glide.jpg", "url": "https://amzn.to/3MVPADc"},
        {"arquivo": "wave-sky.jpg", "url": "https://amzn.to/4raEzMi"},
        {"arquivo": "boston.jpg", "url": "https://amzn.to/4rOAgau"},
        {"arquivo": "endorphin-speed.jpg", "url": "https://amzn.to/4aRrLFS"},
        {"arquivo": "ultrafly-trail.jpg", "url": "https://amzn.to/47nlgrQ"},
        {"arquivo": "react-w.jpg", "url": "https://amzn.to/3MHgLl9"},
        {"arquivo": "clifton-w.jpg", "url": "https://amzn.to/4ssofHW"},
        {"arquivo": "adrenaline-w.jpg", "url": "https://amzn.to/4sgDgwi"},
        {"arquivo": "saucony-w.jpg", "url": "https://amzn.to/3N7vIwK"},
        {"arquivo": "waverider-w.jpg", "url": "https://amzn.to/4cskfm2"},
        {"arquivo": "bondi-w.jpg", "url": "https://amzn.to/4stApQS"},
        {"arquivo": "kayano-w.jpg", "url": "https://amzn.to/3OFw26D"},
        {"arquivo": "olympikus-w.jpg", "url": "https://amzn.to/40akw5z"},
        {"arquivo": "speedcross-w.jpg", "url": "https://amzn.to/409UZJS"},
        {"arquivo": "nb860-w.jpg", "url": "https://amzn.to/4aYFkly"},
        {"arquivo": "puma-velocity-w.jpg", "url": "https://amzn.to/4blNO7E"},
        {"arquivo": "endorphin-speed-w.jpg", "url": "https://amzn.to/4aZuoUF"}
    ]

    mesma_imagem = [
        {"origem": "nimbus.jpg", "destino": "nimbus-w.jpg"},
        {"origem": "nb1080.jpg", "destino": "nb1080-w.jpg"},
        {"origem": "ultraboost.jpg", "destino": "ultraboost-w.jpg"},
        {"origem": "vaporfly.jpg", "destino": "vaporfly-w.jpg"}
    ]

    os.makedirs("imgs", exist_ok=True)

    with open("resultado.txt", "w", encoding="utf-8") as log:
        print("Iniciando extração de imagens...")
        
        with sync_playwright() as p:
            # We launch headless set to False if you want to see it, 
            # but True is faster and less intrusive.
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="pt-BR"
            )
            page = context.new_page()

            for p_info in produtos:
                arquivo = p_info["arquivo"]
                url = p_info["url"]
                print(f"Processando: {arquivo} ({url})")

                try:
                    # Access the Affiliate link layout, which will redirect to Amazon
                    page.goto(url, wait_until="commit", timeout=30000)

                    # Try to wait for one of the common Amazon image selectors
                    try:
                        page.wait_for_selector("#landingImage, #imgBlkFront", timeout=15000)
                    except Exception:
                        pass # Could be a CAPTCHA or a different page layout

                    img_element = page.query_selector("#landingImage") or page.query_selector("#imgBlkFront")
                    
                    if not img_element:
                        raise Exception("Elemento de imagem '#landingImage' ou '#imgBlkFront' não encontrado na página (possível CAPTCHA ou layout alternativo)")

                    # Tenta obter a imagem de maior resolução do JSON em data-a-dynamic-image
                    img_url = None
                    dynamic_image_data = img_element.get_attribute("data-a-dynamic-image")
                    if dynamic_image_data:
                        try:
                            # Converte string JSON para dicionário e pega a URL com maior resolução (largura x altura)
                            images_dict = json.loads(dynamic_image_data)
                            if images_dict:
                                img_url = max(images_dict.keys(), key=lambda k: images_dict[k][0] * images_dict[k][1])
                        except Exception:
                            pass # Em caso de falha, segue para a próxima alternativa

                    # Se a busca via JSON falhar (ou não existir no layout), tentamos fallback para data-old-hires ou src
                    if not img_url:
                        img_url = img_element.get_attribute("data-old-hires") or img_element.get_attribute("src")

                    if not img_url:
                        raise Exception("URL da imagem vazia no elemento")

                    # Download the image using requests
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                    response = requests.get(img_url, headers=headers)
                    response.raise_for_status()

                    filepath = os.path.join("imgs", arquivo)
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    msg = f"✅ {arquivo}"
                    log.write(msg + "\n")
                    log.flush()  # Salva no arquivo instantaneamente
                    print(msg)

                except Exception as e:
                    msg = f"❌ {arquivo} — ERRO: {e}"
                    log.write(msg + "\n")
                    log.flush()  # Salva no arquivo instantaneamente
                    print(msg)

                # Wait slightly between requests to avoid rate limits
                time.sleep(2)
                
                # Limpa os cookies preventivamente para evitar detecção de robô da Amazon
                context.clear_cookies()

            browser.close()

        print("\nProcessando modelos que usam a mesma imagem (cópias)...")
        for item in mesma_imagem:
            orig = os.path.join("imgs", item["origem"])
            dest = os.path.join("imgs", item["destino"])
            if os.path.exists(orig):
                shutil.copy2(orig, dest)
                msg = f"✅ {item['destino']} (cópia gerada a partir de {item['origem']})"
                log.write(msg + "\n")
                print(msg)
            else:
                msg = f"❌ {item['destino']} — Falha ao criar cópia: imagem original '{item['origem']}' não encontrada"
                log.write(msg + "\n")
                print(msg)

    print("\nProcesso finalizado! Veja o arquivo 'resultado.txt' e a pasta 'imgs/' para os resultados.")


if __name__ == "__main__":
    main()
