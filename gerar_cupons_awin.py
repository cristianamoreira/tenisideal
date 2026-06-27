#!/usr/bin/env python3
"""Busca os cupons ativos da Awin e monta uma mensagem pronta pro Canal do WhatsApp.

Como funciona:
- Lê o token da API da Awin da variável de ambiente AWIN_API_TOKEN (NUNCA no código)
- Chama a API de promoções da Awin (só anunciantes em que você é parceira)
- Filtra cupons ATIVOS do Brasil
- Monta um texto formatado, pronto pra copiar e colar no canal

Uso local (teste):
    AWIN_API_TOKEN="seu_token" python3 gerar_cupons_awin.py
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

PUBLISHER_ID = os.environ.get("AWIN_PUBLISHER_ID", "2800712")
TOKEN = os.environ.get("AWIN_API_TOKEN", "")
MAX_CUPONS = int(os.environ.get("MAX_CUPONS", "8"))


def buscar_promocoes():
    url = f"https://api.awin.com/publishers/{PUBLISHER_ID}/promotions/"
    body = {
        "filters": {
            "membership": "joined",     # só lojas em que você é parceira
            "type": "voucher",          # só cupons (não banners)
            "status": "active",         # só ativos
            "regionCodes": ["BR"],
        },
        "pagination": {"page": 1, "pageSize": 100},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def campo(promo, *nomes, default=""):
    """Pega o primeiro campo existente (a API às vezes muda nomes)."""
    for n in nomes:
        if isinstance(promo, dict) and promo.get(n):
            return promo[n]
    return default


def formatar(promocoes):
    hoje = datetime.datetime.now().strftime("%d/%m")
    linhas = [f"🔥 *CUPONS DO DIA — {hoje}* 🔥", ""]

    usados = 0
    for p in promocoes:
        if usados >= MAX_CUPONS:
            break
        loja = campo(p, "advertiserName") or campo(p.get("advertiser", {}), "name", default="Loja")
        titulo = campo(p, "title", "description", default="").strip()
        # código do cupom
        voucher = p.get("voucher") or {}
        codigo = campo(voucher, "code") or campo(p, "code")
        # link de afiliado (rastreado)
        link = campo(p, "urlTracking", "clickThroughUrl", "url")

        if not (titulo or codigo):
            continue

        bloco = f"👟 *{loja}*"
        if titulo:
            bloco += f"\n{titulo[:90]}"
        if codigo:
            bloco += f"\n🎟️ Cupom: *{codigo}*"
        if link:
            bloco += f"\n👉 {link}"
        linhas.append(bloco)
        linhas.append("")  # linha em branco entre cupons
        usados += 1

    if usados == 0:
        linhas.append("Nenhum cupom ativo hoje. 😅")
        linhas.append("")

    linhas.append("—")
    linhas.append("👟 *Tênis Ideal* | tenisideal.com.br")
    return "\n".join(linhas), usados


def main():
    if not TOKEN:
        print("ERRO: variável AWIN_API_TOKEN não definida.", file=sys.stderr)
        print("Defina o token e rode de novo.", file=sys.stderr)
        sys.exit(1)

    try:
        dados = buscar_promocoes()
    except urllib.error.HTTPError as e:
        print(f"ERRO HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)

    promocoes = dados.get("data") or dados.get("promotions") or []
    mensagem, qtd = formatar(promocoes)

    # Salva em arquivo e imprime
    with open("cupons_hoje.txt", "w", encoding="utf-8") as f:
        f.write(mensagem)

    print(mensagem)
    print(f"\n[{qtd} cupons formatados | total recebido da Awin: {len(promocoes)}]", file=sys.stderr)


if __name__ == "__main__":
    main()
