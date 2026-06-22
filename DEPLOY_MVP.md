# No Rats — Deploy MVP (Infra Mínima)

Guia completo para rodar No Rats localmente e na cloud com custo zero/mínimo.

---

## Part 1: Setup Local (Desenvolvimento)

### 1.1 Pré-requisitos

```bash
# Instalar (se não tiver):
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (ou use Railway grátis depois)
- Git

# Verificar instalação:
python --version
node --version
psql --version
```

### 1.2 Backend Setup (Django)

```bash
# 1. Clone/configure projeto Django
cd ~/projects
mkdir no-rats-backend
cd no-rats-backend

# 2. Create virtual env
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou: venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar .env local
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=dev-key-do-not-use-in-prod-very-secret-key-here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/no_rats_dev
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT
DJANGO_SECRET_KEY=dev-key-very-secret
JWT_SIGNING_KEY=dev-jwt-key

# Email (opcional, usar console em dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# S3 (desabilitado em dev)
USE_S3=False
EOF

# 5. Criar database
createdb no_rats_dev

# 6. Migrations
python manage.py migrate

# 7. Load achievements (V1)
python manage.py load_achievements

# 8. Create superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: dev123456

# 9. Rodar servidor
python manage.py runserver 0.0.0.0:8000
```

**Verificar:**
```bash
curl http://localhost:8000/api/v1/auth/users/register/
# Deve retornar 405 Method Not Allowed (esperado, é POST)
```

### 1.3 Frontend Setup (React + Vite)

```bash
# 1. Setup projeto
cd ~/projects
mkdir no-rats-frontend
cd no-rats-frontend

# 2. Create Vite project
npm create vite@latest . -- --template react-ts

# 3. Instalar dependências
npm install

# 4. Instalar shadcn/ui
npm run setup-shadcn  # ou manual: npx shadcn-ui@latest init

# 5. Criar .env.local
cat > .env.local << 'EOF'
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=No Rats
EOF

# 6. Rodar dev server
npm run dev
# Acessa em http://localhost:5173
```

**Estrutura base já está em FRONTEND_IMPLEMENTATION.md**

### 1.4 Testar Fluxo Completo (Local)

```bash
# Terminal 1: Backend
cd ~/projects/no-rats-backend
source venv/bin/activate
python manage.py runserver

# Terminal 2: Frontend
cd ~/projects/no-rats-frontend
npm run dev

# Browser: http://localhost:5173
# Test: Register → Login → Onboarding → Create Task → Complete
```

---

## Part 2: Deploy Cloud Mínimo (Zero/Baixo Custo)

### 2.1 Database — Railway (PostgreSQL Grátis)

**Opção 1: Railway (Recomendado)**

```bash
# 1. Criar conta em railway.app (GitHub login)

# 2. Criar novo projeto
# New Project → Add Service → PostgreSQL

# 3. Copiar connection string
# Em Railway dashboard: PostgreSQL → Connect → Database URL
DATABASE_URL=postgresql://user:pass@host:port/dbname

# 4. Atualizar .env backend
echo "DATABASE_URL=$DATABASE_URL" >> .env

# 5. Local: testar conexão
psql $DATABASE_URL -c "SELECT version();"
```

**Opção 2: Neon (PostgreSQL Serverless, Grátis)**

```bash
# 1. Criar conta em neon.tech

# 2. Criar novo project → PostgreSQL

# 3. Copiar connection string
# Dashboard → Connection string
NEON_DATABASE_URL=postgresql://user:pass@ep-host.neon.tech/dbname

# 4. Usar no .env
DATABASE_URL=$NEON_DATABASE_URL
```

**Opção 3: Local (Desenvolvimento)**

```bash
# Se quer rodar tudo localmente sem cloud:
# Manter PostgreSQL local rodando:

# Mac (via Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Linux (Debian/Ubuntu)
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# Windows (WSL recomendado)
# Ou usar Docker: docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 postgres:14
```

---

### 2.2 Backend — Railway (Grátis até US$5/mês)

```bash
# 1. Criar novo projeto em railway.app

# 2. Conectar repositório GitHub
# New Project → GitHub Repo → Deploy

# 3. Configurar environment variables
# Em Railway Dashboard → Variables:
DEBUG=False
SECRET_KEY=(gere uma chave segura)
DATABASE_URL=(copie do PostgreSQL que criou acima)
ALLOWED_HOSTS=yourdomain.railway.app,www.yourdomain.railway.app
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=changeme

# 4. Adicionar arquivo railway.json na raiz:
cat > railway.json << 'EOF'
{
  "build": {
    "builder": "nixpacks",
    "buildCommand": "pip install -r requirements.txt && python manage.py migrate && python manage.py createsuperuser --noinput || true && python manage.py load_achievements"
  },
  "deploy": {
    "startCommand": "python manage.py runserver 0.0.0.0:$PORT",
    "numReplicas": 1
  }
}
EOF

# 5. Fazer git push (auto-deploy)
git add .
git commit -m "Deploy ready"
git push origin main

# 6. Copiar URL
# Railway gerada URL como: no-rats-backend.railway.app
```

**Ou, usar Procfile (Railway interpreta automaticamente):**

```bash
cat > Procfile << 'EOF'
web: gunicorn no_rats.wsgi --log-file -
EOF

# Instalar gunicorn
pip install gunicorn
pip freeze > requirements.txt
```

---

### 2.3 Frontend — Vercel (Grátis)

```bash
# 1. Criar conta em vercel.com (GitHub login)

# 2. Deploy:
# Option A: Vercel CLI
npm install -g vercel
vercel

# Option B: GitHub import
# Vercel dashboard → New Project → Import Git Repository
# Select no-rats-frontend repo

# 3. Configurar environment
# Em Vercel Project Settings → Environment Variables:
VITE_API_URL=https://no-rats-backend.railway.app/api/v1

# 4. Deploy automático
# Qualquer push para main = auto-deploy

# 5. Copiar URL
# Vercel gerada URL como: no-rats-frontend.vercel.app
```

---

### 2.4 Conectar Frontend ao Backend

```typescript
// src/api/client.ts — Atualizar baseURL

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Em produção: https://no-rats-backend.railway.app/api/v1
// Em dev: http://localhost:8000/api/v1
```

---

## Part 3: Docker (Opcional, Mais Profissional)

### 3.1 Backend Dockerfile

```dockerfile
# Dockerfile (na raiz do backend)

FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Migrations e seed (opcional, melhor fazer manualmente)
# RUN python manage.py migrate
# RUN python manage.py load_achievements

# Expor porta
EXPOSE 8000

# Rodando
CMD ["gunicorn", "no_rats.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 3.2 Docker Compose (Frontend + Backend + DB Local)

```yaml
# docker-compose.yml (na raiz do projeto)

version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: no_rats_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./no-rats-backend
    command: >
      sh -c "python manage.py migrate &&
             python manage.py load_achievements &&
             gunicorn no_rats.wsgi:application --bind 0.0.0.0:8000"
    environment:
      DEBUG: "True"
      SECRET_KEY: dev-secret-key
      DATABASE_URL: postgresql://postgres:postgres@db:5432/no_rats_dev
      ALLOWED_HOSTS: localhost,127.0.0.1,backend
      CORS_ALLOWED_ORIGINS: http://localhost:3000,http://frontend:3000
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./no-rats-backend:/app

  frontend:
    build: ./no-rats-frontend
    environment:
      VITE_API_URL: http://backend:8000/api/v1
    ports:
      - "5173:5173"
    depends_on:
      - backend
    volumes:
      - ./no-rats-frontend:/app

volumes:
  postgres_data:
```

**Rodar com Docker:**

```bash
docker-compose up --build

# Acessa em http://localhost:5173
# Backend: http://localhost:8000
# Admin: http://localhost:8000/admin
```

---

## Part 4: Testing End-to-End

### 4.1 Testar Fluxo Completo

```bash
# 1. Acesso frontend
curl http://localhost:5173
# ✅ Se retorna HTML, frontend está ok

# 2. Testar auth
curl -X POST http://localhost:8000/api/v1/auth/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"pass123","password_confirm":"pass123"}'

# ✅ Response: {"id":"...","email":"test@example.com","name":"Test User",...}

# 3. Login
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# ✅ Response: {"access":"<token>","refresh":"<token>"}

# 4. Criar room
curl -X POST http://localhost:8000/api/v1/houses/rooms/setup_house/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"rooms":["cozinha","banheiro","quarto"]}'

# ✅ Response: [{"id":"...","name":"cozinha",...},...]

# 5. Criar tarefa
curl -X POST http://localhost:8000/api/v1/tasks/tasks/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"room":"<room_id>","title":"Lavar louça","difficulty":"simples","frequency":"diaria"}'

# ✅ Response: {"id":"...","title":"Lavar louça","status":"pendente",...}
```

### 4.2 Testar no Celular

```bash
# Pra acessar seu localhost do celular na mesma rede:

# 1. Descobrir IP local
ipconfig getifaddr en0  # Mac
hostname -I            # Linux
ipconfig               # Windows (procure por "IPv4 Address")

# 2. Frontend: http://<seu-ip>:5173
# 3. Backend: http://<seu-ip>:8000/api/v1

# ou usar ngrok (tunnel automático)
ngrok http 5173  # Frontend
ngrok http 8000  # Backend

# Acessa via URL gerada pelo ngrok (válida por 2h)
```

---

## Part 5: Checklist Deploy

### ✅ Local Development

- [ ] Backend rodando em http://localhost:8000
- [ ] Frontend rodando em http://localhost:5173
- [ ] Database conectado (PostgreSQL local)
- [ ] Criar user (register + login)
- [ ] Setup rooms (3 cômodos)
- [ ] Criar tarefa
- [ ] Completar tarefa (check XP/streak)
- [ ] Ver dashboard

### ✅ Cloud Staging

- [ ] Database (Railway ou Neon)
- [ ] Backend deployed (Railway)
- [ ] Frontend deployed (Vercel)
- [ ] Variáveis de ambiente configuradas
- [ ] CORS habilitado
- [ ] Testar fluxo completo na cloud
- [ ] Admin accessible (http://backend-url/admin)

### ✅ Pre-Launch

- [ ] Segurança:
  - [ ] DEBUG=False em produção
  - [ ] SECRET_KEY única e segura
  - [ ] ALLOWED_HOSTS corretos
  - [ ] HTTPS only (Vercel + Railway já têm)
  
- [ ] Performance:
  - [ ] Testar com 100+ tarefas
  - [ ] Testar dashboard lento (retenção)
  - [ ] Verificar query N+1 (Django Debug Toolbar)
  
- [ ] UX:
  - [ ] Onboarding fluxo (3 cliques)
  - [ ] Primeira tarefa (< 30 segundos)
  - [ ] Completar tarefa (satisfação visual)
  - [ ] Testar em mobile (PWA ready?)

---

## Part 6: Monitoring & Logs

### 6.1 Ver Logs Backend (Railway)

```bash
# SSH em Railway
railway shell

# Dentro do container:
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.all().count()
```

### 6.2 Ver Logs Frontend (Vercel)

```bash
# Vercel dashboard → Deployments → Logs
# Ou via CLI:
vercel logs
```

### 6.3 Monitorar Database

```bash
# Conectar remotamente (Railway PostgreSQL)
psql $DATABASE_URL

# Queries úteis
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM tasks;
SELECT COUNT(*) FROM task_completions;

# Ver performance
\timing on  # Ativa timing
SELECT * FROM tasks WHERE user_id = '<id>';
```

---

## Part 7: Troubleshooting

### Backend não conecta com Database

```bash
# Verificar connection string
echo $DATABASE_URL

# Testar conexão
psql $DATABASE_URL -c "SELECT 1;"

# Se não conecta, verificar:
1. Credenciais corretas
2. Host/port corretos
3. Firewall (Railway: whitelist IP)
4. Database existe
```

### Frontend não conecta com Backend

```bash
# Verificar CORS
curl -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/v1/auth/users/

# Response deve ter:
# Access-Control-Allow-Origin: http://localhost:5173

# Se não tiver, verificar settings.py:
CORS_ALLOWED_ORIGINS = ['http://localhost:5173', ...]
```

### Migrations falham

```bash
# Ver status
python manage.py showmigrations

# Rollback última migration
python manage.py migrate <app> <previous_migration>

# Rodar de novo
python manage.py migrate

# Ou force:
python manage.py migrate --fake-initial
```

### Achievements não existem

```bash
# Load data
python manage.py load_achievements

# Verificar
python manage.py shell
>>> from gamification.models import Achievement
>>> Achievement.objects.count()
# Deve ser 11+
```

---

## Part 8: Próximos Passos

### Após Deploy Local (Funciona)
1. ✅ Convidar amigos testar
2. ✅ Coletar feedback
3. ✅ Iterar gamificação (se churn alto)

### Após Deploy Cloud (Acessível)
1. ✅ Launchá em Product Hunt
2. ✅ Coletar emails (waitlist, se quiser)
3. ✅ Setup analytics (Mixpanel)
4. ✅ Monitor KPIs (retention, completion)

### Antes de V1 (Paywall)
1. ✅ Criptografia em banco (senhas hashed)
2. ✅ Rate limiting (API abuse)
3. ✅ Error monitoring (Sentry)
4. ✅ Backup automático (Railway já faz)
5. ✅ GDPR compliance (delete user data)

---

## Resumo: Custo Total (Primeiro Mês)

| Serviço | Plano | Custo |
|---------|-------|-------|
| Database (Railway PostgreSQL) | Free tier | US$0 |
| Backend (Railway) | Free tier (até 5GB) | US$0 |
| Frontend (Vercel) | Free tier | US$0 |
| Domain (opcional) | namecheap | US$9/year |
| **Total** | | **US$0** |

**Ano 1 após crescimento:**
| Serviço | Plano | Custo |
|---------|-------|-------|
| Database (Railway) | Growth | US$20/mês |
| Backend (Railway) | Growth | US$50/mês |
| Frontend (Vercel) | Pro | US$20/mês |
| Domain | namecheap | US$9/year |
| **Total** | | **US$90/mês** |

---

## 🚀 Quick Start (Resumido)

```bash
# Backend
cd no-rats-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "DATABASE_URL=postgresql://localhost/no_rats_dev" > .env
python manage.py migrate
python manage.py load_achievements
python manage.py runserver

# Frontend (novo terminal)
cd no-rats-frontend
npm install
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev

# Acessa http://localhost:5173
# Pronto! 🎉
```

---

**Status:** MVP pronto para deploy. Escolhe local vs cloud, segue o guia, rodar em 30 min.
