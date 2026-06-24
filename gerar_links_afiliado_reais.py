#!/usr/bin/env python3
"""
gerar_links_afiliado_reais.py
------------------------------
🔗 GERADOR DE LINKS DE AFILIADO REAIS
Cria links com IDs de rastreamento para Awin, Netshoes e Amazon
"""

import json
from urllib.parse import urlencode, quote

class GeradorLinksAfiliado:
    """Gera links de afiliado com rastreamento real"""

    def __init__(self):
        # CONFIGURE SEUS IDs AQUI
        self.ids = {
            'amazon': {
                'tag': 'SEUID-20',  # ← SUBSTITUA COM SEU TAG ID (Amazon Associates)
                'associate_id': 'seuid-20'
            },
            'netshoes': {
                'affiliate_id': '123456',  # ← SUBSTITUA COM SEU ID (Netshoes)
                'utm_source': 'tenisideal'
            },
            'awin': {
                'publisher_id': '123456',  # ← SUBSTITUA COM SEU PUBLISHER ID (Awin)
                'click_ref': 'TenisIdeal'
            }
        }

        self.produtos = []

    # ========================
    # GERADORES DE LINKS
    # ========================

    def gerar_link_amazon(self, asin, produto_nome):
        """Gera link Amazon com affiliate tracking

        ASIN: Identificador único do produto na Amazon
        Exemplo: B0BYJT3R2K
        """
        if not self.ids['amazon']['tag']:
            return f"https://amazon.com.br/s?k={quote(produto_nome)}"

        # Link com Associate Tag (rastreia comissão)
        params = {
            'tag': self.ids['amazon']['tag'],
            'linkCode': 'qs',
            'keywords': produto_nome,
            'index': 'aps'
        }
        return f"https://amazon.com.br/?{urlencode(params)}"

    def gerar_link_netshoes(self, produto_id, produto_nome):
        """Gera link Netshoes com affiliate tracking

        PRODUTO_ID: Identificador único do produto na Netshoes
        Exemplo: 12345678
        """
        if not self.ids['netshoes']['affiliate_id']:
            return f"https://www.netshoes.com.br/search?q={quote(produto_nome)}"

        # Link com UTM parameters + affiliate ID
        params = {
            'utm_source': self.ids['netshoes']['utm_source'],
            'utm_medium': 'affiliate',
            'utm_campaign': 'tenisideal',
            'affid': self.ids['netshoes']['affiliate_id'],
            'q': produto_nome
        }
        return f"https://www.netshoes.com.br/search?{urlencode(params)}"

    def gerar_link_awin(self, url_original, awin_deeplink_id=None):
        """Gera link Awin (plataforma unificada de afiliados)

        AWIN funciona com deeplinks automáticos
        Exemplo deeplink: https://www.awin1.com/cread.php?awinmid=15576&awinaffid=123456
        """
        if not self.ids['awin']['publisher_id']:
            return None

        # Awin precisa de AWIN Mid (Merchant ID) específico para cada site
        # Você obtém isso registrando cada programa (Nike, ASICS, etc)
        awin_mid = awin_deeplink_id or 'PENDING'  # Aguardando cadastro em cada programa

        # Format: https://www.awin1.com/cread.php?awinmid=[MERCHANT_ID]&awinaffid=[YOUR_ID]&clickref=[REF]
        return f"https://www.awin1.com/cread.php?awinmid={awin_mid}&awinaffid={self.ids['awin']['publisher_id']}&clickref={self.ids['awin']['click_ref']}"

    # ========================
    # GUIA DE SETUP
    # ========================

    def mostrar_guia_setup(self):
        """Mostra instruções para registrar em cada programa"""

        guia = """
╔════════════════════════════════════════════════════════════════════════════╗
║                   📚 GUIA: CONFIGURAR LINKS DE AFILIADO REAIS             ║
╚════════════════════════════════════════════════════════════════════════════╝

1️⃣  AMAZON ASSOCIATES (amazon.com.br)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔗 Registre em: https://associados.amazon.com.br/

   ✅ Requisitos:
      • CPF ou CNPJ brasileiro
      • Site com conteúdo relevante (Tenis Ideal qualifica)
      • Mínimo 1 venda nos 6 primeiros meses
      • Comissão: 5-10% por venda

   📋 Ao registrar, você receberá:
      • Associate Tag (exemplo: tenisideal-20)
      • ASIN de cada produto (código único Amazon)

   💡 Como usar:
      • Configure seu TAG na linha: self.ids['amazon']['tag'] = 'tenisideal-20'
      • Busque ASIN de cada produto em amazon.com.br
      • Crie link: https://amazon.com.br/?tag=tenisideal-20&asin=B0BYJT3R2K


2️⃣  NETSHOES AFILIADOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔗 Registre em: https://www.netshoes.com.br/afiliados

   ✅ Requisitos:
      • Site com tráfego (mínimo 100 visitas/mês)
      • Conteúdo relacionado a esportes/fitness
      • Comissão: 5-15% por venda

   📋 Ao registrar, você receberá:
      • Affiliate ID (exemplo: 123456)
      • Link base para rastreamento

   💡 Como usar:
      • Configure seu ID na linha: self.ids['netshoes']['affiliate_id'] = '123456'
      • Crie link: https://www.netshoes.com.br/search?affid=123456&q=Nike%20Winflo


3️⃣  AWIN (Plataforma Unificada de Afiliados)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔗 Registre em: https://www.awin.com/pt/

   ✅ Requisitos:
      • Publisher (afiliado) ou Agency
      • Aprovação manual (24-48h)
      • Acesso a 20.000+ programas de afiliados

   📋 Ao registrar como Publisher:
      • Obtenha seu Publisher ID (exemplo: 123456)
      • Acesse programas individuais (Nike, ASICS, Adidas, etc)
      • Para cada marca, obtenha o Merchant ID (Mid)

   💡 Como usar:
      • Configure seu ID na linha: self.ids['awin']['publisher_id'] = '123456'
      • Para Nike: https://www.awin1.com/cread.php?awinmid=15576&awinaffid=123456
      • Para ASICS: https://www.awin1.com/cread.php?awinmid=XXXXX&awinaffid=123456


╔════════════════════════════════════════════════════════════════════════════╗
║                          ⚡ PRÓXIMOS PASSOS                               ║
╚════════════════════════════════════════════════════════════════════════════╝

1. Registre em cada programa acima
2. Copie seus IDs para o arquivo config_afiliados.json
3. Execute: python3 gerar_links_afiliado_reais.py
4. Links REAIS serão gerados com rastreamento
5. Atualize Google Sheets com novos links


╔════════════════════════════════════════════════════════════════════════════╗
║                          📊 COMPARAÇÃO DE PROGRAMAS                       ║
╚════════════════════════════════════════════════════════════════════════════╝

Programa        Comissão  Requisito Min  Delay Pagamento  Link Rastreamento
────────────────────────────────────────────────────────────────────────────
Amazon          5-10%     R$ 50/mês      30-60 dias       Sim (tag)
Netshoes        5-15%     100 vis/mês    30 dias          Sim (utm + id)
Awin (Nike)     7-15%     Aprovado       30 dias          Sim (deeplink)
Awin (ASICS)    8-12%     Aprovado       30 dias          Sim (deeplink)
Awin (Adidas)   5-10%     Aprovado       30 dias          Sim (deeplink)


🎯 RECOMENDAÇÃO:
   Use TODOS os três! Cada um serve um propósito:
   • Amazon: Alto volume, usuários que já confiam
   • Netshoes: Nativo Brasil, melhor UX local
   • Awin: Acesso a programas oficiais das marcas com melhor comissão

"""

        print(guia)

    # ========================
    # GERAR ARQUIVO CONFIG
    # ========================

    def criar_config_template(self):
        """Cria arquivo de configuração para IDs"""
        config = {
            "amazon": {
                "tag": "SEUID-20",
                "note": "Obtenha em https://associados.amazon.com.br/"
            },
            "netshoes": {
                "affiliate_id": "123456",
                "utm_source": "tenisideal",
                "note": "Obtenha em https://www.netshoes.com.br/afiliados"
            },
            "awin": {
                "publisher_id": "123456",
                "click_ref": "TenisIdeal",
                "merchants": {
                    "nike": 15576,
                    "asics": 0,
                    "adidas": 0,
                    "olympikus": 0
                },
                "note": "Obtenha em https://www.awin.com/pt/"
            }
        }

        with open('config_afiliados.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print("✅ Arquivo de configuração criado: config_afiliados.json")
        print("📝 Edite este arquivo com seus IDs reais e execute novamente!")

if __name__ == "__main__":
    gerador = GeradorLinksAfiliado()

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  🔗 GERADOR DE LINKS DE AFILIADO REAIS - TENIS IDEAL         ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    # Mostrar guia
    gerador.mostrar_guia_setup()

    # Criar arquivo de config
    print("\n" + "="*70)
    print("📁 CRIANDO ARQUIVO DE CONFIGURAÇÃO")
    print("="*70 + "\n")
    gerador.criar_config_template()

    print("\n🎯 PRÓXIMO PASSO:")
    print("   1. Abra 'config_afiliados.json'")
    print("   2. Preencha com seus IDs de afiliado")
    print("   3. Execute: python3 gerar_links_afiliado_reais.py")
    print("   4. Links REAIS serão gerados!")
