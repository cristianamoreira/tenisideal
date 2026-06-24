#!/usr/bin/env python3
"""
sincronizar_precos.py
---------------------
🔄 Sincroniza preços do Google Sheets com shoes-fallback.json e shoes_data.js
Executa uma vez para atualizar todos os preços reais
"""

import json
import gspread
from google.oauth2.service_account import Credentials
import re

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"

def conectar_planilha():
    """Conecta ao Google Sheets"""
    try:
        with open('credenciais.json', 'r') as f:
            credentials_dict = json.load(f)

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )

        client = gspread.authorize(credentials)
        sheet = client.open_by_key(SHEET_ID).sheet1

        print("✅ Conectado ao Google Sheets com sucesso!")
        return sheet

    except Exception as e:
        print(f"❌ Erro ao conectar Google Sheets: {e}")
        return None

def extrair_preco(texto_preco):
    """Extrai valor numérico do preço (ex: 'R$ 1.999,99' -> 1999.99)"""
    if not texto_preco or texto_preco.strip() == '':
        return 0

    # Remove 'R$', espaços
    cleaned = texto_preco.replace('R$', '').strip()
    # Remove ponto de milhar e converte vírgula decimal
    cleaned = cleaned.replace('.', '').replace(',', '.')

    try:
        return float(cleaned)
    except:
        return 0

def formatar_preco(valor):
    """Formata número para R$ 1.234,56"""
    if valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')

def sincronizar_precos():
    """Sincroniza preços do Google Sheets com arquivos locais"""
    print("=" * 70)
    print("🔄 SINCRONIZADOR DE PREÇOS - TENIS IDEAL")
    print("=" * 70 + "\n")

    # Conectar ao Google Sheets
    sheet = conectar_planilha()
    if not sheet:
        return False

    # Obter dados da planilha
    rows = sheet.get_all_values()
    header = rows[0]

    # Encontrar índices das colunas
    try:
        idx_product_id = header.index('product_id')
        idx_brand = header.index('marca')
        idx_name = header.index('nome')
        idx_price_amazon = header.index('preco_amazon')
        idx_price_oficial = header.index('preco_loja_oficial')
        idx_price_netshoes = header.index('preco_netshoes')
        idx_link_amazon = header.index('link_amazon')
        idx_link_oficial = header.index('link_loja_oficial')
        idx_link_netshoes = header.index('link_netshoes')
    except ValueError as e:
        print(f"❌ Coluna não encontrada: {e}")
        return False

    # Carregar dados atuais
    with open('shoes-fallback.json', 'r', encoding='utf-8') as f:
        shoes = json.load(f)

    print(f"📋 Processando {len(shoes)} produtos...\n")

    updated_count = 0
    zero_price_count = 0

    # Atualizar preços
    for row_idx in range(1, len(rows)):
        if row_idx - 1 >= len(shoes):
            break

        row = rows[row_idx]
        shoe = shoes[row_idx - 1]

        product_id = row[idx_product_id] if idx_product_id < len(row) else ""
        brand = row[idx_brand] if idx_brand < len(row) else ""
        name = row[idx_name] if idx_name < len(row) else ""

        price_amazon_str = row[idx_price_amazon] if idx_price_amazon < len(row) else ""
        price_oficial_str = row[idx_price_oficial] if idx_price_oficial < len(row) else ""
        price_netshoes_str = row[idx_price_netshoes] if idx_price_netshoes < len(row) else ""

        # Extrair valores numéricos
        price_amazon = extrair_preco(price_amazon_str)
        price_oficial = extrair_preco(price_oficial_str)
        price_netshoes = extrair_preco(price_netshoes_str)

        # Escolher melhor preço (menor válido)
        prices_validos = [p for p in [price_amazon, price_oficial, price_netshoes] if p > 0]
        melhor_preco = min(prices_validos) if prices_validos else 0

        # Atualizar shoe
        shoe['price'] = melhor_preco
        shoe['price_formatted'] = formatar_preco(melhor_preco)

        # Atualizar links de afiliado
        if not shoe.get('affiliate_links'):
            shoe['affiliate_links'] = {}

        if price_amazon > 0:
            if isinstance(shoe['affiliate_links'].get('amazon'), dict):
                shoe['affiliate_links']['amazon']['price'] = price_amazon
            else:
                shoe['affiliate_links']['amazon'] = price_amazon

        if price_oficial > 0:
            if isinstance(shoe['affiliate_links'].get('oficial'), dict):
                shoe['affiliate_links']['oficial']['price'] = price_oficial
            else:
                shoe['affiliate_links']['oficial'] = price_oficial

        if price_netshoes > 0:
            if isinstance(shoe['affiliate_links'].get('netshoes'), dict):
                shoe['affiliate_links']['netshoes']['price'] = price_netshoes
            else:
                shoe['affiliate_links']['netshoes'] = price_netshoes

        if melhor_preco > 0:
            updated_count += 1
            print(f"✅ [{row_idx:3d}] {brand:12} {name[:30]:30} | R$ {melhor_preco:8.2f}")
        else:
            zero_price_count += 1
            print(f"⚠️  [{row_idx:3d}] {brand:12} {name[:30]:30} | SEM PREÇO")

    # Salvar arquivos
    print("\n💾 Salvando arquivos...\n")

    # Salvar shoes-fallback.json
    with open('shoes-fallback.json', 'w', encoding='utf-8') as f:
        json.dump(shoes, f, ensure_ascii=False, indent=2)
    print("✅ shoes-fallback.json atualizado")

    # Salvar shoes_data.js
    with open('frontend/shoes_data.js', 'w', encoding='utf-8') as f:
        f.write("// Sincronizado de Google Sheets\nvar SHOES = ")
        f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
        f.write(";")
    print("✅ frontend/shoes_data.js atualizado")

    print("\n" + "=" * 70)
    print("✅ SINCRONIZAÇÃO COMPLETA!")
    print("=" * 70)
    print(f"✅ Preços atualizados: {updated_count}")
    print(f"⚠️  Produtos sem preço: {zero_price_count}")
    print(f"📦 Total de produtos: {len(shoes)}")

    return True

if __name__ == "__main__":
    sincronizar_precos()
