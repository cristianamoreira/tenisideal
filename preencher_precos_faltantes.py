#!/usr/bin/env python3
"""
preencher_precos_faltantes.py
------------------------------
🔍 Busca preços dos links de afiliado e preenche automaticamente no Google Sheets
"""

import json
import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import time
import re

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def conectar_planilha():
    """Conecta ao Google Sheets"""
    try:
        with open('credenciais.json', 'r') as f:
            credentials_dict = json.load(f)

        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(credentials)
        sheet = client.open_by_key(SHEET_ID).sheet1

        print("✅ Conectado ao Google Sheets com sucesso!")
        return sheet

    except Exception as e:
        print(f"❌ Erro ao conectar Google Sheets: {e}")
        return None

def extrair_preco_amazon(url):
    """Extrai preço da Amazon"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Procura por preço em várias variações
            price_patterns = [
                'span[data-a-color="price"]',
                'span.a-price-whole',
                '.a-price-whole',
            ]

            for pattern in price_patterns:
                element = soup.select_one(pattern)
                if element:
                    text = element.get_text(strip=True)
                    # Extrai número
                    match = re.search(r'[\d,\.]+', text)
                    if match:
                        return text

        return None
    except Exception as e:
        print(f"    ⚠️ Erro ao buscar Amazon: {e}")
        return None

def extrair_preco_netshoes(url):
    """Extrai preço da Netshoes"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Procura por preço
            price_elements = [
                soup.find('span', {'class': 'price'}),
                soup.find('span', {'data-testid': 'price'}),
                soup.find('div', {'class': 'product-price'}),
            ]

            for element in price_elements:
                if element:
                    text = element.get_text(strip=True)
                    if 'R$' in text or any(c.isdigit() for c in text):
                        return text

        return None
    except Exception as e:
        print(f"    ⚠️ Erro ao buscar Netshoes: {e}")
        return None

def extrair_preco_oficial(url):
    """Extrai preço da loja oficial"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Procura por preço genérico
            price_selectors = [
                'span[itemprop="price"]',
                '.product-price',
                '[data-price]',
                'span.price',
            ]

            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if any(c.isdigit() for c in text):
                        return text

        return None
    except Exception as e:
        print(f"    ⚠️ Erro ao buscar loja oficial: {e}")
        return None

def buscar_precos_do_produto(links):
    """Busca preços em todos os links do produto"""
    precos = {
        'amazon': None,
        'oficial': None,
        'netshoes': None
    }

    # Link Amazon
    if links.get('link_amazon') and links['link_amazon'].strip():
        url = links['link_amazon']
        # Expandir link encurtado se necessário
        if 'amzn.to' in url or 'amazon.com' in url:
            print(f"    🔍 Buscando em Amazon: {url}")
            preco = extrair_preco_amazon(url)
            if preco:
                precos['amazon'] = preco
                print(f"    ✅ Amazon: {preco}")

    # Link Netshoes
    if links.get('link_netshoes') and links['link_netshoes'].strip():
        url = links['link_netshoes']
        print(f"    🔍 Buscando em Netshoes: {url}")
        preco = extrair_preco_netshoes(url)
        if preco:
            precos['netshoes'] = preco
            print(f"    ✅ Netshoes: {preco}")

    # Link Loja Oficial
    if links.get('link_loja_oficial') and links['link_loja_oficial'].strip():
        url = links['link_loja_oficial']
        print(f"    🔍 Buscando em Loja Oficial: {url}")
        preco = extrair_preco_oficial(url)
        if preco:
            precos['oficial'] = preco
            print(f"    ✅ Loja Oficial: {preco}")

    time.sleep(1)  # Rate limiting
    return precos

def preencher_precos():
    """Identifica e preenche preços faltantes"""
    print("=" * 80)
    print("🔍 PREENCHEDOR DE PREÇOS FALTANTES - TENIS IDEAL")
    print("=" * 80 + "\n")

    # Conectar
    sheet = conectar_planilha()
    if not sheet:
        return False

    # Obter dados
    rows = sheet.get_all_values()
    header = rows[0]

    # Encontrar colunas
    try:
        idx_nome = header.index('nome')
        idx_marca = header.index('marca')
        idx_preco_amazon = header.index('preco_amazon')
        idx_preco_oficial = header.index('preco_loja_oficial')
        idx_preco_netshoes = header.index('preco_netshoes')
        idx_link_amazon = header.index('link_amazon')
        idx_link_oficial = header.index('link_loja_oficial')
        idx_link_netshoes = header.index('link_netshoes')
    except ValueError as e:
        print(f"❌ Coluna não encontrada: {e}")
        return False

    # Identificar produtos sem preço
    produtos_sem_preco = []

    for i in range(1, len(rows)):
        row = rows[i]

        preco_amazon = row[idx_preco_amazon].strip() if idx_preco_amazon < len(row) else ""
        preco_oficial = row[idx_preco_oficial].strip() if idx_preco_oficial < len(row) else ""
        preco_netshoes = row[idx_preco_netshoes].strip() if idx_preco_netshoes < len(row) else ""

        # Se todos os preços estão vazios ou inválidos
        if not preco_amazon and not preco_oficial and not preco_netshoes:
            nome = row[idx_nome].strip() if idx_nome < len(row) else ""
            marca = row[idx_marca].strip() if idx_marca < len(row) else ""

            if nome:
                produtos_sem_preco.append({
                    'row_idx': i + 1,  # +1 porque o Google Sheets começa em 1
                    'nome': nome,
                    'marca': marca,
                    'links': {
                        'link_amazon': row[idx_link_amazon].strip() if idx_link_amazon < len(row) else "",
                        'link_loja_oficial': row[idx_link_oficial].strip() if idx_link_oficial < len(row) else "",
                        'link_netshoes': row[idx_link_netshoes].strip() if idx_link_netshoes < len(row) else ""
                    }
                })

    print(f"📋 Encontrados {len(produtos_sem_preco)} produtos sem preço\n")

    # Buscar preços para cada produto
    atualizacoes = []

    for idx, produto in enumerate(produtos_sem_preco, 1):
        print(f"[{idx}/{len(produtos_sem_preco)}] {produto['marca']} - {produto['nome']}")

        precos = buscar_precos_do_produto(produto['links'])

        # Determinar melhor preço
        precos_validos = [p for p in precos.values() if p]
        if precos_validos:
            atualizacoes.append({
                'row': produto['row_idx'],
                'col_amazon': idx_preco_amazon + 1,
                'col_oficial': idx_preco_oficial + 1,
                'col_netshoes': idx_preco_netshoes + 1,
                'preco_amazon': precos['amazon'] or "",
                'preco_oficial': precos['oficial'] or "",
                'preco_netshoes': precos['netshoes'] or ""
            })
            print(f"  ✅ Encontrados preços para {produto['nome']}\n")
        else:
            print(f"  ⚠️ Nenhum preço encontrado para {produto['nome']}\n")

    # Atualizar Google Sheets
    if atualizacoes:
        print("\n💾 Atualizando Google Sheets...\n")

        for atualizacao in atualizacoes:
            try:
                if atualizacao['preco_amazon']:
                    sheet.update_cell(
                        atualizacao['row'],
                        atualizacao['col_amazon'],
                        atualizacao['preco_amazon']
                    )
                    print(f"  ✅ Linha {atualizacao['row']}: Amazon atualizado")

                if atualizacao['preco_oficial']:
                    sheet.update_cell(
                        atualizacao['row'],
                        atualizacao['col_oficial'],
                        atualizacao['preco_oficial']
                    )
                    print(f"  ✅ Linha {atualizacao['row']}: Loja Oficial atualizado")

                if atualizacao['preco_netshoes']:
                    sheet.update_cell(
                        atualizacao['row'],
                        atualizacao['col_netshoes'],
                        atualizacao['preco_netshoes']
                    )
                    print(f"  ✅ Linha {atualizacao['row']}: Netshoes atualizado")

                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"  ❌ Erro ao atualizar linha {atualizacao['row']}: {e}")

        print("\n" + "=" * 80)
        print(f"✅ {len(atualizacoes)} produtos atualizados no Google Sheets!")
        print("=" * 80)
    else:
        print("\n⚠️ Nenhum preço foi encontrado para preencher.")

    return True

if __name__ == "__main__":
    preencher_precos()
