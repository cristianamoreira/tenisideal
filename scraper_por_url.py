import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import os
import re
import json
import unicodedata

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y/edit"
CREDENTIALS_FILE = "credenciais.json"

# Usa a chave GEMINI_API_KEY do ambiente (exportada no terminal) ou pede no fallback
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==============================================================================
# 🔗 CONEXÃO COM GOOGLE SHEETS
# ==============================================================================
def conectar_planilha():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
    except Exception as e:
        print(f"❌ Erro ao conectar no Google Sheets: {e}")
        print("Verifique se o arquivo credenciais.json está na pasta e se a planilha foi compartilhada com o email do robô.")
        exit(1)

# ==============================================================================
# 🤖 INTEGRAÇÃO COM GEMINI AI
# ==============================================================================
def analisar_tenis_com_gemini(nome_tenis, preco_str):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        print("⚠️ Chave GEMINI_API_KEY não encontrada no ambiente.")
        GEMINI_API_KEY = input("Cole sua GEMINI_API_KEY (ou dê enter para tags vazias): ").strip()
    
    if not GEMINI_API_KEY:
        return {}

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Define o budget base
    budget = "300a600"
    try:
        preco_num = float(re.sub(r'[^\d,.-]', '', preco_str).replace('.', '').replace(',', '.'))
        if preco_num < 300: budget = "ate300"
        elif 300 <= preco_num <= 600: budget = "300a600"
        elif 600 < preco_num <= 1000: budget = "600a1000"
        else: budget = "acima1000"
    except:
        pass

    prompt = f"""
Você é um especialista em tênis de corrida. Analise o seguinte modelo: "{nome_tenis}".
Responda OBRIGATORIAMENTE em formato JSON válido contendo APENAS as propriedades abaixo. Siga estritamente as opções permitidas para os arrays.

Opções:
- sexo: ["masculino", "feminino", "unissex"]
- brand: O nome da marca em MAIÚSCULO (ex: "NIKE", "ADIDAS")
- tags: Uma ou duas tags curtas separadas por | (ex: "Amortecimento|Velocidade")
- levels: ["iniciante", "intermediario", "avancado"] (pode ter mais de um separado por |)
- pisadas: ["neutra", "pronada", "supinada", "naosabe"] (pode ter mais de um separado por |)
- terrenos: ["asfalto", "pista", "esteira", "trilha", "mista"] (pode ter mais de um separado por |)
- priors: ["amortecimento", "leveza", "durabilidade", "custo"] (pode ter mais de um separado por |)
- reason: Uma frase persuasiva curta recomendando o tênis (ex: "Ótimo custo-benefício para iniciantes.")

Exemplo de saída esperada:
{{
  "sexo": "masculino",
  "brand": "NIKE",
  "tags": "Amortecimento|Leveza",
  "levels": "iniciante|intermediario",
  "pisadas": "neutra|naosabe",
  "terrenos": "asfalto|esteira|mista",
  "priors": "amortecimento|conforto",
  "reason": "Amortecimento excepcional da linha Pegasus, perfeito para treinos longos."
}}
"""
    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        print(f"⚠️ Erro na classificação do Gemini: {e}")
        return {}

# ==============================================================================
# 🕸️ SCRAPER GENÉRICO POR METADATA
# ==============================================================================
def extrair_dados_da_url(url):
    print(f"\nAcessando {url} ...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Tentar pegar o Nome (Title)
        nome = ""
        og_title = soup.find("meta", property="og:title")
        if og_title: nome = og_title.get("content", "")
        if not nome: 
            title_tag = soup.find("title")
            if title_tag: nome = title_tag.text

        # Limpar o nome (remover "Comprar", "Tênis", "- Loja Oficial", etc.)
        nome = re.sub(r'(?i)(comprar|tênis|tenis|loja oficial|masculino|feminino|- |\|).*', '', nome).strip()

        # 2. Tentar pegar a Imagem
        imagem = ""
        og_img = soup.find("meta", property="og:image")
        if og_img: imagem = og_img.get("content", "")

        # 3. Tentar pegar o Preço
        preco = ""
        # Buscar no meta
        meta_price = soup.find("meta", property="product:price:amount")
        if meta_price:
            preco = f"R${meta_price.get('content', '')}"
        
        # Buscar no HTML por padrões de R$ 
        if not preco:
            textos_precos = re.findall(r'R\$\s*[\d.]+(?:,\d{2})?', response.text)
            if textos_precos:
                # Pega o primeiro que parecer válido
                preco = textos_precos[0]

        return nome, preco, imagem

    except Exception as e:
        print(f"⚠️ Erro ao tentar ler a URL: {e}")
        return "", "", ""

# ==============================================================================
# 🪪 GERADOR DE SLUG (IDENTIFICADOR ÚNICO)
# ==============================================================================
def gerar_slug(nome, marca=""):
    # Concatena marca e nome para garantir unicidade (ex: "Nike Pegasus 42")
    texto = f"{marca} {nome}".strip().lower()
    
    # Remove acentos (ex: tênis -> tenis)
    texto = unicodedata.normalize('NFKD', texto)
    texto = "".join([c for c in texto if not unicodedata.combining(c)])
    
    # Remove caracteres especiais, mantendo letras e números
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    
    # Troca espaços por hifens
    slug = re.sub(r'[-\s]+', '-', texto).strip('-')
    return slug

# ==============================================================================
# 🚀 FUNÇÃO PRINCIPAL
# ==============================================================================
def main():
    print("=========================================")
    print("👟 SCRAPER POR URL + GOOGLE SHEETS 👟")
    print("=========================================")
    print("Conectando à planilha...")
    sheet = conectar_planilha()
    print("✅ Planilha conectada!")

    while True:
        url_input = input("\n🔗 Cole a URL do produto (ou digite 'sair' para encerrar): ").strip()
        if url_input.lower() == 'sair':
            break
        if not url_input.startswith("http"):
            print("URL inválida.")
            continue

        nome_extraido, preco_extraido, img_extraida = extrair_dados_da_url(url_input)

        print("-" * 40)
        print("DADOS EXTRAÍDOS AUTOMATICAMENTE:")
        print(f"NOME:  {nome_extraido}")
        print(f"PREÇO: {preco_extraido}")
        print(f"IMG:   {img_extraida}")
        print("-" * 40)

        # Determinar qual tipo de loja é a URL
        is_amazon = "amazon" in url_input.lower()
        is_netshoes = "netshoes" in url_input.lower()
        # Assumiremos "Oficial" para Nike/Adidas/Mizuno/Olympikus ou qualquer outra loja genérica que não seja as acima
        is_oficial = not is_amazon and not is_netshoes

        # Lógica de Identidade: Ler toda a planilha e verificar Slugs
        linhas = sheet.get_all_values()
        
        # Pular o cabeçalho (linha 0 do array, linha 1 da planilha)
        encontrou_linha = -1
        slug_novo = gerar_slug(nome_extraido) 
        
        for idx, linha in enumerate(linhas):
            if idx == 0: continue # pula cabeçalho
            # As colunas são: 0:sexo, 1:brand, 2:name ...
            if len(linha) > 2:
                marca_linha = linha[1]
                nome_linha = linha[2]
                slug_linha = gerar_slug(nome_linha, marca_linha)
                
                # Se ainda não temos uma marca no nome_extraido, podemos tentar cruzar só com o nome
                slug_novo_com_marca = gerar_slug(nome_extraido, marca_linha)
                
                # Tenta match exato pelo nome limpo ou nome+marca
                if slug_novo == slug_linha or slug_novo_com_marca == slug_linha:
                    encontrou_linha = idx + 1 # +1 porque gspread começa em 1
                    break
        
        # --- LÓGICA DE MERGE AUTOMÁTICO ---
        if encontrou_linha != -1:
            print(f"🔍 Produto ID '{slug_novo}' encontrado na linha {encontrou_linha}!")
            
            # As colunas de links no Google Sheets são (A=1, B=2...):
            # N (14) = amazon_link
            # P (16) = awin_link (Oficial)
            # Q (17) = netshoes_link
            
            col_alvo = 0
            nome_col = ""
            if is_amazon: 
                col_alvo = 14
                nome_col = "Amazon"
            elif is_netshoes: 
                col_alvo = 17
                nome_col = "Netshoes"
            else: 
                col_alvo = 16
                nome_col = "Loja Oficial"
                
            print(f"⚙️ Atualizando oferta da loja {nome_col} automaticamente...")
            try:
                sheet.update_cell(encontrou_linha, col_alvo, url_input)
                # Atualiza também o preço (coluna G = 7) se for Oficial, ou mantemos o original?
                # Vamos manter seguro e apenas adicionar o link secundário para o usuário validar
                print(f"✅ SUCESSO! Link atualizado na linha {encontrou_linha}.")
            except Exception as e:
                print(f"❌ Erro ao atualizar planilha: {e}")
            
            continue # Pula a criação e vai para a próxima URL
            
        # Fallback manual caso o bloqueio do site impeça a extração (e não seja duplicado)
        if not nome_extraido or not preco_extraido:
            print("⚠️ Não foi possível extrair Nome/Preço automaticamente (possível bloqueio da loja).")
            res = input("Deseja digitar manualmente? (s/n): ").strip().lower()
            if res == 's':
                if not nome_extraido: nome_extraido = input("Digite o NOME do tênis: ").strip()
                if not preco_extraido: preco_extraido = input("Digite o PREÇO (ex: R$500): ").strip()
                if not img_extraida: img_extraida = input("Cole a URL da IMAGEM: ").strip()
            else:
                print("Pulando URL...")
                continue

        # Se passou direto, é um produto NOVO. Mandar pro Gemini

        print("🧠 Enviando para a Inteligência Artificial classificar...")
        ia_specs = analisar_tenis_com_gemini(nome_extraido, preco_extraido)
        
        if not ia_specs:
            print("⚠️ IA não conseguiu classificar. Inserindo dados mínimos.")
            ia_specs = {}

        # Determinar orçamento (budget) com base no preço formatado final
        budget = "300a600"
        try:
            p = float(re.sub(r'[^\d,.-]', '', preco_extraido).replace('.', '').replace(',', '.'))
            if p < 300: budget = "ate300"
            elif 300 <= p <= 600: budget = "300a600"
            elif 600 <= p <= 1000: budget = "600a1000"
            else: budget = "acima1000"
        except: pass

        # Determinar em qual coluna de link inserir baseado na URL
        link_amazon = url_input if "amazon" in url_input else ""
        link_netshoes = url_input if "netshoes" in url_input else ""
        # Assumiremos "Oficial" para Nike/Adidas/Mizuno/Olympikus
        link_oficial = url_input if ("nike" in url_input or "adidas" in url_input or "mizuno" in url_input or "olympikus" in url_input) else ""

        # Ordem exata das colunas:
        # 0:sexo, 1:brand, 2:name, 3:img, 4:emoji, 5:tags, 6:price, 7:budget, 8:levels, 
        # 9:pisadas, 10:terrenos, 11:priors, 12:reason, 13:amazon_link, 14:popular, 15:awin_link (Oficial), 16:netshoes_link
        
        nova_linha = [
            ia_specs.get("sexo", "unissex"),
            ia_specs.get("brand", "DESCONHECIDA"),
            nome_extraido,
            img_extraida,
            "👟",
            ia_specs.get("tags", ""),
            preco_extraido,
            budget,
            ia_specs.get("levels", "iniciante"),
            ia_specs.get("pisadas", "neutra"),
            ia_specs.get("terrenos", "asfalto"),
            ia_specs.get("priors", "custo"),
            ia_specs.get("reason", ""),
            link_amazon,
            "", # popular
            link_oficial,
            link_netshoes
        ]

        # Inserir no Google Sheets
        print("📝 Escrevendo nova linha no Google Sheets...")
        try:
            sheet.append_row(nova_linha)
            print("✅ SUCESSO! Produto adicionado com perfeição!")
        except Exception as e:
            print(f"❌ Erro ao adicionar linha na planilha: {e}")

if __name__ == "__main__":
    main()
