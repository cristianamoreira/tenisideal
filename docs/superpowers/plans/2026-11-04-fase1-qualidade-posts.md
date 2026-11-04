# Fase 1 — Qualidade dos Posts (Revisor + Banco + Domingo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Garantir qualidade de texto (pt-BR sem erros, estilo consistente) em todo conteúdo gerado automaticamente, criar o banco de carrosséis pré-aprovados e adicionar o post motivacional de domingo — pré-requisitos para ligar a publicação automática (Fase 2, plano separado).

**Architecture:** Novo módulo `revisor_copy.py` (validações duras por código + revisão opcional por IA, fail-open) importado pelos 4 geradores existentes. Novo par `banco_posts.py` (helpers puros da fila JSON) + `carrossel_do_banco.py` (consome o banco e envia por e-mail). `gerar_arte_instagram.py` ganha o builder `motivacional`. O workflow `conteudo-do-dia.yml` ganha o caso domingo, consulta o banco antes de gerar carrossel e auto-commita a fila.

**Tech Stack:** Python 3 stdlib (urllib, json, re) + OpenRouter (gemini-2.5-flash) para revisão IA. pytest só local (repo não tem CI de testes). Spec: `docs/superpowers/specs/2026-11-04-publicacao-automatica-redes-design.md`.

## Global Constraints

- Todo texto user-facing, commit e comentário em **pt-BR**.
- Regras de copy (do spec): **sem travessão (—)**, **sem itálico**, **máx. 2 emojis por campo** (títulos/corpos de slide; legenda não tem teto de emojis), **legenda ≤ 2.200 caracteres**, **nunca inventar preço**, CTA "link na bio" presente.
- **Fail-open obrigatório:** falha do revisor/IA NUNCA derruba o pipeline — usa o texto original saneado. Toda correção logada "antes → depois".
- Scripts permanecem **standalone** (padrão do repo): invocáveis como `python3 <script>.py`, deps via stdlib + instaladas ad-hoc no workflow. Nenhuma dependência paga nova.
- Git local só funciona via `subprocess` do Python (bloqueio Xcode license no Bash direto). Commits: usar o wrapper Python mostrado nos steps.
- Testes: `python3 -m pytest tests/ -v` (instalar com `pip install pytest` se faltar). Não adicionar workflow de CI para testes.

---

### Task 1: `revisor_copy.py` — validações duras (código puro)

**Files:**
- Create: `revisor_copy.py`
- Create: `tests/test_revisor_copy.py`

**Interfaces:**
- Produces (usadas nas Tasks 2, 3 e 6):
  - `remover_travessao(texto: str) -> str`
  - `limitar_emojis(texto: str, maximo: int = 2) -> str`
  - `precos_citados(texto: str) -> list[float]`
  - `precos_suspeitos(texto: str, validos: list[float], tolerancia: float = 1.0) -> list[float]`
  - `limitar_legenda(texto: str, limite: int = 2200) -> str`
  - `sanear_campo(texto: str, campo: str = "legenda") -> str` — campo ∈ {"titulo", "corpo", "legenda"}

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -m pytest tests/test_revisor_copy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'revisor_copy'` (ou ImportError). Se pytest não estiver instalado: `pip install pytest`.

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -m pytest tests/test_revisor_copy.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'revisor_copy.py', 'tests/test_revisor_copy.py'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: revisor_copy — validações duras de estilo (travessão, emojis, preço, limite de legenda)'], check=True)
"
```

---

### Task 2: `revisor_copy.py` — revisão por IA com fail-open

**Files:**
- Modify: `revisor_copy.py` (acrescentar ao final)
- Modify: `tests/test_revisor_copy.py` (acrescentar testes)

**Interfaces:**
- Consumes: `sanear_campo`, `precos_suspeitos` (Task 1)
- Produces (usadas nas Tasks 3 e 6):
  - `openrouter_chat(prompt: str, model: str = MODELO_REVISOR, response_format: dict | None = None, timeout: int = 60) -> str | None` — texto da resposta ou None em falha
  - `revisar(texto: str, contexto: str = "", campo: str = "legenda", precos_validos: list[float] | None = None) -> str`
  - `revisar_copy_carrossel(obj: dict, precos_validos: list[float] | None = None) -> dict` — revisa in-place as chaves `capa_titulo`, `capa_corpo`, `itens[*]['corpo']`, `legenda`

- [ ] **Step 1: Write the failing tests**

Acrescentar ao final de `tests/test_revisor_copy.py`:

```python
# ---------- camada IA (revisar) — testes com monkeypatch, sem rede ----------

def test_revisar_failopen_quando_ia_indisponivel(monkeypatch):
    monkeypatch.setattr(rc, "_revisar_ia", lambda texto, contexto: None)
    assert rc.revisar("Texto ok — teste", campo="corpo") == "Texto ok: teste"


def test_revisar_aplica_correcao_da_ia(monkeypatch):
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: "Texto corrigido certinho")
    assert rc.revisar("Texto corigido certinho", campo="corpo") == "Texto corrigido certinho"


def test_revisar_descarta_ia_que_inventou_preco(monkeypatch):
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: "Agora por R$ 199!")
    saida = rc.revisar("Por R$ 499", campo="corpo", precos_validos=[499.0])
    assert "199" not in saida and "499" in saida


def test_revisar_descarta_reescrita_radical(monkeypatch):
    # IA devolveu algo com menos da metade / mais que o dobro do tamanho -> descarta
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: "oi")
    original = "Uma legenda longa que fala do tênis ideal pra sua corrida de domingo."
    assert rc.revisar(original, campo="corpo") == original


def test_revisar_sempre_saneia_mesmo_sem_ia(monkeypatch):
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: None)
    saida = rc.revisar("A 🏃 B 🔥 C 👟", campo="titulo")
    assert saida.count("👟") == 0  # 3º emoji removido


def test_revisar_avisa_legenda_sem_cta(monkeypatch, capsys):
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: None)
    rc.revisar("legenda qualquer sem chamada", campo="legenda")
    assert "sem CTA" in capsys.readouterr().err


def test_revisar_copy_carrossel_revisa_todos_os_campos(monkeypatch):
    monkeypatch.setattr(rc, "_revisar_ia", lambda t, c: None)
    obj = {"capa_titulo": "Top — demais", "capa_corpo": "corpo — x",
           "itens": [{"corpo": "item — um"}, {"corpo": "item — dois"}],
           "legenda": "legenda — final"}
    out = rc.revisar_copy_carrossel(obj)
    assert "—" not in json.dumps(out, ensure_ascii=False)


import json  # usado no teste acima (deixar no topo do arquivo junto dos imports)
```

(Mover o `import json` para o topo do arquivo de teste, junto de `import sys, os`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revisor_copy.py -v`
Expected: os 6 novos FAIL com `AttributeError: ... has no attribute '_revisar_ia'`; os 12 antigos PASS.

- [ ] **Step 3: Write the implementation**

Acrescentar ao final de `revisor_copy.py`:

```python
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
    if campo == "legenda" and "bio" not in revisado.lower():
        print("[revisor] ⚠️ legenda sem CTA 'link na bio' — conferir template", file=sys.stderr)
    if revisado != original:
        print(f"[revisor] antes : {original!r}")
        print(f"[revisor] depois: {revisado!r}")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revisor_copy.py -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'revisor_copy.py', 'tests/test_revisor_copy.py'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: revisor_copy — revisão por IA com fail-open e guarda-corpos (reescrita radical, preço inventado)'], check=True)
"
```

---

### Task 3: Integrar o revisor nos 4 geradores

**Files:**
- Modify: `gerar_carrossel_foto.py` (função `gerar_copy`, ~linha 179-182)
- Modify: `gerar_arte_instagram.py` (função `main`, ~linha 545-547)
- Modify: `gerar_video_tiktok.py` (função `main`, ~linha 359-361)
- Modify: `gerar_carrossel_instagram.py` (função `main`, ~linha 262)

**Interfaces:**
- Consumes: `revisor_copy.revisar(texto, contexto, campo, precos_validos)`, `revisor_copy.revisar_copy_carrossel(obj, precos_validos)` (Task 2)
- Produces: nada novo — mesmos retornos dos scripts, agora com texto revisado.

- [ ] **Step 1: `gerar_carrossel_foto.py` — revisar a copy da IA**

No topo do arquivo, junto do `import gerar_video_tiktok as vid`, adicionar:

```python
import revisor_copy
```

Na função `gerar_copy(tema, tenis)`, localizar o `return obj` (fim do bloco `try`, ~linha 179) e o `return fallback` final (~linha 182) e revisá-los antes de devolver. O trecho atual:

```python
        for k in ("capa_titulo", "capa_corpo", "legenda"):
            obj.setdefault(k, fallback[k])
        return obj
    except Exception as e:
        print(f"[copy IA falhou -> fallback] {e}", file=sys.stderr)
        return fallback
```

vira:

```python
        for k in ("capa_titulo", "capa_corpo", "legenda"):
            obj.setdefault(k, fallback[k])
        precos = [vid.preco(s) for s in tenis] + [300.0, 400.0, 500.0]
        return revisor_copy.revisar_copy_carrossel(obj, precos_validos=precos)
    except Exception as e:
        print(f"[copy IA falhou -> fallback] {e}", file=sys.stderr)
        return revisor_copy.revisar_copy_carrossel(fallback)
```

(Os limites 300/400/500 são os tetos citados pelos temas — "até R$500" etc. — e precisam constar como preços válidos para não serem marcados como inventados.)

- [ ] **Step 2: `gerar_arte_instagram.py` — revisar a legenda final**

No bloco de imports (após `import urllib.request`), adicionar:

```python
import revisor_copy
```

Na função `main()`, o trecho atual:

```python
    png, legenda, assunto = res
    print(f"🎨 Formato do dia: {formato} → {assunto} ({png})")
    enviar_email(png, legenda, assunto)
```

vira:

```python
    png, legenda, assunto = res
    legenda = revisor_copy.revisar(legenda, contexto=f"legenda da arte '{assunto}' no Instagram",
                                   campo="legenda")
    print(f"🎨 Formato do dia: {formato} → {assunto} ({png})")
    enviar_email(png, legenda, assunto)
```

- [ ] **Step 3: `gerar_video_tiktok.py` — revisar a legenda final**

No bloco de imports do topo, adicionar:

```python
import revisor_copy
```

Na função `main()`, o trecho atual:

```python
    mp4, legenda = res
    print(f"🎬 Vídeo gerado — tema: {tema['label']} ({mp4})")
    enviar_email(mp4, legenda, tema["label"])
```

vira:

```python
    mp4, legenda = res
    legenda = revisor_copy.revisar(legenda, contexto=f"legenda de vídeo TikTok, tema {tema['label']}",
                                   campo="legenda")
    print(f"🎬 Vídeo gerado — tema: {tema['label']} ({mp4})")
    enviar_email(mp4, legenda, tema["label"])
```

**Atenção import circular:** `revisor_copy` NÃO importa nenhum gerador, então `gerar_carrossel_foto` (que importa `gerar_video_tiktok`, que agora importa `revisor_copy`) continua seguro.

- [ ] **Step 4: `gerar_carrossel_instagram.py` — revisar a legenda final**

No bloco de imports do topo, adicionar:

```python
import revisor_copy
```

Na função `main()`, o trecho atual:

```python
    enviar_email(pngs, cfg["legenda"], cfg["assunto"])
```

vira:

```python
    legenda = revisor_copy.revisar(cfg["legenda"], contexto=f"legenda do carrossel '{cfg['assunto']}'",
                                   campo="legenda")
    enviar_email(pngs, legenda, cfg["assunto"])
```

- [ ] **Step 5: Verificar sintaxe e imports dos 4 scripts**

Run:
```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -m py_compile gerar_carrossel_foto.py gerar_arte_instagram.py gerar_video_tiktok.py gerar_carrossel_instagram.py revisor_copy.py && echo "SINTAXE OK"
```
Expected: `SINTAXE OK`

- [ ] **Step 6: Smoke test do caminho fallback (sem rede, sem chaves)**

Run:
```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import os
os.environ.pop('OPENROUTER_API_KEY', None)
import revisor_copy
out = revisor_copy.revisar('Teste — de sanidade 🏃 🔥 👟 extra', campo='titulo')
assert '—' not in out and out.count('👟') == 0, out
print('FALLBACK OK:', out)
"
```
Expected: `FALLBACK OK: Teste: de sanidade 🏃 🔥  extra`

- [ ] **Step 7: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'gerar_carrossel_foto.py', 'gerar_arte_instagram.py',
                'gerar_video_tiktok.py', 'gerar_carrossel_instagram.py'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: revisor de copy integrado aos 4 geradores de conteúdo'], check=True)
"
```

---

### Task 4: `banco_posts.py` — helpers da fila de carrosséis

**Files:**
- Create: `banco_posts.py`
- Create: `tests/test_banco_posts.py`
- Create: `banco_posts/fila.json` (fila vazia inicial)

**Interfaces:**
- Produces (usadas na Task 5):
  - `carregar_fila(caminho: str = FILA_PADRAO) -> dict` — `{"fila": [...]}`; arquivo ausente → fila vazia
  - `salvar_fila(fila: dict, caminho: str = FILA_PADRAO) -> None`
  - `proximo_aprovado(fila: dict) -> dict | None` — primeiro item com `status == "aprovado"`
  - `contar_aprovados(fila: dict) -> int`
  - `marcar_publicado(fila: dict, item_id: str, quando: str) -> None` — `ValueError` se id não existir
  - `carregar_post(item_id: str, banco_dir: str = BANCO_DIR) -> tuple[list[str], str, str]` — (slides ordenados, legenda, assunto); `FileNotFoundError` se faltar post.json/slides
- Formato de um item da fila: `{"id": "2026-11-c01", "status": "aprovado" | "publicado", "publicado_em": null | "2026-11-10"}`
- Formato do `post.json` de cada diretório: `{"assunto": "...", "legenda": "...", "tema": "...", "estilo": "..."}`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_banco_posts.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_banco_posts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'banco_posts'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Criar a fila vazia inicial**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && mkdir -p banco_posts && printf '{\n  "fila": []\n}\n' > banco_posts/fila.json
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_banco_posts.py -v`
Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'banco_posts.py', 'tests/test_banco_posts.py', 'banco_posts/fila.json'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: banco_posts — fila de carrosséis pré-aprovados (helpers + fila inicial)'], check=True)
"
```

---

### Task 5: `carrossel_do_banco.py` — consumo do banco + e-mail + alerta

**Files:**
- Create: `carrossel_do_banco.py`
- Create: `tests/test_carrossel_do_banco.py`

**Interfaces:**
- Consumes: `banco_posts.carregar_fila/proximo_aprovado/contar_aprovados/marcar_publicado/salvar_fila/carregar_post` (Task 4)
- Produces (usado na Task 7 — o workflow depende DESTES códigos de saída):
  - exit **0** = carrossel enviado (ou gerado sem e-mail por falta de chave) — fila marcada
  - exit **3** = banco vazio → o workflow cai para a geração na hora
  - exit **1** = erro real (post corrompido etc.)
  - `montar_email(slides, legenda, assunto, restantes) -> dict` (body Brevo) — testável puro

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_carrossel_do_banco.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_carrossel_do_banco.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'carrossel_do_banco'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Consome o próximo carrossel APROVADO do banco (banco_posts/) e envia por
e-mail (Brevo), marcando-o como publicado na fila — nunca repete.

Códigos de saída (o workflow conteudo-do-dia.yml depende deles):
  0 = ok (enviado, ou sem chave Brevo — nesse caso NÃO marca e avisa)
  3 = banco vazio -> o workflow cai pra geração na hora
  1 = erro real (post corrompido, slide faltando...)

Alerta de estoque: quando restarem <= 2 aprovados após o consumo, o e-mail sai
com o aviso "BANCO ACABANDO" para reabastecer com a Claude.

Teste local: python3 carrossel_do_banco.py  (sem BREVO_API_KEY só simula)
"""
import os
import sys
import json
import base64
import datetime
import urllib.request

import banco_posts as bp

ALERTA_MINIMO = 2  # <= 2 aprovados restantes -> alerta no e-mail


def montar_email(slides, legenda, assunto, restantes, anexar=True):
    """Monta o body Brevo. anexar=False só nos testes (não lê os PNGs)."""
    remet = os.environ.get("EMAIL_REMETENTE") or "cupons@tenisideal.com.br"
    email = os.environ.get("EMAIL_CUPONS", "")
    anexos = []
    if anexar:
        for p in slides:
            with open(p, "rb") as f:
                anexos.append({"content": base64.b64encode(f.read()).decode(),
                               "name": os.path.basename(p)})
    leg = legenda.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    alerta = ""
    if restantes <= ALERTA_MINIMO:
        alerta = (f"<p style='font-family:sans-serif;background:#fff3cd;border:1px solid #ffc107;"
                  f"border-radius:8px;padding:12px'><b>⚠️ BANCO ACABANDO:</b> só restam "
                  f"<b>{restantes}</b> carrosséis aprovados. Abra o Claude e peça pra "
                  f"reabastecer o banco de posts.</p>")
    html = (f"{alerta}<p style='font-family:sans-serif'>Oi! 👋 Carrossel <b>do banco</b> "
            f"(pré-aprovado) pro <b>@tenisideal_br</b> — <b>{assunto}</b>. "
            f"{len(slides)} slides em anexo (ordem slide-01..0N). Poste na ordem e cole a legenda:</p>"
            f"<pre style='font-family:sans-serif;white-space:pre-wrap;background:#f5f5f5;"
            f"border:1px solid #ddd;border-radius:8px;padding:14px;font-size:14px'>{leg}</pre>")
    return {"sender": {"email": remet, "name": "Conteúdo - Tênis Ideal"},
            "to": [{"email": email}],
            "subject": f"👟 Carrossel do banco — {assunto} — {datetime.date.today().strftime('%d/%m')}",
            "htmlContent": html, "attachment": anexos}


def enviar_brevo(body):
    """Envia via Brevo. Retorna True se enviou, False se não há chave/destino."""
    key = os.environ.get("BREVO_API_KEY", "")
    email = os.environ.get("EMAIL_CUPONS", "")
    if not key or not email:
        print("Sem BREVO_API_KEY/EMAIL_CUPONS — e-mail pulado (fila NÃO marcada).")
        return False
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        print(f"✅ E-mail enviado (HTTP {r.status})")
    return True


def consumir(banco_dir=bp.BANCO_DIR, fila_path=bp.FILA_PADRAO, hoje=None):
    hoje = hoje or datetime.date.today().isoformat()
    fila = bp.carregar_fila(fila_path)
    item = bp.proximo_aprovado(fila)
    if not item:
        print("Banco vazio: nenhum carrossel aprovado na fila (exit 3 -> gerar na hora).")
        return 3
    try:
        slides, legenda, assunto = bp.carregar_post(item["id"], banco_dir=banco_dir)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"ERRO: post '{item['id']}' corrompido: {e}", file=sys.stderr)
        return 1
    restantes = bp.contar_aprovados(fila) - 1  # depois deste
    print(f"🎠 Carrossel do banco: {item['id']} — {assunto} ({len(slides)} slides, restarão {restantes})")
    body = montar_email(slides, legenda, assunto, restantes)
    if enviar_brevo(body):
        bp.marcar_publicado(fila, item["id"], hoje)
        bp.salvar_fila(fila, fila_path)
        print(f"📦 Fila atualizada: {item['id']} -> publicado em {hoje}")
    return 0


if __name__ == "__main__":
    sys.exit(consumir())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_carrossel_do_banco.py -v`
Expected: 5 passed. Rodar também a suíte toda: `python3 -m pytest tests/ -v` → 33 passed.

- [ ] **Step 5: Smoke test com o banco real (vazio)**

Run: `cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 carrossel_do_banco.py; echo "exit=$?"`
Expected: `Banco vazio: ... (exit 3 -> gerar na hora).` e `exit=3`

- [ ] **Step 6: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'carrossel_do_banco.py', 'tests/test_carrossel_do_banco.py'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: carrossel_do_banco — consumo da fila pré-aprovada com alerta de estoque'], check=True)
"
```

---

### Task 6: Domingo motivacional em `gerar_arte_instagram.py`

**Files:**
- Modify: `gerar_arte_instagram.py` (novo template HTML, novo builder, registro no dict `builders`)

**Interfaces:**
- Consumes: `revisor_copy.openrouter_chat`, `revisor_copy.revisar` (Task 2); funções existentes do próprio script: `render(wd, html, outname)`, `hashtags(*extra)`, `CSS` (constante dos templates)
- Produces: builder `build_motivacional(shoes, wd) -> (png, legenda, assunto) | None`, acionado por `FORMATO_ARTE=motivacional` (env var já suportada pelo `main()`)

- [ ] **Step 1: Adicionar frases fallback e o template HTML**

Logo após a constante `SCHEDULE` (linha ~30), adicionar:

```python
# Frases do post motivacional de domingo ("dia de longão"). Pré-revisadas:
# zero risco de erro de português. A palavra entre *asteriscos* ganha destaque.
FRASES_LONGAO = [
    "O longão de hoje é a *prova* de que você é mais forte do que pensava.",
    "Domingo: o dia em que o corredor *conversa* com a própria cabeça.",
    "Não é sobre o ritmo. É sobre *aparecer* mais um domingo.",
    "Cada quilômetro de hoje é um *tijolo* da sua próxima prova.",
    "O despertador doeu, mas a *volta* pra casa vai valer cada passo.",
    "Longão bom não é o mais rápido. É o que termina com *sorriso*.",
    "Hoje o treino é longo e o café da tarde é *merecido*.",
    "Corpo cansado, mente *leve*. É pra isso que serve o domingo.",
    "A planilha pede 15km. O coração pede *rua*. Bora unir os dois.",
    "Quem corre domingo de manhã *dorme* domingo à tarde. Justo.",
]
```

Logo após o template `HTML_CUPOM` (fim dos templates existentes), adicionar:

```python
HTML_MOTIVACIONAL = CSS + """<div class="canvas darkbg" style="background:radial-gradient(70% 55% at 50% 40%,#2c2d37 0%,#17171d 52%,#0a0a0e 100%);text-align:center;">
<div style="position:absolute;width:820px;height:820px;left:50%;top:40px;transform:translateX(-50%);background:radial-gradient(circle,rgba(200,255,0,.12),transparent 62%);filter:blur(24px);"></div>
<div style="position:absolute;top:60px;width:100%;font-family:'Bebas';font-size:46px;letter-spacing:3px;"><span class="wh">TÊNIS</span><span class="gn">IDEAL</span></div>
<div style="position:absolute;top:154px;left:50%;transform:translateX(-50%);background:rgba(200,255,0,.13);border:1.5px solid rgba(200,255,0,.55);color:#C8FF00;font-family:'Bebas';font-size:26px;letter-spacing:4px;padding:10px 28px 8px;border-radius:30px;">DOMINGO DE LONGÃO</div>
<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:880px;font-family:'Bebas';font-size:92px;line-height:1.04;color:#fff;letter-spacing:1px;text-shadow:0 4px 34px rgba(0,0,0,.45);">@@FRASE@@</div>
<div style="position:absolute;bottom:150px;left:50%;transform:translateX(-50%);width:120px;height:7px;background:#C8FF00;border-radius:4px;"></div>
<div style="position:absolute;bottom:46px;left:0;width:100%;text-align:center;">
 <div style="font-family:'Bebas';font-size:34px;letter-spacing:2px;color:#fff;">@TENISIDEAL<span class="gn">_BR</span></div>
 <div style="font-family:'Mont';font-size:19px;color:#9a9ca7;margin-top:3px;letter-spacing:1px;">tenisideal.com.br</div></div>
</div>"""
```

- [ ] **Step 2: Adicionar o builder**

Logo após a função `build_cupom` (antes de `enviar_email`), adicionar:

```python
def _frase_motivacional():
    """Frase do domingo: tenta a IA (com revisor), senão rotaciona o banco fixo.
    Retorno sempre com UMA palavra entre *asteriscos* para o destaque visual."""
    prompt = ("Escreva UMA frase motivacional curta (máx. 90 caracteres) em português do Brasil "
              "sobre o treino longo de domingo na corrida de rua (o 'longão'). Tom: cumplicidade "
              "de corredor, leve, sem clichê de 'não desista'. Marque UMA palavra-chave entre "
              "*asteriscos* para destaque. Sem emoji, sem aspas, sem travessão. "
              "Devolva SÓ a frase.")
    frase = revisor_copy.openrouter_chat(prompt)
    if frase and 20 <= len(frase) <= 120 and frase.count("*") == 2:
        return revisor_copy.revisar(frase, contexto="frase motivacional de domingo", campo="corpo")
    dia = datetime.date.today().timetuple().tm_yday
    return FRASES_LONGAO[dia % len(FRASES_LONGAO)]


def build_motivacional(shoes, wd):
    """Post leve de domingo: frase de longão, sem venda, CTA suave."""
    frase = _frase_motivacional()
    frase_html = re.sub(r"\*(.+?)\*", r"<span class='gn'>\1</span>", frase)
    html = HTML_MOTIVACIONAL.replace("@@FRASE@@", frase_html)
    png = render(wd, html, "arte_motivacional.png")
    if not png:
        return None
    frase_limpa = frase.replace("*", "")
    leg = (f"{frase_limpa} 🧡\n\n"
           "Marca aquele amigo que não perde um longão de domingo! 🏃\n\n"
           "Bom treino e boa semana, corredores.\n\n"
           "📲 @tenisideal_br\n\n" + hashtags("longao", "domingodecorrida", "treinolongo"))
    return png, leg, "Domingo de longão"
```

- [ ] **Step 3: Registrar o builder no `main()`**

Na função `main()`, o dict atual:

```python
    builders = {"destaque": build_destaque, "comparativo": build_comparativo,
                "sonhos": build_grid, "cupom": build_cupom, "amazon": build_amazon}
```

vira:

```python
    builders = {"destaque": build_destaque, "comparativo": build_comparativo,
                "sonhos": build_grid, "cupom": build_cupom, "amazon": build_amazon,
                "motivacional": build_motivacional}
```

E atualizar o docstring do topo do arquivo: a linha de teste local ganha o novo formato:

```
Teste local: FORMATO_ARTE=destaque|comparativo|sonhos|cupom|amazon|motivacional python3 gerar_arte_instagram.py
```

- [ ] **Step 4: Verificar sintaxe e testar o builder localmente**

Run:
```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -m py_compile gerar_arte_instagram.py && python3 -c "
import os
os.environ.pop('OPENROUTER_API_KEY', None)   # força o banco de frases fixo
os.environ.pop('BREVO_API_KEY', None)        # não envia e-mail
os.environ['FORMATO_ARTE'] = 'motivacional'
import gerar_arte_instagram as g
import tempfile
wd = tempfile.mkdtemp()
g.preparar_fontes(wd)
res = g.build_motivacional([], wd)
assert res, 'builder devolveu None'
png, leg, assunto = res
import os.path
assert os.path.exists(png), png
assert 'longão' in leg.lower() or 'longao' in leg.lower()
print('MOTIVACIONAL OK:', png)
print(leg)
"
```
Expected: `MOTIVACIONAL OK: ...arte_motivacional.png` + legenda impressa. (Requer Chrome local; se `render` falhar por falta de Chrome, validar só o `py_compile` + `_frase_motivacional()` e conferir o PNG na primeira execução do workflow.)

Abrir o PNG gerado e conferir visualmente: manchete legível, chip "DOMINGO DE LONGÃO", logo no rodapé.

- [ ] **Step 5: Commit**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'gerar_arte_instagram.py'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: arte motivacional de domingo (dia de longão) — 7 posts/semana'], check=True)
"
```

---

### Task 7: Workflow `conteudo-do-dia.yml` — domingo + banco + auto-commit da fila

**Files:**
- Modify: `.github/workflows/conteudo-do-dia.yml`

**Interfaces:**
- Consumes: `carrossel_do_banco.py` com exit codes 0/3/1 (Task 5); `FORMATO_ARTE=motivacional` (Task 6)
- Produces: workflow com 7 dias ativos e fila auto-commitada.

- [ ] **Step 1: Permissões de escrita**

Trocar:

```yaml
permissions:
  contents: read
```

por:

```yaml
permissions:
  contents: write   # auto-commit da fila do banco de carrosséis (banco_posts/fila.json)
```

- [ ] **Step 2: Domingo no rodízio**

No step "Decidir o tipo do dia", trocar `7) TIPO=folga ;;` por `7) TIPO=domingo ;;` e atualizar o comentário do calendário:

```yaml
          # Calendario fixo por dia da semana (7 posts/semana)
          #   Seg=carrossel  Ter=arte  Qua=video  Qui=arte  Sex=arte(cupom)  Sab=carrossel  Dom=arte motivacional
```

- [ ] **Step 3: Novos cases no step "Gerar e enviar o conteudo do dia"**

O `case` atual vira (mudanças: carrossel tenta o banco primeiro; novo case `domingo`; case `folga` permanece por compatibilidade com disparo manual):

```yaml
          case "${{ steps.tipo.outputs.tipo }}" in
            video)     python3 gerar_video_tiktok.py ;;
            carrossel)
              # 1º: tenta o banco de pré-aprovados. exit 3 = banco vazio -> gera na hora.
              set +e
              python3 carrossel_do_banco.py
              RC=$?
              set -e
              if [ "$RC" = "3" ]; then
                echo "::warning::Banco de carrosséis vazio — gerando na hora (reabastecer com a Claude)."
                # Rodizio por semana ISO: par = formato FOTO, impar = texto.
                FORMATO="${{ github.event.inputs.formato }}"
                if [ -z "$FORMATO" ]; then
                  WK=$(date -u +%V)
                  if [ $((10#$WK % 2)) -eq 0 ]; then FORMATO=foto; else FORMATO=texto; fi
                fi
                if [ "$FORMATO" = "foto" ]; then
                  echo "Carrossel FOTO (formato=$FORMATO)"
                  python3 gerar_carrossel_foto.py
                else
                  echo "Carrossel de texto (formato=$FORMATO)"
                  python3 gerar_carrossel_instagram.py
                fi
              elif [ "$RC" != "0" ]; then
                exit "$RC"
              fi
              ;;
            arte)      python3 gerar_arte_instagram.py ;;
            domingo)   FORMATO_ARTE=motivacional python3 gerar_arte_instagram.py ;;
            folga)     echo "Folga: nenhum conteudo gerado." ;;
            *)         python3 gerar_arte_instagram.py ;;
          esac
```

- [ ] **Step 4: Step de auto-commit da fila (depois de "Gerar e enviar", antes do upload-artifact)**

```yaml
      - name: Commitar a fila do banco (se consumiu carrossel)
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          if [ -n "$(git status --porcelain banco_posts/fila.json)" ]; then
            git add banco_posts/fila.json
            git commit -m "Banco de posts: marca carrossel do dia como publicado (automático)"
            git pull --rebase origin main
            git push
            echo "✅ Fila do banco atualizada."
          else
            echo "ℹ️ Fila do banco sem mudanças hoje."
          fi
```

- [ ] **Step 5: Incluir a arte motivacional no backup**

No step "Guardar o conteudo (backup)", acrescentar `arte_motivacional.png` já coberto pelo glob `arte_*.png` — conferir que o glob existe (existe). Nada a mudar; só verificar.

- [ ] **Step 6: Validar o YAML**

Run:
```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import yaml
with open('.github/workflows/conteudo-do-dia.yml') as f:
    d = yaml.safe_load(f)
print('YAML OK —', d['name'])
" 2>/dev/null || python3 -c "
import json, subprocess
# fallback sem PyYAML: só checa que o arquivo não tem tabs e é legível
txt = open('.github/workflows/conteudo-do-dia.yml').read()
assert '\t' not in txt, 'YAML com TAB!'
print('Checagem básica OK (instale pyyaml para validação completa: pip install pyyaml)')
"
```
Expected: `YAML OK — Conteúdo do dia (rodízio vídeo/carrossel/arte)` (ou a checagem básica).

- [ ] **Step 7: Commit e push**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', '.github/workflows/conteudo-do-dia.yml'], check=True)
subprocess.run(['git', 'commit', '-m', 'Feat: workflow — domingo motivacional + banco de carrosséis com auto-commit da fila'], check=True)
subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], check=True)
subprocess.run(['git', 'push', 'origin', 'main'], check=True)
"
```

- [ ] **Step 8: Teste de ponta a ponta no GitHub Actions (disparo manual)**

Run:
```bash
gh workflow run conteudo-do-dia.yml -R cristianamoreira/tenisideal -f tipo=carrossel
```
Aguardar e conferir o log (`gh run list -R cristianamoreira/tenisideal -w conteudo-do-dia.yml -L 1`):
Expected: log mostra "Banco de carrosséis vazio — gerando na hora" (fila ainda vazia), o carrossel é gerado com as linhas `[revisor]` no log, e-mail chega.

Depois, testar o domingo:
```bash
gh workflow run conteudo-do-dia.yml -R cristianamoreira/tenisideal -f tipo=domingo
```
Expected: e-mail com `arte_motivacional.png` + legenda do longão.

---

### Task 8: Documentação — README do banco + CLAUDE.md

**Files:**
- Create: `banco_posts/README.md`
- Modify: `CLAUDE.md` (linha do calendário/automação)

**Interfaces:** nenhuma — só documentação.

- [ ] **Step 1: Escrever `banco_posts/README.md`**

```markdown
# Banco de carrosséis pré-aprovados

Carrosséis gerados com a Cristiana no Claude (skills `carrossel-teniscerto` e
`carrossel-estilos`), revisados e aprovados por ela ANTES de entrar aqui.
Nos dias de carrossel (Seg/Sáb), o workflow `conteudo-do-dia.yml` roda
`carrossel_do_banco.py`, que consome o próximo aprovado da fila — só gera
na hora (modo antigo) se o banco estiver vazio.

## Estrutura

    fila.json              ordem de publicação + status
    <id>/                  ex.: 2026-11-c01/
      ├── slide-01.png...  slides na ordem (1080x1350 ou maior)
      └── post.json        {"assunto", "legenda", "tema", "estilo"}

## fila.json

    {"fila": [
      {"id": "2026-11-c01", "status": "aprovado",  "publicado_em": null},
      {"id": "2026-11-c02", "status": "publicado", "publicado_em": "2026-11-10"}
    ]}

- A ORDEM da lista é a ordem de publicação.
- `status`: `aprovado` (pronto) → `publicado` (consumido; nunca repete).
- Quando restarem ≤ 2 aprovados, o e-mail do dia sai com alerta "BANCO ACABANDO".

## Como reabastecer

Abrir o Claude no projeto e pedir: "vamos reabastecer o banco de carrosséis".
A sessão gera ~8 carrosséis com as skills, a Cristiana aprova um a um, e os
aprovados são commitados aqui com a fila atualizada.
```

- [ ] **Step 2: Atualizar o CLAUDE.md**

Na tabela de workflows do `CLAUDE.md`, atualizar a linha do conteúdo diário (se existir a linha de `arte-instagram-diaria.yml`, manter — a mudança é descritiva). Acrescentar ao final da seção "Python automation" o parágrafo:

```markdown
### Conteúdo diário e banco de posts

`conteudo-do-dia.yml` (diário 12:00 UTC) publica o rodízio: Seg=carrossel ·
Ter=arte · Qua=vídeo · Qui=arte · Sex=arte(cupom) · Sáb=carrossel · Dom=arte
motivacional ("longão"). Nos dias de carrossel, consome primeiro o banco de
pré-aprovados (`banco_posts/`, ver README de lá); se vazio, gera na hora.
Toda copy passa pelo `revisor_copy.py` (gramática pt-BR + regras de estilo,
fail-open). Specs: `docs/superpowers/specs/2026-11-04-publicacao-automatica-redes-design.md`.
```

- [ ] **Step 3: Commit e push final**

```bash
cd "/Users/cristianamoreira/Desktop/Tenis Ideal" && python3 -c "
import subprocess
subprocess.run(['git', 'add', 'banco_posts/README.md', 'CLAUDE.md'], check=True)
subprocess.run(['git', 'commit', '-m', 'Docs: README do banco de posts + CLAUDE.md atualizado (fase 1 de qualidade)'], check=True)
subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], check=True)
subprocess.run(['git', 'push', 'origin', 'main'], check=True)
"
```

---

## Depois do plano (sessões manuais, fora deste documento)

1. **Abastecer o banco** (sessão interativa): gerar ~8 carrosséis com `carrossel-teniscerto`/`carrossel-estilos`, aprovação um a um pela Cristiana, commit em `banco_posts/`.
2. **Fase 2 — publicação automática**: plano próprio após a sessão de setup (conta profissional do Instagram, app na Meta, tokens, TikTok developers). Pré-requisito: Fase 1 rodando por alguns dias com e-mails conferidos.
