---
name: video-tiktok-tenisideal
description: Use quando a Cristiana quiser um novo VÍDEO vertical pro TikTok do Tênis Ideal (o "slideshow com slides de figuras" que ela recebe por e-mail) — seja criando um TEMA novo pro rodízio (ex.: "tênis pra pisada pronada", "lançamentos 2026", "top Nike") ou VARIANDO o roteiro/formato (mais/menos tênis, gancho diferente, CTA diferente, ordem dos slides). O motor é gerar_video_tiktok.py (slideshow 9:16: gancho → tênis com foto recortada por IA → CTA do quiz, renderizado com Chrome + ffmpeg, enviado por Brevo). Trigger quando ela disser "cria um vídeo/tema novo pro TikTok", "faz uma versão com X tênis", "muda o gancho/CTA", "vídeo do tema Y", ou "gera o vídeo pra eu ver".
---

# video-tiktok-tenisideal

Produz o vídeo vertical 9:16 do TikTok do Tênis Ideal reaproveitando o motor existente
[`gerar_video_tiktok.py`](../../../gerar_video_tiktok.py). **Não reescreva o motor** — edite os
`THEMES` e rode. Textos user-facing sempre em pt-BR.

## Como o motor funciona (leia antes de mexer)

Pipeline por execução, definido em `gerar_video_tiktok.py`:

1. Escolhe um **tema** (via `TEMA_VIDEO=<key>` ou rodízio pelo dia do ano em `THEMES`).
2. `carregar_catalogo()` lê `frontend/shoes_data.js` (o `var SHOES = [...]` gerado pela Sheet).
3. O `select()` do tema filtra o catálogo → escolhe 4-6 tênis (1 por marca, só com foto Amazon, sem trilha).
4. Baixa a foto de cada tênis e **recorta o fundo por IA** (`rembg` u2net; fallback floodfill).
5. Monta os **frames HTML** → renderiza cada um com Chrome headless @2x → 1080x1920 PNG.
6. `ffmpeg` (concat) junta os PNGs num `.mp4` mudo (som é adicionado depois no TikTok).
7. Gera a **legenda** (hook + lista numerada + hashtags) e manda tudo por e-mail (Brevo).

Estrutura fixa do vídeo: **1 frame gancho** → **N frames de tênis** (1.7s cada) → **1 frame CTA "FAÇA O QUIZ"**.
Paleta: fundo grafite radial, destaque verde-lima `#C8FF00`, fontes Bebas (títulos) + Montserrat (corpo).

## Tarefa A — criar um TEMA novo

Cada tema é um dict no array `THEMES` (linhas ~135-151). Schema:

```python
dict(key="<slug>",              # usado em TEMA_VIDEO e no fallback
     label="TÍTULO NO SLIDE",   # aparece em cima de cada tênis (CAIXA ALTA)
     small="LINHA PEQUENA",     # kicker do gancho, ex.: "OS MELHORES"
     big1="LINHA 1", big2="LINHA 2",  # título grande do gancho (big2 é verde-lima)
     sub="chamada do gancho 👇",      # subtítulo do gancho
     select=<funcao_de_selecao>,      # ver abaixo
     hook="1ª linha da legenda 👟🔥",  # abre a legenda do post
     tags=["hashtag1", "hashtag2"]),  # 2 hashtags extras (sem #)
```

**Selecionar os tênis** — reuse um seletor existente ou componha um novo. Todos partem de
`amazon(s) and not eh_trilha(s)` (precisa de foto Amazon recortável e não pode ser trilha) e passam
por `distintas()` (1 tênis por marca). Seletores prontos:

- `sel_premium` — mais caros primeiro (tênis dos sonhos).
- `sel_ate500` — preço ≤ R$520, mais caros primeiro.
- `sel_amort` / `sel_leves` — por tags de amortecimento / leveza.
- `sel_iniciante` — `levels` contém "iniciante", preço ≤ R$700, mais baratos primeiro.
- `sel_tag(sh, ["Tag1","Tag2"])` — genérico por tags do catálogo. **Prefira este pra temas novos.**

Campos disponíveis em cada tênis (`shoes_data.js`): `brand`, `name`, `price`, `photo`,
`affiliate_links` (preços por loja), `tags`, `levels`, `terreno`, `pisada`. Pra um seletor por
pisada/terreno, filtre por esses campos — ex.:

```python
def sel_pronada(sh):
    cands = [s for s in sh if amazon(s) and not eh_trilha(s) and "pronada" in (s.get("pisada") or [])]
    return distintas(sorted(cands, key=lambda s: -(s.get("price") or 0)))
```

Passos:
1. Antes de inventar tags, **confira quais valores existem** no catálogo (senão o seletor volta vazio):
   `python3 -c "import json;d=open('frontend/shoes_data.js').read();S=json.loads(d[d.find('[') :].rstrip().rstrip(';'));from collections import Counter;print(Counter(t for s in S for t in (s.get('tags') or [])))"`
   (troque `tags` por `levels`/`pisada`/`terreno` conforme o eixo do tema).
2. Adicione o seletor (se novo) perto dos outros `sel_*` e o dict em `THEMES`.
3. **Teste local** e confira o `.mp4` gerado (ver "Rodar" abaixo). Um bom tema tem ≥4 tênis; se
   voltar <4, o motor aborta com fallback pra "sonhos" — sinal de que o filtro está apertado demais.

## Tarefa B — variar roteiro/formato

O roteiro está em `build_video()`. **Antes de editar código, prefira as variáveis de ambiente** —
o motor já é parametrizável e o vídeo padrão do rodízio continua idêntico:

| Variável | Default | Efeito |
|---|---|---|
| `TOP_N` | 6 | Nº de tênis (3 a 6). `TOP_N=3` vira um "Top 3". |
| `DUR_TENIS` | 1.7 | Segundos por card de tênis. Menor = mais ágil; maior = mais legível. |
| `DUR_GANCHO` | 2.4 | Segundos do frame de gancho. |
| `DUR_CTA` | 2.9 | Segundos do frame de CTA. |

Ex. "Top 3 acelerado" (~10s em vez de ~17s):
`TEMA_VIDEO=diadia TOP_N=3 DUR_TENIS=1.4 DUR_GANCHO=2.2 DUR_CTA=2.6 python3 gerar_video_tiktok.py`
O motor sempre escreve `video_tiktok.mp4`; salve a variação com nome próprio depois: `cp video_tiktok.mp4 video_tiktok_top3.mp4`.

Só edite o código de `build_video()` quando a variação **não** couber nessas variáveis (mantenha o motor genérico — não hard-code um post):

- **Gancho diferente**: `hook_frame()` monta o slide de abertura a partir de `small/big1/big2/sub`.
  Mudança grande de layout → edite o HTML dessa função.
- **CTA diferente**: `cta_frame()` ("FAÇA O QUIZ / LINK NA BIO"). Troque o texto aqui pra outra chamada.
- **Card do tênis**: `shoe_frame()` (número, label, foto recortada, marca, modelo, preço).
- **Legenda**: montada no fim de `build_video()` (hook + lista `1️⃣ marca modelo` + CTA + hashtags).

Regras de estilo pra manter consistência com o feed: CAIXA ALTA nos títulos, verde-lima só no
realce, sem itálico, emojis com moderação, e o vídeo **sai mudo de propósito**.

## Rodar / conferir

```bash
# gera pra um tema específico e escreve video_tiktok.mp4 na raiz
TEMA_VIDEO=<key> python3 gerar_video_tiktok.py
```

Dependências locais: `pip install Pillow imageio-ffmpeg rembg onnxruntime` + Chrome instalado
(o motor acha o Chrome do macOS automaticamente). Sem `BREVO_API_KEY`/`EMAIL_CUPONS` no ambiente,
ele **gera o vídeo e pula o e-mail** — perfeito pra revisar localmente. Abra `video_tiktok.mp4`
(e, se precisar ver frame a frame, os PNGs ficam no tempdir que ele imprime).

## Publicar de verdade (rodízio diário)

O envio automático por e-mail roda no GitHub Actions (`.github/workflows/video-tiktok-diario.yml`,
Seg/Qua/Sex 10h BRT). Um tema novo adicionado ao `THEMES` **entra no rodízio automaticamente** ao
commitar. Pra disparar um tema sob demanda, use o `workflow_dispatch` (campo "tema") na aba Actions.
Commit/push só quando a Cristiana pedir; mensagens de commit em pt-BR.
