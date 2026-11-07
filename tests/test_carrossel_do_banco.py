import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import banco_posts as bp
import carrossel_do_banco as cdb


@pytest.fixture
def banco(tmp_path):
    """Banco com 2 aprovados (c01, c02) e 1 publicado (c00)."""
    for cid in ("c00", "c01", "c02"):
        d = tmp_path / cid
        d.mkdir()
        (d / "post.json").write_text(json.dumps(
            {"assunto": f"Assunto {cid}", "legenda": f"Legenda {cid}", "tema": "t", "estilo": "e"}),
            encoding="utf-8")
        (d / "slide-01.png").write_bytes(b"\x89PNG-fake")
    fila = {"fila": [
        {"id": "c00", "status": "publicado", "publicado_em": "2026-11-01"},
        {"id": "c01", "status": "aprovado", "publicado_em": None},
        {"id": "c02", "status": "aprovado", "publicado_em": None},
    ]}
    bp.salvar_fila(fila, str(tmp_path / "fila.json"))
    return tmp_path


def test_consumir_pega_o_primeiro_aprovado_e_marca(banco, monkeypatch):
    enviados = []
    monkeypatch.setattr(cdb, "enviar_brevo", lambda body: enviados.append(body) or True)
    rc = cdb.consumir(banco_dir=str(banco), fila_path=str(banco / "fila.json"), hoje="2026-11-10")
    assert rc == 0
    assert len(enviados) == 1
    fila = bp.carregar_fila(str(banco / "fila.json"))
    assert fila["fila"][1]["status"] == "publicado"
    assert fila["fila"][1]["publicado_em"] == "2026-11-10"
    assert fila["fila"][2]["status"] == "aprovado"  # só consumiu um


def test_consumir_banco_vazio_retorna_3(tmp_path):
    bp.salvar_fila({"fila": []}, str(tmp_path / "fila.json"))
    rc = cdb.consumir(banco_dir=str(tmp_path), fila_path=str(tmp_path / "fila.json"), hoje="2026-11-10")
    assert rc == 3


def test_consumir_sem_chave_brevo_nao_marca(banco, monkeypatch):
    monkeypatch.setattr(cdb, "enviar_brevo", lambda body: False)  # sem chave -> não enviou
    rc = cdb.consumir(banco_dir=str(banco), fila_path=str(banco / "fila.json"), hoje="2026-11-10")
    assert rc == 0
    fila = bp.carregar_fila(str(banco / "fila.json"))
    assert fila["fila"][1]["status"] == "aprovado"  # NÃO consumiu


def test_montar_email_inclui_alerta_quando_restam_poucos(banco):
    body = cdb.montar_email(["/x/slide-01.png"], "leg", "Assunto", restantes=1,
                            anexar=False)
    assert "banco acabando" in body["htmlContent"].lower()


def test_montar_email_sem_alerta_quando_estoque_ok(banco):
    body = cdb.montar_email(["/x/slide-01.png"], "leg", "Assunto", restantes=5,
                            anexar=False)
    assert "banco acabando" not in body["htmlContent"].lower()
