# Como montar o funil CERTO no GA4 (Tênis Ideal)

O funil que apareceu no seu print estava com a etapa "Compra" — evento que o
site NÃO tem. Por isso dava 100% de abandono sem sentido. Vamos montar o funil
real, com os eventos que o seu site dispara.

## As 4 etapas do funil real

1. first_visit        → a pessoa chegou no site
2. quiz_started       → começou o quiz
3. quiz_completed     → viu as recomendações
4. click_afiliado     → clicou em COMPRAR (isso vira comissão)

## Passo a passo

1. GA4 → menu à esquerda → **Explorar** (o ícone de bolinhas/análise).
2. Clique em **Análise detalhada de funil** (Funnel exploration).
   - Se abrir a sua análise "Funil" antiga, pode reaproveitá-la e só trocar as etapas.
3. No painel do meio, em **ETAPAS**, clique no lápis (editar etapas).
4. Apague as etapas atuais (Primeiro acesso, Início de sessão, Compra etc.).
5. Adicione as 4 etapas, uma por uma. Para cada etapa:
   - Clique em **Adicionar etapa**.
   - Dê o nome (ex.: "Começou o quiz").
   - Condição: **Evento** → selecione o nome do evento na lista:
     - Etapa 1: `first_visit`
     - Etapa 2: `quiz_started`
     - Etapa 3: `quiz_completed`
     - Etapa 4: `click_afiliado`
   - Aplicar.
6. Em cima à direita, ajuste o período para **Últimos 28 dias** (ou 7 dias).
7. Clique em **Aplicar**.

## Como ler o resultado

Cada barra mostra quantos passaram e a **taxa de abandono** entre etapas.
Onde a barra despenca é onde você perde gente. Pelo seu dado atual, a queda
maior é logo no começo: chega muita gente do social, mas poucos apertam
"Começar o quiz". É nessa primeira queda que está o dinheiro perdido.

## Dica: detalhar por dispositivo ou canal

No painel esquerdo, arraste **Categoria de dispositivo** (celular/desktop) ou
**Mídia atribuída ao primeiro usuário** para o campo DETALHAMENTO. Assim você vê
se quem vem do celular (a maioria do social) abandona mais que o desktop.

## Salvar

Dê um nome à análise (ex.: "Funil Quiz -> Compra") no topo. Ela fica salva em
Explorar e você reabre quando quiser, sem remontar.
