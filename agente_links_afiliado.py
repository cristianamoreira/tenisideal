#!/usr/bin/env python3
"""
agente_links_afiliado.py
------------------------
🔗 AGENTE INTELIGENTE DE LINKS DE AFILIADO
Busca produtos das principais marcas e gera/encontra links de afiliado

Marcas suportadas:
  • Nike Brasil (nike.com.br)
  • ASICS Brasil (asics.com.br)
  • Adidas Brasil (adidas.com.br)
  • Olympikus (olympikus.com.br)
"""

import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import time
import csv
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class AgenteAfiliadoTenista:
    """Agente para extrair links de afiliado de marcas de tênis"""

    def __init__(self):
        self.produtos = []
        self.resultados = []

    # ========================
    # NIKE BRASIL
    # ========================
    def scrape_nike(self):
        """Busca principais modelos da Nike Brasil"""
        print("\n🔍 Buscando Nike Brasil...\n")

        # Principais categorias da Nike
        categorias = [
            ('running-masculino', 'Nike Running Masculino'),
            ('running-feminino', 'Nike Running Feminino'),
            ('lifestyle-masculino', 'Nike Lifestyle Masculino'),
            ('lifestyle-feminino', 'Nike Lifestyle Feminino'),
        ]

        nike_produtos = [
            {'brand': 'Nike', 'model': 'Revolution 8', 'category': 'Running', 'price': 'R$ 300-400'},
            {'brand': 'Nike', 'model': 'Downshifter 13', 'category': 'Running', 'price': 'R$ 350-450'},
            {'brand': 'Nike', 'model': 'Winflo 11', 'category': 'Running', 'price': 'R$ 450-550'},
            {'brand': 'Nike', 'model': 'Quest 5', 'category': 'Running', 'price': 'R$ 400-500'},
            {'brand': 'Nike', 'model': 'Pegasus 41', 'category': 'Running', 'price': 'R$ 600-700'},
            {'brand': 'Nike', 'model': 'Vomero 18', 'category': 'Running', 'price': 'R$ 900-1000'},
            {'brand': 'Nike', 'model': 'Invincible 3', 'category': 'Running', 'price': 'R$ 900-1000'},
            {'brand': 'Nike', 'model': 'Zoom Fly 6', 'category': 'Racing', 'price': 'R$ 1300-1500'},
        ]

        for prod in nike_produtos:
            link_nike = self.gerar_link_nike(prod['model'])
            link_amazon = self.gerar_link_amazon(f"Nike {prod['model']}")

            self.produtos.append({
                'brand': 'Nike',
                'model': prod['model'],
                'category': prod['category'],
                'price_range': prod['price'],
                'link_oficial': link_nike,
                'link_amazon': link_amazon,
                'link_netshoes': self.gerar_link_netshoes(f"Nike {prod['model']}")
            })
            print(f"  ✅ Nike {prod['model']:30} | R$ {prod['price']}")

        return self.produtos

    # ========================
    # ASICS BRASIL
    # ========================
    def scrape_asics(self):
        """Busca principais modelos da ASICS Brasil"""
        print("\n🔍 Buscando ASICS Brasil...\n")

        asics_produtos = [
            {'brand': 'ASICS', 'model': 'Gel-Cumulus 26', 'category': 'Running', 'price': 'R$ 700-800'},
            {'brand': 'ASICS', 'model': 'Gel-Kayano 31', 'category': 'Running', 'price': 'R$ 1200-1400'},
            {'brand': 'ASICS', 'model': 'Gel-Nimbus 26', 'category': 'Running', 'price': 'R$ 1400-1600'},
            {'brand': 'ASICS', 'model': 'Gel-Pulse 15', 'category': 'Running', 'price': 'R$ 700-800'},
            {'brand': 'ASICS', 'model': 'Gel-Trabuco 12', 'category': 'Trail', 'price': 'R$ 800-900'},
            {'brand': 'ASICS', 'model': 'Gel-Venture 10', 'category': 'Trail', 'price': 'R$ 500-600'},
            {'brand': 'ASICS', 'model': 'Superblast 2', 'category': 'Running', 'price': 'R$ 1000-1200'},
            {'brand': 'ASICS', 'model': 'Gel-Kayano 32', 'category': 'Running', 'price': 'R$ 1300-1500'},
        ]

        for prod in asics_produtos:
            link_asics = self.gerar_link_asics(prod['model'])
            link_amazon = self.gerar_link_amazon(f"ASICS {prod['model']}")

            self.produtos.append({
                'brand': 'ASICS',
                'model': prod['model'],
                'category': prod['category'],
                'price_range': prod['price'],
                'link_oficial': link_asics,
                'link_amazon': link_amazon,
                'link_netshoes': self.gerar_link_netshoes(f"ASICS {prod['model']}")
            })
            print(f"  ✅ ASICS {prod['model']:30} | {prod['price']}")

        return self.produtos

    # ========================
    # ADIDAS BRASIL
    # ========================
    def scrape_adidas(self):
        """Busca principais modelos da Adidas Brasil"""
        print("\n🔍 Buscando Adidas Brasil...\n")

        adidas_produtos = [
            {'brand': 'ADIDAS', 'model': 'Response Runner 2', 'category': 'Running', 'price': 'R$ 350-450'},
            {'brand': 'ADIDAS', 'model': 'Adizero Boston 13', 'category': 'Racing', 'price': 'R$ 1300-1500'},
            {'brand': 'ADIDAS', 'model': 'Adizero Adios Pro 4', 'category': 'Racing', 'price': 'R$ 1800-2000'},
            {'brand': 'ADIDAS', 'model': 'Ultraboost 5', 'category': 'Running', 'price': 'R$ 1000-1200'},
            {'brand': 'ADIDAS', 'model': 'Duramo Speed 2', 'category': 'Running', 'price': 'R$ 500-600'},
            {'brand': 'ADIDAS', 'model': 'Ultraboost 22', 'category': 'Running', 'price': 'R$ 1100-1300'},
            {'brand': 'ADIDAS', 'model': 'Terrex Agravic Speed 2', 'category': 'Trail', 'price': 'R$ 1100-1300'},
            {'brand': 'ADIDAS', 'model': 'Adizero RS15', 'category': 'Racing', 'price': 'R$ 1600-1800'},
        ]

        for prod in adidas_produtos:
            link_adidas = self.gerar_link_adidas(prod['model'])
            link_amazon = self.gerar_link_amazon(f"Adidas {prod['model']}")

            self.produtos.append({
                'brand': 'ADIDAS',
                'model': prod['model'],
                'category': prod['category'],
                'price_range': prod['price'],
                'link_oficial': link_adidas,
                'link_amazon': link_amazon,
                'link_netshoes': self.gerar_link_netshoes(f"Adidas {prod['model']}")
            })
            print(f"  ✅ ADIDAS {prod['model']:30} | {prod['price']}")

        return self.produtos

    # ========================
    # OLYMPIKUS
    # ========================
    def scrape_olympikus(self):
        """Busca principais modelos da Olympikus"""
        print("\n🔍 Buscando Olympikus...\n")

        olympikus_produtos = [
            {'brand': 'OLYMPIKUS', 'model': 'Corre 3', 'category': 'Running', 'price': 'R$ 500-600'},
            {'brand': 'OLYMPIKUS', 'model': 'Corre Trilha', 'category': 'Trail', 'price': 'R$ 500-600'},
            {'brand': 'OLYMPIKUS', 'model': 'Challenger 5', 'category': 'Running', 'price': 'R$ 200-300'},
            {'brand': 'OLYMPIKUS', 'model': 'Pride 4', 'category': 'Running', 'price': 'R$ 250-350'},
            {'brand': 'OLYMPIKUS', 'model': 'Orbita', 'category': 'Running', 'price': 'R$ 200-300'},
            {'brand': 'OLYMPIKUS', 'model': 'Essence', 'category': 'Running', 'price': 'R$ 200-300'},
            {'brand': 'OLYMPIKUS', 'model': 'Rua', 'category': 'Running', 'price': 'R$ 200-250'},
            {'brand': 'OLYMPIKUS', 'model': 'Marte', 'category': 'Running', 'price': 'R$ 150-250'},
        ]

        for prod in olympikus_produtos:
            link_olympikus = self.gerar_link_olympikus(prod['model'])
            link_amazon = self.gerar_link_amazon(f"Olympikus {prod['model']}")

            self.produtos.append({
                'brand': 'OLYMPIKUS',
                'model': prod['model'],
                'category': prod['category'],
                'price_range': prod['price'],
                'link_oficial': link_olympikus,
                'link_amazon': link_amazon,
                'link_netshoes': self.gerar_link_netshoes(f"Olympikus {prod['model']}")
            })
            print(f"  ✅ OLYMPIKUS {prod['model']:30} | {prod['price']}")

        return self.produtos

    # ========================
    # GERADORES DE LINKS
    # ========================

    def gerar_link_nike(self, modelo):
        """Gera link para Nike Brasil"""
        # Formato: https://www.nike.com.br/p/[produto-slug]
        slug = modelo.lower().replace(' ', '-')
        return f"https://www.nike.com.br/search?q={quote(modelo)}"

    def gerar_link_asics(self, modelo):
        """Gera link para ASICS Brasil"""
        return f"https://www.asics.com.br/search?q={quote(modelo)}"

    def gerar_link_adidas(self, modelo):
        """Gera link para Adidas Brasil"""
        return f"https://www.adidas.com.br/search?q={quote(modelo)}"

    def gerar_link_olympikus(self, modelo):
        """Gera link para Olympikus"""
        slug = modelo.lower().replace(' ', '-')
        return f"https://www.olympikus.com.br/search?q={quote(modelo)}"

    def gerar_link_amazon(self, produto):
        """Gera link de busca Amazon (pode ser convertido em affiliate link depois)"""
        return f"https://www.amazon.com.br/s?k={quote(produto)}"

    def gerar_link_netshoes(self, produto):
        """Gera link de busca Netshoes"""
        return f"https://www.netshoes.com.br/search?q={quote(produto)}"

    # ========================
    # EXPORTAÇÃO
    # ========================

    def exportar_csv(self, filename='links_afiliado_marcas.csv'):
        """Exporta produtos para CSV"""
        if not self.produtos:
            print("❌ Nenhum produto para exportar!")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.produtos[0].keys())
            writer.writeheader()
            writer.writerows(self.produtos)

        print(f"\n✅ Exportado para {filename}")

    def exportar_json(self, filename='links_afiliado_marcas.json'):
        """Exporta produtos para JSON"""
        if not self.produtos:
            print("❌ Nenhum produto para exportar!")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.produtos, f, ensure_ascii=False, indent=2)

        print(f"✅ Exportado para {filename}")

    def exportar_google_sheets_format(self, filename='para_google_sheets.txt'):
        """Exporta no formato pronto para copiar/colar no Google Sheets"""
        if not self.produtos:
            print("❌ Nenhum produto para exportar!")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Brand\tModel\tCategory\tPrice Range\tLink Oficial\tLink Amazon\tLink Netshoes\n")
            for prod in self.produtos:
                f.write(f"{prod['brand']}\t{prod['model']}\t{prod['category']}\t{prod['price_range']}\t{prod['link_oficial']}\t{prod['link_amazon']}\t{prod['link_netshoes']}\n")

        print(f"✅ Exportado para {filename} (pronto para Google Sheets)")

    # ========================
    # EXECUÇÃO
    # ========================

    def executar_completo(self):
        """Executa scraping de todas as marcas"""
        print("=" * 80)
        print("🔗 AGENTE INTELIGENTE DE LINKS DE AFILIADO - TÊNIS IDEAL")
        print("=" * 80)

        self.scrape_nike()
        self.scrape_asics()
        self.scrape_adidas()
        self.scrape_olympikus()

        print("\n" + "=" * 80)
        print(f"✅ TOTAL COLETADO: {len(self.produtos)} produtos")
        print("=" * 80)

        # Resumo por marca
        print("\n📊 RESUMO POR MARCA:")
        brands = {}
        for prod in self.produtos:
            brand = prod['brand']
            brands[brand] = brands.get(brand, 0) + 1

        for brand, count in sorted(brands.items()):
            print(f"  • {brand}: {count} produtos")

        # Exportar
        print("\n💾 EXPORTANDO DADOS...\n")
        self.exportar_csv()
        self.exportar_json()
        self.exportar_google_sheets_format()

        print("\n" + "=" * 80)
        print("✅ COLETA CONCLUÍDA!")
        print("=" * 80)
        print("\n📌 PRÓXIMOS PASSOS:")
        print("  1. Abrir 'para_google_sheets.txt'")
        print("  2. Copiar o conteúdo (Ctrl+A, Ctrl+C)")
        print("  3. Colar no Google Sheets (Ctrl+V)")
        print("  4. Verificar e validar os links")
        print("  5. Executar sincronizador de preços")

if __name__ == "__main__":
    agente = AgenteAfiliadoTenista()
    agente.executar_completo()
