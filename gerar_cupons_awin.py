#!/usr/bin/env python3
"""Monta a mensagem diária de CUPONS (Awin) + OFERTAS (Amazon) pro WhatsApp.

- Cupons: busca os vouchers ATIVOS das lojas em que você é parceira na Awin (API).
- Ofertas Amazon: a Amazon NÃO tem API de cupons, então destacamos (de forma
  rotativa, mudando a cada dia) os tênis do seu catálogo que têm link de afiliada
  da Amazon. Assim você sempre tem o que postar, com o seu link de comissão.

Saída: cupons_hoje.txt (texto pronto pra colar no Canal do WhatsApp).

Variáveis de ambiente:
- AWIN_API_TOKEN, AWIN_PUBLISHER_ID : só para o bloco de cupons da Awin.
- MAX_CUPONS (opcional, padrão 8), MAX_OFERTAS_AMAZON (opcional, padrão 4).
O bloco da Amazon lê o catálogo (frontend/shoes_data.js) e não precisa de secret.
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
MAX_OFERTAS_AMAZON = int(os.environ.get("MAX_OFERTAS_AMAZON", "4"))


# ───────────────────────── CUPONS (AWIN) ─────────────────────────
def _post(url, headers):
    body = {
        "filters": {
            "membership": "joined",
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
    combos = []
    for path in (f"/publisher/{pid}/promotions/", f"/publishers/{pid}/promotions/"):
        combos.append((base + path, {"Authorization": f"Bearer {TOKEN}"}))
        combos.append((base + path, {"Authorization": TOKEN}))
        combos.append((base + path + f"?accessToken={TOKEN}", {}))

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
    for n in nomes:
        if isinstance(promo, dict) and promo.get(n):
            return promo[n]
    return default


def formatar_cupons(promocoes):
    """Monta só os BLOCOS de cupom (sem cabeçalho/rodapé). Retorna (linhas, qtd)."""
    linhas = []
    usados = 0
    for p in promocoes:
        if usados >= MAX_CUPONS:
            break
        loja = campo(p, "advertiserName") or campo(p.get("advertiser", {}), "name", default="Loja")
        titulo = campo(p, "title", "description", default="").strip()
        voucher = p.get("voucher") or {}
        codigo = campo(voucher, "code") or campo(p, "code")
        link = campo(p, "urlTracking", "clickThroughUrl", "url")
        if not (titulo or codigo):
            continue
        t = " ".join(titulo.split())
        if len(t) > 80:
            t = t[:80].rsplit(" ", 1)[0] + "…"
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
        linhas.append("")
        usados += 1
    return linhas, usados


# ─────────────────────── OFERTAS (AMAZON) ───────────────────────
def carregar_catalogo():
    try:
        c = open("frontend/shoes_data.js", encoding="utf-8").read()
        i = c.find("var SHOES = ")
        return json.loads(c[i + len("var SHOES = "):].rstrip().rstrip(";"))
    except Exception as e:
        print(f"[catálogo indisponível] {e}", file=sys.stderr)
        return []


def _fmt_preco(p):
    try:
        return "R$ " + f"{float(p):.2f}".replace(".", ",")
    except Exception:
        return ""


def ofertas_amazon(n=MAX_OFERTAS_AMAZON):
    """Seleção ROTATIVA dos tênis com link de afiliada da Amazon (muda a cada dia)."""
    shoes = carregar_catalogo()
    amz = []
    for s in shoes:
        a = (s.get("affiliate_links") or {}).get("amazon") or {}
        u = (a.get("url") or "").lower()
        # só links REAIS da Amazon (ignora placeholders quebrados tipo "link.amazon/...")
        if u and ("amzn.to" in u or "amazon." in u):
            amz.append((s, a))
    if not amz:
        return [], 0
    dia = datetime.date.today().timetuple().tm_yday
    start = (dia * n) % len(amz)
    sel = [amz[(start + k) % len(amz)] for k in range(min(n, len(amz)))]
    linhas = []
    for s, a in sel:
        nome = f"{s.get('brand', '')} {s.get('name', '')}".strip()
        preco = _fmt_preco(a.get("price") or s.get("price"))
        parc = (a.get("installments") or "").strip()
        bloco = f"👟 *{nome}*"
        if preco:
            bloco += f"\n💰 {preco}" + (f"  ({parc})" if parc else "")
        bloco += f"\n👉 {a['url']}"
        linhas.append(bloco)
        linhas.append("")
    return linhas, len(sel)


# ───────────────────────── MONTAGEM ─────────────────────────
def montar():
    hoje = datetime.datetime.now().strftime("%d/%m")
    out = [f"🔥 *CUPONS E OFERTAS DO DIA — {hoje}* 🔥", ""]

    # 1) Cupons Awin (resiliente: se falhar, segue sem travar)
    cupons_linhas, qtd_cupons = [], 0
    if TOKEN:
        try:
            dados = buscar_promocoes()
            if isinstance(dados, list):
                promocoes = dados
            else:
                promocoes = (dados.get("data") or dados.get("promotions") or dados.get("offers") or [])
            cupons_linhas, qtd_cupons = formatar_cupons(promocoes)
        except Exception as e:
            print(f"[cupons Awin indisponíveis] {e}", file=sys.stderr)
    else:
        print("[sem AWIN_API_TOKEN — pulando cupons Awin]", file=sys.stderr)

    out.append("🎟️ *CUPONS DAS LOJAS*")
    out.append("")
    if qtd_cupons:
        out += cupons_linhas
    else:
        out.append("Sem cupom ativo hoje — confira as ofertas abaixo. 👇")
        out.append("")

    # 2) Ofertas Amazon (rotativas)
    amz_linhas, qtd_amz = ofertas_amazon()
    if qtd_amz:
        out.append("🛒 *OFERTAS AMAZON — destaques do dia*")
        out.append("")
        out += amz_linhas

    out.append("—")
    out.append("👟 *Tênis Ideal* | tenisideal.com.br")
    return "\n".join(out), qtd_cupons, qtd_amz


def main():
    mensagem, qc, qa = montar()
    with open("cupons_hoje.txt", "w", encoding="utf-8") as f:
        f.write(mensagem)
    print(mensagem)
    print(f"\n[{qc} cupons Awin | {qa} ofertas Amazon]", file=sys.stderr)


if __name__ == "__main__":
    main()
