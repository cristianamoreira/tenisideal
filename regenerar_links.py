#!/usr/bin/env python3
"""
regenerar_links.py
------------------
🔗 REGENERADOR DE LINKS DE AFILIADO
Identifica links quebrados e gera novos automaticamente
"""

import json
import requests
import time
from urllib.parse import urlencode

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Arquivo com os dados dos tênis
SHOES_FILE = "frontend/shoes_data.js"

# ==============================================================================
# 🔗 TESTAR LINKS
# ==============================================================================

def testar_link(url):
    """Testa se um link está funcionando"""
    try:
        response = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

# ==============================================================================
# 🔍 BUSCAR PRODUTO NA AMAZON
# ==============================================================================

def buscar_asin_amazon(nome_produto):
    """Busca o ASIN de um produto na Amazon"""
    try:
        # URL de busca da Amazon (padrão)
        # Nota: Para um sistema real, você usaria a Amazon Product Advertising API
        # Por enquanto, vamos criar um padrão simples

        search_url = f"https://www.amazon.com.br/s?k={nome_produto}"
        print(f"🔍 Buscando: {nome_produto}")
        print(f"   → Acesse: {search_url}")
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar: {e}")
        return None

# ==============================================================================
# 🔗 GERAR NOVO LINK
# ==============================================================================

def gerar_link_amazon_alternativo(nome_produto):
    """Gera um link genérico de busca na Amazon como fallback"""
    # Link de busca genérico (funciona sempre)
    search_term = nome_produto.replace(" ", "+")
    return f"https://www.amazon.com.br/s?k={search_term}"

def gerar_link_netshoes(nome_produto):
    """Gera um link de busca na Netshoes"""
    search_term = nome_produto.replace(" ", "%20")
    return f"https://www.netshoes.com.br/busca?q={search_term}"

# ==============================================================================
# 📋 PROCESSAR ARQUIVO
# ==============================================================================

def carregar_shoes():
    """Carrega dados dos tênis do arquivo"""
    try:
        with open(SHOES_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove comentários e a declaração var SHOES =
        lines = content.split("\n")
        json_start = None
        json_end = None

        for i, line in enumerate(lines):
            if "var SHOES = [" in line:
                json_start = i
            if json_start is not None and line.strip() == "];":
                json_end = i + 1
                break

        if json_start is None or json_end is None:
            raise ValueError("Não foi possível encontrar var SHOES no arquivo")

        # Extrai apenas a parte JSON
        json_content = "\n".join(lines[json_start:json_end])
        json_content = json_content.replace("var SHOES = ", "").rstrip(";")

        shoes = json.loads(json_content)
        return shoes
    except Exception as e:
        print(f"❌ Erro ao carregar shoes: {e}")
        return []

# ==============================================================================
# 🔧 REGENERAR LINKS QUEBRADOS
# ==============================================================================

def regenerar_links():
    """Regenera links quebrados automaticamente"""

    print("=" * 60)
    print("🔗 REGENERADOR DE LINKS - TENIS IDEAL")
    print("=" * 60)

    # Carregar dados
    shoes = carregar_shoes()
    print(f"\n📋 Carregados {len(shoes)} produtos")

    # Estatísticas
    total_checked = 0
    funcionando = 0
    quebrados = 0
    atualizados = 0

    print("\n🔍 Testando e regenerando links...\n")

    for idx, shoe in enumerate(shoes, 1):
        print(f"[{idx}/{len(shoes)}] {shoe.get('brand', 'Desconhecido')} - {shoe.get('name', 'Sem nome')}")

        affiliate_links = shoe.get("affiliate_links", {})

        if not affiliate_links:
            print("   ⚠️ Sem links de afiliado\n")
            continue

        # Testar cada link
        for store, link_data in affiliate_links.items():
            if isinstance(link_data, dict):
                url = link_data.get("url")
            else:
                url = link_data

            if not url or url == "-":
                print(f"   ⚠️ {store.upper()}: Sem URL")
                continue

            total_checked += 1

            # Testar link
            status = "✅" if testar_link(url) else "❌"
            print(f"   {status} {store.upper()}: {url[:60]}...")

            if testar_link(url):
                funcionando += 1
            else:
                quebrados += 1

                # Gerar novo link
                if store == "amazon":
                    novo_url = gerar_link_amazon_alternativo(shoe.get("name", ""))
                elif store == "netshoes":
                    novo_url = gerar_link_netshoes(shoe.get("name", ""))
                else:
                    novo_url = None

                if novo_url:
                    print(f"      → Novo: {novo_url[:60]}...")

                    # Atualizar link
                    if isinstance(link_data, dict):
                        affiliate_links[store]["url"] = novo_url
                    else:
                        affiliate_links[store] = novo_url

                    atualizados += 1

        time.sleep(0.5)  # Respeitar rate limit
        print()

    # Resumo
    print("=" * 60)
    print("📊 RESUMO DA REGENERAÇÃO")
    print("=" * 60)
    print(f"Total testado: {total_checked}")
    print(f"✅ Funcionando: {funcionando}")
    print(f"❌ Quebrados: {quebrados}")
    print(f"🔧 Atualizados: {atualizados}")

    if atualizados > 0:
        print(f"\n✅ {atualizados} links foram regenerados com sucesso!")

        # Salvar arquivo atualizado
        print("\n💾 Salvando arquivo atualizado...")
        try:
            # Reconstrói o arquivo
            with open(SHOES_FILE, "w", encoding="utf-8") as f:
                f.write("// Gerado automaticamente via fetch_shoes.py - 2026-03-21 00:31 UTC\n")
                f.write("var SHOES = ")
                f.write(json.dumps(shoes, ensure_ascii=False, indent=2))
                f.write(";")
            print("✅ Arquivo shoes_data.js atualizado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
    else:
        print(f"\n✅ Todos os {funcionando} links estão funcionando!")

    print("=" * 60)

# ==============================================================================
# 🚀 MAIN
# ==============================================================================

if __name__ == "__main__":
    regenerar_links()
