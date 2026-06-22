# No Rats — Setup Local (Step-by-Step)

Guia prático: copie/cole cada comando, espere completar, passe pro próximo.

---

## STEP 1: Verificar Pré-requisitos (2 min)

```bash
# Mac/Linux:
python --version
# Output esperado: Python 3.10.x ou 3.11.x ou 3.12.x

node --version
# Output esperado: v18.x ou v20.x ou v21.x

git --version
# Output esperado: git version 2.x.x
```

**Se faltar algo:**
```bash
# Mac (usando Homebrew)
brew install python@3.11 node git

# Linux (Debian/Ubuntu)
sudo apt-get install python3.11 nodejs npm git

# Verificar PostgreSQL (vamos usar versão cloud depois, ok local agora)
# Pular por enquanto, usar SQLite em dev se necessário
```

---

## STEP 2: Criar Estrutura de Pastas (1 min)

```bash
# Criar diretório raiz do projeto
mkdir ~/no-rats-project
cd ~/no-rats-project

# Criar subpastas
mkdir backend
mkdir frontend

# Listar para verificar
ls -la
# Output esperado:
# drwxr-xr-x  backend
# drwxr-xr-x  frontend
```

---

## STEP 3: Setup Backend (Django) — 12 min

### 3.1 Inicializar projeto Django

```bash
cd ~/no-rats-project/backend

# Criar virtual environment
python3 -m venv venv

# Ativar (Mac/Linux)
source venv/bin/activate
# Ou Windows: venv\Scripts\activate

# Verificar que venv está ativo
which python
# Output: /Users/YOUR_USER/no-rats-project/backend/venv/bin/python
```

### 3.2 Instalar Django e dependências

```bash
# Copie/cole tudo de uma vez:
pip install --upgrade pip setuptools wheel

pip install \
  Django==4.2.0 \
  djangorestframework==3.14.0 \
  djangorestframework-simplejwt==5.2.0 \
  django-cors-headers==4.0.0 \
  python-decouple==3.8 \
  psycopg2-binary==2.9.6 \
  pillow==10.0.0

# Verificar instalação
pip list | grep Django
# Output: Django                    4.2.0
```

### 3.3 Criar projeto Django

```bash
# Dentro de ~/no-rats-project/backend

# Criar projeto
django-admin startproject no_rats .

# Criar apps
python manage.py startapp accounts
python manage.py startapp houses
python manage.py startapp tasks
python manage.py startapp gamification
python manage.py startapp core

# Verificar estrutura
ls -la
# Output esperado:
# manage.py
# no_rats/
# accounts/
# houses/
# tasks/
# gamification/
# core/
```

### 3.4 Configurar Django (settings.py)

```bash
# Editar no_rats/settings.py
# Copie/cole este conteúdo após "INSTALLED_APPS = [":

cat > no_rats/settings_apps.txt << 'EOF'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'houses.apps.HousesConfig',
    'tasks.apps.TasksConfig',
    'gamification.apps.GamificationConfig',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
]

AUTH_USER_MODEL = 'accounts.User'

# Database: SQLite em dev (simples!)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
EOF

# Visualizar o arquivo para copiar
cat no_rats/settings_apps.txt
```

**⚠️ Manual: Edite `no_rats/settings.py` e:**
1. Substitua `INSTALLED_APPS` pelo conteúdo acima
2. Substitua `MIDDLEWARE` pelo conteúdo acima
3. Adicione `REST_FRAMEWORK`, `CORS_ALLOWED_ORIGINS`, `AUTH_USER_MODEL` (após DATABASES)

### 3.5 Criar .env

```bash
cd ~/no-rats-project/backend

cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=this-is-a-dev-key-dont-use-in-production-very-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
EOF

# Verificar
cat .env
```

### 3.6 Migrations & Setup

```bash
cd ~/no-rats-project/backend

# Criar migrations
python manage.py makemigrations

# Rodar migrations
python manage.py migrate

# Saída esperada:
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, sessions, ...
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   ...
```

### 3.7 Criar Superuser

```bash
python manage.py createsuperuser

# Preencha:
# Username: admin
# Email: admin@example.com
# Password: dev123456
# Confirm password: dev123456

# Output: Superuser created successfully.
```

### 3.8 Testar Backend

```bash
python manage.py runserver

# Output esperado:
# Starting development server at http://127.0.0.1:8000/
# Quit the server with CONTROL-C.
```

**Deixe rodando! Em outro terminal, teste:**

```bash
# Terminal 2 (novo)
curl http://localhost:8000/admin/

# Deve retornar HTML da página de admin
# Se vir HTML, ✅ Backend está ok!

# Parar com Ctrl+C no terminal 1 depois
```

---

## STEP 4: Setup Frontend (React + Vite) — 8 min

### 4.1 Criar projeto Vite

```bash
cd ~/no-rats-project/frontend

# Criar template React + TypeScript
npm create vite@latest . -- --template react-ts

# Pergunta: Do you want to use TypeScript? → yes
# Pergunta: SWC or Babel? → Babel (default)

# Saída esperada:
# Done. Now run:
#   npm install
#   npm run dev
```

### 4.2 Instalar dependências

```bash
cd ~/no-rats-project/frontend

# Instalar
npm install

# Adicionar packages necessários
npm install react-router-dom axios
npm install recharts

# Saída esperada (final):
# added 200+ packages

# Verificar
npm list react react-dom
# Deve mostrar versões
```

### 4.3 Criar .env.local

```bash
cat > .env.local << 'EOF'
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=No Rats
EOF

# Verificar
cat .env.local
```

### 4.4 Estrutura de Pastas

```bash
# Copiar estrutura mínima do frontend
# Criar diretórios base:

mkdir -p src/pages
mkdir -p src/components
mkdir -p src/hooks
mkdir -p src/context
mkdir -p src/api
mkdir -p src/types
mkdir -p src/utils

ls -la src/
# Output esperado: diretórios listados
```

### 4.5 Testar Frontend

```bash
npm run dev

# Output esperado:
#   VITE v4.x.x  ready in 123 ms
#   ➜  Local:   http://localhost:5173/
#   ➜  press h + enter to show help
```

**Em outro terminal:**

```bash
curl http://localhost:5173/

# Deve retornar HTML
# Se vir HTML, ✅ Frontend está ok!
```

---

## STEP 5: Testar Fluxo Completo (3 min)

### 5.1 Manter ambos rodando

```bash
# Terminal 1: Backend
cd ~/no-rats-project/backend
source venv/bin/activate
python manage.py runserver
# Rodando em http://localhost:8000

# Terminal 2: Frontend
cd ~/no-rats-project/frontend
npm run dev
# Rodando em http://localhost:5173

# Terminal 3: Testes (deixe livre)
```

### 5.2 Testar API (via curl)

```bash
# Terminal 3:

# Teste 1: Register
curl -X POST http://localhost:8000/api/v1/auth/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test User",
    "password": "testpass123",
    "password_confirm": "testpass123"
  }'

# Output esperado:
# {"id":"<uuid>","email":"test@example.com","name":"Test User",...}
# ✅ SE VIR ISSO, registro funcionou!
```

```bash
# Teste 2: Login
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Output esperado:
# {"access":"<token>","refresh":"<token>"}
# COPIE o valor de "access" para usar abaixo
TOKEN="<token-copiado>"
```

```bash
# Teste 3: Setup Rooms (com token)
curl -X POST http://localhost:8000/api/v1/houses/rooms/setup_house/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rooms": ["cozinha", "banheiro", "quarto"]}'

# Output esperado:
# [{"id":"<uuid>","name":"cozinha",...},...]
# ✅ SE VIR LISTA DE ROOMS, está funcionando!
```

### 5.3 Acessar Dashboard no Browser

```
Abra: http://localhost:5173/

Deve fazer:
1. Redirecionar para /login (não autenticado)
2. Clicar "Criar Conta"
3. Preencher: Email, Nome, Senha
4. Clicar "Criar Conta"
5. Fazer login
6. Selecionar 3 cômodos → "Começar"
7. Ver dashboard (XP: 0, Nível: 1, Streak: 0)
8. Criar tarefa: "Lavar louça", Cozinha, Simples, Diária
9. Completar tarefa: Botão "+ 10 XP"
10. Dashboard atualiza: XP: 10, Streak: 1 ✅

SE VIR TUDO ISSO, LOCAL ESTÁ 100% FUNCIONANDO!
```

---

## ✅ Checklist Local

- [ ] Backend rodando (port 8000)
- [ ] Frontend rodando (port 5173)
- [ ] Criar conta (register)
- [ ] Login
- [ ] Setup rooms
- [ ] Criar tarefa
- [ ] Completar tarefa
- [ ] Ver XP/Streak atualizar
- [ ] Dashboard mostra corretamente

---

## 🎉 Se Tudo Funcionou

```
✅ No Rats MVP está 100% funcional localmente!

Você pode:
- Convidar amigos (mesma rede Wi-Fi)
- Usar URL: http://<seu-ip>:5173
- Testar no celular
- Iterar features
```

---

## 🐛 Troubleshooting

### Backend não inicia

```bash
# Erro: "ModuleNotFoundError: No module named 'django'"
# Solução:
source venv/bin/activate  # Verifique que venv está ativo
pip install Django

# Erro: "Address already in use"
# Solução:
python manage.py runserver 0.0.0.0:8001  # Use porta diferente
```

### Frontend não inicia

```bash
# Erro: "npm: command not found"
# Solução:
brew install node  # Mac
# ou
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -  # Linux
sudo apt-get install -y nodejs

# Erro: "VITE_API_URL is not defined"
# Solução:
cat .env.local  # Verifique se existe
# Se não existir, criar manualmente
```

### API retorna 404

```bash
# Erro: curl localhost:8000/api/v1/auth/ → 404
# Solução: Falta configurar URLs

# Editar no_rats/urls.py:
cat > no_rats/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/houses/', include('houses.urls')),
    path('api/v1/tasks/', include('tasks.urls')),
]
EOF

# Criar accounts/urls.py (vazio por enquanto, depois adicionar views)
touch accounts/urls.py
```

---

## Pronto para Próximo Passo?

Quando você confirmar que local está funcionando, avançamos para:

**STEP 6: Deploy Cloud (30 min)**
- Railway PostgreSQL (database)
- Railway Backend deployment
- Vercel Frontend deployment
- Testar ponta-a-ponta na cloud

Confirme quando estiver pronto: ✅ Local funcionando 100%
