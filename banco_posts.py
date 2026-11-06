#!/usr/bin/env python3
"""Helpers da fila do banco de carrosséis pré-aprovados (banco_posts/).

Estrutura em disco:
    banco_posts/
    ├── fila.json              {"fila": [{"id", "status", "publicado_em"}, ...]}
    └── <id>/                  um diretório por carrossel aprovado
        ├── slide-01.png ...
        └── post.json          {"assunto", "legenda", "tema", "estilo"}

status: "aprovado" (pronto pra publicar) | "publicado" (já foi; nunca repete).
A ordem da lista É a ordem de publicação.
"""
import os
import json

RAIZ = os.path.dirname(os.path.abspath(__file__))
BANCO_DIR = os.path.join(RAIZ, "banco_posts")
FILA_PADRAO = os.path.join(BANCO_DIR, "fila.json")


def carregar_fila(caminho=FILA_PADRAO):
    if not os.path.exists(caminho):
        return {"fila": []}
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def salvar_fila(fila, caminho=FILA_PADRAO):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)
        f.write("\n")


def proximo_aprovado(fila):
    return next((i for i in fila["fila"] if i.get("status") == "aprovado"), None)


def contar_aprovados(fila):
    return sum(1 for i in fila["fila"] if i.get("status") == "aprovado")


def marcar_publicado(fila, item_id, quando):
    for item in fila["fila"]:
        if item["id"] == item_id:
            item["status"] = "publicado"
            item["publicado_em"] = quando
            return
    raise ValueError(f"id '{item_id}' não está na fila")


def carregar_post(item_id, banco_dir=BANCO_DIR):
    """Retorna (slides_ordenados, legenda, assunto) de um carrossel do banco."""
    pasta = os.path.join(banco_dir, item_id)
    meta_path = os.path.join(pasta, "post.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    slides = sorted(os.path.join(pasta, n) for n in os.listdir(pasta)
                    if n.startswith("slide-") and n.endswith(".png"))
    if not slides:
        raise FileNotFoundError(f"nenhum slide-*.png em {pasta}")
    return slides, meta["legenda"], meta["assunto"]
