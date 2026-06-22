#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  TENISIDEAL — Automação nº 3: Gerador de Comparativos         ║
║  Pesquisa especificações técnicas de dois tênis na web,       ║
║  cruza com os links afiliados da planilha Google Sheets, e    ║
║  gera um artigo completo otimizado para SEO usando Gemini AI. ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import json
import time
import urllib.parse
import argparse
import unicodedata
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Tenta carregar gspread e google credentials
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# Tenta carregar o SDK do Gemini
try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

# ══════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════

SHEET_ID = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"
CREDENTIALS_FILE = "credenciais.json"

def carregar_env():
    """Lê variáveis do arquivo .env local se existir"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    os.environ[k] = v

carregar_env()

# ══════════════════════════════════════════════════════════════
# 🔗  CONEXÃO COM GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════

def conectar_planilha():
    """Conecta na planilha do Google Sheets usando credenciais.json"""
    if not HAS_GSPREAD:
        print("⚠️ Bibliotecas 'gspread' ou 'google-auth' não instaladas. Pulando consulta à planilha.")
        return None
        
    caminho_cred = Path(CREDENTIALS_FILE)
    if not caminho_cred.exists():
        print(f"⚠️ Arquivo de credenciais '{CREDENTIALS_FILE}' não encontrado. Pulando consulta à planilha.")
        return None

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
        print(f"⚠️ Erro ao conectar ao Google Sheets: {e}. Pulando consulta à planilha.")
        return None

def obter_registros(sheet):
    """Obtém registros da planilha de forma limpa e estruturada"""
    if not sheet:
        return []
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            return []
        headers = [h.strip() for h in all_values[0]]
        records = []
        for row in all_values[1:]:
            record = {}
            for idx, val in enumerate(row):
                if idx < len(headers):
                    header = headers[idx]
                    if header:
                        record[header] = val
            records.append(record)
        return records
    except Exception as e:
        print(f"⚠️ Erro ao ler dados da planilha: {e}")
        return []

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9\s]+', '', texto)

def buscar_produto_planilha(sheet, nome_busca):
    """Busca aproximada de um tênis na planilha"""
    registros = obter_registros(sheet)
    if not registros:
        return None
        
    nome_busca_norm = normalizar_texto(nome_busca)
    palavras_busca = set(nome_busca_norm.split())
    
    melhor_match = None
    max_intersection = 0
    
    for r in registros:
        marca = r.get("marca", "")
        nome = r.get("nome", "")
        versao = r.get("versao", "")
        
        full_name = f"{marca} {nome} {versao}"
        full_name_norm = normalizar_texto(full_name)
        palavras_full = set(full_name_norm.split())
        
        # Calcula interseção de palavras
        intersection = len(palavras_busca.intersection(palavras_full))
        if intersection > max_intersection:
            max_intersection = intersection
            melhor_match = r
            
    # Limiar mínimo de aceitação
    if max_intersection >= 2:
        print(f"   ✓ Encontrado na planilha: '{melhor_match.get('marca')} {melhor_match.get('nome')} {melhor_match.get('versao')}'")
        return melhor_match
        
    return None

# ══════════════════════════════════════════════════════════════
# 🔍  BUSCADOR DE ESPECIFICAÇÕES TÉCNICAS NA WEB
# ══════════════════════════════════════════════════════════════

def buscar_snippets_web(query):
    """Faz busca orgânica no DuckDuckGo HTML e retorna os snippets compilados"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    snippets = []
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            results = soup.find_all("div", class_="result")
            for res in results[:5]: # Top 5 resultados
                title_el = res.find("a", class_="result__a")
                snippet_el = res.find("a", class_="result__snippet")
                url_el = res.find("a", class_="result__url")
                
                title = title_el.text.strip() if title_el else ""
                snippet = snippet_el.text.strip() if snippet_el else ""
                res_url = url_el.text.strip() if url_el else ""
                
                snippets.append(f"Título: {title}\nURL: {res_url}\nSnippet: {snippet}\n")
    except Exception as e:
        print(f"⚠️ Erro ao pesquisar web para '{query}': {e}")
        
    return "\n".join(snippets)

def coletar_contexto_comparativo(modelo1, modelo2):
    """Gera contexto da web para ambos os tênis de corrida"""
    print(f"⌛ Coletando especificações técnicas na web...")
    
    # Modelo 1
    print(f"   - Pesquisando specs de: '{modelo1}'...")
    specs_m1 = buscar_snippets_web(f"{modelo1} review especificações técnicas peso drop sola entressola")
    time.sleep(0.5)
    
    # Modelo 2
    print(f"   - Pesquisando specs de: '{modelo2}'...")
    specs_m2 = buscar_snippets_web(f"{modelo2} review especificações técnicas peso drop sola entressola")
    time.sleep(0.5)
    
    # Comparação direta
    print(f"   - Pesquisando comparativo: '{modelo1} vs {modelo2}'...")
    specs_vs = buscar_snippets_web(f"{modelo1} vs {modelo2} comparativo diferença")
    
    contexto = f"""
=== INFORMAÇÕES DE CONTEXTO DA WEB ===

DADOS DE PESQUISA PARA: {modelo1}
{specs_m1}
--------------------------------------------------

DADOS DE PESQUISA PARA: {modelo2}
{specs_m2}
--------------------------------------------------

DADOS DE COMPARATIVO DIRETO ({modelo1} vs {modelo2}):
{specs_vs}
======================================
"""
    return contexto

# ══════════════════════════════════════════════════════════════
# 🤖  ESCRITA DE ARTIGO VIA GEMINI AI
# ══════════════════════════════════════════════════════════════

def obter_gemini_api_key():
    """Tenta obter a chave do Gemini do ambiente ou avisa"""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key

def gerar_artigo_comparativo(modelo1, modelo2, dados_m1, dados_m2, contexto_web, api_key):
    """Monta o prompt estruturado e gera o artigo comparativo no Gemini"""
    
    # Formata os dados da planilha para o prompt
    p1_info = "Não disponível na planilha (usar dados da web)"
    if dados_m1:
        p1_info = f"""
        Marca: {dados_m1.get('marca')}
        Nome: {dados_m1.get('nome')} {dados_m1.get('versao')}
        Preço Oficial/Pix: R$ {dados_m1.get('preco_pix_oficial') or dados_m1.get('preco_loja_oficial')}
        Link Amazon: {dados_m1.get('link_amazon')}
        Link Netshoes: {dados_m1.get('link_netshoes')}
        Link Loja Oficial: {dados_m1.get('link_loja_oficial')}
        Pisada: {dados_m1.get('pisada')}
        Terreno: {dados_m1.get('terreno')}
        """
        
    p2_info = "Não disponível na planilha (usar dados da web)"
    if dados_m2:
        p2_info = f"""
        Marca: {dados_m2.get('marca')}
        Nome: {dados_m2.get('nome')} {dados_m2.get('versao')}
        Preço Oficial/Pix: R$ {dados_m2.get('preco_pix_oficial') or dados_m2.get('preco_loja_oficial')}
        Link Amazon: {dados_m2.get('link_amazon')}
        Link Netshoes: {dados_m2.get('link_netshoes')}
        Link Loja Oficial: {dados_m2.get('link_loja_oficial')}
        Pisada: {dados_m2.get('pisada')}
        Terreno: {dados_m2.get('terreno')}
        """

    # Links afiliados a usar
    link_m1 = "https://amzn.to/exemplo"
    if dados_m1:
        link_m1 = dados_m1.get('link_amazon') or dados_m1.get('link_netshoes') or dados_m1.get('link_loja_oficial') or link_m1
        
    link_m2 = "https://amzn.to/exemplo"
    if dados_m2:
        link_m2 = dados_m2.get('link_amazon') or dados_m2.get('link_netshoes') or dados_m2.get('link_loja_oficial') or link_m2

    if not api_key or not HAS_GEMINI_SDK:
        print("\n⚠️ Chave GEMINI_API_KEY ausente ou SDK não instalado.")
        print("   -> Executando no Modo Offline / Fallback local para gerar artigo modelo estruturado.")
        return gerar_artigo_offline(modelo1, modelo2, link_m1, link_m2)

    print("\n🤖 Chamando Gemini AI ('gemini-2.0-flash') para redigir o artigo comparativo completo...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""
Você é um redator especialista em corrida de rua, SEO e marketing de afiliados. Escreve para o site "Tênis Ideal" (tenisideal.com.br).
Sua tarefa é escrever um artigo comparativo de SEO completo, aprofundado e altamente engajador entre dois modelos: "{modelo1}" e "{modelo2}".

Utilize as seguintes informações de contexto e dados técnicos extraídos da web e da planilha do site:

--- DADOS DA PLANILHA PARA TÊNIS 1 ({modelo1}):
{p1_info}

--- DADOS DA PLANILHA PARA TÊNIS 2 ({modelo2}):
{p2_info}

--- CONTEXTO EXTRAÍDO DA BUSCA WEB (Specs Reais):
{contexto_web}

--- DIRETRIZES DO ARTIGO:
1. IDIOMA: Português do Brasil (PT-BR), tom amigável, especialista, confiável e focado no corredor.
2. ESTRUTURA OBRIGATÓRIA (Use Markdown):
   - # [Título SEO atraente com H1] (ex: "Olympikus Corre 3 vs Kiprun KD900: Qual Tênis de Corrida Escolher?")
   - **Introdução**: Apresente brevemente a proposta de cada tênis e para quem se destinam.
   - **Tabela Comparativa de Especificações**: Crie uma tabela Markdown contendo as colunas: Característica, {modelo1}, {modelo2}. Inclua Peso (g), Drop (mm), Espessura da Sola (Stack Height), Placa de Carbono (Sim/Não), Espuma da Entressola, Preço Médio e Link de Compra.
   - ## Entressola e Amortecimento: Compare o tipo de amortecimento, retorno de energia e maciez/firmeza de ambos.
   - ## Cabedal e Ajuste: Compare o conforto, respirabilidade e firmeza do ajuste do mesh/knit de cada um.
   - ## Solado e Durabilidade: Avalie a borracha, aderência e durabilidade dos solados.
   - ## Prós e Contras: Crie listas de prós e contras para cada modelo.
   - ## Veredicto: Qual Comprar?: Crie subseções detalhando quem deve escolher o {modelo1} (ex: iniciantes, treinos diários) e quem deve escolher o {modelo2} (ex: velocidade, maratona).
3. CTAs E BOTÕES DE COMPRA: Insira chamadas para ação claras ao longo do artigo usando os links de afiliados corretos:
   - Link de compra do {modelo1}: {link_m1}
   - Link de compra do {modelo2}: {link_m2}
   Use links em formato markdown, ex: `[Ver preço do {modelo1} na Amazon]({link_m1})` ou Netshoes.
4. SEO: Use palavras-chave naturalmente como "tênis de corrida custo benefício", "amortecimento", "comparativo de tênis", "peso e drop". Não invente especificações técnicas, se houver conflito nos dados web, use os dados mais citados ou mais lógicos.

Escreva o artigo completo em formato Markdown abaixo:
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Erro ao chamar API do Gemini: {e}. Usando fallback offline.")
        return gerar_artigo_offline(modelo1, modelo2, link_m1, link_m2)

def gerar_artigo_offline(modelo1, modelo2, link_m1, link_m2):
    """Gera um artigo comparativo modelo de forma estruturada offline"""
    artigo = f"""# {modelo1} vs {modelo2}: Qual Tênis de Corrida Vale Mais a Pena?

Se você está na dúvida entre o **{modelo1}** e o **{modelo2}**, veio ao lugar certo. Ambos são excelentes tênis de corrida, mas foram desenvolvidos para perfis de corredores e objetivos diferentes. 

Neste comparativo completo, vamos colocar lado a lado suas especificações técnicas, pontos positivos, negativos e o veredicto de qual escolher com base no seu tipo de treino.

---

## Tabela Comparativa de Especificações

| Característica | {modelo1} | {modelo2} |
| :--- | :--- | :--- |
| **Peso** | ~230g (variação tamanho) | ~250g (variação tamanho) |
| **Drop** | 8 mm | 6 mm |
| **Placa de Carbono** | Não | Não (Verificar modelo) |
| **Entressola** | EVA Premium / Nitrogênio | Espuma Responsiva |
| **Preço Médio** | Sob consulta | Sob consulta |
| **Onde Comprar** | [Ver Preço na Loja]({link_m1}) | [Ver Preço na Loja]({link_m2}) |

---

## Entressola e Amortecimento

O **{modelo1}** é muito conhecido por entregar um amortecimento focado em conforto e transições suaves. A entressola é macia, ideal para rodagens diárias e corredores iniciantes a intermediários que buscam proteção para as articulações.

Por outro lado, o **{modelo2}** apresenta uma batida ligeiramente mais firme e responsiva. Ele foi desenhado para quem busca maior retorno de energia nas passadas, tornando-se uma excelente opção para treinos de ritmo, tiros ou provas onde a velocidade é prioridade.

---

## Cabedal e Ajuste (Conforto)

No cabedal, o **{modelo1}** conta com um mesh tecnológico respirável que abraça o pé de forma confortável, oferecendo excelente espaço na caixa de dedos (toe box).

O **{modelo2}** busca um ajuste mais esportivo/abraçado (estilo meia ou de competição), garantindo estabilidade lateral em curvas e passadas mais fortes, ideal para quem gosta de sentir o tênis bem firme no pé.

---

## Solado e Durabilidade

A borracha do solado do **{modelo1}** oferece uma tração exemplar em asfalto molhado e esteiras, com alta resistência à abrasão. 

O **{modelo2}** economiza borracha em áreas de menor contato para reduzir o peso, focando a tração nas zonas de maior desgaste, o que garante excelente aderência sem comprometer a leveza.

---

## Prós e Contras

### {modelo1}
*   **Prós:** Excelente custo-benefício, amortecimento macio, forma confortável.
*   **Contras:** Menos responsivo para treinos rápidos de tiro.

### {modelo2}
*   **Prós:** Ótimo retorno de energia, ajuste firme, excelente estabilidade.
*   **Contras:** Preço ligeiramente superior, batida de passada mais firme.

---

## Veredicto: Qual Comprar?

### Escolha o **{modelo1}** se você:
*   Está iniciando na corrida e busca um tênis versátil para rodagens diárias.
*   Prioriza conforto e amortecimento macio em ritmos moderados.
*   Busca o melhor custo-benefício do mercado de corrida.
*   [Clique aqui para comprar o {modelo1} com desconto]({link_m1})

### Escolha o **{modelo2}** se você:
*   Já corre e busca um tênis para treinos de velocidade e tempo run.
*   Prefere uma entressola responsiva com maior retorno de energia.
*   Busca um tênis de performance firme e estável.
*   [Clique aqui para comprar o {modelo2} com desconto]({link_m2})
"""
    return artigo

# ══════════════════════════════════════════════════════════════
# 🚀  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Automação 3 — Gerador de Comparativos SEO TênisIdeal")
    parser.add_argument("--modelo1", type=str, required=True, help="Nome do primeiro modelo de tênis")
    parser.add_argument("--modelo2", type=str, required=True, help="Nome do segundo modelo de tênis")
    parser.add_argument("--api-key", type=str, help="Chave API Gemini")
    args = parser.parse_args()

    m1 = args.modelo1.strip()
    m2 = args.modelo2.strip()

    print("=" * 60)
    print(f"  TENISIDEAL — Comparativo SEO: {m1} vs {m2}")
    print("=" * 60)
    print()

    # Passo 1: Tenta ler links afiliados e dados reais da planilha do Sheets
    print("📂 Conectando ao Google Sheets...")
    sheet = conectar_planilha()
    dados_m1 = None
    dados_m2 = None
    
    if sheet:
        print(f"🔍 Procurando tênis '{m1}' na planilha...")
        dados_m1 = buscar_produto_planilha(sheet, m1)
        
        print(f"🔍 Procurando tênis '{m2}' na planilha...")
        dados_m2 = buscar_produto_planilha(sheet, m2)
        
        if not dados_m1:
            print(f"   ℹ️ '{m1}' não localizado na planilha. Usando dados da web.")
        if not dados_m2:
            print(f"   ℹ️ '{m2}' não localizado na planilha. Usando dados da web.")
    else:
        print("   ℹ️ Continuando sem integração com Google Sheets.")

    # Passo 2: Coleta especificações técnicas na Web via DuckDuckGo
    contexto_web = coletar_contexto_comparativo(m1, m2)

    # Passo 3: Envia para o Gemini redigir o artigo SEO com os links corretos
    api_key = args.api_key or obter_gemini_api_key()
    artigo = gerar_artigo_comparativo(m1, m2, dados_m1, dados_m2, contexto_web, api_key)

    # Passo 4: Salva o artigo gerado em Markdown
    pasta_saida = Path("artigos_gerados")
    if not pasta_saida.exists():
        pasta_saida.mkdir()

    slug_m1 = normalizar_texto(m1).replace(" ", "-")
    slug_m2 = normalizar_texto(m2).replace(" ", "-")
    nome_arquivo = pasta_saida / f"comparativo_{slug_m1}_vs_{slug_m2}.md"

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(artigo)

    print()
    print("=" * 60)
    print("  ✅ ARTIGO COMPARATIVO GERADO COM SUCESSO!")
    print("=" * 60)
    print(f"  📄 Arquivo gerado: {nome_arquivo}")
    print("=" * 60)

if __name__ == "__main__":
    main()
