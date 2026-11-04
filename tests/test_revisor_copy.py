# tests/test_revisor_copy.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import revisor_copy as rc


def test_remover_travessao_com_espacos():
    assert rc.remover_travessao("O melhor — na real") == "O melhor: na real"


def test_remover_travessao_sem_espacos():
    assert rc.remover_travessao("pré—treino") == "pré-treino"


def test_limitar_emojis_mantem_ate_o_maximo():
    assert rc.limitar_emojis("Corre 🏃 muito 🔥", 2) == "Corre 🏃 muito 🔥"


def test_limitar_emojis_remove_excedentes():
    assert rc.limitar_emojis("A 🏃 B 🔥 C 👟 D ✨", 2) == "A 🏃 B 🔥 C  D "


def test_limitar_emojis_preserva_keycaps_numericos():
    # 1️⃣ é sequência keycap — nunca remover (usada nas listas numeradas)
    texto = "1️⃣ Nike\n2️⃣ Mizuno\n3️⃣ Asics 🔥 👟 ✨"
    saida = rc.limitar_emojis(texto, 2)
    assert "1️⃣" in saida and "2️⃣" in saida and "3️⃣" in saida


def test_precos_citados_formatos_brasileiros():
    txt = "De R$ 1.313,78 por R$499. Até R$ 500!"
    assert rc.precos_citados(txt) == [1313.78, 499.0, 500.0]


def test_precos_suspeitos_detecta_inventado():
    assert rc.precos_suspeitos("Só R$ 299", validos=[499.0, 500.0]) == [299.0]


def test_precos_suspeitos_aceita_validos_com_tolerancia():
    assert rc.precos_suspeitos("Por R$ 499", validos=[499.9]) == []


def test_limitar_legenda_corta_em_quebra_de_linha():
    longa = ("linha\n" * 500)  # 3000 chars
    saida = rc.limitar_legenda(longa, 2200)
    assert len(saida) <= 2200
    assert not saida.endswith("lin")  # cortou em \n, não no meio da palavra


def test_limitar_legenda_nao_mexe_em_texto_curto():
    assert rc.limitar_legenda("curta", 2200) == "curta"


def test_sanear_campo_titulo_aplica_emojis_e_travessao():
    saida = rc.sanear_campo("Top — 🔥 🔥 🔥 demais", campo="titulo")
    assert "—" not in saida
    assert saida.count("🔥") == 2


def test_sanear_campo_legenda_nao_limita_emojis():
    txt = "🏃 🔥 👟 ✨ corre"
    assert rc.sanear_campo(txt, campo="legenda").count("🏃") == 1
    assert "✨" in rc.sanear_campo(txt, campo="legenda")
