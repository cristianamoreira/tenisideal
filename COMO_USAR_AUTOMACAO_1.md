# 📖 Como Usar — Automação nº 1: Potencial de Receita

## O que esta automação faz

Cruza os dados de **tráfego orgânico** do seu site com os **cliques nos links afiliados** e gera um relatório visual mostrando quais páginas têm alto tráfego mas baixa conversão — ou seja, onde você está "deixando dinheiro na mesa".

---

## Passo 0 — Configure o Google Search Console (faça uma vez)

Se ainda não tem o Search Console configurado:

1. Acesse: https://search.google.com/search-console
2. Clique em **"Adicionar propriedade"**
3. Digite: `tenisideal.com.br`
4. Escolha a verificação por **"Prefixo de URL"**
5. Faça o download do arquivo HTML de verificação e coloque na raiz do seu site
6. Aguarde 24–72h para os dados aparecerem

---

## Passo 1 — Exporte os CSVs das suas fontes

### 📊 Google Search Console (OBRIGATÓRIO)
1. Acesse: https://search.google.com/search-console
2. Clique em **"Resultados da pesquisa"** (menu lateral)
3. Clique na aba **"Páginas"**
4. No canto superior direito, clique em **"Exportar" > "Baixar CSV"**
5. Salve como: `search_console.csv`

### 🛒 Amazon Associates BR (se usar)
1. Acesse: https://associados.amazon.com.br
2. Menu: **Relatórios > Relatório de Ganhos**
3. Selecione o período (últimos 30 dias)
4. Clique em **"Exportar"**
5. Salve como: `amazon.csv`

### 🔗 Awin (se usar)
1. Acesse: https://ui.awin.com
2. Menu: **Reports > Publisher > Transaction Report**
3. Selecione o período e clique em **"Download CSV"**
4. Salve como: `awin.csv`

### 👟 Netshoes/Lomadee (se usar)
1. Acesse o painel da Lomadee ou Netshoes Afiliados
2. Exporte o relatório de cliques e comissões
3. Salve como: `netshoes.csv`

---

## Passo 2 — Coloque os arquivos na pasta correta

Mova todos os CSVs exportados para a pasta:
```
📁 tenisideal/
  📁 dados_analise/
    ├── search_console.csv   ← obrigatório
    ├── amazon.csv           ← opcional
    ├── awin.csv             ← opcional
    └── netshoes.csv         ← opcional
```

---

## Passo 3 — Execute o script

Abra o **Terminal** e navegue até a pasta do projeto:
```bash
cd "/Users/cristianamoreira/Desktop/Mesa - MacBook Air de Cristiana (2)/tenisideal"
```

Execute:
```bash
python3 analise_receita.py
```

---

## Passo 4 — Abra o relatório

O script vai gerar dois arquivos:
- **`relatorio_oportunidades.html`** → Abra no navegador (Safari, Chrome)
- **`relatorio_oportunidades.csv`** → Abra no Excel se quiser filtrar

---

## ⚡ Modo de Teste (sem CSVs)

Se rodar o script **sem nenhum CSV na pasta**, ele gera automaticamente um relatório com **dados de exemplo** baseados nas páginas reais do seu site. Assim você já consegue ver como o relatório ficará.

---

## 🔴 Interpretando as Prioridades

| Cor | Significado | O que fazer |
|-----|-------------|-------------|
| 🔴 ALTA | Alto tráfego + baixa conversão | Otimize AGORA |
| 🟡 MÉDIA | Potencial moderado | Planeje uma otimização |
| 🟢 BAIXA | Já está convertendo bem | Mantenha e escale |

---

## ❓ Dúvidas?

Volte ao Antigravity e pergunte — estou aqui para ajudar!
