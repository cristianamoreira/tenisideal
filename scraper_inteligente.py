import requests
from bs4 import BeautifulSoup
import time
import json
import csv
import re
import os
import google.generativeai as genai

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================
AMAZON_AFFILIATE_TAG = "tenisideal26-20"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==============================================================================
# 🔥 FUNÇÕES DE IA (GEMINI)
# ==============================================================================
def analisar_tenis_com_gemini(nome_tenis, preco_str):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSyCHVbrFakslrOWjkPYa8WfyYYHlmEsUwtY_AQUI":
        return formata_resultado_vazio()

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    budget = "300a600"
    try:
        preco_num = int(re.sub(r'\D', '', preco_str.split(',')[0]))
        if preco_num < 300: budget = "ate300"
        elif 300 <= preco_num <= 600: budget = "300a600"
        elif 600 < preco_num <= 1000: budget = "600a1000"
        else: budget = "acima1000"
    except:
        pass

    prompt = f"""
Você é um especialista em tênis de corrida. Analise o seguinte modelo: "{nome_tenis}" (Preço base: {budget}).
Responda OBRIGATORIAMENTE em formato JSON válido contendo APENAS a estrutura abaixo. Siga estritamente os arrays.

Opções permitidas:
- sexo: ["masculino", "feminino", "outro"] (Coloque ["masculino", "outro"] se nome for masculino, ou os 3 se for unissex)
- levels: ["iniciante", "intermediario", "avancado"]
- pisadas: ["neutra", "pronada", "supinada", "naosabe"]
- terrenos: ["asfalto", "pista", "esteira", "trilha", "mista"]
- priors: ["amortecimento", "leveza", "durabilidade", "custo"]
- distancias: ["curta", "media", "longa", "maratona"]
- marca: O nome da marca (ex: "ASICS", "NIKE", "OLYMPIKUS")

Exemplo esperado:
{{
  "sexo": ["masculino", "outro"], "brand": "NIKE", "tags": ["Tag1", "Tag2"], "emoji": "👟", "budget": "{budget}",
  "levels": ["iniciante"], "pisadas": ["neutra"], "terrenos": ["asfalto"], "priors": ["amortecimento"],
  "distancias": ["media"], "reason": "Frase persuasiva recomendando."
}}
"""
    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        print(f"Erro na IA para '{nome_tenis}': {e}")
        return formata_resultado_vazio()

def formata_resultado_vazio():
    return {
        "sexo": ["masculino", "outro"], "brand": "Indefinida", "tags": ["Pendente"], "emoji": "👟",
        "budget": "300a600", "levels": ["iniciante"], "pisadas": ["neutra", "naosabe"], 
        "terrenos": ["asfalto"], "priors": ["custo"], "distancias": ["curta"], "reason": "Falta descrição automática."
    }

# ==============================================================================
# 🎬 LEITOR DE HTML LOCAL
# ==============================================================================
def raspar_arquivos_locais():
    print("Procurando por arquivos HTML da Amazon na pasta atual...")
    arquivos_html = [f for f in os.listdir('.') if f.startswith('amazon_vitrine') and f.endswith('.html')]
    
    if not arquivos_html:
        print("❌ Nenhum arquivo encontrado. Salve as páginas da Amazon como 'amazon_vitrine_1.html', 'amazon_vitrine_2.html', etc.")
        return []
        
    print(f"Encontrados {len(arquivos_html)} arquivo(s): {', '.join(arquivos_html)}")
    
    todos_produtos = []
    
    for arquivo in arquivos_html:
        print(f"\nLendo '{arquivo}'...")
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        soup = BeautifulSoup(conteudo, "html.parser")
        cards = soup.select('div[data-component-type="s-search-result"]')
        
        print(f" > Encontrados {len(cards)} tênis neste arquivo.")
        
        for card in cards:
            asin = card.get("data-asin")
            if not asin: continue
                
            nome_el = card.select_one("h2")
            nome = nome_el.text.strip() if nome_el else ""
            
            preco_el = card.select_one(".a-price-whole")
            preco = "R$ " + preco_el.text.strip() if preco_el else "R$ ???"
            
            img_el = card.select_one("img.s-image")
            img_url = img_el.get("src") if img_el else ""
            
            if nome and img_url and preco != "R$ ???":
                # Verifica se o produto já existe na lista para não duplicar
                if not any(p['asin'] == asin for p in todos_produtos):
                    todos_produtos.append({
                        "asin": asin, "nome": nome, "preco": preco, "img_url": img_url
                    })
                
    return todos_produtos

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("👟 Scraper Afiliado + IA via HTML Local")
    print("=========================================\n")
    
    todos_produtos = raspar_arquivos_locais()

    if len(todos_produtos) == 0:
        return

    print(f"\n✅ Scraping Local Realizado! Coletamos {len(todos_produtos)} tênis únicos no total.")
    print("🧠 Iniciando a IA Gemini para catalogar cada tênis... (pode demorar alguns minutos)\n")

    planilha = []
    os.makedirs("imgs", exist_ok=True)

    for i, prod in enumerate(todos_produtos):
        print(f"[{i+1}/{len(todos_produtos)}] Analisando: {prod['nome'][:30]}... ", end="", flush=True)
        ia_specs = analisar_tenis_com_gemini(prod['nome'], prod['preco'])

        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', prod['nome'].lower()).strip()
        clean_name = re.sub(r'\s+', '-', clean_name)
        img_filename = f"{clean_name[:30]}-{prod['asin']}.jpg"

        try:
            r = requests.get(prod['img_url'], headers={"User-Agent": HEADERS["User-Agent"]})
            with open(os.path.join("imgs", img_filename), "wb") as f: f.write(r.content)
            img_path = f"imgs/{img_filename}"
        except Exception as e:
            print(f"Erro ao baixar imagem: {e}")
            img_path = "imgs/placeholder.png"

        affiliate_link = f"https://www.amazon.com.br/dp/{prod['asin']}?tag={AMAZON_AFFILIATE_TAG}"

        planilha.append({
            "sexo": ",".join(ia_specs.get("sexo", ["naosabe"])),
            "brand": ia_specs.get("brand", "Várias"),
            "name": prod['nome'].split(',')[0],
            "img": img_path,
            "emoji": ia_specs.get("emoji", "👟"),
            "tags": ",".join(ia_specs.get("tags", [])),
            "price": prod['preco'],
            "budget": ia_specs.get("budget", "300a600"),
            "levels": ",".join(ia_specs.get("levels", [])),
            "pisadas": ",".join(ia_specs.get("pisadas", [])),
            "terrenos": ",".join(ia_specs.get("terrenos", [])),
            "priors": ",".join(ia_specs.get("priors", [])),
            "distancias": ",".join(ia_specs.get("distancias", [])),
            "reason": ia_specs.get("reason", "Ótima escolha."),
            "link": affiliate_link
        })
        print("✔️ OK")
        time.sleep(4) # Pausa obrigatória da API Grátis do Gemini

    with open("amazon_tenis_catalogados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=planilha[0].keys() if planilha else [])
        if planilha: w.writeheader()
        w.writerows(planilha)

    print("\n🎉 SUCESSO! O arquivo 'amazon_tenis_catalogados.csv' foi gerado perfeitamente!")

if __name__ == "__main__":
    main()
