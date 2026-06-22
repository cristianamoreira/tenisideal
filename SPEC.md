# No Rats — Especificação MVP

## 1. Personas

### Persona 1: Marina, 28 anos — Trabalha remoto, mora sozinha

**Contexto:** Desenvolvedora freelancer, trabalha de casa, tem rotina flexível mas desorganizada. Apartamento pequeno fica bagunçado rapidinho entre prazos de projeto.

**Dor:** Culpa por deixar cômodos sujos, demora pra achar motivação pra limpar, sem gamificação fica monótono.

**Objetivo:** Manter casa limpa com pequenas ações diárias, sem virar rotina pesada. Quer ver progresso visual.

**Comportamento no app:**
- Abre 1-2x ao dia, durante pausas de trabalho
- Faz tarefas rápidas (15-30 min)
- Responde bem a feedback visual (XP, notificações)
- Quer competir consigo mesma (streak, níveis)

---

### Persona 2: João, 35 anos — Casal, jornada 9-17h

**Contexto:** Executivo com rotina fixa. Mora com parceiro, ambos trabalham o dia todo. Casa precisa de atenção mas ninguém "tem tempo".

**Dor:** Responsabilidade vaga sobre quem limpa o quê. Tarefas se acumulam. Fim de semana viça limpeza.

**Objetivo:** Distribuir pequenas tarefas na semana, criar rotina automática, não deixar acumular.

**Comportamento no app:**
- Abre à noite (planejamento) ou no fim de semana
- Prefere tarefas claras, com frequência predefinida
- Valida streak (não deixar falhar) mais que nível
- Foco em organização, menos em gamificação pura

---

### Persona 3: Ana, 42 anos — Trabalha presencialmente, casa grande

**Contexto:** Psicóloga, consultório próprio, casa com 5-6 cômodos. Renda média-alta. Quer casa organizada mas não tem time.

**Dor:** Cômodos "esquecidos" (escritório, lavanderia) ficam negligenciados. Stress com controle.

**Objetivo:** Não esquecer nenhum cômodo, manter infestação baixa, visualizar tudo num dashboard.

**Comportamento no app:**
- Abre 1x ao dia pela manhã (visão geral)
- Tira 15-20 min à noite pra 2-3 tarefas
- Usa dashboard como checklist visual
- Importa streak e infestação por cômodo (prioriza piores)

---

## 2. Jornada do Usuário — Happy Path

```
[Instalação] → [Onboarding Setup] → [Primeira Tarefa] 
  ↓
[Primeira Infestação Sobe] → [Primeira Conclusão] 
  ↓
[XP e Nível 1→2] → [Streak=1] → [Rotina Estabelecida]
```

### Step-by-step detalhado:

**Step 1: Instalação + Onboarding (Tela 1-3)**
- Usuário abre app → Login simples (e-mail + senha, ou social)
- Tela "Bem-vindo ao No Rats!" — explica conceito em 1 frase + GIF de rato
- Seleciona cômodos da casa (checkboxes: cozinha, banheiro, quarto, sala, lavanderia, escritório)
- Cria perfil básico (nome, foto opcional)
- **Estado**: Usuário criado, 0 XP, Nível 1, Streak 0, Infestação 0 em todos os cômodos

---

**Step 2: Primeira Tarefa (Tela "Adicionar Tarefa")**
- Clica "+" → Modal "Nova Tarefa"
- Preenche:
  - **Nome**: "Lavar louça" (obrigatório)
  - **Cômodo**: "Cozinha" (dropdown, obrigatório)
  - **Dificuldade**: "Simples" (radio, padrão; opções: Simples, Média, Difícil, Pesada)
  - **Frequência**: "Diária" (default; opções: Diária, Semanal, Quinzenal, Mensal)
  - **Prazo**: Baseado em frequência (Diária = hoje até 23:59)
  - **Categoria**: Auto-preenchida por cômodo (ex: "Cozinha" → opções: Louça, Geladeira, etc.)
- Clica "Criar"
- **Estado**: Tarefa criada no backlog

---

**Step 3: Primeira Infestação (Sistema Automático — Background Job)**
- Sistema roda job a cada 6 horas ou quando usuário entra (regra: "tarefas vencidas")
- Lógica:
  - Tarefa "Lavar louça" foi criada com prazo hoje
  - Usuário **não faz nada** por 25 horas → prazo vence
  - **Trigger**: Sistema detecta "Lavar louça" vencida → tarefa muda status para "Vencida"
  - **Infestação sobe**: `Infestação_Cozinha += 15` (fórmula abaixo)
  - Ratos aparecem no cômodo (animação/visual)
- **Notificação**: "Cozinha ficou bagunçada! +15 infestação"
- **Estado**: Infestação_Cozinha = 15, Infestação_Total = 15, Tarefa.status = "Vencida"

---

**Step 4: Primeira Conclusão (Tela Dashboard)**
- Usuário entra no app → vê "Cozinha: 15 ratos" no dashboard
- Clica na tarefa "Lavar louça" (ainda visível com badge "Vencida")
- Clica "Completar" → modal de confirmação
- Clica "Sim, completei!"
- **Sistema executa**:
  - `Tarefa.status = "Concluída"`
  - `Tarefa.completed_at = now()`
  - `XP_earned = 10` (simples)
  - `User.total_xp += 10`
  - `User.level_xp += 10` (progressão dentro do nível)
  - `Infestação_Cozinha -= 15` (remove infestação causada)
  - `User.streak += 1` (agora = 1)
  - Se nível atualizar → toast "Parabéns! Nível 1 → 2"
- **Animação**: Ratos desaparecem, XP float up, visual de sucesso
- **Estado**: Infestação_Cozinha = 0, User.total_xp = 10, User.level = 2, Streak = 1

---

**Step 5: Rotina Estabelecida (Semana 1)**
- Usuário continua criando tarefas (ex: "Varrer sala" semanal, "Limpar banheiro" semanal)
- Completa tarefas antes de vencer → streak mantém
- Deixa uma tarefa vencer → streak quebra (volta a 0)
- A cada nível, notificação e visual update
- Dashboard mostra: Total XP, Nível, Streak, Infestação por cômodo

---

## 3. Regras de Negócio Detalhadas

### 3.1 Infestação por Cômodo

**Fórmula de Aumento (quando tarefa vence):**

```
ΔInfestação = dificuldade_multiplicador × frequência_multiplicador × tempo_vencimento_multiplicador

Onde:
  dificuldade_multiplicador = {
    "Simples": 2,
    "Média": 4,
    "Difícil": 8,
    "Pesada": 15
  }
  
  frequência_multiplicador = {
    "Diária": 1.5,      // aumenta rápido se daily falha
    "Semanal": 1.0,
    "Quinzenal": 0.8,
    "Mensal": 0.5
  }
  
  tempo_vencimento_multiplicador = {
    "até 24h vencida": 1.0,
    "1-3 dias vencida": 1.3,
    "3-7 dias vencida": 1.6,
    "7+ dias vencida": 2.0   (cap em 100 por aplicação)
  }
```

**Exemplos:**
- Tarefa: "Lavar louça" (Simples, Diária, 24h vencida)
  - ΔInfestação = 2 × 1.5 × 1.0 = **3 pontos**
  
- Tarefa: "Limpar banheiro" (Difícil, Semanal, 5 dias vencida)
  - ΔInfestação = 8 × 1.0 × 1.6 = **12.8 ≈ 13 pontos**

- Tarefa: "Polir pisos" (Pesada, Mensal, 14 dias vencida)
  - ΔInfestação = 15 × 0.5 × 2.0 = **15 pontos** (sempre que vence nova tarefa, cumulativo)

**Infestação é acumulada:** Se múltiplas tarefas do mesmo cômodo vencerem, somas aditivas.

**Cap:** Infestação por cômodo máx = 100 (visual: cômodo "infestado", ícone crítico)

---

### 3.2 Redução de Infestação (quando tarefa é concluída)

**Regra simples:**
```
ΔInfestação_reduzida = ΔInfestação_que_causou (revertido com sinal negativo)
```

**Contextos:**
- Se tarefa **foi concluída no prazo**: remove 100% da infestação que teria causado (por vencimento)
- Se tarefa **foi concluída após vencer**: remove 100% da infestação já acumulada
- Se tarefa **foi concluída e há outras vencidas do mesmo cômodo**: não remove a delas

**Exemplo:**
1. Criado "Lavar louça" (Simples, Diária, causaria +3 se vencesse)
2. Usuário completa antes de vencer → infestação do cômodo fica 0 (nada adicionado)
3. Vs: Usuário deixa vencer (+3), depois completa → volta a 0 (remove os 3)

---

### 3.3 Infestação Total

```
Infestação_Total = MÉDIA( [Infestação_Cozinha, Infestação_Banheiro, ...] )

Exemplo:
  Cozinha: 20
  Banheiro: 15
  Quarto: 5
  Sala: 0
  Lavanderia: 10
  Escritório: 25
  
  Infestação_Total = (20+15+5+0+10+25) / 6 = 75/6 = 12.5 ≈ 13%
```

**Lógica:** Reflete "estado geral da casa". Um cômodo muito sujo não sufoca a média se outros estão limpos.

**Visual no Dashboard:**
- Barra global 0-100 com cores:
  - Verde (0-30): "Limpa"
  - Amarelo (31-60): "Atenção"
  - Vermelho (61-100): "Infestação crítica"

---

### 3.4 Streak (Dias Consecutivos)

**Regra de Incremento:**
```
Streak incrementa em +1 quando:
  - Usuário completa ≥1 tarefa num dia
  - AND nenhuma tarefa venceu naquele dia
  
Streak reseta para 0 quando:
  - Qualquer tarefa vence (mesmo que depois seja completada)
  - Nunca incrementa retroativamente
```

**Exemplos:**
- Seg: Completa "Lavar louça" antes de vencer → Streak = 1 ✓
- Ter: Deixa "Varrer sala" vencer, depois completa → Streak = 0 ✗ (mesmo que tenha completado depois)
- Qua-Sex: Completa 1+ tarefas por dia, nenhuma vence → Streak = 5 ✓
- Sab: Não faz nada, nenhuma tarefa vencia naquele dia → Streak mantém ✓
- Dom: 1 tarefa vence às 14:00, ele completa às 15:00 → Streak = 0 ✗

**Visual:** Número com ícone de chama 🔥, embaixo do nome de usuário no dashboard.

---

### 3.5 Progressão de XP e Níveis

**Tabela de Níveis (10-12 total):**

| Nível | Nome | XP Necessário Acumulado | XP Para Next | Descrição |
|-------|------|------------------------|----|-----------|
| 1 | Novato | 0 | 100 | Começando a jornada |
| 2 | Aprendiz | 100 | 200 | Pegou o jeito |
| 3 | Organizado | 300 | 300 | Rotina em progresso |
| 4 | Disciplinado | 600 | 400 | Compromissado |
| 5 | Meticuloso | 1000 | 500 | Atenção aos detalhes |
| 6 | Guardião da Limpeza | 1500 | 600 | Responsável pelos cômodos |
| 7 | Mestre do Lar | 2100 | 700 | Domina a casa |
| 8 | Eliminador de Ratos | 2800 | 800 | Ratos já conhecem seu nome |
| 9 | Lenda Doméstica | 3600 | 900 | Praticamente perfeito |
| 10 | Zen Cleaner | 4500 | 1000 | O equilíbrio supremo |
| 11 | Rei/Rainha da Limpeza | 5500 | 1200 | Ícone de excelência |
| 12 | Guardião Absoluto | 6700 | — | Status final (sem progressão) |

**Cálculo de XP por Tarefa:**

```
XP_tarefa = {
  "Simples": 10,
  "Média": 25,
  "Difícil": 50,
  "Pesada": 100
}

XP_final = XP_tarefa (sem bônus de streak no MVP)
```

**Progressão dentro de um nível:**
- Barra visual 0-100% que preenche conforme acumula XP para o próximo nível
- Exemplo: Nível 2 precisa de 200 XP total; usuário tem 150 XP → barra em 75%

---

### 3.6 Frequências de Tarefa

```
Frequência | Próximo Prazo Após Conclusão | Recorrer?
-----------|------------------------------|----------
Diária     | Dia seguinte 00:00           | Sim (sempre reaparece)
Semanal    | 7 dias depois                | Sim
Quinzenal  | 14 dias depois               | Sim
Mensal     | 30 dias depois               | Sim
```

**Lógica de recorrência:**
- Tarefa é concluída → status = "Concluída"
- Se frequência != "Uma vez", sistema cria nova instância da mesma tarefa (mesmo ID, nova ocorrência)
- Nova instância tem prazo calculado a partir da conclusão (ex: completou terça, próxima vence terça+7)

---

## 4. Casos de Uso Principais

### UC-1: Configurar Cômodos da Casa

**Atores:** Usuário novo

**Fluxo:**
1. Usuário entra no app pela primeira vez
2. Tela "Qual é sua casa?" com checkboxes: Cozinha, Banheiro, Quarto, Sala, Lavanderia, Escritório
3. Seleciona ≥1 (obrigatório)
4. Clica "Confirmar"
5. **Sistema:**
   - Salva lista de cômodos no perfil do usuário
   - Inicializa Infestação = 0 para cada um
   - Redireciona para dashboard
6. **Pós-condição:** Dashboard mostra apenas cômodos selecionados

---

### UC-2: Criar Tarefa

**Atores:** Usuário autenticado

**Fluxo:**
1. Usuário clica "+" ou "Nova Tarefa"
2. Modal/Form "Adicionar Tarefa" com campos:
   - **Nome** (input text, obrigatório, max 100 chars)
   - **Cômodo** (dropdown, obrigatório, mostra apenas cômodos configurados)
   - **Dificuldade** (radio: Simples/Média/Difícil/Pesada, default Simples)
   - **Frequência** (dropdown: Diária/Semanal/Quinzenal/Mensal, default Semanal)
   - **Categoria** (dropdown auto-preenchida por cômodo, opcional no MVP)
   - **Descrição** (textarea, opcional, max 500 chars)
3. Clica "Criar"
4. **Sistema:**
   - Valida campos obrigatórios
   - Calcula prazo baseado em frequência
   - Cria Task no DB com status = "Pendente"
   - Retorna para dashboard
5. **Pós-condição:** Tarefa aparece na lista "Pendentes" do cômodo

---

### UC-3: Completar Tarefa

**Atores:** Usuário autenticado

**Fluxo:**
1. Usuário vê lista de tarefas pendentes no dashboard ou por cômodo
2. Clica em tarefa → abre detalhe (ou card que expande)
3. Clica botão "Completar" ou "✓ Feito"
4. Modal de confirmação: "Tem certeza que completou 'Lavar louça'?"
5. Clica "Sim, completei!"
6. **Sistema:**
   - Valida: tarefa existe, status = "Pendente" ou "Vencida"
   - Atualiza: `Task.status = "Concluída"`, `Task.completed_at = now()`
   - Calcula XP: `xp_earned = dificuldade_map[tarefa.dificuldade]`
   - Atualiza usuário:
     - `User.total_xp += xp_earned`
     - `User.level_xp += xp_earned` (progressão dentro do nível)
     - Checa se nível subiu → se sim, `User.level += 1`, reset `level_xp = 0`, notificação
     - Incrementa streak se nenhuma tarefa estava vencida
   - Reduz infestação do cômodo (remove a que foi acumulada)
   - Se recorrente, cria nova instância com novo prazo
7. **Pós-condição:** 
   - Tarefa sai de "Pendentes", vai para "Concluídas" (histórico)
   - Dashboard atualiza: XP, nível, streak, infestação
   - Animação visual: XP flota, ratos desaparecem, confete opcional

---

### UC-4: Tarefa Vence Automaticamente

**Atores:** Sistema (background job)

**Trigger:** Job roda a cada 6 horas (ou quando usuário abre app)

**Fluxo:**
1. Sistema identifica tarefas onde `Task.due_date < now()` AND `Task.status = "Pendente"`
2. Para cada tarefa vencida:
   - Atualiza: `Task.status = "Vencida"`
   - Calcula infestação: `ΔInf = dificuldade × freq × tempo_vencido`
   - Atualiza: `Room.infestation += ΔInf` (capped 100)
   - Notifica usuário: "⚠️ [Cômodo]: Tarefa vencida! +X infestação"
3. Recalcula `User.total_infestation = média(all_rooms)`
4. **Pós-condição:** Dashboard reflete novas infestações, streak pode estar em risco se usuário não agir

**Nota:** Se usuário depois completa tarefa vencida, streak já foi quebrado; infestação é removida retroativamente.

---

### UC-5: Visualizar Dashboard

**Atores:** Usuário autenticado

**Fluxo:**
1. Usuário abre app ou clica "Dashboard"
2. **Tela mostra:**
   - **Topo:** Nome do usuário, avatar
   - **Stats Globais:** 
     - 🔥 Streak: N dias
     - ⭐ XP: XXXX
     - 📊 Nível: N (com barra de progressão)
   - **Infestação Global:** Barra 0-100 com cores
   - **Por Cômodo:** Cards mostrando:
     - Nome do cômodo
     - Infestação local (0-100, visual com ratos)
     - Tarefas pendentes (contador)
     - Botão "Ver tarefas"
   - **Tarefas Rápidas:** 3-5 tarefas mais próximas de vencer
3. Clica em cômodo → expande lista de tarefas daquele cômodo
4. **Pós-condição:** Interface visual atualiza em tempo real (WebSocket no futuro)

---

## 5. Entidades e Relacionamentos

```
User
├─ id (UUID)
├─ email (unique)
├─ password (hashed)
├─ name
├─ avatar_url
├─ created_at
├─ total_xp (int, default 0)
├─ level (int, 1-12, default 1)
├─ level_xp (int, 0-100 dentro do nível)
├─ streak (int, default 0)
├─ total_infestation (float, 0-100, calculated)
└─ updated_at

Room
├─ id (UUID)
├─ user_id (FK → User)
├─ name (Cozinha, Banheiro, etc)
├─ infestation (float, 0-100, default 0)
├─ created_at
└─ updated_at

Task
├─ id (UUID)
├─ user_id (FK → User)
├─ room_id (FK → Room)
├─ title (string)
├─ description (optional, string)
├─ category (optional, string)
├─ difficulty (Simples/Média/Difícil/Pesada)
├─ frequency (Diária/Semanal/Quinzenal/Mensal)
├─ due_date (datetime)
├─ completed_at (optional, datetime)
├─ status (Pendente/Concluída/Vencida)
├─ xp_value (int, computed from difficulty)
├─ recurring (bool, default true)
├─ parent_task_id (optional, FK → Task, para recorrências)
├─ created_at
└─ updated_at

TaskHistory (para auditoria)
├─ id (UUID)
├─ task_id (FK → Task)
├─ user_id (FK → User)
├─ action (Criada/Concluída/Vencida)
├─ xp_earned (int, se concluída)
├─ infestation_delta (float, se vencida)
├─ created_at
```

---

## 6. Estados de Tarefa

```
Pendente → [Data de vencimento atinge] → Vencida
       ↓
    Concluída
       ↓
  (Se recorrente: cria nova Task com status Pendente)
```

**Status não é linear:** Uma tarefa pode ir de Pendente → Vencida → Concluída (vencida mas completada depois).

---

## 7. Mockups Mentais

### Dashboard (Vista Principal)
```
┌─────────────────────────────────┐
│ No Rats                      👤 │
├─────────────────────────────────┤
│ 🔥 Streak: 12 | ⭐ XP: 3400     │
│ Nível 7: Mestre do Lar          │
│ ████████░░ 80% para próx nível  │
├─────────────────────────────────┤
│ Infestação Total: 23% 🟢        │
│ ███░░░░░░░░░░░░░░░░░           │
├─────────────────────────────────┤
│ 🍳 Cozinha: 15% (2 pendentes)   │
│ 🚿 Banheiro: 30% (1 pendente)   │
│ 🛏️  Quarto: 5% (0 pendentes)    │
│ 🛋️  Sala: 40% (3 pendentes)     │
│ 🧺 Lavanderia: 50% (2 vencidas) │
│ 🖥️  Escritório: 10% (1 pendente)│
├─────────────────────────────────┤
│ [+ Nova Tarefa]                 │
└─────────────────────────────────┘
```

### Nova Tarefa Modal
```
┌──────────────────────────────┐
│ Nova Tarefa                  │
├──────────────────────────────┤
│ Nome: [Lavar louça_______]   │
│ Cômodo: [Cozinha ▼]          │
│ Dificuldade:                 │
│  ◉ Simples   ○ Média         │
│  ○ Difícil   ○ Pesada        │
│ Frequência: [Diária ▼]       │
│ Categoria: [Louça ▼]         │
│ Descrição: [opcional_____]   │
│                              │
│        [Criar]  [Cancelar]   │
└──────────────────────────────┘
```

---

## 8. Notas de Implementação

- **JWT + Refresh Tokens** para auth no backend
- **Background job** (Celery no Django recomendado) para check de vencimento
- **Cache** de usuário no frontend (Redux/Context)
- **Notificações** via toast (primária no MVP), push (futura)
- **Testes:** Unit (lógica de infestação/XP) + Integration (flow completo)
- **Analytics:** Rastrear criação/conclusão de tarefas, churn (usuários que param)

---

**Versão:** 1.0  
**Última atualização:** 2026-06-19  
**Status:** Pronto para Development
