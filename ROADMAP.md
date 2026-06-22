# No Rats — Roadmap MVP → V1.x → V2

## Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          NO RATS ROADMAP                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MVP (DONE)      V1.0 (Q4 2024)    V1.x (Q1 2025)    V2 (H2 2025)      │
│  ───────         ──────────         ──────────       ──────────        │
│  Tarefas         Achievements       Photos Gallery   Família            │
│  Cômodos         Níveis até 50      Gráficos        Marketplace         │
│  XP/Níveis       Fotos B/D          Analytics        Integrações        │
│  Streak                             Push notifications  Ranking         │
│  Dashboard                                                              │
│                                                                          │
│  Phase 1: Foundation  Phase 2: Engagement  Phase 3: Community            │
│  Release: 50K users  Release: 150K users   Release: 500K users          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: MVP (CURRENT — Já Entregue)

### 1.1 Core Features ✅ DONE

| Feature | Status | Notes |
|---------|--------|-------|
| User auth (JWT) | ✅ | Django REST + SimplJWT |
| Rooms setup (6 cômodos) | ✅ | Onboarding, user selects |
| Task CRUD | ✅ | Create, update, delete, list |
| Task completion | ✅ | Marcação + XP award |
| Streak tracking | ✅ | +1 se não vencer, reset se vencer |
| XP/Level progression | ✅ | 1-12 níveis, hardcoded table |
| Infestation model | ✅ | Aumenta ao vencer, diminui ao completar |
| Dashboard | ✅ | XP, nível, streak, infestação, tarefas rápidas |
| Task expiry job | ✅ | Management command mark_expired_tasks |
| Vite + React + TypeScript | ✅ | Frontend scaffold |
| Tailwind + shadcn/ui | ✅ | UI components |
| Auth flow (login/register) | ✅ | Completo |

### 1.2 Métricas de Lançamento
- **Target:** 50K users (first month)
- **Retention D7:** 40% (baseline produtividade)
- **Retention D30:** 20% (conservador)
- **Free-only (sem paywall)**
- **One user per account (sem família)**

### 1.3 Launch Strategy
- Product Hunt (1º tráfego)
- Reddit (r/productivity, r/todoist)
- Email outreach (productivity bloggers)
- Organic (word-of-mouth)

---

## Phase 2: V1.0 — Engagement Loop (Q3-Q4 2024)

### 2.1 Features Planejadas

#### Achievement System
```python
Models: Achievement, UserAchievement
Data-driven: 15-20 achievements iniciais
Extensível: Adicionar nova = 1 INSERT SQL
Examples: 
  - first_task (complete 1)
  - streak_7 (7 dias)
  - level_10 (nível 10)
```

**Why:** Aumenta D30 retention (~25% → 35%)  
**Timeline:** 2 weeks  
**Complexity:** Low (templates + JSON conditions)

#### Levels Expansion (1→50)
```python
Formula: 100 * (level+1)^1.05
Total XP: ~105k para nível 50
Motivation: Progression feels infinite
```

**Why:** Grindy games têm melhor retention  
**Timeline:** 1 week (só fórmula no model)  
**Complexity:** Trivial

#### Photos Before/After
```
Models: TaskPhoto, RoomPhoto
Upload: ImageField → local/S3
UI: Gallery per task/room
Retention impact: +10% D30 (social proof)
```

**Why:** Visualização de progresso = dopamina  
**Timeline:** 2 weeks (upload + gallery UI)  
**Complexity:** Medium (S3 config, file handling)

#### Analytics Dashboard
```
Endpoints:
  /stats/weekly/?weeks=4
  /stats/monthly/?months=12
  /stats/summary/

Visualization: Recharts charts
Data: XP/day, Tasks/day, Infestation avg
```

**Why:** Users want to see their progress  
**Timeline:** 1 week (aggregate queries)  
**Complexity:** Low

### 2.2 Paywall Introduction

```
FREE:
  ✅ 3 cômodos (soft limit)
  ✅ Tudo do MVP

PREMIUM (US$3.99/mês):
  ✅ Todos os cômodos
  ✅ Fotos + gallery
  ✅ Gráficos
  ✅ Dark mode

Conversion target: 5% (5K paid users)
```

### 2.3 Timeline V1.0

| Sprint | Week | Feature | Owner | Status |
|--------|------|---------|-------|--------|
| 1 | 1 | Achievement system | Backend | |
| 1 | 2 | Achievement frontend | Frontend | |
| 2 | 3 | Photos models + upload | Backend | |
| 2 | 4 | Photos gallery + camera UI | Frontend | |
| 3 | 5 | Analytics backend | Backend | |
| 3 | 6 | Charts (Recharts) | Frontend | |
| 4 | 7 | Paywall logic | Backend | |
| 4 | 8 | Payment integration (Stripe) | Backend | |
| 5 | 9 | QA + polish | QA | |
| 5 | 10 | Soft launch (beta) | Ops | |

**Total: 10 weeks (~2.5 months)**

### 2.4 Success Criteria
- Free users: 50K → 150K (3x)
- Premium users: 0 → 7.5K (5% conversion)
- MRR: US$0 → US$30K
- Retention D30: 20% → 35%
- No critical bugs in production

---

## Phase 3: V1.x — Retention Optimization (Q1 2025)

### 3.1 Features

#### Push Notifications
```
Triggers:
  - Daily reminder (morning)
  - Task about to expire
  - Streak is breaking
  - New achievement unlocked
  - Weekly recap (Sat)

Platform: Firebase Cloud Messaging
```

**Why:** Engagement x2 (but risk churn if spammy)  
**Timeline:** 2 weeks  
**Complexity:** Medium

#### Advanced Analytics
```
Cohort analysis: Retention by signup week
Funnel: Free → Premium conversion rate
Segmentation: By #cômodos, #tasks/week
Churn prediction: Users likely to cancel
```

**Why:** Data-driven retention campaigns  
**Timeline:** 2 weeks (backend) + 1 week (dashboard)  
**Complexity:** Medium

#### Gamification Depth (V1.x content)
```
Mini-achievements:
  - "Clean sweep": 5 tasks no mesmo dia
  - "Perfection": 0% infestation 3 dias
  - "Consistency": 15 dias straight

Badges visual
Daily challenges
```

**Why:** Behavioral psychology (variable rewards)  
**Timeline:** 2 weeks  
**Complexity:** Low

#### Notifications (In-app + Email)
```
In-app toasts: Achievement unlocks
Email digest: Weekly recap
Segmented: Premium-only features
Customizable: User can adjust frequency
```

**Why:** Keep users engaged between sessions  
**Timeline:** 2 weeks  
**Complexity:** Low

#### Mobile Optimization (Progressive Web App)
```
PWA: Installable no home screen
Offline: Cache tarefas, sync quando online
Native feel: No browser chrome
Platform: Already Vite + React
```

**Why:** Mobile is 60%+ of traffic  
**Timeline:** 2 weeks  
**Complexity:** Low

### 3.2 Timeline V1.x

| Month | Weeks | Features | Expected Users | Expected MRR |
|-------|-------|----------|-----------------|--------------|
| Jan | 1-4 | Push + Email | 200K | US$50K |
| Feb | 5-8 | Analytics + Cohorts | 250K | US$70K |
| Mar | 9-12 | Gamification depth | 300K | US$100K |

### 3.3 Success Criteria
- Users: 150K → 350K
- Premium: 7.5K → 20K
- MRR: US$30K → US$80K
- Retention D30: 35% → 50%
- Churn rate: 25% → 15%

---

## Phase 4: V2 — Community & Expansion (H2 2025)

### 4.1 Pillar 1: Família (Shared Lists)

```
Features:
  ✅ Multi-user per account (up to 5)
  ✅ Role-based: Admin, supervisor, worker
  ✅ Task assignment: "João, trash"
  ✅ Ranking: XP leaderboard
  ✅ Rewards: Unlock pizza night at 500 XP
  ✅ Notifications: "Task waiting for you"

New Plan: FAMILY (US$7.99/mês)
Target: 1M family households globally
```

**Why:** Retention 80% (vs 70% individual)  
**Timeline:** 4 weeks  
**Complexity:** High (multi-user, permissions)  
**Revenue:** US$95K ARR (3K users × US$7.99 × 4)

### 4.2 Pillar 2: Marketplace (B2B2C)

```
Phase 1 (V2.0):
  - Affiliate links: Cleaning products
  - Coupons: Local cleaning services
  - Referral: "Get R$20 cleaning credit"

Phase 2 (V2.1):
  - Direct marketplace: Vetted cleaners
  - Booking: "Hire cleaner for Thursday"
  - Revenue: Commission 20% per booking
  - Target: US$500-1000/cleaning → US$100-200/revenue
```

**Why:** High LTV, viral (referral)  
**Timeline:** 6 weeks (Phase 1), 8 weeks (Phase 2)  
**Complexity:** Very High (payments, vetting)  
**Revenue:** US$500K+ ARR (1K bookings/week × US$100)

### 4.3 Pillar 3: Integrações

```
Google Calendar:
  - Auto-sync task deadlines
  - Block time for cleaning

Slack:
  - Daily reminder in channel
  - Celebrate achievements
  - "@housekeep complete kitchen"

Zapier:
  - Trigger: Task completed → Add event to spreadsheet
  - Trigger: Achievement → Tweet
  - Trigger: Streak broken → Send SMS
```

**Why:** Power users + SMBs  
**Timeline:** 2 weeks per integration  
**Complexity:** Medium  
**Revenue:** +5% premium conversion

### 4.4 Pillar 4: IA (Experimental)

```
Phase 1 (V2.1):
  - Suggestion: "Your kitchen was messy Wed, needs bi-daily sweep"
  - Prediction: "Will skip next task? We noticed pattern"

Phase 2 (V2.2):
  - Photo analysis: Vision API detects bagunça level
  - Recommendation: "Add 'organize closet' tomorrow"

Phase 3 (V2.3):
  - Personalization: "Best time to do tasks for you is 7am"
  - Ranking: "Vs. similar households"
```

**Why:** Retention + engagement  
**Timeline:** 8 weeks (V2.1), 12 weeks (V2.2)  
**Complexity:** Very High  
**Cost:** US$0.01-0.10 per photo (Vision API)  
**Revenue:** Premium tier US$9.99/mês (AI-powered)

### 4.5 Timeline V2

| Phase | Months | Features | Users Target |
|-------|--------|----------|--------------|
| V2.0 | Jun-Jul | Família beta | 500K |
| V2.1 | Aug-Oct | Marketplace Phase 1 + IA Phase 1 | 750K |
| V2.2 | Nov-Dec | Marketplace Phase 2 + Integrações | 1M |

### 4.6 Success Criteria
- Total users: 350K → 1M
- Premium: 20K → 50K
- Family: 0 → 20K
- Professional: 0 → 100
- MRR: US$80K → US$250K+
- Revenue diversification:
  - Premium: 40%
  - Family: 30%
  - Marketplace: 20%
  - Professional: 10%

---

## 5. Recursos Necessários (Headcount)

### MVP → V1.0 (1-2 pessoas)
- 1x Full-stack (React + Django)
- 0.5x Designer (parte-time)
- 0.5x PM (você ou co-founder)

### V1.0 → V1.x (3-4 pessoas)
- 2x Backend (escalabilidade, analytics)
- 1x Frontend (UI polish, PWA)
- 1x Designer (design system)
- 0.5x PM/QA

### V1.x → V2 (5-8 pessoas)
- 2x Backend (Família, marketplace, IA)
- 2x Frontend (complexidade crescente)
- 1x Designer (design system)
- 1x DevOps/Infra (scaling)
- 1x PM (strategy, prioritization)

### Budget Estimado (Annual)

| Phase | Salários | Infra | Terceiros | Total |
|-------|----------|-------|-----------|-------|
| MVP | US$40K | US$2K | US$5K | US$47K |
| V1.0 | US$80K | US$5K | US$10K | US$95K |
| V1.x | US$120K | US$10K | US$20K | US$150K |
| V2 | US$200K | US$20K | US$50K | US$270K |

---

## 6. Technical Debt & Maintenance

### MVP Tech Debt (Acceptable)
- ✅ Hardcoded XP table (refactored em V1)
- ✅ No rate limiting (add em V1)
- ✅ No caching strategy (add em V1.x)
- ❌ No error monitoring (add immediately)

### V1.0 Debt
- Task recurrence logic (clean em V1.x)
- Achievement condition parser (add tests)
- Photo storage (migrate S3 em V2)

### V1.x Debt
- Analytics queries (add indexing)
- Frontend state management (migrate Zustand)
- Email system (add queue, retry logic)

### V2 Debt (Unavoidable at scale)
- Distributed transactions (Família)
- Eventual consistency (marketplace)
- Caching strategy (Redis)

---

## 7. Key Milestones

| Date | Milestone | Metric |
|------|-----------|--------|
| **Week 1** | MVP live (Product Hunt) | 5K users |
| **Week 8** | 50K users | D30: 20% |
| **Week 24** | V1.0 launch (achievements + photos) | 150K users, 5% premium |
| **Week 36** | V1.x launch (analytics + push) | 300K users, 10K premium |
| **Week 48** | V2.0 beta (Família) | 500K users, 15K premium |
| **Week 52** | V2.0 full launch | 750K users, MRR US$150K |

---

## 8. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Churn > 40% D30 | 🔴 Fatal | Pivot gamification, add features faster |
| Photo uploads > server | 🟡 Medium | Scale S3 from day 1 |
| Stripe integration fails | 🟡 Medium | Test extensively, fallback to PayPal |
| Competitor clones | 🔵 Low | Speed to market, community first |
| Burnout (solo dev) | 🟡 Medium | Hire early, delegate non-core tasks |
| Market says "not ready" | 🔵 Low | Pivot to B2B (property management) |

---

## 9. Decision Checkpoints

### After MVP (Week 8)
**Question:** D7 retention > 35%?
- **Yes:** Proceed to V1.0
- **No:** Iterate on core loop (tarefas), delay V1

### After V1.0 (Week 24)
**Question:** Premium conversion > 3%?
- **Yes:** Proceed to V1.x
- **No:** Change paywall strategy, test differently

### After V1.x (Week 36)
**Question:** MRR > US$50K or 50K users?
- **Yes:** Proceed to V2 (Família)
- **No:** Extend V1.x, focus on retention

### After V2.0 Beta (Week 48)
**Question:** Família retention > 80%? Revenue > US$20K?
- **Yes:** Scale marketplace
- **No:** Keep iterating, delay marketplace

---

## 10. Success Definition by Phase

### MVP Success
> "No Rats é usado por 50K pessoas. 40% voltam uma semana depois. Gaming loop é viciante."

### V1.0 Success
> "150K usuários ativos. 10K pagam US$3.99/mês. Retention D30 é 35%. Achievements aumentaram engagement."

### V1.x Success
> "300K usuários. 20K pagando. MRR > US$80K. Push notifications aumentaram D30 em 15 pp."

### V2 Success
> "1M usuários globais. 50K premium + 20K family + 100 professional. MRR > US$250K. Marketplace é 20% da receita."

---

**Conclusion:** Road é clara, achievable, e data-driven. MVP→V1 é 3 meses com 1-2 pessoas. V1→V2 é 6 meses com time pequeno. Monetização começa em V1.0 (não espera V2).
