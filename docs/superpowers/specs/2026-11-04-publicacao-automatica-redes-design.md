# Design — Publicação automática nas redes sociais (Instagram + TikTok)

**Data:** 2026-11-04
**Status:** aprovado pela Cristiana (brainstorming em sessão)

## Problema

O workflow `conteudo-do-dia.yml` gera conteúdo diário (carrossel/arte/vídeo) há meses e envia por e-mail, mas as postagens manuais não acontecem. Resultado: tráfego ~zero no site (funil GA4: 0 cliques COMPRAR em 90 dias). O gargalo é o passo manual entre o e-mail e o feed.

## Objetivo

Publicar o conteúdo diário automaticamente no Instagram (@tenisideal_br) e TikTok, com qualidade de texto garantida (zero erros de português) **antes** de ligar o piloto automático.

## Decisões tomadas

| Decisão | Escolha |
|---|---|
| Plataformas | Instagram + TikTok |
| Aprovação | 100% automático (sem gate manual por post) |
| Abordagem | APIs oficiais direto do GitHub Actions (custo R$ 0) |
| Qualidade | Revisor automático (artes/vídeos) + banco pré-aprovado (carrosséis) |
| Domingos | Novo post leve motivacional ("dia de longão") → 7 posts/semana |
| Conta Instagram | Tipo atual desconhecido — verificar/converter para Profissional + Página FB no setup |

## Arquitetura

```
FASE 1 — QUALIDADE
├─ 1A. revisor_copy.py          (revisão automática de texto, artes e vídeos)
└─ 1B. banco_posts/             (carrosséis pré-aprovados pela Cristiana)
    + modo "domingo motivacional" no gerar_arte_instagram.py

FASE 2 — PUBLICAÇÃO
└─ publicar_redes.py no final do conteudo-do-dia.yml
   ├─ mídia commitada em posts/ → URL pública via tenisideal.com.br
   ├─ Instagram Graph API  → feed/carrossel/Reel publicados na hora
   ├─ TikTok Content API   → vídeo como rascunho no app (até auditoria)
   └─ e-mail diário continua como registro/confirmação
```

## Fase 1A — Revisor automático de copy

Novo módulo `revisor_copy.py` na raiz, importado por `gerar_arte_instagram.py`, `gerar_video_tiktok.py` e `gerar_carrossel_foto.py` (fallback).

**Fluxo:** Gemini gera a copy (como hoje) → `revisar_copy(texto, contexto)` faz uma 2ª chamada de IA com papel de REVISOR (corrige, não reescreve o estilo) → validação dura por código.

**Checklist do revisor (prompt):**
1. Gramática e ortografia pt-BR (concordância, crase, acentos)
2. Sem travessão (—), sem itálico
3. Máximo 2 emojis por campo
4. Não inventar preço/desconto que não veio dos dados
5. CTA sempre presente ("link na bio")
6. Manchetes: caixa consistente, UMA palavra de destaque

**Validação por código (garantia dura, não-IA):**
- Regex remove travessões e emojis excedentes
- Preço citado deve bater com o catálogo
- Legenda ≤ 2.200 caracteres (limite do Instagram)

**Regras de robustez:**
- Revisor falhou (API fora) → publica a versão original; o revisor melhora, nunca bloqueia
- Toda alteração do revisor aparece no log do Actions ("antes → depois")

## Fase 1B — Banco de carrosséis pré-aprovados

**Estrutura:**
```
banco_posts/
├── fila.json          # ordem de publicação + status (aprovado/publicado)
├── 2026-11-c01/
│   ├── slide-01.png ... slide-06.png
│   └── post.json      # legenda, hashtags, tema, estilo usado
└── ...
```

**Abastecimento (sessão Claude local):**
1. Gerar ~8 carrosséis/lote (≈1 mês de Seg+Sáb) com as skills `carrossel-teniscerto` (foto) e `carrossel-estilos` (texto), temas do catálogo real
2. Cristiana revisa um a um: aprova, ajusta ou descarta
3. Só aprovados entram na `fila.json`; tudo commitado no repo

**Consumo (automação, Seg/Sáb):**
1. Workflow lê `fila.json`, pega o próximo `aprovado`
2. Publica e marca `publicado` (com data) — nunca repete
3. ≤ 2 aprovados restantes → e-mail de alerta "banco acabando"
4. Banco vazio → gera na hora como hoje (com revisor) e avisa no e-mail

O banco no repo também vira histórico permanente do que foi ao ar.

## Domingo motivacional

Novo caso `7) TIPO=domingo` no rodízio do workflow. `gerar_arte_instagram.py` ganha modo "motivacional": frase de corrida tema "dia de longão" (IA + revisor, banco de frases fallback), visual clean, sem venda, CTA suave ("marca aquele amigo do longão").

**Calendário final (7 posts/semana):**
Seg=carrossel(banco) · Ter=arte · Qua=vídeo · Qui=arte · Sex=arte(cupom) · Sáb=carrossel(banco) · Dom=arte motivacional

## Fase 2 — Publicação automática

### Hospedagem da mídia
A Graph API busca mídia de URL pública (não aceita upload direto). Fluxo:
1. Workflow commita a mídia gerada na hora em `posts/AAAA-MM-DD/` (carrosséis do banco já estão públicos em `banco_posts/...`, sem cópia extra — o site publica a raiz do repo)
2. Netlify publica → `https://tenisideal.com.br/posts/.../slide-01.png`
3. Script aguarda o deploy (~1-2 min) e confirma que a URL responde (HTTP 200)
4. Chama a API com essas URLs

### Instagram (Meta Graph API)
- Carrossel: 1 container por slide → container de carrossel → publish com legenda
- Arte: container único → publish
- Vídeo: publicado como **Reel**
- Pré-requisitos (setup guiado): conta Profissional + Página FB vinculada + app na Meta for Developers + token de longa duração (60 dias)
- Workflow mensal renova o token automaticamente

### TikTok (Content Posting API)
- Dias de vídeo (Qua): vídeo enviado via API → **rascunho no app** (Cristiana confirma em 2 toques)
- Submeter o app à auditoria da ByteDance; quando aprovado → publicação direta

### Robustez
- Falha de publicação **não quebra** o workflow: e-mail sai como hoje + aviso "⚠️ publicação automática falhou — poste manualmente"
- Log no Actions: o que publicou, link do post, correções do revisor

### Secrets novos (GitHub)
`META_ACCESS_TOKEN`, `IG_USER_ID`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`

## Ordem de implementação

1. **Fase 1A** — revisor automático (sem risco; melhora o que já sai por e-mail)
2. **Fase 1B** — domingo motivacional + banco de carrosséis (gerar e aprovar o 1º lote)
3. **Fase 2** — setup dos tokens (sessão guiada com a Cristiana) → ligar publicação, primeiro Instagram, depois TikTok

## Fora de escopo (por enquanto)

- Auditoria do app TikTok para publicação direta (submeter, mas não bloquear)
- Stories automáticos (API da Meta suporta; avaliar depois)
- Agendamento de horário nobre (hoje publica ao rodar, ~09:00 BRT; ajustar cron depois se as métricas pedirem)
- Impulsionamento pago (decisão registrada: só com ~300-500 visitas/mês orgânicas)

## Critérios de sucesso

- 7 posts/semana publicados sem intervenção manual (exceto confirmar rascunho TikTok)
- Zero erros de português nos posts publicados
- E-mail diário confirma cada publicação com link
- Métricas GA4 passam a registrar tráfego vindo de social (UTM do link da bio)
