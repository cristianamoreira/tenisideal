#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  TENISIDEAL — Automação nº 1: Potencial de Receita           ║
║  Cruza tráfego orgânico com cliques afiliados e gera         ║
║  um relatório priorizado de oportunidades.                   ║
╚══════════════════════════════════════════════════════════════╝

COMO USAR:
1. Exporte os CSVs das suas fontes (veja COMO_USAR.md)
2. Coloque os arquivos na pasta "dados_analise/" (ao lado deste script)
3. Execute: python analise_receita.py
4. Abra o arquivo "relatorio_oportunidades.html" no seu navegador
"""

import os
import sys
import csv
import json
import math
import glob
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÕES — Ajuste aqui se necessário
# ══════════════════════════════════════════════════════════════

# Pasta onde você vai colocar os CSVs exportados
PASTA_DADOS = "dados_analise"

# URL base do seu site (para normalizar os links)
URL_BASE = "https://tenisideal.com.br"

# Comissão média estimada por clique (em R$) — usado para estimar receita potencial
# Ajuste com base na sua experiência real
COMISSAO_MEDIA_POR_CLIQUE = {
    "amazon":   0.15,   # ~15 centavos por clique qualificado (estimativa)
    "netshoes":  0.20,
    "awin":     0.18,
    "geral":    0.16,
}

# ══════════════════════════════════════════════════════════════
# 📂  DETECÇÃO AUTOMÁTICA DE ARQUIVOS
# ══════════════════════════════════════════════════════════════

def detectar_arquivos():
    """Detecta automaticamente os CSVs na pasta dados_analise/"""
    pasta = Path(PASTA_DADOS)
    if not pasta.exists():
        pasta.mkdir()
        print(f"📁 Pasta '{PASTA_DADOS}' criada. Coloque seus CSVs lá e rode novamente.")
        print("   Veja o arquivo COMO_USAR.md para saber quais arquivos exportar.")
        sys.exit(0)

    arquivos = {
        "search_console": None,
        "amazon":         None,
        "awin":           None,
        "netshoes":       None,
    }

    for f in pasta.glob("*.csv"):
        nome = f.name.lower()
        if "search" in nome or "console" in nome or "gsc" in nome or "queries" in nome or "performance" in nome:
            arquivos["search_console"] = f
        elif "amazon" in nome or "associates" in nome or "one_tag" in nome:
            arquivos["amazon"] = f
        elif "awin" in nome or "publisher" in nome:
            arquivos["awin"] = f
        elif "netshoes" in nome or "lomadee" in nome:
            arquivos["netshoes"] = f

    return arquivos

# ══════════════════════════════════════════════════════════════
# 🔍  LEITORES DE CSV POR PLATAFORMA
# ══════════════════════════════════════════════════════════════

def normalizar_url(url):
    """Remove domínio, parâmetros e normaliza para comparação"""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    for prefixo in ["https://tenisideal.com.br", "http://tenisideal.com.br",
                    "https://www.tenisideal.com.br", "http://www.tenisideal.com.br"]:
        if url.startswith(prefixo):
            url = url[len(prefixo):]
    if "?" in url:
        url = url.split("?")[0]
    return url or "/"

def ler_search_console(caminho):
    """
    Lê o CSV do Google Search Console (aba Performance > Páginas > Exportar).
    Colunas esperadas: Página, Cliques, Impressões, CTR, Posição
    (ou em inglês: Page, Clicks, Impressions, CTR, Position)
    """
    dados = {}
    if not caminho:
        return dados

    print(f"  📊 Lendo Search Console: {caminho.name}")
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Normaliza nomes de colunas
        for row in reader:
            chaves = {k.lower().strip(): v for k, v in row.items()}

            pagina = (chaves.get("página") or chaves.get("page") or
                      chaves.get("top pages") or chaves.get("landing page") or "")
            cliques_str = (chaves.get("cliques") or chaves.get("clicks") or "0")
            impressoes_str = (chaves.get("impressões") or chaves.get("impressions") or "0")
            ctr_str = (chaves.get("ctr") or "0%")
            posicao_str = (chaves.get("posição") or chaves.get("position") or "0")

            try:
                cliques = int(cliques_str.replace(",", "").replace(".", ""))
            except:
                cliques = 0
            try:
                impressoes = int(impressoes_str.replace(",", "").replace(".", ""))
            except:
                impressoes = 0
            try:
                posicao = float(posicao_str.replace(",", ".").replace("%", ""))
            except:
                posicao = 0.0

            url_norm = normalizar_url(pagina)
            if url_norm:
                dados[url_norm] = {
                    "url": url_norm,
                    "cliques_organicos": cliques,
                    "impressoes": impressoes,
                    "posicao_google": round(posicao, 1),
                }

    print(f"     ✅ {len(dados)} páginas encontradas")
    return dados

def ler_amazon_associates(caminho):
    """
    Lê o relatório do Amazon Associates BR.
    Exportar em: Relatórios > Relatório de Ganhos > por Link/URL
    Colunas esperadas: URL / Link, Cliques, Pedidos Enviados, Ganhos
    """
    dados = {}
    if not caminho:
        return dados

    print(f"  🛒 Lendo Amazon Associates: {caminho.name}")
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chaves = {k.lower().strip(): v for k, v in row.items()}

            # Amazon usa vários formatos dependendo do tipo de relatório
            url = (chaves.get("url de referência") or chaves.get("referring url") or
                   chaves.get("url") or chaves.get("tracking id") or "")
            cliques_str = chaves.get("cliques") or chaves.get("clicks") or "0"
            ganhos_str = (chaves.get("ganhos totais") or chaves.get("total earnings") or
                          chaves.get("ganhos") or chaves.get("earnings") or "0")

            try:
                cliques = int(cliques_str.replace(",", ""))
            except:
                cliques = 0
            try:
                ganhos = float(ganhos_str.replace("R$", "").replace(",", ".").strip())
            except:
                ganhos = 0.0

            url_norm = normalizar_url(url)
            if url_norm and cliques > 0:
                existing = dados.get(url_norm, {"cliques_afiliado": 0, "ganhos": 0.0, "fonte": "amazon"})
                existing["cliques_afiliado"] = existing["cliques_afiliado"] + cliques
                existing["ganhos"] = existing["ganhos"] + ganhos
                existing["fonte"] = "amazon"
                dados[url_norm] = existing

    print(f"     ✅ {len(dados)} páginas com cliques afiliados (Amazon)")
    return dados

def ler_awin(caminho):
    """
    Lê o relatório da Awin.
    Exportar em: Reports > Publisher > Click & Impression Stats
    Colunas esperadas: Publisher URL / Referrer, Clicks, Sales, Commission
    """
    dados = {}
    if not caminho:
        return dados

    print(f"  🔗 Lendo Awin: {caminho.name}")
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chaves = {k.lower().strip(): v for k, v in row.items()}

            url = (chaves.get("publisher url") or chaves.get("referrer url") or
                   chaves.get("url") or chaves.get("click ref") or "")
            cliques_str = chaves.get("clicks") or chaves.get("click count") or "0"
            comissao_str = (chaves.get("commission amount") or chaves.get("publisher commission") or
                            chaves.get("commission") or "0")

            try:
                cliques = int(cliques_str.replace(",", ""))
            except:
                cliques = 0
            try:
                comissao = float(comissao_str.replace("R$", "").replace(",", ".").strip())
            except:
                comissao = 0.0

            url_norm = normalizar_url(url)
            if url_norm and cliques > 0:
                existing = dados.get(url_norm, {"cliques_afiliado": 0, "ganhos": 0.0, "fonte": "awin"})
                existing["cliques_afiliado"] = existing["cliques_afiliado"] + cliques
                existing["ganhos"] = existing["ganhos"] + comissao
                existing["fonte"] = "awin"
                dados[url_norm] = existing

    print(f"     ✅ {len(dados)} páginas com cliques afiliados (Awin)")
    return dados

def ler_netshoes(caminho):
    """
    Lê o relatório da Netshoes (via Lomadee ou painel próprio).
    Colunas esperadas: URL, Cliques, Comissão
    """
    dados = {}
    if not caminho:
        return dados

    print(f"  👟 Lendo Netshoes/Lomadee: {caminho.name}")
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chaves = {k.lower().strip(): v for k, v in row.items()}

            url = chaves.get("url") or chaves.get("página") or chaves.get("page") or ""
            cliques_str = chaves.get("cliques") or chaves.get("clicks") or "0"
            comissao_str = chaves.get("comissão") or chaves.get("commission") or chaves.get("ganhos") or "0"

            try:
                cliques = int(cliques_str.replace(",", ""))
            except:
                cliques = 0
            try:
                comissao = float(comissao_str.replace("R$", "").replace(",", ".").strip())
            except:
                comissao = 0.0

            url_norm = normalizar_url(url)
            if url_norm and cliques > 0:
                existing = dados.get(url_norm, {"cliques_afiliado": 0, "ganhos": 0.0, "fonte": "netshoes"})
                existing["cliques_afiliado"] = existing["cliques_afiliado"] + cliques
                existing["ganhos"] = existing["ganhos"] + comissao
                existing["fonte"] = "netshoes"
                dados[url_norm] = existing

    print(f"     ✅ {len(dados)} páginas com cliques afiliados (Netshoes)")
    return dados

# ══════════════════════════════════════════════════════════════
# 🧮  CRUZAMENTO E CÁLCULO DE PRIORIDADE
# ══════════════════════════════════════════════════════════════

def cruzar_dados(sc_dados, afiliados_dados):
    """
    Cruza os dados do Search Console com os dados de afiliados.
    Calcula Taxa de Clique Afiliado e Potencial de Receita.
    """
    resultado = []

    # Conjunto de todas as URLs conhecidas
    todas_urls = set(sc_dados.keys()) | set(afiliados_dados.keys())

    for url in todas_urls:
        sc = sc_dados.get(url, {})
        af = afiliados_dados.get(url, {})

        cliques_org = sc.get("cliques_organicos", 0)
        impressoes = sc.get("impressoes", 0)
        posicao = sc.get("posicao_google", 0.0)
        cliques_afil = af.get("cliques_afiliado", 0)
        ganhos_reais = af.get("ganhos", 0.0)
        fonte = af.get("fonte", "—")

        # Taxa de clique afiliado (% dos visitantes que clicam no link afiliado)
        taxa_clique = (cliques_afil / cliques_org * 100) if cliques_org > 0 else 0.0

        # Potencial estimado: se a taxa de clique fosse 5% (referência de bom desempenho)
        # quanto seria o ganho?
        META_TAXA = 5.0  # 5% é uma meta realista para páginas de produto
        cliques_potenciais = cliques_org * (META_TAXA / 100)
        comissao_ref = COMISSAO_MEDIA_POR_CLIQUE.get(fonte, COMISSAO_MEDIA_POR_CLIQUE["geral"])
        receita_potencial = cliques_potenciais * comissao_ref * 100  # em R$ por mês

        # Receita atual estimada
        receita_atual = ganhos_reais if ganhos_reais > 0 else cliques_afil * comissao_ref * 100

        # Gap (oportunidade não capturada)
        gap = max(0, receita_potencial - receita_atual)

        # Score de prioridade: alto tráfego + baixa conversão + boa posição no Google
        # Normalizado de 0 a 100
        score_trafego = min(cliques_org / 10, 50)       # até 50 pontos pelo tráfego
        score_gap = min(gap / 10, 30)                    # até 30 pontos pelo gap
        score_posicao = max(0, 15 - posicao / 2) if posicao > 0 else 0  # até 15 pts pela posição
        score_afil = 5 if cliques_afil == 0 and cliques_org > 0 else 0  # 5 bônus se zero cliques
        prioridade_score = round(score_trafego + score_gap + score_posicao + score_afil, 1)

        # Nível de prioridade
        if prioridade_score >= 40:
            nivel = "🔴 ALTA"
            nivel_ordem = 1
        elif prioridade_score >= 20:
            nivel = "🟡 MÉDIA"
            nivel_ordem = 2
        else:
            nivel = "🟢 BAIXA"
            nivel_ordem = 3

        # Recomendação automática
        recomendacao = gerar_recomendacao(url, cliques_org, taxa_clique, posicao, cliques_afil)

        resultado.append({
            "url": url,
            "url_completa": URL_BASE + url,
            "cliques_organicos": cliques_org,
            "impressoes": impressoes,
            "posicao_google": posicao,
            "cliques_afiliado": cliques_afil,
            "taxa_clique_pct": round(taxa_clique, 2),
            "ganhos_reais": round(ganhos_reais, 2),
            "receita_atual": round(receita_atual, 2),
            "receita_potencial": round(receita_potencial, 2),
            "gap_receita": round(gap, 2),
            "fonte_afiliado": fonte,
            "prioridade_score": prioridade_score,
            "nivel_prioridade": nivel,
            "nivel_ordem": nivel_ordem,
            "recomendacao": recomendacao,
        })

    # Ordena por prioridade (maior score primeiro)
    resultado.sort(key=lambda x: (-x["prioridade_score"], -x["cliques_organicos"]))
    return resultado

def gerar_recomendacao(url, cliques_org, taxa_clique, posicao, cliques_afil):
    """Gera uma recomendação de ação específica para a página."""
    if cliques_org == 0:
        return "Página sem tráfego orgânico. Foque em SEO ou crie conteúdo para este URL."
    if cliques_afil == 0 and cliques_org > 50:
        return "🚨 Alto tráfego mas ZERO cliques no link afiliado. Verifique se o botão de compra está visível e funcionando."
    if taxa_clique < 1.0 and cliques_org > 30:
        return "Taxa de conversão muito baixa (<1%). Adicione botão de compra mais destacado, sticky CTA no mobile ou urgência (ex: 'Última unidade')."
    if taxa_clique < 3.0:
        return "Taxa abaixo da meta (meta: 5%). Tente adicionar comparação de preços, reviews ou tabela de vantagens."
    if posicao > 10 and cliques_org < 20:
        return "Página na 2ª página do Google (pos. %.1f). Melhore o SEO on-page para subir para top 10 e triplicar o tráfego." % posicao
    if taxa_clique >= 5.0:
        return "✅ Boa conversão! Considere aumentar o tráfego com anúncios pagos ou link interno de outras páginas."
    return "Monitore e otimize o design do CTA para melhorar a taxa de clique."

# ══════════════════════════════════════════════════════════════
# 📄  GERAÇÃO DO RELATÓRIO HTML
# ══════════════════════════════════════════════════════════════

def gerar_relatorio_html(dados, arquivos_usados):
    """Gera o relatório visual em HTML."""

    total_trafego = sum(d["cliques_organicos"] for d in dados)
    total_cliques_afil = sum(d["cliques_afiliado"] for d in dados)
    total_ganhos = sum(d["ganhos_reais"] for d in dados)
    total_potencial = sum(d["receita_potencial"] for d in dados)
    paginas_alta = sum(1 for d in dados if d["nivel_ordem"] == 1)
    paginas_zero = sum(1 for d in dados if d["cliques_afiliado"] == 0 and d["cliques_organicos"] > 0)

    fontes_usadas = [k for k, v in arquivos_usados.items() if v]
    data_hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")

    rows_html = ""
    for i, d in enumerate(dados[:50]):  # Mostra top 50
        taxa_bar = min(d["taxa_clique_pct"] * 10, 100)
        url_display = d["url"] or "/"
        rows_html += f"""
        <tr class="row-{d['nivel_ordem']}">
            <td class="rank">#{i+1}</td>
            <td class="url-cell">
                <a href="{d['url_completa']}" target="_blank">{url_display}</a>
            </td>
            <td class="num">{d['cliques_organicos']:,}</td>
            <td class="num pos">{d['posicao_google']:.1f}º</td>
            <td class="num afil">{d['cliques_afiliado']:,}</td>
            <td class="taxa-cell">
                <div class="taxa-bar-wrap">
                    <div class="taxa-bar" style="width:{taxa_bar:.0f}%"></div>
                    <span>{d['taxa_clique_pct']:.1f}%</span>
                </div>
            </td>
            <td class="num ganhos">R$ {d['ganhos_reais']:.2f}</td>
            <td class="num pot">R$ {d['receita_potencial']:.2f}</td>
            <td class="badge">{d['nivel_prioridade']}</td>
            <td class="rec">{d['recomendacao']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório de Oportunidades — TênisIdeal</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Bebas+Neue&display=swap');

  :root {{
    --bg: #0d0f14;
    --card: #161a23;
    --border: #252a38;
    --text: #e8eaf0;
    --muted: #6b7280;
    --green: #10B981;
    --yellow: #F59E0B;
    --red: #EF4444;
    --blue: #3B82F6;
    --purple: #8B5CF6;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 32px 24px;
  }}

  .header {{
    text-align: center;
    margin-bottom: 40px;
  }}

  .logo {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    letter-spacing: 2px;
    color: var(--text);
    margin-bottom: 8px;
  }}

  .logo span {{ color: var(--green); }}

  .header p {{
    color: var(--muted);
    font-size: 0.875rem;
  }}

  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }}

  .kpi {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }}

  .kpi-value {{
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 4px;
  }}

  .kpi-label {{
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .kpi.green .kpi-value {{ color: var(--green); }}
  .kpi.yellow .kpi-value {{ color: var(--yellow); }}
  .kpi.red .kpi-value {{ color: var(--red); }}
  .kpi.blue .kpi-value {{ color: var(--blue); }}
  .kpi.purple .kpi-value {{ color: var(--purple); }}

  .section-title {{
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .alert-box {{
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 24px;
    font-size: 0.875rem;
    line-height: 1.6;
  }}

  .alert-box strong {{ color: var(--red); }}

  .table-wrap {{
    overflow-x: auto;
    border-radius: 12px;
    border: 1px solid var(--border);
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }}

  thead th {{
    background: #1e2433;
    padding: 12px 10px;
    text-align: left;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--muted);
    white-space: nowrap;
    border-bottom: 1px solid var(--border);
  }}

  tbody tr {{
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }}

  tbody tr:hover {{ background: rgba(255,255,255,0.03); }}

  tbody tr.row-1 {{ border-left: 3px solid var(--red); }}
  tbody tr.row-2 {{ border-left: 3px solid var(--yellow); }}
  tbody tr.row-3 {{ border-left: 3px solid var(--green); }}

  td {{
    padding: 10px 10px;
    vertical-align: top;
  }}

  .rank {{ color: var(--muted); font-weight: 600; text-align: center; }}

  .url-cell a {{
    color: var(--blue);
    text-decoration: none;
    font-weight: 500;
    word-break: break-all;
  }}

  .url-cell a:hover {{ text-decoration: underline; }}

  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .pos {{ color: var(--purple); }}
  .afil {{ color: var(--yellow); }}
  .ganhos {{ color: var(--green); }}
  .pot {{ color: var(--blue); }}

  .taxa-cell {{ min-width: 100px; }}
  .taxa-bar-wrap {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .taxa-bar {{
    height: 6px;
    background: var(--green);
    border-radius: 3px;
    flex-shrink: 0;
    transition: width 0.3s;
  }}

  .badge {{
    white-space: nowrap;
    font-size: 0.75rem;
    font-weight: 600;
  }}

  .rec {{
    color: var(--muted);
    font-size: 0.75rem;
    line-height: 1.5;
    min-width: 220px;
    max-width: 300px;
  }}

  .footer {{
    text-align: center;
    margin-top: 40px;
    color: var(--muted);
    font-size: 0.75rem;
  }}

  .fontes-tag {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.7rem;
    margin: 2px;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">Tênis<span>ideal</span></div>
  <p>Relatório de Oportunidades de Receita — Gerado em {data_hoje}</p>
  <p style="margin-top:6px">
    Fontes: {''.join(f'<span class="fontes-tag">✓ {f.upper()}</span>' for f in fontes_usadas)}
  </p>
</div>

<div class="kpi-grid">
  <div class="kpi blue">
    <div class="kpi-value">{total_trafego:,}</div>
    <div class="kpi-label">Visitas Orgânicas</div>
  </div>
  <div class="kpi yellow">
    <div class="kpi-value">{total_cliques_afil:,}</div>
    <div class="kpi-label">Cliques Afiliados</div>
  </div>
  <div class="kpi green">
    <div class="kpi-value">R$ {total_ganhos:.0f}</div>
    <div class="kpi-label">Ganhos Reais</div>
  </div>
  <div class="kpi purple">
    <div class="kpi-value">R$ {total_potencial:.0f}</div>
    <div class="kpi-label">Potencial Estimado</div>
  </div>
  <div class="kpi red">
    <div class="kpi-value">{paginas_alta}</div>
    <div class="kpi-label">Páginas Alta Prioridade</div>
  </div>
  <div class="kpi red">
    <div class="kpi-value">{paginas_zero}</div>
    <div class="kpi-label">Páginas Sem Clique Afiliado</div>
  </div>
</div>

{'<div class="alert-box">⚠️ <strong>' + str(paginas_zero) + ' páginas</strong> com tráfego orgânico mas <strong>zero cliques</strong> em links afiliados. Este é o maior vazamento de receita do seu site. Verifique se os botões de compra estão visíveis e funcionando.</div>' if paginas_zero > 0 else ''}

<div class="section-title">📋 Ranking de Oportunidades (Top 50)</div>

<div class="table-wrap">
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Página</th>
      <th>Visitas Org.</th>
      <th>Posição Google</th>
      <th>Cliques Afil.</th>
      <th>Taxa Clique</th>
      <th>Ganhos Reais</th>
      <th>Potencial/mês</th>
      <th>Prioridade</th>
      <th>Recomendação</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>
</div>

<div class="footer">
  <p>TênisIdeal · Automação nº 1 · {data_hoje}</p>
  <p style="margin-top:4px">Potencial calculado com meta de 5% de taxa de clique. Ganhos estimados com base na comissão média das redes.</p>
</div>

</body>
</html>"""

    return html

# ══════════════════════════════════════════════════════════════
# 📊  DADOS DE EXEMPLO (para teste sem CSVs reais)
# ══════════════════════════════════════════════════════════════

def gerar_dados_exemplo():
    """Gera dados de exemplo para testar o relatório sem CSVs reais."""
    print("\n  ℹ️  Nenhum CSV encontrado. Gerando relatório com dados de EXEMPLO para demonstração.")
    print("     Quando tiver os CSVs reais, coloque na pasta 'dados_analise/' e rode novamente.\n")

    sc = {
        "/": {"url": "/", "cliques_organicos": 1200, "impressoes": 15000, "posicao_google": 3.2},
        "/index.html": {"url": "/", "cliques_organicos": 0, "impressoes": 0, "posicao_google": 0},
        "/mizuno-wave-prophecy-preco.html": {"url": "/mizuno-wave-prophecy-preco.html", "cliques_organicos": 480, "impressoes": 6200, "posicao_google": 5.1},
        "/adidas-ultraboost-preco.html": {"url": "/adidas-ultraboost-preco.html", "cliques_organicos": 310, "impressoes": 4100, "posicao_google": 7.4},
        "/olympikus-corre-3-preco.html": {"url": "/olympikus-corre-3-preco.html", "cliques_organicos": 220, "impressoes": 3300, "posicao_google": 8.9},
        "/melhores-tenis-corrida.html": {"url": "/melhores-tenis-corrida.html", "cliques_organicos": 890, "impressoes": 11000, "posicao_google": 4.3},
        "/tenis-ate-500.html": {"url": "/tenis-ate-500.html", "cliques_organicos": 540, "impressoes": 7200, "posicao_google": 6.0},
        "/tenis-pisada-supinada.html": {"url": "/tenis-pisada-supinada.html", "cliques_organicos": 190, "impressoes": 2800, "posicao_google": 11.2},
        "/blog.html": {"url": "/blog.html", "cliques_organicos": 340, "impressoes": 5500, "posicao_google": 9.8},
        "/melhor-tenis-corrida.html": {"url": "/melhor-tenis-corrida.html", "cliques_organicos": 670, "impressoes": 9000, "posicao_google": 5.8},
        "/melhores-tenis-adidas.html": {"url": "/melhores-tenis-adidas.html", "cliques_organicos": 130, "impressoes": 1900, "posicao_google": 14.5},
        "/melhores-tenis-mizuno.html": {"url": "/melhores-tenis-mizuno.html", "cliques_organicos": 95, "impressoes": 1400, "posicao_google": 16.2},
    }

    af = {
        "/mizuno-wave-prophecy-preco.html": {"cliques_afiliado": 38, "ganhos": 4.20, "fonte": "amazon"},
        "/adidas-ultraboost-preco.html": {"cliques_afiliado": 4, "ganhos": 0.50, "fonte": "awin"},
        "/melhores-tenis-corrida.html": {"cliques_afiliado": 62, "ganhos": 8.10, "fonte": "amazon"},
        "/tenis-ate-500.html": {"cliques_afiliado": 12, "ganhos": 1.40, "fonte": "netshoes"},
        "/melhor-tenis-corrida.html": {"cliques_afiliado": 45, "ganhos": 5.80, "fonte": "amazon"},
    }

    return sc, af

# ══════════════════════════════════════════════════════════════
# 🚀  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  TENISIDEAL — Análise de Potencial de Receita")
    print("=" * 60)
    print()

    arquivos = detectar_arquivos()
    tem_dados_reais = any(v is not None for v in arquivos.values())

    if not tem_dados_reais:
        sc_dados, af_dados_combinados = gerar_dados_exemplo()
        arquivos_usados = {"exemplo": True}
    else:
        print("📂 Arquivos detectados:")
        sc_dados = {}
        af_dados_combinados = {}

        sc_dados = ler_search_console(arquivos["search_console"])

        af_amazon = ler_amazon_associates(arquivos["amazon"])
        af_awin = ler_awin(arquivos["awin"])
        af_netshoes = ler_netshoes(arquivos["netshoes"])

        # Combina todos os dados de afiliados (soma cliques por URL)
        for url, d in {**af_amazon, **af_awin, **af_netshoes}.items():
            if url in af_dados_combinados:
                af_dados_combinados[url]["cliques_afiliado"] += d["cliques_afiliado"]
                af_dados_combinados[url]["ganhos"] += d["ganhos"]
            else:
                af_dados_combinados[url] = d.copy()

        arquivos_usados = {k: v for k, v in arquivos.items() if v is not None}
        if not arquivos_usados:
            arquivos_usados = {"dados_parciais": True}

    print("\n🧮 Cruzando dados e calculando oportunidades...")
    dados_cruzados = cruzar_dados(sc_dados, af_dados_combinados)

    if not dados_cruzados:
        print("❌ Nenhum dado para analisar. Verifique os CSVs na pasta dados_analise/")
        return

    # Gera relatório HTML
    print("🎨 Gerando relatório visual...")
    html = gerar_relatorio_html(dados_cruzados, arquivos_usados)

    saida_html = "relatorio_oportunidades.html"
    with open(saida_html, "w", encoding="utf-8") as f:
        f.write(html)

    # Gera CSV simplificado
    saida_csv = "relatorio_oportunidades.csv"
    campos = ["url", "cliques_organicos", "posicao_google", "cliques_afiliado",
              "taxa_clique_pct", "ganhos_reais", "receita_potencial",
              "gap_receita", "nivel_prioridade", "recomendacao"]
    with open(saida_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(dados_cruzados)

    print()
    print("=" * 60)
    print("  ✅ RELATÓRIO GERADO COM SUCESSO!")
    print("=" * 60)
    print(f"  📄 HTML visual:  {saida_html}")
    print(f"  📊 Dados brutos: {saida_csv}")
    print()

    alta = [d for d in dados_cruzados if d["nivel_ordem"] == 1]
    if alta:
        print(f"  🔴 {len(alta)} páginas de ALTA prioridade identificadas:")
        for d in alta[:5]:
            print(f"     • {d['url']} ({d['cliques_organicos']} visitas, {d['taxa_clique_pct']:.1f}% conversão)")
    print()
    print("  Abra o arquivo 'relatorio_oportunidades.html' no seu navegador!")
    print("=" * 60)

if __name__ == "__main__":
    main()
