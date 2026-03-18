import csv
import google.generativeai as genai
import os
import json
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("ERRO: Configure a variável de ambiente GEMINI_API_KEY")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_ai_data(name, brand):
    prompt = f"""
Você é um especialista em tênis de corrida. Analise o modelo {brand} {name}.
Retorne OBRIGATORIAMENTE um JSON válido com a seguinte estrutura e preenchendo as tags mais adequadas.
Restrições estritas:
-"levels": array com strings (escolha entre: "iniciante", "intermediario", "avancado")
-"pisadas": array com strings (escolha entre: "neutra", "pronada", "supinada")
-"terrenos": array com strings (escolha entre: "asfalto", "pista", "esteira", "trilha", "mista")
-"priors": array com strings (escolha entre: "amortecimento", "leveza", "durabilidade", "custo")
-"distancias": array com strings (escolha entre: "curta", "media", "longa", "maratona")

Exemplo esperado:
{{
  "levels": ["iniciante", "intermediario"],
  "pisadas": ["neutra", "supinada"],
  "terrenos": ["asfalto", "esteira"],
  "priors": ["amortecimento"],
  "distancias": ["media", "longa"]
}}
Vá direto ao ponto e não coloque blocos markdown.
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Erro IA para {name}: {e}")
        return None

def main():
    # As colunas da planilha publicadas pelo google sheets sem cabeçalho amigável, indexadas por número
    with open('data.csv', 'r', encoding='utf-8') as f:
        # A planilha não tem headers na 1a linha bons, criaremos hardcoded base no index.html JS parse function
        # cols[0]=sexo, 1=brand, 2=name, 3=img, 4=emoji, 5=tags, 6=price, 7=budget, 8=levels, 9=pisadas
        # 10=terrenos, 11=priors, 12=reason, 13=link, 14=link2, 15=popular, 16=distancias
        fieldnames = [
            "sexo", "brand", "name", "img", "emoji", "tags", "price", "budget", 
            "levels", "pisadas", "terrenos", "priors", "reason", "link", "link2", "popular", "distancias"
        ]
        reader = list(csv.DictReader(f, fieldnames=fieldnames))
        # Omit first row (it should be the real headers from google sheets)
        headers_row = reader[0]
        data_rows = reader[1:]
        
    updated = []
    print(f"Processando {len(data_rows)} tênis...")
    
    for row in data_rows:
        if not row["pisadas"].strip() or not row["terrenos"].strip():
            print(f"Buscando IA para: {row['brand']} {row['name']}...")
            ai_data = get_ai_data(row['name'], row['brand'])
            if ai_data:
                row["levels"] = ",".join(ai_data.get("levels", []))
                row["pisadas"] = ",".join(ai_data.get("pisadas", []))
                row["terrenos"] = ",".join(ai_data.get("terrenos", []))
                row["priors"] = ",".join(ai_data.get("priors", []))
                row["distancias"] = ",".join(ai_data.get("distancias", []))
            time.sleep(4) 
        updated.append(row)
        
    with open('data_updated.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated)
        
    print("Arquivo 'data_updated.csv' gerado.")

if __name__ == "__main__":
    main()
