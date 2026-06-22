#!/usr/bin/env python3
"""
reclassificar_tags.py
---------------------
Percorre todos os produtos ATIVOS na planilha e atualiza a coluna `tags`
usando o Gemini com o novo prompt (apenas tecnologias e características físicas).

Uso:
    python3 reclassificar_tags.py              # Re-classifica todos os ativos
    python3 reclassificar_tags.py --dry-run   # Mostra o que seria alterado sem salvar
    python3 reclassificar_tags.py --id <product_id>  # Atualiza apenas um produto
"""

import argparse
import sys
import os
import re
import json
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================
SHEET_ID        = "1SrOeEOwQsR5BcNcVni0W20c5npazOn5iKHpIr3Zy42Y"
CREDENTIALS_FILE = "credenciais.json"
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

# Índices das colunas (0-based, conforme SCHEMA_COLS do scraper)
COL_PRODUCT_ID = 0   # A
COL_ATIVO      = 1   # B
COL_MARCA      = 2   # C
COL_NOME       = 3   # D
COL_VERSAO     = 4   # E
COL_TAGS       = 8   # I  ← coluna que vamos atualizar

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
        sys.exit(1)

# ==============================================================================
# 🤖 NOVO PROMPT — APENAS TECNOLOGIAS E CARACTERÍSTICAS FÍSICAS
# ==============================================================================
def gerar_tags_com_gemini(nome_tenis, marca):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = input("Cole sua GEMINI_API_KEY: ").strip()
    if not GEMINI_API_KEY:
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""
Você é um especialista em tênis de corrida. Analise o tênis: "{nome_tenis}" da marca {marca}.

Retorne APENAS um JSON com o campo "tags".

Regra para "tags":
- Exatamente 1 ou 2 palavras/expressões de TECNOLOGIA ou CARACTERÍSTICA FÍSICA do tênis, separadas por |.
- PERMITIDO: nomes de tecnologias proprietárias (ex: "ZoomX", "Boost", "PWRRUN", "Wave", "React", "DNA Loft", "CloudTec", "EnergyFoam", "FF BLAST+"), materiais especiais (ex: "Knit", "Gore-Tex", "Nylon"), diferenciais físicos (ex: "Placa de carbono", "Drop zero", "Meia entressola").
- PROIBIDO em tags (essas info já existem em outras colunas): "Iniciante", "Intermediário", "Avançado", "Treino", "Maratona", "Diário", "Longa distância", "Asfalto", "Trilha", "Esteira", "Pista", "Neutra", "Pronada", "Supinada", "Leveza", "Custo", "Durabilidade", "Velocidade", "Conforto", "Amortecimento".

Exemplos corretos:
- Nike Alphafly: "ZoomX|Placa de carbono"
- Adidas Ultraboost: "Boost|Primeknit"
- Mizuno Wave Prophecy: "Wave|SmoothRide"
- Olympikus Corre: "EnergyFoam"
- Asics Gel Nimbus: "Gel|FlyteFoam"

Formato da resposta (JSON puro, sem markdown):
{{"tags": "Tecnologia1|Tecnologia2"}}
"""

    try:
        response = model.generate_content(prompt)
        texto = response.text.replace("```json", "").replace("```", "").strip()
        dados = json.loads(texto)
        return dados.get("tags", "").strip()
    except Exception as e:
        print(f"  ⚠️  Erro Gemini: {e}")
        return None

# ==============================================================================
# 🚀 RECLASSIFICAÇÃO
# ==============================================================================
def reclassificar(filtro_id=None, dry_run=False):
    print("🔗 Conectando à planilha...")
    sheet = conectar_planilha()

    todas_linhas = sheet.get_all_values()
    header = todas_linhas[0]
    dados   = todas_linhas[1:]  # sem cabeçalho

    # Determinar índice real da coluna tags pelo cabeçalho (mais robusto)
    col_tags_idx = COL_TAGS
    if "tags" in header:
        col_tags_idx = header.index("tags")

    total   = 0
    ok      = 0
    erros   = 0
    pulados = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Iniciando re-classificação de tags...\n")
    print("-" * 60)

    for i, row in enumerate(dados):
        linha_sheet = i + 2  # +2: 1-based + cabeçalho

        # Garantir que a linha tem colunas suficientes
        while len(row) <= max(COL_PRODUCT_ID, COL_ATIVO, COL_MARCA, COL_NOME, col_tags_idx):
            row.append("")

        product_id = row[COL_PRODUCT_ID].strip()
        ativo      = row[COL_ATIVO].strip().lower()
        marca      = row[COL_MARCA].strip()
        nome       = row[COL_NOME].strip()
        tags_atual = row[col_tags_idx].strip() if col_tags_idx < len(row) else ""

        # Filtros
        if ativo != "sim":
            continue
        if not nome:
            continue
        if filtro_id and product_id != filtro_id:
            continue

        total += 1
        print(f"[{total}] {nome} ({marca}) — linha {linha_sheet}")
        print(f"     Tags atuais : {tags_atual or '(vazio)'}")

        # Chamar Gemini
        novas_tags = gerar_tags_com_gemini(nome, marca)

        if novas_tags is None:
            print("     ❌ Falha ao gerar tags. Pulando.")
            erros += 1
            continue

        print(f"     Novas tags  : {novas_tags}")

        if tags_atual == novas_tags:
            print("     ✅ Tags já estão corretas. Sem alteração.")
            pulados += 1
        elif dry_run:
            print("     🔍 [DRY RUN] Seria atualizado — nada salvo.")
            ok += 1
        else:
            try:
                # Coluna gspread é 1-based
                sheet.update_cell(linha_sheet, col_tags_idx + 1, novas_tags)
                print("     ✅ Tags atualizadas na planilha!")
                ok += 1
                # Pausa para respeitar o rate limit da API do Sheets (60 req/min)
                time.sleep(1.2)
            except Exception as e:
                print(f"     ❌ Erro ao salvar: {e}")
                erros += 1

        print()

    print("=" * 60)
    print(f"✅ Concluído!")
    print(f"   Produtos processados : {total}")
    print(f"   Tags atualizadas     : {ok}")
    print(f"   Já estavam corretas  : {pulados}")
    print(f"   Erros                : {erros}")
    if dry_run:
        print("\n⚠️  Modo DRY RUN — nenhuma alteração foi salva na planilha.")
        print("    Rode sem --dry-run para aplicar as mudanças.")

# ==============================================================================
# 🎮 ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-classifica a coluna 'tags' de todos os produtos ativos usando Gemini"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria alterado sem salvar na planilha"
    )
    parser.add_argument(
        "--id",
        metavar="PRODUCT_ID",
        help="Atualiza apenas o produto com esse product_id"
    )
    args = parser.parse_args()

    reclassificar(filtro_id=args.id, dry_run=args.dry_run)
