#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  TENISIDEAL — Automação nº 2: Pesquisa de Pautas e Palavras   ║
║  Expande palavras-chave usando Google Suggest, avalia a       ║
║  concorrência na SERP e gera um calendário editorial premium  ║
║  com briefings gerados por IA.                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import csv
import json
import time
import urllib.parse
import argparse
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Tenta carregar o SDK do Gemini
try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

# ══════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÕES E CARREGAMENTO DE ENVIROMENT
# ══════════════════════════════════════════════════════════════

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

# Sementes padrão se o usuário não digitar nada
SEMENTES_PADRAO = [
    "tênis de corrida",
    "melhor tênis de corrida",
    "tênis de corrida barato",
    "tênis para pisada pronada"
]

# Lista de grandes varejistas e marcas dominantes no Brasil (para cálculo de concorrência)
GRANDES_VAREJOS = [
    "netshoes.com.br", "centauro.com.br", "decathlon.com.br", "amazon.com.br",
    "mercadolivre.com.br", "dafiti.com.br", "nike.com.br", "adidas.com.br",
    "asics.com.br", "olympikus.com.br", "mizuno.com.br", "fila.com.br",
    "underarmour.com.br", "puma.com", "magazineluiza.com.br", "casasbahia.com.br",
    "americanas.com.br", "worldtennis.com.br"
]

# ══════════════════════════════════════════════════════════════
# 🔍  GOOGLE SUGGEST (AUTOCOMPLETE) & EXPANSÃO
# ══════════════════════════════════════════════════════════════

def fetch_google_suggest(query):
    """Consulta a API pública do Google Autocomplete"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(query)}&hl=pt"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data[1] # Retorna a lista de sugestões sugeridas
    except Exception as e:
        pass
    return []

def expandir_sementes(sementes):
    """Expande as palavras-chave semente em centenas de variações de cauda longa"""
    print("=" * 60)
    print("  🚀 EXPANDINDO PALAVRAS-CHAVE VIA GOOGLE SUGGEST")
    print("=" * 60)
    
    palavras_encontradas = {}
    
    for semente in sementes:
        semente = semente.strip().lower()
        if not semente:
            continue
            
        print(f"\n🌱 Processando semente: '{semente}'...")
        
        # 1. Sugestões diretas da semente
        sugs = fetch_google_suggest(semente)
        for idx, sug in enumerate(sugs):
            val = sug.strip().lower()
            if val not in palavras_encontradas:
                palavras_encontradas[val] = {
                    "source": "direta",
                    "rank": idx + 1,
                    "seed": semente
                }
                
        # 2. Sugestões combinadas com letras (semente + [a-z])
        print("   - Coletando variações alfabéticas...")
        for letra in "abcdefghijklmnopqrstuvwxyz":
            q = f"{semente} {letra}"
            sugs = fetch_google_suggest(q)
            for idx, sug in enumerate(sugs):
                val = sug.strip().lower()
                if val not in palavras_encontradas:
                    palavras_encontradas[val] = {
                        "source": "letra",
                        "rank": idx + 1,
                        "seed": semente
                    }
            time.sleep(0.08) # Pequena pausa para evitar limites de taxa
            
        # 3. Sugestões com modificadores comuns de compra/pesquisa
        print("   - Coletando variações com modificadores...")
        modificadores = ["melhor", "barato", "iniciante", "masculino", "feminino", "como", "qual", "versus", "vs", "para", "corrida", "amortecimento", "custo beneficio", "caminhada"]
        for mod in modificadores:
            q = f"{semente} {mod}"
            sugs = fetch_google_suggest(q)
            for idx, sug in enumerate(sugs):
                val = sug.strip().lower()
                if val not in palavras_encontradas:
                    palavras_encontradas[val] = {
                        "source": "modificador",
                        "rank": idx + 1,
                        "seed": semente
                    }
            time.sleep(0.08)

    # Filtragem e limpeza de termos irrelevantes
    resultados_filtrados = []
    ignorar_termos = ["mercado livre", "shopee", "shein", "aliexpress", "olx", "enjoei", "netshoes reclame aqui"]
    
    for kw, meta in palavras_encontradas.items():
        # Remove termos muito curtos (menos de 3 palavras) ou que não contenham a semente/tênis/corrida
        palavras = kw.split()
        if len(palavras) < 3:
            continue
            
        # Filtra marcas/lojas concorrentes indesejadas
        if any(term in kw for term in ignorar_termos):
            continue
            
        # Calcula um índice de interesse preliminar (1-10) baseado em como apareceu
        if meta["source"] == "direta":
            interesse = max(10 - meta["rank"], 6)
        elif meta["source"] == "modificador":
            interesse = max(8 - meta["rank"], 4)
        else:
            interesse = max(6 - meta["rank"], 2)
            
        resultados_filtrados.append({
            "keyword": kw,
            "seed": meta["seed"],
            "interesse_index": interesse
        })

    print(f"\n✅ Total de palavras únicas geradas e filtradas: {len(resultados_filtrados)}")
    return resultados_filtrados

# ══════════════════════════════════════════════════════════════
# 🧮  ANÁLISE DE CONCORRÊNCIA NA SERP (DUCKDUCKGO HTML)
# ══════════════════════════════════════════════════════════════

def analisar_concorrencia_serp(keyword):
    """Mede a concorrência na SERP analisando a presença de grandes e-commerces e otimização de títulos"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(keyword)}"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            # Fallback seguro caso haja bloqueio ou erro
            return 50, "Média", []
            
        soup = BeautifulSoup(r.text, "html.parser")
        results = soup.find_all("div", class_="result")
        
        if not results:
            return 30, "Baixa", []
            
        ecommerces_count = 0
        titles_optimized = 0
        details = []
        
        kw_words = set(re.findall(r'\w+', keyword.lower()))
        
        # Analisa os top 8 resultados
        for idx, res in enumerate(results[:8]):
            title_el = res.find("a", class_="result__a")
            url_el = res.find("a", class_="result__url")
            snippet_el = res.find("a", class_="result__snippet")
            
            title = title_el.text.strip() if title_el else ""
            res_url = url_el.text.strip().lower() if url_el else ""
            snippet = snippet_el.text.strip() if snippet_el else ""
            
            # Verifica se o site é e-commerce gigante
            is_ecommerce = False
            for domain in GRANDES_VAREJOS:
                if domain in res_url:
                    is_ecommerce = True
                    break
            if is_ecommerce:
                ecommerces_count += 1
                
            # Verifica se o título do resultado contém a maioria das palavras-chave
            title_words = set(re.findall(r'\w+', title.lower()))
            match_ratio = len(kw_words.intersection(title_words)) / len(kw_words) if kw_words else 0
            is_optimized = match_ratio >= 0.70
            if is_optimized:
                titles_optimized += 1
                
            details.append({
                "rank": idx + 1,
                "title": title,
                "url": "https://" + url_el.text.strip() if url_el else "",
                "snippet": snippet,
                "is_ecommerce": is_ecommerce,
                "is_optimized": is_optimized
            })
            
        # Pontuação de concorrência (0 a 100)
        # 1. Presença de grandes lojas: até 70 pontos (+8.75 por e-commerce nos top 8)
        score_ecom = min(ecommerces_count * 8.75, 70.0)
        # 2. Otimização de títulos dos concorrentes: até 30 pontos (+3.75 por título otimizado)
        score_title = min(titles_optimized * 3.75, 30.0)
        
        comp_score = int(round(score_ecom + score_title))
        
        # Classificação qualitativa
        if comp_score < 35:
            dificuldade = "Baixa"
        elif comp_score < 65:
            dificuldade = "Média"
        else:
            dificuldade = "Alta"
            
        return comp_score, dificuldade, details
        
    except Exception as e:
        # Se der erro de rede, retorna valores padrão
        return 50, "Média", []

def processar_candidatos(candidatos, max_analise=30):
    """Filtra os candidatos por relevância básica e analisa detalhadamente na SERP"""
    print(f"\n🔍 Selecionando os {max_analise} melhores candidatos para análise de SERP...")
    
    # Heurística rápida de relevância para filtrar
    for c in candidatos:
        kw = c["keyword"]
        score = 0
        
        # Palavras comerciais que geram receita direta com links afiliados
        if any(w in kw for w in ["melhor", "melhores"]):
            score += 15
        if any(w in kw for w in ["barato", "baratos", "custo beneficio", "preco", "preço", "ate", "até"]):
            score += 12
        if any(w in kw for w in ["vs", "versus", "comparativo", "diferença"]):
            score += 10
        if any(w in kw for w in ["masculino", "feminino"]):
            score += 8
        if any(w in kw for w in ["pisada", "amortecimento", "placa", "corrida"]):
            score += 6
            
        # Penaliza termos muito genéricos ou informacionais frios
        if any(w in kw for w in ["como lavar", "como secar", "como amarrar", "significado"]):
            score -= 10
            
        c["relevance_score"] = score
        
    # Ordena por relevância e interesse
    candidatos.sort(key=lambda x: (-x["relevance_score"], -x["interesse_index"]))
    selecionados = candidatos[:max_analise]
    
    print(f"⌛ Analisando concorrência das SERPs (com delay de 0.5s para evitar bloqueio)...")
    analisados = []
    
    for i, c in enumerate(selecionados):
        kw = c["keyword"]
        print(f"   [{i+1}/{len(selecionados)}] '{kw}'...")
        
        comp_score, dificuldade, serp_details = analisar_concorrencia_serp(kw)
        
        # Pontuação de Oportunidade: prioriza concorrência baixa e volume/interesse alto
        # Fórmula: (100 - concorrência) + (interesse * 2)
        oportunidade = (100 - comp_score) + (c["interesse_index"] * 2)
        
        analisados.append({
            "keyword": kw,
            "seed": c["seed"],
            "interesse_index": c["interesse_index"],
            "concorrencia_score": comp_score,
            "dificuldade": dificuldade,
            "oportunidade_score": oportunidade,
            "serp": serp_details
        })
        time.sleep(0.5)
        
    # Ordena os analisados pelo Score de Oportunidade
    analisados.sort(key=lambda x: -x["oportunidade_score"])
    return analisados[:10]

# ══════════════════════════════════════════════════════════════
# 🤖  INTEGRAÇÃO COM GEMINI AI (BRIEFING E TÍTULO)
# ══════════════════════════════════════════════════════════════

def obter_gemini_api_key():
    """Tenta obter a chave do Gemini do ambiente ou avisa"""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key

def gerar_briefings_com_gemini(top_10, api_key):
    """Envia as 10 pautas para o Gemini gerar os títulos SEO, intenção e briefings estruturados"""
    if not api_key or not HAS_GEMINI_SDK:
        print("\n⚠️ Chave GEMINI_API_KEY ausente ou SDK não instalado.")
        print("   -> Executando no Modo Offline / Fallback local para gerar os briefings automaticamente.")
        return gerar_briefings_offline(top_10)
        
    print("\n🤖 Integrando com Gemini AI ('gemini-2.0-flash') para gerar os briefings...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = """
Você é um analista especialista em SEO e marketing de afiliados de tênis de corrida (site: tenisideal.com.br).
Recebi as seguintes 10 palavras-chave com potencial de receita. Para CADA UMA delas, você deve gerar:
1. Um Título SEO altamente clicável e atraente (com até 65 caracteres) em Português do Brasil.
2. A Intenção de Busca ("Informacional", "Comercial" ou "Transacional").
3. Um Esboço/Briefing de Conteúdo estruturado em tópicos contendo subtítulos H2 e H3 recomendados, pontos chaves a abordar e modelos de tênis ideais para incluir.
4. Modelos de tênis sugeridos (ex: "Olympikus Corre 3", "Nike Pegasus 40", "Mizuno Wave Rider 27").

Forneça a resposta OBRIGATORIAMENTE em formato JSON válido contendo uma lista de objetos chamada "briefings".
Cada objeto deve conter exatamente os campos abaixo:
- keyword: string (a palavra-chave original exata)
- intent: string ("Informacional", "Comercial" ou "Transacional")
- seo_title: string (o título proposto)
- outline: array de strings (cada elemento é uma seção do artigo, ex: "## H2: Introdução", "### H3: Peso e Drop")
- suggested_shoes: array de strings (nomes dos modelos recomendados)

Lista de palavras-chave:
"""
    for idx, item in enumerate(top_10):
        prompt += f"{idx+1}. {item['keyword']}\n"
        
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Limpa possíveis blocos de código markdown do JSON
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        briefings_dict = {item["keyword"]: item for item in data.get("briefings", [])}
        
        # Mescla de volta com os dados de concorrência
        for item in top_10:
            kw = item["keyword"]
            if kw in briefings_dict:
                item["intent"] = briefings_dict[kw].get("intent", "Comercial")
                item["seo_title"] = briefings_dict[kw].get("seo_title", kw.title())
                item["outline"] = briefings_dict[kw].get("outline", [])
                item["suggested_shoes"] = briefings_dict[kw].get("suggested_shoes", [])
            else:
                # Fallback individual se a IA esqueceu alguma
                item["intent"] = "Comercial"
                item["seo_title"] = kw.title()
                item["outline"] = ["## Introdução", "## Como escolher", "## Veredicto"]
                item["suggested_shoes"] = []
                
        print("✅ Briefings gerados via Gemini com sucesso!")
        return top_10
    except Exception as e:
        print(f"❌ Erro ao chamar API do Gemini: {e}. Usando fallback offline.")
        return gerar_briefings_offline(top_10)

def gerar_briefings_offline(top_10):
    """Gera briefings baseados em templates offline se não houver Gemini disponível"""
    for item in top_10:
        kw = item["keyword"]
        
        # Detecta intenção
        if any(w in kw for w in ["vs", "versus", "comparativo", "diferenca", "diferença"]):
            intent = "Comercial"
            seo_title = f"{kw.title().replace('Vs', 'vs')} — Qual Vale Mais a Pena em 2026?"
            outline = [
                "## 1. Introdução: O Confronto Direto",
                "## 2. Tabela Comparativa de Especificações",
                "## 3. Amortecimento e Entressola: As Diferenças",
                "## 4. Conforto do Cabedal e Ajuste no Pé",
                "## 5. Durabilidade e Aderência do Solado",
                "## 6. Custo-Benefício: Comparativo de Preços",
                "## 7. Veredicto Final: Qual Tênis Você Deve Escolher?"
            ]
            suggested_shoes = [kw.split("vs")[0].strip().title(), kw.split("vs")[-1].strip().title()] if "vs" in kw else []
            
        elif any(w in kw for w in ["melhor", "melhores", "barato", "ate", "até"]):
            intent = "Comercial"
            seo_title = f"Os {kw.title()} que Valem a Pena em 2026"
            outline = [
                "## 1. Introdução: Por que Escolher com Cuidado?",
                "## 2. Fatores Críticos a Analisar (Amortecimento, Peso, Drop)",
                "## 3. Tabela Resumo dos Selecionados",
                "## 4. Análise Detalhada dos Melhores Modelos",
                "## 5. Qual o Mais Barato do Ranking?",
                "## 6. Como Identificar Sua Pisada Corrida",
                "## 7. Conclusão: Escolha do Editor"
            ]
            suggested_shoes = ["Olympikus Corre 3", "Nike Pegasus 40", "Mizuno Wave Rider 27", "Adidas Duramo Speed"]
            
        else:
            intent = "Informacional"
            seo_title = f"{kw.title()}: Guia Completo e Prático para Corredores"
            outline = [
                "## 1. Introdução ao Tema",
                "## 2. O que a Ciência/Treinadores Recomendam",
                "## 3. Benefícios Práticos na Sua Corrida",
                "## 4. Erros Comuns a Evitar",
                "## 5. Melhores Equipamentos Recomendados",
                "## 6. Dicas Passo a Passo",
                "## 7. Perguntas Frequentes (FAQ)"
            ]
            suggested_shoes = ["Olympikus Corre 3", "Asics Novablast 4"]
            
        item["intent"] = intent
        item["seo_title"] = seo_title
        item["outline"] = outline
        item["suggested_shoes"] = suggested_shoes
        
    return top_10

# ══════════════════════════════════════════════════════════════
# 🎨  GERAÇÃO DOS RELATÓRIOS (HTML E CSV)
# ══════════════════════════════════════════════════════════════

def gerar_relatorio_html(dados, sementes):
    """Gera um relatório interativo moderno com tema escuro e visual premium"""
    data_hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")
    
    # Prepara os cards de cada pauta
    cards_html = ""
    for i, d in enumerate(dados):
        # Cores para concorrência
        if d["concorrencia_score"] < 35:
            badge_comp = "low"
            badge_label = "Fácil"
        elif d["concorrencia_score"] < 65:
            badge_comp = "medium"
            badge_label = "Média"
        else:
            badge_comp = "high"
            badge_label = "Difícil"
            
        # Cores para intenção
        intent_class = d["intent"].lower().split()[0]
        
        # Prepara a lista de esboços em HTML
        outline_html = "".join(f"<li>{line}</li>" for line in d["outline"])
        
        # Prepara a lista de tênis recomendados em HTML
        shoes_html = "".join(f'<span class="shoe-tag">{shoe}</span>' for shoe in d["suggested_shoes"] if shoe)
        if not shoes_html:
            shoes_html = '<span class="shoe-tag none">Nenhum tênis específico</span>'
            
        # Lista dos resultados reais do DuckDuckGo para o usuário ver
        serp_html = ""
        for r in d["serp"][:4]: # Mostra os top 4 concorrentes
            ecommerce_badge = '<span class="badge-ecom">Loja</span>' if r["is_ecommerce"] else '<span class="badge-blog">Blog/Nicho</span>'
            title_opt_badge = '✓ Título Otimizado' if r["is_optimized"] else '✗ Sem otimização exata'
            domain_name = r["url"].replace("https://www.", "").replace("https://", "").split("/")[0]
            serp_html += f"""
            <div class="serp-item">
                <span class="serp-rank">#{r['rank']}</span>
                <div class="serp-content">
                    <a href="{r['url']}" target="_blank" class="serp-title">{r['title']}</a>
                    <div class="serp-meta">
                        <span class="serp-url">{domain_name}</span>
                        {ecommerce_badge}
                        <span class="serp-opt {r['is_optimized']}">{title_opt_badge}</span>
                    </div>
                </div>
            </div>"""
            
        cards_html += f"""
        <div class="card card-comp-{badge_comp}" data-comp="{badge_label.lower()}">
            <div class="card-header">
                <span class="rank-number">#{i+1}</span>
                <div class="header-main">
                    <h3>{d['seo_title']}</h3>
                    <p class="kw-label">Palavra-chave: <strong>{d['keyword']}</strong></p>
                </div>
                <div class="badges-wrap">
                    <span class="badge intent-{intent_class}">{d['intent']}</span>
                    <span class="badge comp-{badge_comp}">{badge_label} ({d['concorrencia_score']}/100)</span>
                </div>
            </div>
            
            <div class="card-body">
                <div class="analysis-section">
                    <div class="metric-mini">
                        <div class="metric-val">{d['interesse_index']}/10</div>
                        <div class="metric-lbl">Índice de Interesse</div>
                    </div>
                    <div class="metric-mini">
                        <div class="metric-val">{d['oportunidade_score']}</div>
                        <div class="metric-lbl">Score Oportunidade</div>
                    </div>
                </div>
                
                <div class="briefing-toggle-btn" onclick="toggleBriefing(this)">
                    <span>Ver Briefing e Concorrentes</span>
                    <svg viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"/></svg>
                </div>
                
                <div class="briefing-drawer hidden">
                    <div class="drawer-grid">
                        <div class="briefing-left">
                            <h4 class="sub-title">📝 Estrutura Sugerida do Artigo</h4>
                            <ul class="outline-list">
                                {outline_html}
                            </ul>
                            
                            <h4 class="sub-title" style="margin-top:20px;">👟 Tênis Sugeridos para Incluir</h4>
                            <div class="shoes-wrap">
                                {shoes_html}
                            </div>
                        </div>
                        
                        <div class="briefing-right">
                            <h4 class="sub-title">🔍 Quem está ranqueando na busca (Top 4)</h4>
                            <div class="serp-list">
                                {serp_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""

    # Estatísticas rápidas
    total_low = sum(1 for d in dados if d["concorrencia_score"] < 35)
    total_med = sum(1 for d in dados if 35 <= d["concorrencia_score"] < 65)
    total_high = sum(1 for d in dados if d["concorrencia_score"] >= 65)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Calendário Editorial — TênisIdeal</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Bebas+Neue&display=swap');

  :root {{
    --bg: #090b0f;
    --card-bg: rgba(22, 28, 45, 0.5);
    --border: rgba(255, 255, 255, 0.08);
    --border-hover: rgba(255, 255, 255, 0.15);
    --text: #f1f3f9;
    --muted: #8b9bb4;
    --green: #10B981;
    --yellow: #F59E0B;
    --red: #EF4444;
    --blue: #3B82F6;
    --purple: #8B5CF6;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Outfit', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 40px 24px;
    background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%),
                      radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 40%);
  }}

  .container {{
    max-width: 900px;
    margin: 0 auto;
  }}

  .header {{
    text-align: center;
    margin-bottom: 40px;
  }}

  .logo {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.5rem;
    letter-spacing: 2px;
    color: var(--text);
    margin-bottom: 8px;
  }}

  .logo span {{ color: var(--green); }}

  .header p {{
    color: var(--muted);
    font-size: 0.95rem;
  }}

  .tag-seeds {{
    margin-top: 12px;
    display: flex;
    justify-content: center;
    gap: 8px;
    flex-wrap: wrap;
  }}

  .seed-badge {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    padding: 4px 12px;
    border-radius: 99px;
    font-size: 0.8rem;
    color: var(--muted);
  }}

  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }}

  .stat-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    backdrop-filter: blur(8px);
  }}

  .stat-val {{
    font-size: 2.25rem;
    font-weight: 700;
    margin-bottom: 4px;
  }}

  .stat-lbl {{
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
  }}

  .stat-card.green .stat-val {{ color: var(--green); }}
  .stat-card.yellow .stat-val {{ color: var(--yellow); }}
  .stat-card.red .stat-val {{ color: var(--red); }}
  .stat-card.blue .stat-val {{ color: var(--blue); }}

  .filters-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border);
    padding: 12px 20px;
    border-radius: 12px;
  }}

  .filters-lbl {{
    font-size: 0.9rem;
    color: var(--muted);
  }}

  .filter-btns {{
    display: flex;
    gap: 8px;
  }}

  .filter-btn {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    padding: 6px 14px;
    border-radius: 8px;
    color: var(--muted);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }}

  .filter-btn:hover, .filter-btn.active {{
    background: var(--text);
    color: var(--bg);
    border-color: var(--text);
  }}

  .cards-list {{
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 24px;
    transition: all 0.3s;
    backdrop-filter: blur(8px);
  }}

  .card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  }}

  .card-comp-low {{ border-left: 4px solid var(--green); }}
  .card-comp-medium {{ border-left: 4px solid var(--yellow); }}
  .card-comp-high {{ border-left: 4px solid var(--red); }}

  .card-header {{
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 16px;
  }}

  .rank-number {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    color: var(--muted);
    flex-shrink: 0;
  }}

  .header-main {{
    flex-grow: 1;
  }}

  .header-main h3 {{
    font-size: 1.15rem;
    font-weight: 600;
    line-height: 1.4;
    margin-bottom: 4px;
  }}

  .kw-label {{
    font-size: 0.85rem;
    color: var(--muted);
  }}

  .kw-label strong {{
    color: var(--text);
  }}

  .badges-wrap {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
  }}

  .badge {{
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .intent-informacional {{ background: rgba(59, 130, 246, 0.15); color: var(--blue); border: 1px solid rgba(59, 130, 246, 0.3); }}
  .intent-comercial {{ background: rgba(139, 92, 246, 0.15); color: var(--purple); border: 1px solid rgba(139, 92, 246, 0.3); }}
  .intent-transacional {{ background: rgba(245, 158, 11, 0.15); color: var(--yellow); border: 1px solid rgba(245, 158, 11, 0.3); }}

  .comp-low {{ background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); }}
  .comp-medium {{ background: rgba(245, 158, 11, 0.15); color: var(--yellow); border: 1px solid rgba(245, 158, 11, 0.3); }}
  .comp-high {{ background: rgba(239, 68, 68, 0.15); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); }}

  .card-body {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  .analysis-section {{
    display: flex;
    gap: 24px;
    background: rgba(0, 0, 0, 0.15);
    padding: 12px 20px;
    border-radius: 12px;
  }}

  .metric-mini {{
    display: flex;
    flex-direction: column;
  }}

  .metric-val {{
    font-size: 1.1rem;
    font-weight: 600;
  }}

  .metric-lbl {{
    font-size: 0.75rem;
    color: var(--muted);
  }}

  .briefing-toggle-btn {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--muted);
    transition: all 0.2s;
  }}

  .briefing-toggle-btn:hover {{
    background: rgba(255, 255, 255, 0.07);
    color: var(--text);
  }}

  .briefing-toggle-btn svg {{
    width: 16px;
    height: 16px;
    fill: currentColor;
    transition: transform 0.2s;
  }}

  .briefing-toggle-btn.active svg {{
    transform: rotate(180deg);
  }}

  .briefing-drawer {{
    margin-top: 10px;
    border-top: 1px dashed var(--border);
    padding-top: 16px;
  }}

  .briefing-drawer.hidden {{
    display: none;
  }}

  .drawer-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }}

  @media (max-width: 768px) {{
    .drawer-grid {{
      grid-template-columns: 1fr;
    }}
    .card-header {{
      flex-direction: column;
      gap: 12px;
    }}
    .badges-wrap {{
      align-self: flex-start;
    }}
  }}

  .sub-title {{
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--muted);
    margin-bottom: 12px;
    font-weight: 600;
  }}

  .outline-list {{
    list-style: none;
    font-size: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .outline-list li {{
    padding-left: 14px;
    position: relative;
    line-height: 1.4;
  }}

  .outline-list li::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: var(--green);
  }}

  .shoes-wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}

  .shoe-tag {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    color: var(--text);
  }}

  .shoe-tag.none {{
    color: var(--muted);
    border-style: dashed;
  }}

  .serp-list {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .serp-item {{
    display: flex;
    gap: 12px;
    background: rgba(0,0,0,0.1);
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.02);
  }}

  .serp-rank {{
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--muted);
    width: 20px;
    flex-shrink: 0;
  }}

  .serp-content {{
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .serp-title {{
    color: var(--blue);
    font-size: 0.8rem;
    font-weight: 500;
    text-decoration: none;
    line-height: 1.3;
  }}

  .serp-title:hover {{
    text-decoration: underline;
  }}

  .serp-meta {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
    font-size: 0.7rem;
    margin-top: 4px;
  }}

  .serp-url {{
    color: var(--muted);
  }}

  .badge-ecom, .badge-blog {{
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 600;
  }}

  .badge-ecom {{ background: rgba(239, 68, 68, 0.1); color: var(--red); }}
  .badge-blog {{ background: rgba(16, 185, 129, 0.1); color: var(--green); }}

  .serp-opt {{
    color: var(--muted);
  }}
  .serp-opt.True {{
    color: var(--green);
    font-weight: 500;
  }}

  .footer {{
    text-align: center;
    margin-top: 60px;
    color: var(--muted);
    font-size: 0.8rem;
  }}
</style>
</head>
<body>

<div class="container">

  <div class="header">
    <div class="logo">Tênis<span>ideal</span></div>
    <h1>Calendário Editorial Mensal</h1>
    <p>As 10 melhores oportunidades de palavras-chave selecionadas por ROI e baixa concorrência.</p>
    <p style="margin-top:4px">Gerado em: {data_hoje}</p>
    <div class="tag-seeds">
      {''.join(f'<span class="seed-badge">Semente: {s}</span>' for s in sementes)}
    </div>
  </div>

  <div class="stats-grid">
    <div class="stat-card blue">
      <div class="stat-val">10</div>
      <div class="stat-lbl">Oportunidades</div>
    </div>
    <div class="stat-card green">
      <div class="stat-val">{total_low}</div>
      <div class="stat-lbl">Concorrência Fácil</div>
    </div>
    <div class="stat-card yellow">
      <div class="stat-val">{total_med}</div>
      <div class="stat-lbl">Concorrência Média</div>
    </div>
    <div class="stat-card red">
      <div class="stat-val">{total_high}</div>
      <div class="stat-lbl">Concorrência Difícil</div>
    </div>
  </div>

  <div class="filters-bar">
    <span class="filters-lbl">Filtrar por Dificuldade:</span>
    <div class="filter-btns">
      <button class="filter-btn active" onclick="filterDifficulty('todos')">Todos</button>
      <button class="filter-btn" onclick="filterDifficulty('fácil')">Fácil</button>
      <button class="filter-btn" onclick="filterDifficulty('média')">Média</button>
      <button class="filter-btn" onclick="filterDifficulty('difícil')">Difícil</button>
    </div>
  </div>

  <div class="cards-list">
    {cards_html}
  </div>

  <div class="footer">
    <p>TênisIdeal · Automação nº 2 · {data_hoje}</p>
    <p style="margin-top:4px">Briefings gerados e analisados a partir das SERPs brasileiras em tempo real.</p>
  </div>

</div>

<script>
  function toggleBriefing(btn) {{
    btn.classList.toggle('active');
    const drawer = btn.nextElementSibling;
    drawer.classList.toggle('hidden');
    
    const textEl = btn.querySelector('span');
    if (drawer.classList.contains('hidden')) {{
      textEl.innerText = "Ver Briefing e Concorrentes";
    }} else {{
      textEl.innerText = "Fechar Briefing";
    }}
  }}

  function filterDifficulty(diff) {{
    // Atualiza botões
    const btns = document.querySelectorAll('.filter-btn');
    btns.forEach(btn => btn.classList.remove('active'));
    
    event.target.classList.add('active');
    
    // Filtra cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {{
      if (diff === 'todos') {{
        card.style.display = 'block';
      }} else {{
        const cardComp = card.getAttribute('data-comp');
        if (cardComp === diff) {{
          card.style.display = 'block';
        }} else {{
          card.style.display = 'none';
        }}
      }}
    }});
  }}
</script>

</body>
</html>"""
    return html

# ══════════════════════════════════════════════════════════════
# 🚀  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Automação 2 — Calendário Editorial TênisIdeal")
    parser.add_argument("--seeds", type=str, help="Lista de palavras semente separadas por vírgula")
    parser.add_argument("--api-key", type=str, help="Chave API Gemini")
    args = parser.parse_args()

    print("=" * 60)
    print("  TENISIDEAL — Automação nº 2: Calendário Editorial")
    print("=" * 60)
    print()

    # Define sementes a usar
    if args.seeds:
        sementes = [s.strip() for s in args.seeds.split(",") if s.strip()]
    else:
        # Tenta carregar do prompt ou assume padrão
        sementes = SEMENTES_PADRAO

    print(f"📁 Sementes ativas: {', '.join(sementes)}")

    # Carrega chave API do Gemini
    api_key = args.api_key or obter_gemini_api_key()

    # Passo 1: Expande palavras-chave usando Google Suggest API
    candidatos = expandir_sementes(sementes)
    
    if not candidatos:
        print("❌ Nenhuma palavra-chave candidata foi gerada. Abortando.")
        return

    # Passo 2: Analisa SERPs ( DuckDuckGo ) e calcula concorrência
    top_10 = processar_candidatos(candidatos, max_analise=25)
    
    if not top_10:
        print("❌ Erro ao analisar concorrência das palavras-chave. Abortando.")
        return

    # Passo 3: Envia as melhores para o Gemini gerar briefings estruturados
    top_10 = gerar_briefings_com_gemini(top_10, api_key)

    # Passo 4: Gera arquivos de saída (HTML e CSV)
    print("\n🎨 Gerando relatórios de calendário editorial...")
    
    # 4.1 HTML
    html_content = gerar_relatorio_html(top_10, sementes)
    saida_html = "calendario_editorial.html"
    with open(saida_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # 4.2 CSV
    saida_csv = "calendario_editorial.csv"
    campos = ["rank", "keyword", "seo_title", "intent", "concorrencia_score", 
              "dificuldade", "oportunidade_score", "suggested_shoes", "outline"]
              
    with open(saida_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(campos)
        for idx, d in enumerate(top_10):
            w.writerow([
                idx + 1,
                d["keyword"],
                d["seo_title"],
                d["intent"],
                d["concorrencia_score"],
                d["dificuldade"],
                d["oportunidade_score"],
                ", ".join(d["suggested_shoes"]),
                " | ".join(d["outline"])
            ])

    print("=" * 60)
    print("  ✅ CALENDÁRIO EDITORIAL GERADO COM SUCESSO!")
    print("=" * 60)
    print(f"  📄 HTML interativo: {saida_html}")
    print(f"  📊 Planilha CSV:    {saida_csv}")
    print()
    if not api_key:
        print("  ⚠️ Nota: O Gemini rodou em MODO OFFLINE (briefings de modelo).")
        print("     Para briefings 100% personalizados de IA, crie uma chave gratuita no")
        print("     Google AI Studio (https://aistudio.google.com) e insira no arquivo '.env' como:")
        print("     GEMINI_API_KEY=sua_chave_aqui")
    print("=" * 60)

if __name__ == "__main__":
    main()
