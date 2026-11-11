#!/usr/bin/env python3
"""Revisor de copy do Tênis Ideal — garante pt-BR correto e as regras de estilo
da marca em todo texto gerado automaticamente (artes, vídeos, carrosséis).

Duas camadas:
  1. Validações DURAS por código (este arquivo, funções puras): travessão,
     emojis excedentes, preço inventado, limite de legenda do Instagram.
  2. Revisão por IA (OpenRouter, opcional — só se OPENROUTER_API_KEY existir):
     corrige gramática/ortografia SEM reescrever o estilo. Fail-open: qualquer
     falha da IA devolve o texto original saneado. Ver revisar() na camada 2.

Uso típico (nos geradores):
    import revisor_copy
    legenda = revisor_copy.revisar(legenda, contexto="legenda de arte do dia",
                                   campo="legenda", precos_validos=[499.0])
"""
import os
import re
import sys
import json
import urllib.request

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODELO_REVISOR = "google/gemini-2.5-flash"
LIMITE_LEGENDA = 2200  # limite de caracteres de legenda do Instagram

# Emojis "soltos" (pictogramas). NÃO casa keycaps (1️⃣ = dígito+FE0F+20E3) nem
# dígitos — as listas numeradas das legendas usam keycaps e devem sobreviver.
_EMOJI_RE = re.compile(
    "(?:[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\U0001F900-\U0001F9FF]️?)"
)

# R$ 1.313,78 | R$499 | R$ 500
_PRECO_RE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d+(?:,\d{2})?)")


def remover_travessao(texto):
    """Regra da marca: nada de travessão. ' — ' vira ': '; '—' colado vira '-'."""
    return texto.replace(" — ", ": ").replace("—", "-")


def limitar_emojis(texto, maximo=2):
    """Mantém só os primeiros `maximo` emojis pictográficos; remove o resto.
    Keycaps numéricos (1️⃣..9️⃣) não contam nem são removidos."""
    vistos = 0
    saida = []
    i = 0
    while i < len(texto):
        m = _EMOJI_RE.match(texto, i)
        if m:
            vistos += 1
            if vistos <= maximo:
                saida.append(m.group(0))
            i = m.end()
        else:
            saida.append(texto[i])
            i += 1
    return "".join(saida)


def precos_citados(texto):
    """Extrai todos os valores R$ do texto como float (parse pt-BR)."""
    valores = []
    for bruto in _PRECO_RE.findall(texto):
        normalizado = bruto.replace(".", "").replace(",", ".")
        valores.append(float(normalizado))
    return valores


def precos_suspeitos(texto, validos, tolerancia=1.0):
    """Preços citados que NÃO batem com nenhum valor válido (catálogo + limites
    do tema, ex.: 300/400/500). Retorna a lista de suspeitos ([] = tudo ok)."""
    validos = list(validos or [])
    return [p for p in precos_citados(texto)
            if not any(abs(p - v) <= tolerancia for v in validos)]


def limitar_legenda(texto, limite=LIMITE_LEGENDA):
    """Trunca a legenda no limite do Instagram, cortando na última quebra de
    linha antes do limite (nunca no meio de palavra/hashtag)."""
    if len(texto) <= limite:
        return texto
    corte = texto.rfind("\n", 0, limite)
    if corte == -1:
        corte = texto.rfind(" ", 0, limite)
    if corte == -1:
        corte = limite
    return texto[:corte].rstrip()


def sanear_campo(texto, campo="legenda"):
    """Validações duras por tipo de campo. campo: 'titulo' | 'corpo' | 'legenda'."""
    t = remover_travessao(texto)
    if campo in ("titulo", "corpo"):
        t = limitar_emojis(t, 2)
    if campo == "legenda":
        t = limitar_legenda(t)
    return t


# ──────────────────── camada 2: revisão por IA (fail-open) ────────────────────

PROMPT_REVISOR = (
    "Você é um revisor profissional de texto publicitário em português do Brasil. "
    "Revise o texto abaixo e devolva APENAS o texto corrigido, sem comentários, "
    "sem aspas em volta, sem markdown.\n\n"
    "REGRAS (siga TODAS):\n"
    "1. Corrija gramática, ortografia, concordância, crase e acentuação (pt-BR).\n"
    "2. NÃO reescreva o estilo: mantenha o tom, as gírias da marca, os emojis, "
    "as hashtags, as quebras de linha e a estrutura EXATAMENTE como estão.\n"
    "3. NÃO use travessão (—) nem itálico.\n"
    "4. NÃO altere nomes de marca/modelo de tênis nem valores em R$.\n"
    "5. NÃO adicione nem remova frases. Só conserte erros.\n"
    "6. Se o texto já estiver correto, devolva-o idêntico.\n"
)


def _openrouter(payload, timeout=60):
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + OPENROUTER_KEY,
                 "Content-Type": "application/json"}, method="POST")
    try:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.URLError as e:  # macOS local: cert store ausente
            import ssl
            if not isinstance(getattr(e, "reason", None), ssl.SSLError):
                raise
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return json.load(r)
    except Exception as e:
        print(f"[openrouter erro] {e}", file=sys.stderr)
        return None


def openrouter_chat(prompt, model=MODELO_REVISOR, response_format=None, timeout=60):
    """Chamada simples de chat. Retorna o texto da resposta, ou None em falha."""
    if not OPENROUTER_KEY:
        return None
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if response_format:
        payload["response_format"] = response_format
    try:
        d = _openrouter(payload, timeout=timeout)
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[openrouter falhou] {e}", file=sys.stderr)
        return None


def _revisar_ia(texto, contexto=""):
    """Uma chamada de revisão. Retorna o texto revisado ou None em falha."""
    extra = f"\nContexto do texto: {contexto}.\n" if contexto else "\n"
    return openrouter_chat(PROMPT_REVISOR + extra + "\nTEXTO:\n" + texto)


def revisar(texto, contexto="", campo="legenda", precos_validos=None):
    """Revisa um texto: IA (se disponível) + validações duras. NUNCA lança
    exceção por falha de IA — no pior caso devolve o original saneado."""
    original = texto
    revisado = _revisar_ia(texto, contexto)

    if not revisado:
        revisado = original
    # guarda-corpo 1: revisor reescreveu demais (< 50% ou > 200% do tamanho) -> descarta
    elif not (0.5 * len(original) <= len(revisado) <= 2.0 * len(original)):
        print(f"[revisor descartado: reescrita radical] {revisado[:80]!r}", file=sys.stderr)
        revisado = original
    # guarda-corpo 2: revisor introduziu preço que não existia -> descarta
    elif precos_validos and precos_suspeitos(revisado, precos_validos) \
            and not precos_suspeitos(original, precos_validos):
        print("[revisor descartado: inventou preço]", file=sys.stderr)
        revisado = original

    revisado = sanear_campo(revisado, campo)
    # checklist item 5: CTA presente na legenda (só avisa — não bloqueia)
    if campo == "legenda" and not re.search(r"\bbio\b", revisado.lower()):
        print("[revisor] ⚠️ legenda sem CTA 'link na bio' — conferir template", file=sys.stderr)
    if revisado != original:
        print(f"[revisor] antes : {original!r}", file=sys.stderr)
        print(f"[revisor] depois: {revisado!r}", file=sys.stderr)
    return revisado


def revisar_copy_carrossel(obj, precos_validos=None):
    """Revisa o dict de copy do carrossel foto (capa_titulo, capa_corpo,
    itens[*].corpo, legenda). Altera e retorna o próprio dict."""
    if obj.get("capa_titulo"):
        obj["capa_titulo"] = revisar(obj["capa_titulo"], "manchete da capa do carrossel",
                                     campo="titulo", precos_validos=precos_validos)
    if obj.get("capa_corpo"):
        obj["capa_corpo"] = revisar(obj["capa_corpo"], "linha de gancho da capa",
                                    campo="corpo", precos_validos=precos_validos)
    for item in obj.get("itens", []):
        if item.get("corpo"):
            item["corpo"] = revisar(item["corpo"], "descrição curta de um tênis",
                                    campo="corpo", precos_validos=precos_validos)
    if obj.get("legenda"):
        obj["legenda"] = revisar(obj["legenda"], "legenda do post no Instagram",
                                 campo="legenda", precos_validos=precos_validos)
    return obj
