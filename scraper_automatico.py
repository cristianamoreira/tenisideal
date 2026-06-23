#!/usr/bin/env python3
"""
scraper_automatico.py
---------------------
🚀 SCRAPER AUTOMÁTICO PARA GITHUB ACTIONS
Pega URLs da planilha Google Sheets e atualiza preços automaticamente
Sem input do usuário - roda 100% automático!
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================
SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"

# Credenciais via variável de ambiente (GitHub Actions)
CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ==============================================================================
# 🔗 CONEXÃO COM GOOGLE SHEETS
# ==============================================================================
def conectar_planilha():
    """Conecta ao Google Sheets usando credenciais de variável de ambiente ou arquivo"""
    try:
        credentials_dict = None

        # Tenta ler de variável de ambiente primeiro
        if CREDENTIALS_JSON:
            credentials_dict = json.loads(CREDENTIALS_JSON)
            print("✅ Credenciais carregadas de variável de ambiente")
        # Fallback: tenta ler do arquivo credenciais.json
        elif os.path.exists("credenciais.json"):
            with open("credenciais.json", "r") as f:
                credentials_dict = json.load(f)
            print("✅ Credenciais carregadas do arquivo credenciais.json")
        else:
            print("❌ Erro: GOOGLE_CREDENTIALS não configurado e arquivo credenciais.json não encontrado")
            return None

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

# ==============================================================================
# 📋 OBTER URLS DA PLANILHA
# ==============================================================================
def obter_urls_para_scraping(sheet):
    """Retorna lista de URLs que precisam atualização"""
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            return []

        headers = [h.strip().lower() for h in all_values[0]]

        # Procura coluna de URLs (pode ser "link_amazon", "url", etc)
        url_col_idx = None
        for idx, header in enumerate(headers):
            if "link" in header or "url" in header:
                url_col_idx = idx
                break

        if url_col_idx is None:
            print("⚠️ Coluna de URL não encontrada")
            return []

        # Coleta URLs (ignora linhas vazias)
        urls = []
        for row in all_values[1:]:
            if url_col_idx < len(row) and row[url_col_idx].strip():
                urls.append(row[url_col_idx].strip())

        print(f"📋 Encontradas {len(urls)} URLs para atualizar")
        return urls

    except Exception as e:
        print(f"❌ Erro ao obter URLs: {e}")
        return []

# ==============================================================================
# 💰 EXTRAIR PREÇO DE UMA URL
# ==============================================================================
def extrair_preco(url):
    """Tenta extrair preço de uma página HTML"""
    try:
        response = requests.get(url, headers=HEADERS_HTTP, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Procura por padrões comuns de preço
        price_patterns = [
            r'R\$\s*[\d.,]+',
            r'\d+,\d{2}',
            r'price.*?[\d.,]+',
        ]

        # Tenta encontrar em atributos data-price, data-value, etc
        for attr in ['data-price', 'data-value', 'price', 'value']:
            for tag in soup.find_all(True, {attr: True}):
                if tag.get(attr):
                    return str(tag.get(attr))

        # Tenta encontrar em texto
        text = soup.get_text()
        for pattern in price_patterns:
            import re
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    except Exception as e:
        print(f"⚠️ Erro ao extrair preço de {url}: {e}")
        return None

# ==============================================================================
# 🤖 USAR GEMINI PARA CLASSIFICAR
# ==============================================================================
def classificar_com_gemini(nome_tenis):
    """Usa Gemini para classificar o tênis (nível, pisada, etc)"""
    try:
        if not GEMINI_API_KEY:
            print("⚠️ Gemini API não configurado")
            return {}

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        Analise este nome de tênis: "{nome_tenis}"

        Retorne JSON com:
        - nivel: iniciante, intermediario ou avancado
        - pisada: neutra, pronada, supinada ou naosabe
        - terreno: asfalto, trilha ou esteira

        Exemplo: {{"nivel": "intermediario", "pisada": "neutra", "terreno": "asfalto"}}
        """

        response = model.generate_content(prompt)

        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        return {}

    except Exception as e:
        print(f"⚠️ Erro Gemini: {e}")
        return {}

# ==============================================================================
# 📤 ATUALIZAR PLANILHA
# ==============================================================================
def atualizar_planilha(sheet, urls_precos):
    """Atualiza preços na planilha"""
    try:
        all_values = sheet.get_all_values()
        headers = [h.strip().lower() for h in all_values[0]]

        # Encontra coluna de preço
        preco_col_idx = None
        for idx, header in enumerate(headers):
            if "preco" in header or "price" in header:
                preco_col_idx = idx
                break

        if preco_col_idx is None:
            print("⚠️ Coluna de preço não encontrada")
            return

        # Atualiza preços
        updates = []
        for url, preco in urls_precos.items():
            # Encontra a linha com essa URL
            for row_idx, row in enumerate(all_values[1:], start=2):
                if row_idx - 1 < len(row) and url in row:
                    # Atualiza o preço
                    cell_ref = f"{chr(64 + preco_col_idx + 1)}{row_idx}"
                    updates.append({"range": cell_ref, "values": [[preco]]})

        if updates:
            for update in updates:
                try:
                    sheet.update(update["range"], update["values"])
                    print(f"✅ Preço atualizado: {update['range']}")
                except Exception as e:
                    print(f"⚠️ Erro ao atualizar {update['range']}: {e}")

        print(f"✅ {len(updates)} preços atualizados na planilha")

    except Exception as e:
        print(f"❌ Erro ao atualizar planilha: {e}")

# ==============================================================================
# 🚀 MAIN - EXECUÇÃO AUTOMÁTICA
# ==============================================================================
def main():
    print("=" * 50)
    print("🚀 SCRAPER AUTOMÁTICO - TENIS IDEAL")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. Conectar
    sheet = conectar_planilha()
    if not sheet:
        print("❌ Falha ao conectar. Encerrando.")
        sys.exit(1)

    # 2. Obter URLs
    urls = obter_urls_para_scraping(sheet)
    if not urls:
        print("❌ Nenhuma URL encontrada. Encerrando.")
        sys.exit(1)

    # 3. Extrair preços
    print("\n🕷️ Iniciando extração de preços...")
    urls_precos = {}
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Processando: {url[:50]}...")
        preco = extrair_preco(url)
        if preco:
            urls_precos[url] = preco
            print(f"   ✅ Preço encontrado: {preco}")
        else:
            print(f"   ⚠️ Preço não encontrado")
        time.sleep(1)  # Respeitar rate limit

    # 4. Atualizar planilha
    print("\n📤 Atualizando planilha...")
    if urls_precos:
        atualizar_planilha(sheet, urls_precos)
    else:
        print("⚠️ Nenhum preço foi extraído")

    print("\n" + "=" * 50)
    print("✅ SCRAPER AUTOMÁTICO CONCLUÍDO COM SUCESSO!")
    print("=" * 50)

if __name__ == "__main__":
    main()
