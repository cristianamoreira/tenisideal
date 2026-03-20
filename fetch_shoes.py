import csv
import json
import sys
import re
import pandas as pd

FILE_PATH = "tenisideal-catalogo atualizada.xlsx"

def parse_list(val):
    if not val or pd.isna(val):
        return []
    # Divide por vírgula ou barra (|) e remove espaços em branco
    return [re.sub(r'^\s*-\s*', '', str(v).strip()) for v in re.split(r'[,|]', str(val)) if str(v).strip()]

def calculate_price_range(price_num):
    if price_num < 300:
        return "ate300"
    elif 300 <= price_num <= 600:
        return "300a600"
    elif 600 < price_num <= 1000:
        return "600a1000"
    else:
        return "acima1000"

def extract_numeric_price(price_str):
    if pd.isna(price_str):
        return 0.0
    # Extrai o valor numérico de strings como "R$ 899,90" -> 899.90
    clean_str = re.sub(r'[^\d,.-]', '', str(price_str))
    if not clean_str:
        return 0.0
    # Substitui ponto de milhar se houver (ex: 1.200,50 -> 1200,50) e vírgula por ponto
    clean_str = clean_str.replace('.', '').replace(',', '.')
    try:
        return float(clean_str)
    except:
        return 0.0

def generate_slug(brand, name):
    # Gera slug amigável: "Mizuno", "Wave Rider 29" -> "mizuno-wave-rider-29"
    full_name = f"{brand} {name}".lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', full_name)
    slug = re.sub(r'[\s-]+', '-', slug).strip('-')
    return slug

def main():
    try:
        df = pd.read_excel(FILE_PATH)
        # Converte para lista de dicionários lidando com NaN
        reader = df.fillna("").to_dict('records')
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel local: {e}")
        sys.exit(1)

    shoes = []
    
    for row in reader:
        # Pega as chaves reais
        keys = list(row.keys())
        if not keys: continue

        # Função auxiliar para buscar chaves, ignorando maiúsculas/minúsculas e espaços extras
        def get_val(*possible_keys):
            for pk in possible_keys:
                for k in keys:
                    if pk.lower() in k.lower().strip():
                        return row[k].strip()
            return ""

        brand = get_val("brand", "marca")
        name = get_val("name", "nome do tênis")
        
        if not name or not brand:
            continue
            
        # Parse Price
        price_str = get_val("price", "r$ 000", "preço")
        price_num = extract_numeric_price(price_str)
        # Calcula range se budget estiver vazio, senão usa o que está na planilha
        budget = get_val("budget", "ate300 / 300a600 / 600a1000 / acima1000")
        price_range = budget if budget else calculate_price_range(price_num)

        # Parse Affiliate Links & Specific Prices
        affiliate_links = {}
        link_amazon = get_val("link_amazon", "amazon", "url amazon")
        link_oficial = get_val("link_oficial", "oficial marca", "afiliado mizuno", "awin", "link loja", "loja oficial")
        link_netshoes = get_val("link_netshoes", "netshoes")
        
        price_amazon = extract_numeric_price(get_val("price_amazon", "preco_amazon", "preço amazon"))
        price_oficial = extract_numeric_price(get_val("price_oficial", "preco_oficial", "preço oficial", "site oficial", "valor oficial", "oficial"))
        price_netshoes = extract_numeric_price(get_val("price_netshoes", "preco_netshoes", "preço netshoes"))
        
        if link_amazon and link_amazon != "-": 
            affiliate_links["amazon"] = {"url": link_amazon, "price": price_amazon}
        if link_oficial and link_oficial != "-": 
            affiliate_links["oficial"] = {"url": link_oficial, "price": price_oficial}
        if link_netshoes and link_netshoes != "-": 
            affiliate_links["netshoes"] = {"url": link_netshoes, "price": price_netshoes}

        # Preenche outras propriedades migrando de colunas velhas para novas ou lendo direto das novas se já existirem
        gender = get_val("gender", "sexo", "masculino|feminino|outro")
        
        # Parse Imagens
        img_main = get_val("img", "url da imagem")
        images = parse_list(get_val("images", img_main))
        if not images and img_main: images = [img_main]

        shoe = {
            "brand": brand,
            "model": get_val("model", name), # Se não houver coluna model, usa name
            "version": get_val("version", ""), 
            "name": name,
            "slug": get_val("slug", generate_slug(brand, name)),
            "category": get_val("category", "corrida"),
            "sexo": parse_list(gender), # Alterado de 'gender' para 'sexo'
            "discipline": parse_list(get_val("discipline", "disciplina")),
            
            "price": price_num,
            "price_formatted": price_str,
            "budget": price_range, # Alterado de 'price_range' para 'budget'
            
            "drop": get_val("drop", ""),
            "weight": get_val("weight", ""),
            
            "levels": parse_list(get_val("levels", "iniciante|intermediario|avancado")),
            "terrenos": parse_list(get_val("terrain", "terrenos", "asfalto|trilha|pista|esteira|mista")), # Alterado de 'terrain' para 'terrenos'
            "pisadas": parse_list(get_val("pronation", "pisadas", "neutra|pronada|supinada|naosabe")), # Alterado de 'pronation' para 'pisadas'
            
            "priors": parse_list(get_val("priors", "amortecimento|leveza|durabilidade|custo")),
            
            "technologies": parse_list(get_val("technologies", "")),
            
            "affiliate_links": affiliate_links,
            
            "rating": get_val("rating", ""),
            "reviews_count": get_val("reviews_count", ""),
            "release_year": get_val("release_year", ""),
            "is_best_seller": str(get_val("is_best_seller", "popular")).lower() in ['sim', 'true', '1'],
            
            "images": images,
            "emoji": get_val("emoji", "👟") or "👟",
            "tags": parse_list(get_val("tags", "tag1|tag2")),
            
            "description": get_val("description", "reason", "motivo"),
            "reason": get_val("reason", "description", "motivo"), # Adicionado 'reason' explicito
            "pros": parse_list(get_val("pros", "")),
            "cons": parse_list(get_val("cons", ""))
        }

        shoes.append(shoe)

    json_data = json.dumps(shoes, indent=2, ensure_ascii=False)
    js_content = f"// Gerado automaticamente via fetch_shoes.py\nvar SHOES = {json_data};\n"

    try:
        with open("shoes_data.js", "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"Sucesso! {len(shoes)} tênis catalogados e salvos em shoes_data.js com o novo formato.")
    except Exception as e:
        print(f"Erro salvando JS: {e}")

if __name__ == "__main__":
    main()
