import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import banco_posts as bp


def _fila(*itens):
    return {"fila": [dict(i) for i in itens]}


def test_carregar_fila_inexistente_devolve_vazia(tmp_path):
    assert bp.carregar_fila(str(tmp_path / "nada.json")) == {"fila": []}


def test_salvar_e_carregar_roundtrip(tmp_path):
    caminho = str(tmp_path / "fila.json")
    fila = _fila({"id": "c01", "status": "aprovado", "publicado_em": None})
    bp.salvar_fila(fila, caminho)
    assert bp.carregar_fila(caminho) == fila


def test_proximo_aprovado_pula_publicados():
    fila = _fila({"id": "c01", "status": "publicado", "publicado_em": "2026-11-03"},
                 {"id": "c02", "status": "aprovado", "publicado_em": None})
    assert bp.proximo_aprovado(fila)["id"] == "c02"


def test_proximo_aprovado_fila_esgotada():
    fila = _fila({"id": "c01", "status": "publicado", "publicado_em": "2026-11-03"})
    assert bp.proximo_aprovado(fila) is None


def test_contar_aprovados():
    fila = _fila({"id": "c01", "status": "aprovado", "publicado_em": None},
                 {"id": "c02", "status": "publicado", "publicado_em": "x"},
                 {"id": "c03", "status": "aprovado", "publicado_em": None})
    assert bp.contar_aprovados(fila) == 2


def test_marcar_publicado():
    fila = _fila({"id": "c01", "status": "aprovado", "publicado_em": None})
    bp.marcar_publicado(fila, "c01", "2026-11-10")
    assert fila["fila"][0]["status"] == "publicado"
    assert fila["fila"][0]["publicado_em"] == "2026-11-10"


def test_marcar_publicado_id_inexistente():
    with pytest.raises(ValueError):
        bp.marcar_publicado(_fila(), "fantasma", "2026-11-10")


def test_carregar_post(tmp_path):
    d = tmp_path / "c01"
    d.mkdir()
    (d / "post.json").write_text(json.dumps(
        {"assunto": "Teste", "legenda": "leg", "tema": "x", "estilo": "brutalism"}),
        encoding="utf-8")
    (d / "slide-02.png").write_bytes(b"png2")
    (d / "slide-01.png").write_bytes(b"png1")
    slides, legenda, assunto = bp.carregar_post("c01", banco_dir=str(tmp_path))
    assert [os.path.basename(s) for s in slides] == ["slide-01.png", "slide-02.png"]
    assert legenda == "leg" and assunto == "Teste"


def test_carregar_post_sem_slides_falha(tmp_path):
    d = tmp_path / "c02"
    d.mkdir()
    (d / "post.json").write_text(json.dumps({"assunto": "a", "legenda": "l"}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        bp.carregar_post("c02", banco_dir=str(tmp_path))
