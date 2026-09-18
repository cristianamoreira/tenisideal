# Puxador automático de métricas do GA4

O script `puxar_metricas_ga4.py` busca os eventos do funil direto do Google
Analytics e preenche `painel_semanal_tenisideal.csv` sozinho, reaproveitando a
mesma conta de serviço do Google que já sincroniza a planilha de tênis.

## Setup — 3 passos (uma vez só)

Conta de serviço a autorizar:
`robotenis@fiery-airlock-498900-t5.iam.gserviceaccount.com`
Projeto no Google Cloud: `fiery-airlock-498900-t5`

### 1. Property ID — JÁ DESCOBERTO: `543426890`
(Estava na URL do GA4: `.../a387180396p543426890/...` → o número depois do `p`.)
O `G-W8LTCQBW0X` do site é o "Measurement ID", outra coisa — não é usado aqui.

> ⚠️ ATENÇÃO: em 2026-08-01 o GA4 mostrava "A coleta de dados não está ativa /
> Nenhum dado foi recebido". A tag ESTÁ instalada e publicada no site, então a
> causa provável é tráfego quase zero (ou tag adicionada há pouco). Confirme com
> o teste do relatório **Tempo real** antes de confiar nos números.

### 2. Dar acesso de Leitor à conta de serviço
- GA4 → **Administrador** → coluna **Propriedade** → **Gerenciamento de acesso à propriedade**.
- Botão **+** (canto superior direito) → **Adicionar usuários**.
- Cole o e-mail `robotenis@fiery-airlock-498900-t5.iam.gserviceaccount.com`.
- Função: **Leitor** (Viewer). Desmarque "notificar por e-mail". Adicionar.

### 3. Ativar a API de dados do Analytics
- Abra: https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com?project=fiery-airlock-498900-t5
- Clique em **Ativar** (Enable). Se já estiver ativa, aparece "Gerenciar" — está ok.

## Rodar

```bash
GA4_PROPERTY_ID=543426890 python3 puxar_metricas_ga4.py
# opcional: puxar período maior (padrão 60 dias)
GA4_PROPERTY_ID=543426890 DIAS=90 python3 puxar_metricas_ga4.py
```

Ele preenche o painel semanal e imprime um resumo dos últimos ~28 dias com as
taxas do funil, pra decidir na hora se vale a pena impulsionar.

## Rodar sozinho toda semana (JÁ MONTADO)

O workflow `.github/workflows/metricas-ga4-semanal.yml` roda toda **segunda 08:00 BRT**
(ou pelo botão "Run workflow" na aba Actions do GitHub). Ele puxa os eventos,
atualiza `painel_semanal_tenisideal.csv` e faz commit sozinho.

- Usa o mesmo secret `GOOGLE_CREDENTIALS` que os outros workflows.
- O Property ID `543426890` está embutido. Se um dia mudar, crie a variável de
  repositório `GA4_PROPERTY_ID` (Settings > Secrets and variables > Actions >
  Variables) que ela sobrescreve o padrão.

> O workflow (e o script) só retornam dados DEPOIS que os 2 acessos acima
> (passos 2 e 3) estiverem feitos. Antes disso ele roda mas volta vazio/erro.
