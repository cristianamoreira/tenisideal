import json
import sys
import re
import pandas as pd

FILE_PATH = "tenisideal-catalogo atualizada.xlsx"

def parse_list(val):
    if not val or pd.isna(val) or val == "":
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

def extract_numeric_price(price_val):
    if pd.isna(price_val) or price_val == "":
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
    
    # Se for string, limpa e tenta converter
    s = str(price_val)
    # Extrai o valor numérico de strings como "R$ 899,90" -> 899.90
    clean_str = re.sub(r'[^\d,.-]', '', s)
    if not clean_str:
        return 0.0
    
    # Lógica para detectar se o separador decimal é vírgula ou ponto
    # Se houver vírgula e ponto, assume ponto como milhar e vírgula como decimal (BR)
    if ',' in clean_str and '.' in clean_str:
        clean_str = clean_str.replace('.', '').replace(',', '.')
    # Se houver apenas vírgula, assume que é decimal (BR)
    elif ',' in clean_str:
        clean_str = clean_str.replace(',', '.')
    
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
        df = pd.read_excel(FILE_PATH, header=1)
        # Use fillna("") instead of relying on it later
        df = df.fillna("")
        reader = df.to_dict('records')
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
                        val = row[k]
                        if isinstance(val, str):
                            return val.strip()
                        return val
            return ""

        brand = get_val("marca", "brand")
        name = get_val("nome do tênis", "name")
        
        if not name or not brand or name == "" or brand == "":
            continue
            
        # Parse Affiliate Links & Specific Prices
        affiliate_links = {}
        link_amazon = get_val("link_amazon", "amazon")
        link_oficial = get_val("link_oficial", "oficial")
        link_netshoes = get_val("link_netshoes", "netshoes")
        
        price_amazon = extract_numeric_price(get_val("preco_amazon", "price_amazon"))
        price_oficial = extract_numeric_price(get_val("preco_oficial", "price_oficial"))
        price_netshoes = extract_numeric_price(get_val("preco_netshoes", "price_netshoes"))

        if link_amazon and link_amazon != "" and link_amazon != "-": 
            affiliate_links["amazon"] = {"url": link_amazon, "price": price_amazon}
        if link_oficial and link_oficial != "" and link_oficial != "-": 
            affiliate_links["oficial"] = {"url": link_oficial, "price": price_oficial}
        if link_netshoes and link_netshoes != "" and link_netshoes != "-": 
            affiliate_links["netshoes"] = {"url": link_netshoes, "price": price_netshoes}

        # Determinamos o melhor preço principal a partir das ofertas encontradas
        best_price = 0.0
        best_price_str = ""
        
        valid_prices = [v["price"] for v in affiliate_links.values() if v["price"] > 0]
        if valid_prices:
            best_price = min(valid_prices)
            best_price_str = f"R$ {best_price:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        else:
            # Fallback para o preço geral da planilha se não houver links/preços específicos
            price_raw = get_val("price", "r$ 000", "preço")
            best_price = extract_numeric_price(price_raw)
            best_price_str = price_raw if best_price > 0 else ""

        # Calcula range se budget estiver vazio, senão usa o que está na planilha
        budget = get_val("price_range", "budget")
        price_range = budget if budget and budget != "" else calculate_price_range(best_price)

        # Preenche outras propriedades
        gender = get_val("gender", "sexo")
        
        # Parse Imagens
        img_main = get_val("url_imagem", "img")
        if img_main and "amzn.to" in img_main:
            # Se for link encurtado da Amazon, não é imagem. Força placeholder.
            img_main = "imgs/placeholder.jpg"
            
        images = parse_list(get_val("images", ""))
        if not images and img_main: 
            images = [img_main]
        elif images:
            # Limpa links de afiliados das imagens se houver
            images = [img if "amzn.to" not in img else "imgs/placeholder.jpg" for img in images]

        shoe = {
            "brand": brand,
            "model": get_val("model", name),
            "version": get_val("version", ""), 
            "name": name,
            "slug": generate_slug(brand, name),
            "category": get_val("category", "corrida"),
            "sexo": parse_list(gender),
            "discipline": parse_list(get_val("discipline", "terrenos")),
            
            "price": best_price,
            "price_formatted": best_price_str,
            "budget": price_range,
            
            "drop": get_val("drop", ""),
            "weight": get_val("weight", ""),
            
            "levels": parse_list(get_val("runner_level", "levels")),
            "terrenos": parse_list(get_val("terrain", "terrenos")),
            "pisadas": parse_list(get_val("pronation", "pisadas")),
            
            "priors": parse_list(get_val("feature", "priors")),
            
            "technologies": parse_list(get_val("technologies", "")),
            
            "affiliate_links": affiliate_links,
            
            "rating": get_val("rating", ""),
            "reviews_count": get_val("reviews_count", ""),
            "release_year": get_val("release_year", ""),
            "is_best_seller": str(get_val("popular", "is_best_seller")).lower() in ['sim', 'true', '1'],
            
            "images": images,
            "emoji": get_val("emoji", "👟") or "👟",
            "tags": parse_list(get_val("tags", "")),
            
            "description": get_val("reason", "description"),
            "reason": get_val("reason", "description"),
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
