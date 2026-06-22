# No Rats — Click by Click (Pra Leigo)

Vou descrever cada clique. Copie EXATAMENTE.

---

## ✅ PASSO 1: Criar Repo Novo (1 min)

**1. Clique aqui:**
```
https://github.com/new
```

**2. Você vai ver um formulário. Preencha:**
```
Repository name: no-rats
Description: Gamified household tasks MVP
Public: ✅ (marque)
Initialize: ❌ (NÃO marque nada)
```

**3. Clique botão verde: "Create repository"**

**✅ Pronto! Você vai pra página do repo vazio**

---

## ✅ PASSO 2: Upload dos Arquivos (2 min)

**1. Nessa página (seu repo vazio), clique:**
```
"Add file" (botão com + sign)
```

**2. Selecione:**
```
"Upload files"
```

**3. Você vai ver uma área cinza com:**
```
"drag files here or click to select"
```

**4. Clique nessa área cinza**

**5. Sua janela de pasta vai abrir. Navegue pra:**
```
~/no-rats-project
```

**6. Selecione TUDO (Ctrl+A ou Cmd+A)**

**7. Clique "Open" (ou "Select")**

**8. Aguarde upload (alguns segundos)**

**9. Embaixo vai ter um botão: "Commit changes"**
```
Clique nele
```

**✅ Seus arquivos estão no GitHub!**

---

## ✅ PASSO 3: Abrir Codespaces (1 min)

**1. Seu repo GitHub, clique botão verde:**
```
"< > Code"
```

**2. Vai abrir um menu. Procure aba:**
```
"Codespaces"
```

**3. Clique em:**
```
"+ Create codespace on main"
```

**4. Aguarde 3-5 minutos (tela toda preta com barrinhas de carregamento)**

**5. Vai abrir VS Code no browser (tela com editor, terminal embaixo)**

**✅ Está pronto! Você tem terminal aberto**

---

## ✅ PASSO 4: Backend Rodando (3 min)

**No terminal (parte inferior), copie/cole TUDO de uma vez:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_achievements
python manage.py runserver 0.0.0.0:8000
```

**Vai aparecer várias linhas. No final deve dizer:**
```
Starting development server at http://127.0.0.1:8000/
```

**VS Code vai perguntar na janelinha no canto:**
```
"Port 8000 is already in use. Forward it?"
```

**Clique: "Yes"**

**✅ Backend rodando!**

---

## ✅ PASSO 5: Frontend Rodando (2 min)

**1. No VS Code, embaixo do terminal, clique no "+"**

**2. Novo terminal vai abrir**

**3. Copie/cole TUDO:**

```bash
cd frontend
npm install
npm run dev
```

**Vai demorar 1-2 min instalando. No final vai dizer:**
```
  ➜  Local:   http://localhost:5173/
```

**VS Code pergunta:**
```
"Port 5173 is already in use. Forward it?"
```

**Clique: "Yes"**

**✅ Frontend rodando!**

---

## ✅ PASSO 6: Testar no Browser (2 min)

**1. VS Code, esquerda, clique em:**
```
"Ports" (ou procure aba de Ports)
```

**2. Você vai ver 2 linhas:**
```
5173 (http://localhost:5173)
8000 (http://localhost:8000)
```

**3. Clique na linha do 5173**

**4. Vai abrir nova aba do browser com seu site!**

**5. Fazer:**
- Clique "Sign Up"
- Preencha: Email, Nome, Senha
- Clique "Create Account"
- Clique "Login"
- Preencha: Email, Senha (mesmos)
- Clique "Login"
- Selecione 3 cômodos (Cozinha, Banheiro, Quarto)
- Clique "Começar"
- Clique "+ Nova Tarefa"
- Preencha: "Lavar louça", Cozinha, Simples
- Clique "Criar Tarefa"
- Clique "+ 10 XP"
- **Dashboard atualiza: XP agora é 10, Streak é 1**

**✅ TUDO FUNCIONANDO!**

---

## 📋 Resumo dos 6 Passos

```
1. github.com/new → repo "no-rats" → Create ✅
2. Add file → Upload files → seleciona ~/no-rats-project → Commit ✅
3. Code → Codespaces → Create → aguarda 5 min ✅
4. Terminal: cd backend + python setup + runserver ✅
5. Terminal: cd frontend + npm + npm run dev ✅
6. Browser: 5173 → criar conta → login → task → complete ✅
```

---

## 🚨 Se Travar em Algum Passo

**"Não acho o botão X"**
→ Me manda print (F12) que acho pra você

**"Terminal com erro"**
→ Copia/cola o erro aqui

**"Página não abre"**
→ Aguarda mais 1-2 min (às vezes demora)

---

## ✅ Quando Tudo Funcionar

Você confirma comigo:
```
PASSO 1: ✅ Repo criado
PASSO 2: ✅ Arquivos uploaded
PASSO 3: ✅ Codespaces aberto
PASSO 4: ✅ Backend rodando (vê "Starting dev server")
PASSO 5: ✅ Frontend rodando (vê "localhost:5173")
PASSO 6: ✅ Browser: dashboard completo, tarefa funciona
```

**Aí fazemos o deploy cloud permanente!**

---

**Pode começar? Começa pelo PASSO 1:**

```
https://github.com/new
```

Confirma aqui quando terminar cada passo! 🎯
