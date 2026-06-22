# No Rats — KPIs & Metrics (Primeiras 12 Semanas)

## 1. Visão Geral

```
Objetivos:
  ✅ Validar core product (gamificação funciona)
  ✅ Medir engagement (usuários voltam)
  ✅ Entender retenção (D1, D7, D30)
  ✅ Diagnosticar churn (por quê saem?)
  ✅ Guiar iterações (o quê melhorar)

Público: MVP lançado, 50K users target em 8 semanas
```

---

## 2. KPIs Primários (O que realmente importa)

### 2.1 Retenção Cohort (CRÍTICO)

**Métrica:** DAU/MAU, por coorte de signup

```python
Definição:
  D1: % usuarios que voltam 1 dia após signup
  D7: % usuários que voltam 7 dias após signup
  D30: % usuários que voltam 30 dias após signup

Fórmula:
  D1 = (Users retidos no dia 1) / (Users que signed up no dia N) × 100
  D7 = (Users ativos no dia N+7) / (Users que signed up no dia N) × 100
  D30 = (Users ativos no dia N+30) / (Users que signed up no dia N) × 100
```

**Benchmark:**
- Gaming apps: 40% D1, 25% D7, 15% D30
- Productivity apps: 30% D1, 15% D7, 8% D30
- **No Rats target:** 50% D1, 35% D7, 20% D30 (entre os dois)

**Coleta:**
```sql
-- D1 Retention (exemplo)
SELECT 
  DATE(signup_date) as cohort,
  COUNT(DISTINCT user_id) as signed_up,
  COUNT(DISTINCT CASE WHEN last_active_date >= DATE_ADD(signup_date, INTERVAL 1 DAY) 
    THEN user_id END) as d1_users,
  COUNT(DISTINCT CASE WHEN last_active_date >= DATE_ADD(signup_date, INTERVAL 1 DAY) 
    THEN user_id END) * 100.0 / COUNT(DISTINCT user_id) as d1_rate
FROM users
GROUP BY DATE(signup_date)
ORDER BY cohort DESC
```

**Dashboard:**
```
Cohort Analysis — Last 8 Weeks

         D1    D7    D14   D30
Week 1:  52%   36%   25%   18%   ← 8 semanas atrás
Week 2:  50%   34%   24%   17%
Week 3:  48%   32%   22%   15%
Week 4:  55%   38%   27%   20%   ← 4 semanas atrás
Week 5:  54%   36%   26%   19%
Week 6:  51%   33%   23%   —
Week 7:  49%   31%   —
Week 8:  53%   —              ← Hoje
```

**Meta Week 1-4:** D1 ≥ 45%, D7 ≥ 30%, D30 ≥ 15%  
**Meta Week 5-8:** D1 ≥ 50%, D7 ≥ 35%, D30 ≥ 20%  
**Alerta:** D1 < 40% = core loop quebrado, investigar urgente

---

### 2.2 Task Completion Rate (GAMIFICAÇÃO FUNCIONA?)

**Métrica:** % de tarefas completadas vs vencidas

```python
Definição:
  Completion Rate = Tasks Concluídas / (Tasks Criadas - Tasks Deletadas)
  Expiry Rate = Tasks Vencidas / Tasks Criadas
  Balance = Completion Rate vs Expiry Rate

Exemplo:
  Semana 1:
    Tasks criadas: 100K
    Tasks concluídas: 60K (60%)
    Tasks vencidas: 25K (25%)
    Tasks em aberto: 15K (15%)
```

**Benchmark:**
- Todo apps genéricos: 40-50% completion (resto fica)
- Habitica: 65-75% completion (gamificação força)
- **No Rats target:** 60% completion (bom engagement)

**Coleta:**
```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_tasks,
  SUM(CASE WHEN status = 'concluida' THEN 1 ELSE 0 END) as completed,
  SUM(CASE WHEN status = 'vencida' THEN 1 ELSE 0 END) as expired,
  ROUND(SUM(CASE WHEN status = 'concluida' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as completion_rate
FROM tasks
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC
```

**Dashboard:**
```
Completion vs Expiry — Last 7 Days

Date       | Completion | Expiry | In Progress
2026-06-19 |    62%     |  20%  |    18%   ← Hoje (good!)
2026-06-18 |    59%     |  22%  |    19%
2026-06-17 |    58%     |  23%  |    19%
2026-06-16 |    61%     |  19%  |    20%
...
Weekly Avg |    60%     |  21%  |    19%
```

**Meta:** Completion ≥ 55%  
**Alerta:** Completion < 50% = gamificação não tá motivando, investigar

---

### 2.3 Streak Médio (MOTIVAÇÃO)

**Métrica:** Distribuição de streak entre usuários ativos

```python
Definição:
  Avg Streak = Média de dias consecutivos sem deixar tarefa vencer
  Distribuição: % users com streak 0, 1-3, 4-7, 8-14, 15+

Exemplo:
  Semana 1:
    Avg Streak: 2.3 dias
    0 dias: 45% (deixou vencer)
    1-3: 35%
    4-7: 15%
    8+: 5%
```

**Benchmark:**
- Casual apps: Avg 1.2 dias
- Gamified apps: Avg 3-5 dias
- **No Rats target:** Avg 3+ dias (win!)

**Coleta:**
```sql
SELECT
  AVG(streak) as avg_streak,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY streak) as median_streak,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY streak) as p75_streak,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY streak) as p95_streak,
  SUM(CASE WHEN streak = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_zero,
  SUM(CASE WHEN streak BETWEEN 1 AND 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_1_3,
  SUM(CASE WHEN streak BETWEEN 4 AND 7 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_4_7
FROM users
WHERE last_active_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
```

**Dashboard:**
```
Streak Distribution — Last 7 Days

Avg Streak: 2.8 dias   |  [████░░░░░]
Median: 2 dias         |  [███░░░░░░░]
P95: 8 dias            |  [████████░░]

Breakdown:
  0 dias:   42% (quebrou streak)
  1-3 dias: 38% (começando)
  4-7 dias: 14% (consistent)
  8+ dias:  6% (superusers!)
```

**Meta:** Avg Streak ≥ 2.5 dias  
**Alerta:** Avg Streak < 1.5 = streak reset trigger está demais, sugerir ajuste

---

### 2.4 DAU/MAU Ratio (STICKY PRODUCT?)

**Métrica:** Daily Active Users / Monthly Active Users

```python
Definição:
  DAU: Usuários que fizeram ≥1 ação no dia
  MAU: Usuários que fizeram ≥1 ação no mês
  DAU/MAU ratio = DAU / MAU

Benchmark:
  Low engagement: 10-15% (Facebook: ~66%, Netflix: ~50%, Slack: ~60%)
  Productivity: 20-40%
  Gaming: 30-50%
  No Rats target: 25-35% (sticky mas não addictive)

Exemplo:
  Today:
    DAU: 15K
    MAU (last 30 days): 50K
    Ratio: 30% ← Good!
```

**Coleta:**
```sql
SELECT
  DATE(DATE_SUB(NOW(), INTERVAL 1 DAY)) as yesterday,
  (SELECT COUNT(DISTINCT user_id) FROM events 
   WHERE DATE(created_at) = DATE(DATE_SUB(NOW(), INTERVAL 1 DAY))) as dau,
  (SELECT COUNT(DISTINCT user_id) FROM events 
   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as mau,
  ROUND((SELECT COUNT(DISTINCT user_id) FROM events 
   WHERE DATE(created_at) = DATE(DATE_SUB(NOW(), INTERVAL 1 DAY))) * 100.0 /
  (SELECT COUNT(DISTINCT user_id) FROM events 
   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)), 2) as dau_mau_ratio
```

**Dashboard:**
```
DAU/MAU Ratio — Last 8 Weeks

Week 1: 21%  ← Bom (early adopters sticky)
Week 2: 24%  ← Melhora!
Week 3: 22%
Week 4: 26%  ← Target atingido
Week 5: 28%
Week 6: 30%  ← Sustentável
Week 7: 29%
Week 8: 31%  ← Trending up (achievement impact?)
```

**Meta:** DAU/MAU ≥ 20%  
**Alerta:** DAU/MAU < 15% = produto não tá sticky, falta reengajement

---

## 3. KPIs Secundários (Diagnóstico)

### 3.1 Session Frequency & Duration

```python
Session Frequency:
  % users with 0 sessions last week: 30% (churn)
  % users with 1-3 sessions/week: 50% (casual)
  % users with 4+ sessions/week: 20% (power users)

Avg Session Duration:
  Day 1: 12 min (excited, onboarding)
  Day 7: 8 min (routine)
  Day 30: 5-6 min (optimized)
  
Target:
  Keep avg session time stable (doesn't drop below 4 min)
```

**Coleta:**
```sql
SELECT
  user_id,
  COUNT(DISTINCT session_id) as sessions_last_7,
  ROUND(AVG(session_duration_minutes), 2) as avg_duration
FROM sessions
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY user_id
ORDER BY sessions_last_7 DESC
```

---

### 3.2 Feature Adoption (O que funciona?)

```python
Achievements:
  % users with ≥1 achievement: 35% (expected by week 4)
  Avg achievements per user: 1.2

XP Grinding:
  % users past level 3: 20% (engaged)
  Avg level: 1.8 (good — most still climbing)

Streak:
  % users with streak > 0: 55% (good!)
  % who saw streak break: 45% (guardrail working)

Rooms:
  Avg rooms per user: 2.5 (out of 3 free)
  % users with 3 rooms (hitting limit): 25%
```

---

### 3.3 Funnel Analysis (Onde churn?)

```python
Signup → Onboarding → First Task → Completion → D7 Return

Week 1:
  Signups: 10K (100%)
  Complete Onboarding: 9.2K (92%) ← Good
  Create 1st Task: 8.5K (85%) ← Good
  Complete 1st Task: 7.2K (72%) ← Expected drop
  Return D7: 3.5K (50% of day-1) ← Churn point #1
  
Action: If < 85% at any step, investigate UI/UX
```

---

## 4. Alertas Automáticos (Red Flags)

| Métrica | Alerta Verde | Alerta Amarelo | Alerta Vermelho |
|---------|-------------|-----------------|-----------------|
| **D1 Retention** | > 45% | 40-45% | < 40% |
| **D7 Retention** | > 30% | 25-30% | < 25% |
| **D30 Retention** | > 15% | 10-15% | < 10% |
| **Completion Rate** | > 55% | 45-55% | < 45% |
| **Avg Streak** | > 2.5 | 1.5-2.5 | < 1.5 |
| **DAU/MAU** | > 20% | 15-20% | < 15% |
| **Onboarding Drop** | < 10% | 10-15% | > 15% |

**Reação Automática:**
```
IF d1_retention < 40% AND avg_session_duration < 5min:
  → Alerta Slack: "Core loop may be broken"
  → PM review: Gamification feedback loop

IF completion_rate < 45% AND streak_avg < 1.5:
  → Alerta: "Users not motivated to complete"
  → A/B test: Increase XP reward?

IF dau_mau < 15% AND session_duration < 4min:
  → Alerta: "Product not sticky"
  → Test: Push notifications, achievement celebration
```

---

## 5. Segmentação & Cohort Analysis

### 5.1 By Signup Channel

```python
Product Hunt:
  D1: 52%, D7: 38%, D30: 22%
  Quality: High (engaged, gaming-native)
  
Reddit:
  D1: 48%, D7: 32%, D30: 18%
  Quality: Medium (productivity-focused)
  
Organic:
  D1: 45%, D7: 28%, D30: 15%
  Quality: Low (random discovery)
  
Note: PH users are best retention, allocate ad spend there
```

### 5.2 By Number of Rooms Selected

```python
1 room:   D1: 40%, D7: 20%, D30: 8%   ← Low engagement
2 rooms:  D1: 48%, D7: 32%, D30: 18%  ← Medium
3 rooms:  D1: 55%, D7: 40%, D30: 25%  ← High (optimal)

Insight: Users with 3 rooms are 3x more likely to stay
Action: Encourage "full house setup" in onboarding
```

### 5.3 By Task Frequency Preference

```python
Daily only:       D7: 42%, Avg Streak: 4.2   ← Most gamified
Weekly + Daily:   D7: 35%, Avg Streak: 2.8   ← Balanced
Monthly mixed:    D7: 20%, Avg Streak: 1.2   ← Low engagement

Insight: Daily tasks drive engagement (as expected)
Action: Suggest ≥1 daily task in onboarding
```

---

## 6. Weekly Reporting Template

```markdown
# No Rats Metrics — Week of June 19-25, 2026

## 🔴 Red Flags
- D1 Retention: 48% (target 50%) ← Monitor
- Onboarding drop: 12% (target < 10%)

## 🟢 Green Lights
- Completion Rate: 61% (target 55%+) ✅
- Avg Streak: 2.9 days (target 2.5+) ✅
- DAU/MAU: 31% (target 20%+) ✅

## 📊 Headline Numbers
- Total Users: 42K (up from 38K)
- DAU: 13K (up from 11K)
- D7 Retention: 34% (up from 32%)
- Avg Session Duration: 6.8 min

## 🎯 This Week's Focus
1. Investigate onboarding drop (12% → goal 10%)
2. A/B test achievement notification (increase by 10%)
3. Monitor D1 retention trend (48% → goal 50%+)

## 🔧 Hypotheses to Test
- **H1:** Users with 3 rooms stay longer (segment analysis shows +20%)
  → Action: Add "Pro tip: Pick 3 rooms" in onboarding
  
- **H2:** Push notification at 7am increases D1 retention
  → Action: A/B test: 20% get push, 20% get email, 60% control
  
- **H3:** Gamified users (with achievements) have 2x streak
  → Action: Surface achievements more (notification on unlock)

## 📈 Next Week Goals
- D1: 50%+
- D7: 35%+
- Completion: 60%+
- Total users: 45K (organic growth)
```

---

## 7. Monthly Review (Após 4 semanas)

```markdown
# NO RATS MONTHLY REVIEW — June 2026

## P&L Snapshot
- Revenue: $0 (MVP free)
- CAC: $0.50/user (organic + PH)
- LTV: $2/user (5% will convert to Premium later)
- Unit economics: Neutral (growth-mode)

## User Metrics
| Métrica | Week 1 | Week 4 | Target | Status |
|---------|--------|--------|--------|--------|
| Signups | 10K | 12K | 10K+ | ✅ |
| DAU | 5K | 13K | 10K+ | ✅ |
| D1 Retention | 48% | 51% | 50% | ✅ |
| D7 Retention | 32% | 35% | 30% | ✅ |
| D30 Retention | — | 18% | 15% | ✅ |

## Gamification Metrics
| Métrica | Week 1 | Week 4 | Assessment |
|---------|--------|--------|------------|
| Avg Streak | 2.1 | 2.9 | Good (trending up) |
| Completion Rate | 56% | 61% | Excellent |
| Users with 1+ Achievement | 12% | 35% | Great adoption |

## Biggest Wins
1. **D7 retention 35%** (3pp above target) — core loop works!
2. **Completion rate 61%** (6pp above target) — gamification resonates
3. **Organic growth sustaining** — word-of-mouth kicking in

## Biggest Challenges
1. **Onboarding drop 12%** (target < 10%) — fix UI/flow
2. **DAU/MAU trending down** (31% → 28%) — need reengagement
3. **Segmentation shows rural users churn more** — geo/demographic play?

## Actions for July
1. **Reduce onboarding drop:** A/B test simplified flow (target: 10%)
2. **Test push notifications:** 7am daily reminder (target: +5% D7)
3. **Feature test:** Achievements celebration (target: +3% DAU)
4. **Geographic expansion:** Test UK/EU ads (target: 50K users by end of July)

## Go/No-Go Decision
- **GO:** Proceed with V1.0 planning (achievements, photos, levels)
- **Timeline:** 8-week sprint, start July 1
- **Metrics:** Hit 150K users by end of August
```

---

## 8. Instrumentação & Stack

### Backend Tracking

```python
# Django middleware para rastrear events
class AnalyticsMiddleware:
    def process_response(self, request, response):
        if request.user.is_authenticated:
            track_event.delay(
                user_id=request.user.id,
                event_name=request.path,
                metadata={
                    'method': request.method,
                    'response_time': time.time() - request._start_time,
                }
            )
        return response

# Celery task para enviar eventos (async)
@shared_task
def track_event(user_id, event_name, metadata):
    # Enviar para analytics backend (Mixpanel, Segment, etc)
    pass
```

### Analytics Platform

**Opções:**
1. **Mixpanel** — Recomendado (product-centric, cohort analysis)
2. **Amplitude** — Alternativa (mais UX-focused)
3. **PostHog** — Open-source (self-hosted)

**Custo:**
- MVP: Mixpanel free tier (até 100K eventos/mês)
- V1: Mixpanel grow (~$995/mês)

### Frontend Tracking

```typescript
// React component
import { track } from '@/utils/analytics';

export const Dashboard = () => {
  useEffect(() => {
    track('page_view', { page: 'dashboard' });
  }, []);
  
  const completeTask = (taskId) => {
    track('task_completed', { 
      task_id: taskId,
      xp_earned: 50,
      level_before: 1,
      level_after: 1,
    });
  };
};
```

---

## 9. Dashboard Recomendado (Vercel + Mixpanel)

```
┌──────────────────────────────────────────────────────┐
│            NO RATS ANALYTICS DASHBOARD                │
├────────────────────┬────────────────────┬────────────┤
│ Total Users: 42K   │ DAU: 13K (31%)     │ Churn: 8%  │
├────────────────────┼────────────────────┼────────────┤
│  D1: 51% ✅        │ D7: 35% ✅         │ D30: 18%   │
├────────────────────┴────────────────────┴────────────┤
│                                                      │
│  Completion vs Expiry (7 days)                       │
│  [Chart: 61% completed, 20% expired, 19% pending]   │
│                                                      │
│  Avg Streak Distribution                            │
│  [Chart: 0: 42%, 1-3: 38%, 4-7: 14%, 8+: 6%]       │
│                                                      │
│  Cohort Retention                                    │
│  Week 1: 52% D1, 36% D7, 18% D30                    │
│  Week 2: 50% D1, 34% D7, 17% D30                    │
│  ...                                                 │
│  Week 8: 51% D1, — D7 (active)                      │
│                                                      │
│  Alerts                                              │
│  ⚠️  Onboarding drop 12% (target 10%)               │
│  ⚠️  DAU/MAU trending down 31% → 28%                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 10. Checklist de Setup (Semana 1)

```
Backend:
☐ Integrar Mixpanel via API
☐ Track: signup, login, task_created, task_completed, level_up, achievement_unlocked
☐ Track: session_start, session_end, page_view
☐ Setup data retention (90 days min)

Frontend:
☐ Integrar Mixpanel.js SDK
☐ Track user properties (signup_date, rooms_count, etc)
☐ A/B testing framework (Optimizely or homemade)

Database:
☐ Create events table (redundant but useful for debugging)
☐ Setup BigQuery export (cost-effective analytics)
☐ Create views for cohort queries

Alerts:
☐ Setup Slack webhook para red flags
☐ Daily 9am: KPI summary
☐ Weekly 9am Monday: Detailed report

Dashboards:
☐ Mixpanel dashboard (shared with team)
☐ Google Sheets automated (via Zapier)
☐ Metabase local (open-source, self-hosted)
```

---

**Conclusão:** KPIs ✅ Retention (D1/D7/D30), ✅ Completion Rate, ✅ Streak, ✅ DAU/MAU. Tudo rastreado, alerta automático, reporte semanal. Com isso, você saberá exatamente o que tá funcionando e o que precisa de ajuste em tempo real.
