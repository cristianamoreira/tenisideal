#!/usr/bin/env python3
"""
scraper_por_url.py
------------------
👟 SCRAPER POR URL + GOOGLE SHEETS 👟
Com suporte a:
- Exclusão lógica (--delete <product_id> -> ativo=nao)
- Reativação (--reactivate <product_id> -> ativo=sim)
- Comparação de preços multi-lojas (merge automático se produto já existe)
- Fallback interativo/manual se a extração falhar (aceita "s" e "sim")
- Classificação inteligente via Gemini AI
"""

import argparse
import sys
import os
import re
import json
import unicodedata
import hashlib
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================
SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"
CREDENTIALS_FILE = "credenciais.json"

# Usa a chave GEMINI_API_KEY do ambiente ou pede fallback
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STORES = ["amazon", "loja_oficial", "netshoes"]
STORE_LABELS = {
    "amazon": "Amazon",
    "loja_oficial": "Loja Oficial",
    "netshoes": "Netshoes"
}

SCHEMA_COLS = [
    "product_id", "ativo", "marca", "nome", "versao", 
    "sexo", "img", "emoji", "tags", "nível", 
    "pisada", "terreno", "priors", "razão", 
    "link_amazon", "preco_amazon", "parcelas_amazon",
    "link_loja_oficial", "preco_loja_oficial", "parcelas_loja_oficial", "preco_pix_oficial",
    "link_netshoes", "preco_netshoes", "preco_pix_netshoes", "parcelas_netshoes",
    "budget"
]

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
        sheet = client.open_by_key(SHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"❌ Erro ao conectar no Google Sheets: {e}")
        print("Verifique se o arquivo credenciais.json está na pasta e se a planilha foi compartilhada.")
        sys.exit(1)

# ==============================================================================
# 📋 HELPER PARA OBTER REGISTROS DA PLANILHA SEM ERRO DE CABEÇALHOS DUPLICADOS
# ==============================================================================
def obter_registros(sheet):
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            return []
        # Limpar cabeçalhos e identificar colunas válidas (ignorar vazias)
        headers = [h.strip() for h in all_values[0]]
        records = []
        for row in all_values[1:]:
            record = {}
            for idx, val in enumerate(row):
                if idx < len(headers):
                    header = headers[idx]
                    if header:  # Ignora colunas sem cabeçalho
                        record[header] = val
            records.append(record)
        return records
    except Exception as e:
        print(f"❌ Erro ao ler registros da planilha: {e}")
        return []

# ==============================================================================
# 🪪 GERADOR DE SLUG (IDENTIFICADOR ÚNICO)
# ==============================================================================
def gerar_slug(marca, nome, versao=""):
    base = f"{marca} {nome} {versao}".strip().lower()
    s = unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    suffix = hashlib.md5(s.encode()).hexdigest()[:4]
    return f"{s}-{suffix}"

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
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Detectar gênero explícito no nome para usar como override
    nome_lower = nome_tenis.lower()
    genero_detectado = None
    if any(p in nome_lower for p in ['feminino', 'feminina', 'women', 'woman', ' w ', '-w-', 'wmns', 'mujer']):
        genero_detectado = 'feminino'
    elif any(p in nome_lower for p in ['masculino', 'masculina', 'men', 'man', ' m ', '-m-', 'mens', 'hombre']):
        genero_detectado = 'masculino'

    instrucao_sexo = ""
    if genero_detectado:
        instrucao_sexo = f'\n⚠️ ATENÇÃO: O nome do produto contém indicação explícita de gênero. O campo "sexo" DEVE ser obrigatoriamente "{genero_detectado}". NÃO use "unissex" neste caso.'

    prompt = f"""
Você é um especialista em tênis de corrida. Analise o seguinte modelo: "{nome_tenis}".
Responda OBRIGATORIAMENTE em formato JSON válido contendo APENAS as propriedades abaixo. Siga estritamente as opções permitidas.
{instrucao_sexo}

Opções:
- sexo: ["masculino", "feminino", "unissex"] — Se o nome contiver feminino/women/wmns use "feminino"; se contiver masculino/men/mens use "masculino"; senão analise o modelo.
- brand: O nome da marca em MAIÚSCULO (ex: "NIKE", "ADIDAS")
- tags: Exatamente 1 ou 2 tags de TECNOLOGIA ou CARACTERÍSTICA FÍSICA, separadas por |.
    PERMITIDO: nomes de tecnologias (ex: "ZoomX", "Boost", "PWRRUN", "Wave", "React", "DNA Loft", "CloudTec"), materiais (ex: "Knit", "Gore-Tex") ou diferenciais físicos (ex: "Placa de carbono", "Drop zero").
    PROIBIDO: NÃO use em tags palavras que já existem em outras colunas: "Iniciante", "Intermediário", "Avançado", "Treino", "Maratona", "Diário", "Asfalto", "Trilha", "Esteira", "Pista", "Neutra", "Pronada", "Supinada", "Leveza", "Custo", "Durabilidade", "Velocidade", "Conforto".
- levels: ["iniciante", "intermediario", "avancado"] (pode ter mais de um separado por |)
- pisadas: ["neutra", "pronada", "supinada", "naosabe"] (pode ter mais de um separado por |)
- terrenos: ["asfalto", "pista", "esteira", "trilha", "mista"] (pode ter mais de um separado por |)
- priors: ["amortecimento", "leveza", "durabilidade", "custo"] (pode ter mais de um separado por |)
- reason: Uma frase persuasiva curta recomendando o tênis (ex: "Ótimo custo-benefício para iniciantes.")

Exemplo de saída esperada:
{{
  "sexo": "masculino",
  "brand": "NIKE",
  "tags": "ZoomX|Placa de carbono",
  "levels": "iniciante|intermediario",
  "pisadas": "neutra|naosabe",
  "terrenos": "asfalto|esteira|mista",
  "priors": "amortecimento|custo",
  "reason": "Amortecimento excepcional da linha Pegasus, perfeito para treinos longos."
}}
"""
    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        resultado = json.loads(texto)
        # Override de segurança: se o nome tem gênero explícito, força o valor correto
        if genero_detectado:
            resultado["sexo"] = genero_detectado
        return resultado
    except Exception as e:
        print(f"⚠️ Erro na classificação do Gemini: {e}")
        return {}

# ==============================================================================
# 🕸️ SCRAPER GENÉRICO POR METADATA
# ==============================================================================
def extrair_dados_da_url(url):
    print(f"\nAcessando {url} ...")
    try:
        response = requests.get(url, headers=HEADERS_HTTP, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ Resposta da loja não foi 200 (Status: {response.status_code})")
            return "", "", ""
            
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Tentar pegar o Nome (Title)
        nome = ""
        og_title = soup.find("meta", property="og:title")
        if og_title: nome = og_title.get("content", "")
        if not nome: 
            title_tag = soup.find("title")
            if title_tag: nome = title_tag.text

        # Limpar o nome
        nome = re.sub(r'(?i)(comprar|loja oficial|- |\|).*', '', nome).strip()

        # 2. Tentar pegar a Imagem
        imagem = ""
        og_img = soup.find("meta", property="og:image")
        if og_img: imagem = og_img.get("content", "")

        # 3. Tentar pegar o Preço
        preco = ""
        meta_price = soup.find("meta", property="product:price:amount")
        if meta_price:
            preco = f"R$ {meta_price.get('content', '')}"
        
        if not preco:
            textos_precos = re.findall(r'R\$\s*[\d.]+(?:,\d{2})?', response.text)
            if textos_precos:
                preco = textos_precos[0]

        return nome, preco, imagem

    except Exception as e:
        print(f"⚠️ Erro ao ler a URL: {e}")
        return "", "", ""

def get_store_from_url(url):
    url_lower = url.lower()
    if "amazon" in url_lower:
        return "amazon"
    elif "netshoes" in url_lower:
        return "netshoes"
    else:
        return "loja_oficial"

# ==============================================================================
# 🛠️ OPERAÇÕES DA PLANILHA
# ==============================================================================
def marcar_inativo(product_id):
    sheet = conectar_planilha()
    records = obter_registros(sheet)
    found_idx = -1
    for idx, row in enumerate(records):
        if str(row.get("product_id", "")).strip() == product_id.strip():
            found_idx = idx + 2  # +2: 1-indexed and header
            break
            
    if found_idx == -1:
        print(f"⚠️ Produto com ID '{product_id}' não encontrado.")
        return
        
    sheet.update_cell(found_idx, 2, "nao")  # coluna B é 'ativo'
    print(f"✅ Produto '{product_id}' marcado como INATIVO com sucesso.")

def reativar(product_id):
    sheet = conectar_planilha()
    records = obter_registros(sheet)
    found_idx = -1
    for idx, row in enumerate(records):
        if str(row.get("product_id", "")).strip() == product_id.strip():
            found_idx = idx + 2
            break
            
    if found_idx == -1:
        print(f"⚠️ Produto com ID '{product_id}' não encontrado.")
        return
        
    sheet.update_cell(found_idx, 2, "sim")
    print(f"✅ Produto '{product_id}' reativado com sucesso (ATIVO).")

# ==============================================================================
# 🚀 PROCESSO DE INSERÇÃO / ATUALIZAÇÃO
# ==============================================================================
def processar_produto(url, sexo_cli=None):
    sheet = conectar_planilha()
    store = get_store_from_url(url)
    store_label = STORE_LABELS.get(store, store)
    
    nome_extraido, preco_extraido, img_extraida = extrair_dados_da_url(url)

    print("-" * 40)
    print("DADOS EXTRAÍDOS AUTOMATICAMENTE:")
    print(f"NOME:  {nome_extraido}")
    print(f"PREÇO: {preco_extraido}")
    print(f"IMG:   {img_extraida}")
    print("-" * 40)

    # Fallback manual caso falhe
    if not nome_extraido or not preco_extraido:
        print("⚠️ Não foi possível extrair Nome/Preço automaticamente (possível bloqueio da loja).")
        res = input("Deseja digitar manualmente? (s/n): ").strip().lower()
        if res in ("s", "sim"):
            if not nome_extraido: nome_extraido = input("Digite o NOME do tênis: ").strip()
            if not preco_extraido: preco_extraido = input("Digite o PREÇO listado (ex: R$ 500,00): ").strip()
            if not img_extraida: img_extraida = input("Cole a URL da IMAGEM: ").strip()
        else:
            print("Pulando URL...")
            return

    # Solicitar versão opcional
    versao = ""
    res_v = input("Deseja informar uma VERSÃO/Variante específica? (ex: Trail, Shield, V2) [Pressione Enter para pular]: ").strip()
    if res_v:
        versao = res_v

    # Classificação Gemini
    print("🧠 Enviando para a Inteligência Artificial classificar...")
    ia_specs = analisar_tenis_com_gemini(nome_extraido, preco_extraido)
    
    # Se a classificação falhar ou retornar vazia (ex: limite de cota 429)
    if not ia_specs:
        print("\n⚠️ O Gemini atingiu o limite de cota ou falhou. Vamos preencher as especificações manualmente:")
        ia_specs = {}
        
        # Marca
        marca_input = input("Digite a MARCA do tênis [Enter para usar 'Nike']: ").strip().upper()
        ia_specs["brand"] = marca_input if marca_input else "NIKE"
        
        # Gênero
        sexo_input = input("Gênero [masculino/feminino/unissex] [Enter para unissex]: ").strip().lower()
        ia_specs["sexo"] = sexo_input if sexo_input in ["masculino", "feminino", "unissex"] else "unissex"
        
        # Tags
        tags_input = input("Digite as TAGS separadas por | (ex: Gel|Knit) [Enter para pular]: ").strip()
        ia_specs["tags"] = tags_input
        
        # Nível
        nivel_input = input("Nível [iniciante/intermediario/avancado] [Enter para iniciante]: ").strip().lower()
        ia_specs["levels"] = nivel_input if nivel_input in ["iniciante", "intermediario", "avancado"] else "iniciante"
        
        # Pisada
        pisada_input = input("Pisada [neutra/pronada/supinada/naosabe] [Enter para neutra]: ").strip().lower()
        ia_specs["pisadas"] = pisada_input if pisada_input in ["neutra", "pronada", "supinada", "naosabe"] else "neutra"
        
        # Terreno
        terreno_input = input("Terreno [asfalto/pista/esteira/trilha/mista] [Enter para asfalto]: ").strip().lower()
        ia_specs["terrenos"] = terreno_input if terreno_input in ["asfalto", "pista", "esteira", "trilha", "mista"] else "asfalto"
        
        # Prioridades
        priors_input = input("Prioridades [amortecimento/leveza/durabilidade/custo] [Enter para custo]: ").strip().lower()
        ia_specs["priors"] = priors_input if priors_input in ["amortecimento", "leveza", "durabilidade", "custo"] else "custo"
        
        # Razão
        reason_input = input("Frase de recomendação (razão) [Enter para pular]: ").strip()
        ia_specs["reason"] = reason_input
        
    marca = ia_specs.get("brand", "Nike").title()
    
    # Gerar slug para busca
    slug_novo = gerar_slug(marca, nome_extraido, versao)
    
    # Carregar registros sem erros de cabeçalho duplicado
    records = obter_registros(sheet)
    encontrou_linha = -1
    for idx, row in enumerate(records):
        if str(row.get("product_id", "")).strip() == slug_novo:
            encontrou_linha = idx + 2
            break

    # Se já existe, atualiza apenas a oferta daquela loja (Merge)
    if encontrou_linha != -1:
        print(f"🔍 Produto ID '{slug_novo}' encontrado na linha {encontrou_linha}!")
        print(f"⚙️ Atualizando oferta da loja {store_label}...")
        
        store_base_col = SCHEMA_COLS.index(f"link_{store}") + 1 # +1 gspread 1-based
        
        # Coleta parcelas e pix do terminal
        preco_pix = ""
        if store != "amazon":
            preco_pix = input(f"Preço PIX na {store_label} (ex: R$ 450,00) [Enter para pular]: ").strip()
        parcelas = input(f"Condições de parcelamento na {store_label} (ex: 10x sem juros) [Enter para pular]: ").strip()
        
        try:
            sheet.update_cell(encontrou_linha, store_base_col, url)            # link
            sheet.update_cell(encontrou_linha, store_base_col + 1, preco_extraido) # preco
            
            if store == "amazon":
                if parcelas:
                    sheet.update_cell(encontrou_linha, store_base_col + 2, parcelas) # parcelas
            elif store == "loja_oficial":
                if parcelas:
                    sheet.update_cell(encontrou_linha, store_base_col + 2, parcelas) # parcelas
                if preco_pix:
                    sheet.update_cell(encontrou_linha, store_base_col + 3, preco_pix) # preco_pix
            elif store == "netshoes":
                if preco_pix:
                    sheet.update_cell(encontrou_linha, store_base_col + 2, preco_pix) # preco_pix
                if parcelas:
                    sheet.update_cell(encontrou_linha, store_base_col + 3, parcelas) # parcelas
                
            # Garante que o produto esteja ativo se receber nova oferta
            sheet.update_cell(encontrou_linha, 2, "sim")
            print(f"✅ SUCESSO! Oferta da loja {store_label} atualizada na linha {encontrou_linha}.")
        except Exception as e:
            print(f"❌ Erro ao atualizar planilha: {e}")
        return

    # Se é um produto NOVO, preenche tudo e anexa nova linha
    print(f"✨ Cadastrando novo produto '{nome_extraido}' com ID '{slug_novo}'...")
    
    # Preço PIX e parcelamento específicos da loja
    preco_pix = ""
    if store != "amazon":
        preco_pix = input(f"Preço PIX na {store_label} (ex: R$ 450,00) [Enter para pular]: ").strip()
    parcelas = input(f"Condições de parcelamento na {store_label} (ex: 10x sem juros) [Enter para pular]: ").strip()

    # Determinar orçamento (budget)
    budget = "300a600"
    try:
        p_val = preco_pix or preco_extraido
        p = float(re.sub(r'[^\d,.-]', '', p_val).replace('.', '').replace(',', '.'))
        if p < 300: budget = "ate300"
        elif 300 <= p <= 600: budget = "300a600"
        elif 600 < p <= 1000: budget = "600a1000"
        else: budget = "acima1000"
    except:
        pass

    # Determinar gênero (sexo)
    sexo_final = ia_specs.get("sexo", "unissex")
    if sexo_cli:
        sexo_final = sexo_cli
        print(f"⚧️ Gênero forçado via argumento: {sexo_final}")
    else:
        print(f"⚧️ Gênero detectado: {sexo_final}")
        sexo_input = input("Alterar gênero? [m]asculino / [f]eminino / [u]nissex ou [Enter] para manter: ").strip().lower()
        if sexo_input in ["m", "masculino"]:
            sexo_final = "masculino"
        elif sexo_input in ["f", "feminino"]:
            sexo_final = "feminino"
        elif sexo_input in ["u", "unissex"]:
            sexo_final = "unissex"

    # Cria dicionário do produto
    prod_dict = {col: "" for col in SCHEMA_COLS}
    prod_dict["product_id"] = slug_novo
    prod_dict["ativo"] = "sim"
    prod_dict["marca"] = marca
    prod_dict["nome"] = nome_extraido
    prod_dict["versao"] = versao
    prod_dict["sexo"] = sexo_final
    prod_dict["img"] = img_extraida
    prod_dict["emoji"] = "👟"
    prod_dict["tags"] = ia_specs.get("tags", "")
    prod_dict["budget"] = budget
    prod_dict["nível"] = ia_specs.get("levels", "iniciante")
    prod_dict["pisada"] = ia_specs.get("pisadas", "neutra")
    prod_dict["terreno"] = ia_specs.get("terrenos", "asfalto")
    prod_dict["priors"] = ia_specs.get("priors", "custo")
    prod_dict["razão"] = ia_specs.get("reason", "")
    
    # Insere link, preco, pix, parcelas específicos da loja
    prod_dict[f"link_{store}"] = url
    prod_dict[f"preco_{store}"] = preco_extraido
    if store != "amazon":
        if store == "loja_oficial":
            prod_dict["preco_pix_oficial"] = preco_pix
        elif store == "netshoes":
            prod_dict["preco_pix_netshoes"] = preco_pix
    prod_dict[f"parcelas_{store}"] = parcelas

    nova_linha = [prod_dict[col] for col in SCHEMA_COLS]
    
    try:
        sheet.append_row(nova_linha)
        print("✅ SUCESSO! Novo produto adicionado com perfeição!")
    except Exception as e:
        print(f"❌ Erro ao adicionar linha na planilha: {e}")

# ==============================================================================
# 🎮 ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper TenisIdeal com exclusão lógica e fallback manual")
    parser.add_argument("url", nargs="?", help="URL do produto a ser inserido")
    parser.add_argument("--delete", help="Marca produto como inativo usando product_id")
    parser.add_argument("--reactivate", help="Reativa produto usando product_id")
    parser.add_argument("--sexo", choices=["masculino", "feminino", "unissex"], help="Força o gênero do produto")
    args = parser.parse_args()

    if args.delete:
        marcar_inativo(args.delete)
        sys.exit(0)
        
    if args.reactivate:
        reativar(args.reactivate)
        sys.exit(0)
        
    if args.url:
        processar_produto(args.url, sexo_cli=args.sexo)
    else:
        # Modo interativo padrão se nenhum argumento for fornecido
        print("=========================================")
        print("👟 SCRAPER POR URL + GOOGLE SHEETS 👟")
        print("=========================================")
        while True:
            url_input = input("\n🔗 Cole a URL do produto (ou digite 'sair' para encerrar): ").strip()
            if url_input.lower() == 'sair':
                print("👋 Programa finalizado.")
                break
            if not url_input.startswith("http"):
                print("URL inválida.")
                continue
            processar_produto(url_input)
