# No Rats — Deploy Cloud (Parte B) — 1 Hora

Local está funcionando. Agora sobe pra cloud (Railway + Vercel, grátis).

---

## PARTE 1: Git Setup (10 min)

### 1.1 Criar repositório GitHub

```bash
# 1. Criar conta em github.com (se não tiver)
# 2. Criar novo repositório "no-rats" (vazio, sem README)
# 3. Copiar URL: https://github.com/SEU_USER/no-rats

# No seu computador:
cd ~/no-rats-project

# Inicializar git
git init

# Adicionar remote
git remote add origin https://github.com/SEU_USER/no-rats

# Verificar
git remote -v
# Output esperado:
# origin  https://github.com/SEU_USER/no-rats (fetch)
# origin  https://github.com/SEU_USER/no-rats (push)
```

### 1.2 Preparar backend pra deploy

```bash
cd ~/no-rats-project/backend

# Criar requirements.txt
pip freeze > requirements.txt

# Adicionar gunicorn
echo "gunicorn==21.2.0" >> requirements.txt

# Editar requirements.txt: remover linhas com "venv" ou caminhos locais

# Verificar
cat requirements.txt | head -20
```

### 1.3 Criar Procfile (Django no Railway)

```bash
cd ~/no-rats-project/backend

cat > Procfile << 'EOF'
web: gunicorn no_rats.wsgi --log-file -
release: python manage.py migrate && python manage.py load_achievements
EOF

# Verificar
cat Procfile
```

### 1.4 Editar settings.py (production ready)

```bash
# Editar no_rats/settings.py:

# No final do arquivo, adicione:

cat >> no_rats/settings.py << 'EOF'

# Production
ALLOWED_HOSTS = ['*']  # Railway vai colocar domínio
DEBUG = False

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database: usar Railway
import os
import dj_database_url

if os.environ.get('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
EOF

# Instalar dependência
pip install dj-database-url
echo "dj-database-url" >> requirements.txt
```

### 1.5 Commit & Push para GitHub

```bash
cd ~/no-rats-project

# Adicionar todos arquivos
git add .

# Commit
git commit -m "Initial commit: No Rats MVP"

# Push para main
git branch -M main
git push -u origin main

# Verificar no github.com
# Deve ver todos os arquivos lá
```

---

## PARTE 2: Database na Cloud (10 min)

### 2.1 Railway PostgreSQL

```bash
# 1. Acesse railway.app
# 2. Login com GitHub
# 3. Clique "+ New Project"
# 4. Selecione "Add Service" → "PostgreSQL"
# 5. Clique em PostgreSQL service
# 6. Vá para aba "Connect"
# 7. Copie "Database URL"

# Deve parecer:
# postgresql://postgres:PASSWORD@containers.railway.app:PORT/railway

# ⚠️ COPIE E GUARDE ESSA URL (vai usar no Railway Backend)
```

---

## PARTE 3: Deploy Backend (15 min)

### 3.1 Railway Backend Setup

```bash
# 1. Em railway.app, mesmo projeto
# 2. Clique "+ New Service"
# 3. Selecione "GitHub Repo"
# 4. Selecione seu repo "no-rats"
# 5. Selecione root directory: "backend/"

# Aguarde Railway detectar Procfile
# Deve aparecer: "Django app detected"
```

### 3.2 Configurar variáveis de ambiente

```
Em Railway Dashboard → Backend Service → Variables:

Adicione:
DEBUG=False
SECRET_KEY=django-insecure-GERE-UMA-CHAVE-SEGURA-MUITO-LONGA-E-COMPLEXA
DATABASE_URL=(Copie da etapa 2.1)
ALLOWED_HOSTS=seu-app.railway.app
CORS_ALLOWED_ORIGINS=https://seu-frontend.vercel.app

⚠️ SECRET_KEY: Cole uma string longa e aleatória
   Opção: Gere em: https://djecrety.ir/
```

### 3.3 Deploy

```
Railway auto-deploy quando você fez git push.

Para forçar redeploy:
1. Em Railway dashboard → Backend
2. Clique ⋮ (menu)
3. Selecione "Redeploy"

Aguarde 2-3 min. Deve ver:
✅ Deployment successful
```

### 3.4 Copiar URL do Backend

```
Em Railway Dashboard → Backend:
- Vá para "Deployments" tab
- Procure por "Service Domain"

Deve parecer:
https://no-rats-backend-production.railway.app

⚠️ GUARDE ESSA URL (vai usar no Frontend)
```

### 3.5 Testar Backend Cloud

```bash
# Terminal (seu PC):
BACKEND_URL="https://seu-backend.railway.app"

# Teste 1: Admin
curl $BACKEND_URL/admin/
# Deve retornar HTML

# Teste 2: Register
curl -X POST $BACKEND_URL/api/v1/auth/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cloud@test.com",
    "name": "Cloud Test",
    "password": "cloudpass123",
    "password_confirm": "cloudpass123"
  }'

# Output esperado:
# {"id":"...","email":"cloud@test.com","name":"Cloud Test",...}

# ✅ SE VIR ISSO, backend cloud está funcionando!
```

---

## PARTE 4: Deploy Frontend (15 min)

### 4.1 Vercel Setup

```bash
# 1. Acesse vercel.com
# 2. Login com GitHub
# 3. Clique "New Project"
# 4. Selecione seu repo "no-rats"
# 5. Configure:
   - Root Directory: frontend/
   - Framework: Vite
   - Build Command: npm run build (default)
   - Output Directory: dist (default)
```

### 4.2 Variáveis de Ambiente (Vercel)

```
Em Vercel → Project Settings → Environment Variables:

Adicione:
VITE_API_URL=https://seu-backend.railway.app/api/v1

(Cole a URL que guardou em 3.4)
```

### 4.3 Deploy

```
Vercel auto-deploy quando fez git push.

Para forçar redeploy:
1. Em Vercel dashboard
2. Clique em último deployment
3. Clique "Redeploy"

Aguarde 1-2 min. Deve ver:
✅ Production
```

### 4.4 Copiar URL do Frontend

```
Em Vercel Dashboard:
- Procure por "Deployment Domains"

Deve parecer:
https://no-rats-frontend.vercel.app

⚠️ ESSA É SUA URL PÚBLICA!
```

---

## PARTE 5: Testar Ponta-a-Ponta Cloud (10 min)

### 5.1 Acessar Frontend Cloud

```
1. Abra browser: https://seu-frontend.vercel.app
2. Deve redirecionar para /login
3. Criar conta:
   - Email: cloud@test.com
   - Nome: Cloud User
   - Senha: cloudpass123
4. Login
5. Setup rooms: selecione 3 cômodos
6. Dashboard: XP 0, Nível 1, Streak 0
7. Criar tarefa: "Lavar louça"
8. Completar: clique "+ 10 XP"
9. Dashboard atualiza: XP 10, Streak 1 ✅

SE TUDO FUNCIONOU, CLOUD ESTÁ LIVE!
```

### 5.2 Testar Responsividade Mobile

```
No celular (mesma rede Wi-Fi ou internet):
1. Abra: https://seu-frontend.vercel.app
2. Mesmo fluxo acima
3. Deve funcionar perfeitamente em mobile ✅
```

---

## ✅ Checklist Cloud

- [ ] GitHub repo criado + código sincronizado
- [ ] Railway PostgreSQL criado
- [ ] Railway Backend deployed
- [ ] Backend URL funciona (curl /admin/)
- [ ] Vercel Frontend deployed
- [ ] Frontend URL funciona (abre no browser)
- [ ] Criar conta na cloud
- [ ] Login na cloud
- [ ] Setup rooms
- [ ] Criar tarefa
- [ ] Completar tarefa (XP atualiza)
- [ ] Dashboard mostra corretamente

---

## 🎉 Se Tudo Funcionou

```
✅ No Rats está LIVE na cloud!

URLs públicas:
📱 Frontend: https://seu-frontend.vercel.app
⚙️ Backend: https://seu-backend.railway.app
🗄️ Admin: https://seu-backend.railway.app/admin

Você pode:
- Compartilhar link com amigos
- Testar em qualquer dispositivo
- Modificar código local → git push → auto-deploy
- Monitorar em Railway/Vercel dashboards
```

---

## 🚀 Depois de Tudo Funcionando

### Próximos Passos:

1. **Compartilhar com amigos** (coletar feedback)
   ```
   Link: https://seu-frontend.vercel.app
   Pedir pra: Criar conta → Setup rooms → Criar 2-3 tarefas → Completar
   Feedback: O que acham? Tá motivante?
   ```

2. **Coletar métricas** (D1/D7 retention)
   - Quantas pessoas voltaram amanhã?
   - Quantas completaram tarefas?
   - Alguém atingiu nível 2?

3. **Iterar se necessário**
   - Se D1 < 40%: Aumentar XP reward
   - Se completion < 50%: Simplificar onboarding
   - Se alguém reclama: Ajustar rapidamente

4. **Launch público** (quando estiver confiante)
   - Product Hunt
   - Reddit (r/productivity, r/todoist)
   - Hackernews

---

## 🐛 Troubleshooting Cloud

### Backend deployment falha

```
Em Railway → Deployments → Logs:
Procure por erros como:
- "ModuleNotFoundError": pip install faltando
- "ALLOWED_HOSTS": Variable não configurada
- "DATABASE_URL": Conexão falha

Solução:
1. Verificar variáveis de ambiente
2. Verificar requirements.txt
3. Clicar "Redeploy"
```

### Frontend não conecta com backend

```
Em browser console (F12):
Procure por erro "CORS" ou "TypeError: fetch failed"

Solução:
1. Verificar VITE_API_URL em Vercel variables
2. Verificar CORS_ALLOWED_ORIGINS no backend
3. Redeploy ambos
```

### Database connection failed

```
Erro: "psycopg2.OperationalError"

Solução:
1. Railway Dashboard → PostgreSQL → Logs
2. Verificar DATABASE_URL está correto
3. Verificar password não tem caracteres especiais problemáticos
4. Clicar "Redeploy" no backend
```

---

## 💡 Dicas Finais

### Monitorar Performance

```
Railway Dashboard:
- CPU usage
- Memory usage
- Network I/O
- Database connections

Vercel Dashboard:
- Build time
- Response time
- Error rate
```

### Configurar Domain Custom (Futuro)

```
Domínio próprio (ex: no-rats.app):
1. Comprar domínio (namecheap, google domains)
2. Railway: Custom domain → https://seu-backend.no-rats.app
3. Vercel: Domains → https://no-rats.app
4. Configurar DNS (30 min setup)

Custo: ~US$12/ano domínio + US$0 hosting (rails+vercel grátis)
```

---

## 📊 Seu No Rats está LIVE

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  🎉 NO RATS MVP — LIVE NA CLOUD 🎉            │
│                                                 │
│  ✅ Local development setup                    │
│  ✅ Cloud infrastructure deployed              │
│  ✅ Database connected (PostgreSQL)            │
│  ✅ API working (Django REST)                  │
│  ✅ Frontend live (React + Vite)               │
│  ✅ Authentication (JWT)                       │
│  ✅ Gamification (XP, Streak, Levels)         │
│  ✅ Ready for users!                           │
│                                                 │
│  Frontend: https://seu-frontend.vercel.app    │
│  Backend: https://seu-backend.railway.app     │
│  Admin: https://seu-backend.railway.app/admin │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

**Confirme quando cloud estiver 100% funcionando! ✅**

Depois avançamos para:
- **Feedback loop** (coletar dados de usuários)
- **KPI tracking** (retention, completion)
- **V1.0 planning** (achievements, fotos)
