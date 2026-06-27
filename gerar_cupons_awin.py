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


def _post(url, headers):
    body = {
        "filters": {
            "membership": "joined",     # lojas em que você é parceira
            "regionCodes": ["BR"],
            "status": "active",
            "type": "voucher",
            "exclusiveOnly": False,
        },
        "pagination": {"page": 1, "pageSize": 100},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def buscar_promocoes():
    pid = PUBLISHER_ID
    base = "https://api.awin.com"
    # Matriz: caminho (singular/plural) × autenticação (raw / Bearer / query param)
    combos = []
    for path in (f"/publisher/{pid}/promotions/", f"/publishers/{pid}/promotions/"):
        combos.append((base + path, {"Authorization": f"Bearer {TOKEN}"}))           # ✅ combinação que funciona
        combos.append((base + path, {"Authorization": TOKEN}))                       # token cru no header
        combos.append((base + path + f"?accessToken={TOKEN}", {}))                   # token na URL

    erros = []
    for i, (url, headers) in enumerate(combos, 1):
        url_log = url.replace(TOKEN, "***") if TOKEN else url
        try:
            print(f"[tentativa {i}] {url_log} | auth={'header' if headers else 'query'}", file=sys.stderr)
            dados = _post(url, headers)
            print(f"[✅ funcionou na tentativa {i}] {url_log}", file=sys.stderr)
            return dados
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", "ignore")[:200]
            erros.append(f"t{i}: HTTP {e.code} {corpo}")
            print(f"[tentativa {i} falhou] HTTP {e.code}: {corpo}", file=sys.stderr)
        except Exception as e:
            erros.append(f"t{i}: {type(e).__name__}")
            print(f"[tentativa {i} erro] {type(e).__name__}: {e}", file=sys.stderr)
    raise RuntimeError("Nenhuma combinação funcionou. Erros: " + " | ".join(erros))


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

        # título limpo: normaliza espaços e corta em palavra inteira
        t = " ".join(titulo.split())
        if len(t) > 80:
            t = t[:80].rsplit(" ", 1)[0] + "…"

        # validade do cupom (se a API informar)
        fim = campo(p, "endDate", "datetimeEnd", "validTo")
        validade = ""
        if fim:
            try:
                d = datetime.datetime.fromisoformat(str(fim).replace("Z", "+00:00"))
                validade = d.strftime("%d/%m")
            except Exception:
                validade = ""

        bloco = f"👟 *{loja}*"
        if t:
            bloco += f"\n{t}"
        if codigo:
            bloco += f"\n🎟️ Cupom: *{codigo}*"
        if validade:
            bloco += f"\n🗓️ Válido até {validade}"
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

    if isinstance(dados, list):
        promocoes = dados
    else:
        promocoes = (dados.get("data") or dados.get("promotions")
                     or dados.get("offers") or [])
    mensagem, qtd = formatar(promocoes)

    # Salva em arquivo e imprime
    with open("cupons_hoje.txt", "w", encoding="utf-8") as f:
        f.write(mensagem)

    print(mensagem)
    print(f"\n[{qtd} cupons formatados | total recebido da Awin: {len(promocoes)}]", file=sys.stderr)


if __name__ == "__main__":
    main()
