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
