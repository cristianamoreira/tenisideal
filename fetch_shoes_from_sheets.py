#!/usr/bin/env python3
import json
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"

def safe_float(val):
    """Converte string para float com segurança"""
    if not val or val == '-':
        return 0
    try:
        # Remove R$, espaços, etc
        clean = str(val).replace('R$', '').replace(',', '.').strip()
        return float(clean)
    except:
        return 0

def fetch_shoes():
    print("=" * 60)
    print("📥 Sincronizando Google Sheets → shoes_data.js")
    print("=" * 60 + "\n")
    
    creds = Credentials.from_service_account_file('credenciais.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)
    ws = sheet.worksheets()[0]
    
    all_values = ws.get_all_values()
    headers = all_values[0]
    
    shoes = []
    for row in all_values[1:]:
        row_dict = {h: (row[i] if i < len(row) else '') for i, h in enumerate(headers) if h}
        
        if row_dict.get('ativo', '').lower() != 'sim':
            continue
        if not row_dict.get('nome'):
            continue
        
        # Pegar melhor preço disponível
        price = safe_float(row_dict.get('preco_loja_oficial', 0)) or safe_float(row_dict.get('preco_amazon', 0)) or safe_float(row_dict.get('preco_netshoes', 0))
        
        shoe = {
            "brand": row_dict.get('marca', '').upper(),
            "name": row_dict.get('nome', ''),
            "slug": row_dict.get('product_id', ''),
            "sexo": [s.strip() for s in str(row_dict.get('sexo', '')).split('|') if s.strip()] or ['unissex'],
            "budget": row_dict.get('budget', ''),
            "price": price,
            "price_formatted": f"R$ {price:,.2f}".replace(',', '@').replace('.', ',').replace('@', '.'),
            "levels": [l.strip() for l in str(row_dict.get('nível', '')).split('|') if l.strip()],
            "pisada": [p.strip() for p in str(row_dict.get('pisada', '')).split('|') if p.strip()],
            "terreno": [t.strip() for t in str(row_dict.get('terreno', '')).split('|') if t.strip()],
            "distancia": [],
            "photo": row_dict.get('img', ''),
            "affiliate_links": {},
            "tags": [t.strip() for t in str(row_dict.get('tags', '')).split('|') if t.strip()],
            "description": row_dict.get('razão', ''),
            "reason": row_dict.get('razão', ''),
        }
        
        # Links de afiliado
        if row_dict.get('link_amazon') and row_dict.get('link_amazon') != '-':
            shoe['affiliate_links']['amazon'] = {
                'url': row_dict.get('link_amazon'),
                'price': safe_float(row_dict.get('preco_amazon', 0))
            }
        if row_dict.get('link_loja_oficial') and row_dict.get('link_loja_oficial') != '-':
            shoe['affiliate_links']['oficial'] = {
                'url': row_dict.get('link_loja_oficial'),
                'price': safe_float(row_dict.get('preco_loja_oficial', 0))
            }
        if row_dict.get('link_netshoes') and row_dict.get('link_netshoes') != '-':
            shoe['affiliate_links']['netshoes'] = {
                'url': row_dict.get('link_netshoes'),
                'price': safe_float(row_dict.get('preco_netshoes', 0))
            }
        
        shoes.append(shoe)
    
    # Salvar
    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write("// Sincronizado de Google Sheets\nvar SHOES = ")
        f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
        f.write(";")
    
    print(f"✅ {len(shoes)} produtos sincronizados!\n")
    print("=" * 60)
    print("✅ SUCESSO!")
    print("=" * 60)

if __name__ == "__main__":
    fetch_shoes()
