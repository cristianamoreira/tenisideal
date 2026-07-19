#!/usr/bin/env python3
"""Carrossel FOTO do @tenisideal_br (capa POV IA + 4 tenis recortados + CTA), estilo
brutalism verde-lima. Formato do "vencedor viral": mesma familia visual do GH-005.

Reaproveita o motor de video (selecao de tenis + download + recorte rembg) e o engine
carrossel_estilos/render.js (arquetipos fotocapa/foto/cta). Gera capa por IA e a copy
(manchete, blurb de cada tenis, legenda) via OpenRouter, com fallback por template.

Rodizio proprio de TEMAS; escolha por TEMA_FOTO=<key> ou pela semana do ano.
Envia por e-mail (Brevo), como os outros robos.

Teste local (sem enviar): TEMA_FOTO=iniciante python3 gerar_carrossel_foto.py
Enviar de verdade: BREVO_API_KEY=... EMAIL_CUPONS=... OPENROUTER_API_KEY=... python3 gerar_carrossel_foto.py
"""
import os, sys, io, json, base64, tempfile, subprocess, datetime, urllib.request
from PIL import Image

import gerar_video_tiktok as vid  # carregar_catalogo, baixar, recortar, amazon, eh_trilha, distintas, sel_*, fmt, preco

RAIZ = os.path.dirname(os.path.abspath(__file__))
RENDER_JS = os.path.join(RAIZ, "carrossel_estilos", "render.js")
CAPA_FALLBACK = os.path.join(RAIZ, "assets", "capa-pov-fallback.png")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CANVAS = 1500
SHOE_W, SHOE_H = 0.82, 0.66

# Temas do rodizio foto. select: reaproveita os seletores do motor de video.
TEMAS_FOTO = [
    dict(key="iniciante", assunto="Tênis de iniciante", n=4, select=vid.sel_iniciante,
         tema_pt="os melhores tênis pra quem está começando a correr", realce="centavo",
         capa_fb="{n} tênis pra você *começar* a correr sem erro.",
         tags=["iniciante", "corridainiciante"]),
    dict(key="ate500", assunto="Tênis até R$500", n=4, select=vid.sel_ate500,
         tema_pt="os melhores tênis de corrida até R$500", realce="bolso",
         capa_fb="{n} tênis até R$500 que não pesam no *bolso*.",
         tags=["custobeneficio", "tenisbarato"]),
    dict(key="amort", assunto="Máximo amortecimento", n=4, select=vid.sel_amort,
         tema_pt="tênis de máximo amortecimento pra correr sem dor", realce="conforto",
         capa_fb="{n} tênis que amortecem e poupam o *joelho*.",
         tags=["amortecimento", "conforto"]),
    dict(key="leves", assunto="Leves e rápidos", n=4, select=vid.sel_leves,
         tema_pt="tênis leves e rápidos pra ganhar velocidade", realce="velocidade",
         capa_fb="{n} tênis leves que te fazem *voar*.",
         tags=["velocidade", "carbono"]),
]

CTA = dict(type="cta", kicker="A REAL QUE NINGUÉM FALA", titulo="O *melhor* tênis não existe.",
           corpo=("Existe o certo pra VOCÊ: pra sua pisada, seu peso e seu objetivo. "
                  "Descubra o seu em 2 minutos, de graça."),
           cta="Faz o quiz no link da bio 👆", plug="@tenisideal_br")


def escolher_tema():
    chave = (os.environ.get("TEMA_FOTO") or "").strip().lower()
    t = next((x for x in TEMAS_FOTO if x["key"] == chave), None)
    if t:
        return t
    semana = datetime.date.today().isocalendar()[1]
    return TEMAS_FOTO[semana % len(TEMAS_FOTO)]


def preparar_tenis(prod, wd, idx):
    """Baixa a foto do catalogo, recorta o fundo (rembg) e centraliza numa tela
    1500x1500 transparente com folga. Retorna o caminho do PNG (ou None)."""
    url = prod.get("photo")
    if not url:
        return None
    try:
        cut = vid.recortar(vid.baixar(url))
    except Exception as e:
        print(f"[foto {idx} falhou] {e}", file=sys.stderr)
        return None
    if cut is None:
        return None
    bb = cut.getbbox()
    if bb:
        cut = cut.crop(bb)
    sw, sh = cut.size
    scale = min(CANVAS * SHOE_W / sw, CANVAS * SHOE_H / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    cut = cut.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(cut, ((CANVAS - nw) // 2, (CANVAS - nh) // 2), cut)
    p = os.path.join(wd, f"shoe{idx}.png")
    canvas.save(p)
    return p


def _openrouter(payload, timeout=90):
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Authorization": "Bearer " + OPENROUTER_KEY,
                                          "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.URLError as e:  # macOS local: cert store ausente -> fallback sem verificacao
        import ssl
        if not isinstance(getattr(e, "reason", None), ssl.SSLError):
            raise
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.load(r)


def gerar_capa(tema, wd):
    """Gera a capa POV por IA (OpenRouter gemini image). Fallback: foto fixa commitada."""
    dest = os.path.join(wd, "capa.png")
    if OPENROUTER_KEY:
        prompt = ("Dynamic action shot of a runner mid-stride on a scenic road at golden-hour "
                  "sunrise, wearing brightly colored running shoes with orange and lime green "
                  "accents and vibrant colorful athletic wear, vivid saturated colors, warm "
                  "sunlight, blue sky with soft clouds, lush green scenery on the sides, energetic "
                  "sense of motion, realistic photo, tall vertical 4:5 composition, plenty of open "
                  "sky and road space in the upper half for a headline, no text, no letters, no "
                  "words, no logos, no brand marks, no swoosh.")
        try:
            d = _openrouter({"model": "google/gemini-2.5-flash-image",
                             "messages": [{"role": "user", "content": prompt}],
                             "modalities": ["image", "text"]})
            imgs = d["choices"][0]["message"].get("images", [])
            b64 = imgs[0]["image_url"]["url"].split(",", 1)[1]
            open(dest, "wb").write(base64.b64decode(b64))
            print(f"capa IA gerada (custo ~{d.get('usage', {}).get('cost', 0):.4f} USD)")
            return dest
        except Exception as e:
            print(f"[capa IA falhou -> fallback] {e}", file=sys.stderr)
    if os.path.exists(CAPA_FALLBACK):
        Image.open(CAPA_FALLBACK).convert("RGB").save(dest)
        return dest
    return None


def gerar_copy(tema, tenis):
    """Manchete da capa, blurb de cada tenis e legenda. Via OpenRouter (JSON), com fallback."""
    nomes = [f"{s['brand']} {s['name']}" for s in tenis]
    blurbs_fb = [
        "Conforto e custo que fazem sentido. Aguenta o treino do dia a dia.",
        "Amortecimento honesto pelo preço. Cumpre o que promete.",
        "Leve no pé e no bolso. Boa pra rodar sem drama.",
        "Estável e durável. Pra quilometragem de verdade.",
        "Versátil da rua à esteira. Vai bem em qualquer treino.",
    ]
    fallback = {
        "capa_titulo": tema.get("capa_fb", "{n} tênis que valem cada passada.").format(n=len(tenis)),
        "capa_corpo": "Deslize até o final. O último muda tudo.",
        "itens": [{"corpo": blurbs_fb[i % len(blurbs_fb)]} for i in range(len(tenis))],
        "legenda": (f"{len(tenis)} {tema['tema_pt']} 👟\n\n" + "\n".join(f"{i+1}️⃣ {n}" for i, n in enumerate(nomes)) +
                    "\n\nNenhum é o melhor pra todo mundo. O melhor é o que combina com a SUA pisada, peso e objetivo.\n\n"
                    "🔎 Descubra o seu no quiz grátis (link na bio)."),
    }
    if not OPENROUTER_KEY:
        return fallback
    lista = "\n".join(f"- {n} (R$ {int(vid.preco(s))})" for n, s in zip(nomes, tenis))
    instrucao = (
        "Você escreve copy de carrossel do Instagram/TikTok de uma marca brasileira de recomendação "
        "de tênis de corrida (@tenisideal_br), tom direto, empolgado e honesto, PT-BR. "
        f"Tema: {tema['tema_pt']}. Tênis (na ordem):\n{lista}\n\n"
        "Devolva SÓ um JSON com as chaves: "
        "capa_titulo (manchete curta em CAIXA natural, com UMA palavra entre *asteriscos* pra destaque, "
        "termine com ponto), capa_corpo (uma linha curta de gancho), "
        "itens (lista com um objeto {\"corpo\": \"...\"} por tênis, na MESMA ordem; cada corpo com 2 frases "
        "curtas dizendo pra quem serve e por quê, sem repetir a marca), "
        "legenda (texto pro post: gancho + lista numerada dos tênis + porque 'o melhor' depende da pisada + "
        "CTA pro quiz no link da bio + hashtags). "
        "Regras: nada de travessão (—), nada de itálico, no máximo 2 emojis por campo, não invente preço.")
    try:
        d = _openrouter({"model": "google/gemini-2.5-flash",
                         "messages": [{"role": "user", "content": instrucao}],
                         "response_format": {"type": "json_object"}})
        txt = d["choices"][0]["message"]["content"]
        obj = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        # sanidade: precisa ter itens do tamanho certo
        if not obj.get("itens") or len(obj["itens"]) < len(tenis):
            raise ValueError("itens insuficientes")
        obj["itens"] = obj["itens"][:len(tenis)]
        for k in ("capa_titulo", "capa_corpo", "legenda"):
            obj.setdefault(k, fallback[k])
        return obj
    except Exception as e:
        print(f"[copy IA falhou -> fallback] {e}", file=sys.stderr)
        return fallback


def montar(tema, wd):
    catalogo = vid.carregar_catalogo()
    escolhidos = tema["select"](catalogo)[: tema["n"]]
    if len(escolhidos) < tema["n"]:
        print(f"ERRO: só {len(escolhidos)} tênis pro tema {tema['key']}.", file=sys.stderr)
        return None
    imgs = []
    tenis_ok = []
    for s in escolhidos:
        p = preparar_tenis(s, wd, len(tenis_ok) + 1)
        if p:
            imgs.append(p); tenis_ok.append(s)
    if len(tenis_ok) < tema["n"]:
        print(f"ERRO: só {len(tenis_ok)} fotos recortadas.", file=sys.stderr)
        return None
    capa = gerar_capa(tema, wd)
    if not capa:
        print("ERRO: sem capa.", file=sys.stderr); return None
    copy = gerar_copy(tema, tenis_ok)

    slides = [dict(type="fotocapa", titulo=copy["capa_titulo"], corpo=copy["capa_corpo"], img=os.path.basename(capa))]
    for i, (s, item) in enumerate(zip(tenis_ok, copy["itens"]), 1):
        slides.append(dict(type="foto", kicker=f"{i:02d}",
                           titulo=f"{s['brand']} {s['name']}", corpo=item.get("corpo", ""),
                           img=os.path.basename(imgs[i - 1])))
    slides.append(dict(CTA))
    roteiro = dict(estilo="brutalism", formato="carrossel", outDir="out", slides=slides)
    open(os.path.join(wd, "roteiro.json"), "w", encoding="utf-8").write(json.dumps(roteiro, ensure_ascii=False))
    r = subprocess.run(["node", RENDER_JS, os.path.join(wd, "roteiro.json")],
                       capture_output=True, text=True)
    print(r.stdout[-400:]);
    if r.returncode != 0:
        print("render.js erro:", r.stderr[-500:], file=sys.stderr); return None
    outdir = os.path.join(wd, "out")
    pngs = sorted(os.path.join(outdir, f) for f in os.listdir(outdir) if f.endswith(".png"))
    return pngs, copy["legenda"], tema["assunto"]


def enviar(pngs, legenda, assunto):
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    anexos = []
    for p in pngs:
        with open(p, "rb") as f:
            anexos.append({"content": base64.b64encode(f.read()).decode(), "name": os.path.basename(p)})
    if not key or not email:
        print(f"Sem BREVO_API_KEY/EMAIL_CUPONS — {len(anexos)} slides gerados, e-mail pulado.")
        return
    leg = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = ("<p style='font-family:sans-serif'>Oi! 👋 Carrossel <b>foto</b> pro <b>@tenisideal_br</b> "
            f"— <b>{assunto}</b>. {len(anexos)} slides em anexo (ordem slide-01..0N). Poste na ordem e cole a "
            "legenda abaixo. No TikTok, escolha um <b>som em alta</b>.</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;border:1px solid #ddd;"
            f"border-radius:8px;padding:14px;font-size:14px'>{leg}</pre>")
    body = {"sender": {"email": remet, "name": "Conteúdo - Tênis Ideal"}, "to": [{"email": email}],
            "subject": f"👟 Carrossel foto — {assunto} — {datetime.date.today().strftime('%d/%m')}",
            "htmlContent": html, "attachment": anexos}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        print(f"✅ E-mail enviado para {email} com {len(anexos)} slides (HTTP {r.status})")


def main():
    tema = escolher_tema()
    print(f"🎠 Tema foto: {tema['assunto']} ({tema['key']})")
    wd = tempfile.mkdtemp(prefix="carr_foto_")
    res = montar(tema, wd)
    if not res:
        sys.exit(1)
    pngs, legenda, assunto = res
    print(f"{len(pngs)} slides em {os.path.dirname(pngs[0])}")
    enviar(pngs, legenda, assunto)


if __name__ == "__main__":
    main()
