#!/usr/bin/env python3
"""Arte de CUPOM manual (imagem única 1080x1080) — mesma identidade do feed.

Diferente do build_cupom() do gerar_arte_instagram.py (que puxa o cupom da Awin),
aqui os dados do cupom vêm por variáveis de ambiente, pra campanhas pontuais
(ex.: cupom CASUAL30 da Nike). Reusa o template HTML_CUPOM e o render() do gerador
oficial, então a arte fica visualmente idêntica às artes de cupom do dia.

Uso:
    CUPOM_PCT=30 CUPOM_STORE=NIKE CUPOM_CODE=CASUAL30 \
    CUPOM_DESC="EXTRA na linha casual · até 16/07" \
    python3 gerar_arte_cupom.py

Para enviar por e-mail (workflow), exporte também BREVO_API_KEY / EMAIL_CUPONS
e passe CUPOM_ENVIAR=1. Sem isso, só gera o PNG (arte_cupom_manual.png).
"""
import os
import tempfile

import gerar_arte_instagram as ti

# ---- dados do cupom (default = campanha CASUAL30 da Nike) ----
PCT   = os.environ.get("CUPOM_PCT", "30")
STORE = os.environ.get("CUPOM_STORE", "NIKE")
CODE  = os.environ.get("CUPOM_CODE", "CASUAL30")
DESC  = os.environ.get("CUPOM_DESC", "EXTRA na linha casual · até 16/07")
CHIP  = os.environ.get("CUPOM_CHIP", "CUPOM NIKE")
LINK  = os.environ.get("CUPOM_LINK", "https://www.nike.com.br/hotsite/casual30?sorting=Relevance")

# legenda pronta pro WhatsApp / Stories (consumidor final)
LEGENDA = os.environ.get("CUPOM_LEGENDA") or (
    f"🚨 CUPOM NIKE {CODE} — {PCT}% OFF EXTRA 🚨\n\n"
    f"A Nike liberou o cupom *{CODE}*: {PCT}% de desconto EXTRA (em cima do preço que já está em promoção) "
    "na linha casual inteira — Air Force, Dunk, Court, moletom, camiseta e chinelo. 🔥\n\n"
    "⏳ Vai até quinta (16/07) às 23h59 — mas os tamanhos mais procurados somem bem antes.\n\n"
    "Como usar:\n"
    f"1️⃣ Entra pelo link 👉 {LINK}\n"
    "2️⃣ Escolhe seu produto\n"
    f"3️⃣ Aplica o cupom {CODE} no carrinho\n"
    "4️⃣ Vê os 30% caírem 🥳\n\n"
    f"🎟️ Cupom: {CODE}\n"
    "Corre que Air Force com 30% off não dura. 👟💨"
)


def main():
    wd = tempfile.mkdtemp(prefix="ti_cupom_")
    ti.preparar_fontes(wd)
    html = (ti.HTML_CUPOM
            .replace("CUPOM DO DIA", CHIP)
            .replace("@@PCT@@", f"{PCT}%")
            .replace("@@STORE@@", STORE.upper()[:16])
            .replace("@@DESC@@", DESC)
            .replace("@@CODE@@", CODE.upper()))
    png = ti.render(wd, html, "arte_cupom_manual.png")
    if not png:
        raise SystemExit("ERRO: arte não gerada (Chrome?).")
    print(f"🎟️ Arte gerada: {png}")
    print("\n----- LEGENDA (copie e cole) -----\n" + LEGENDA)
    if os.environ.get("CUPOM_ENVIAR") == "1":
        ti.enviar_email(png, LEGENDA, f"Cupom {STORE} {CODE}")


if __name__ == "__main__":
    main()
