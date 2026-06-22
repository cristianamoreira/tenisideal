# No Rats — Jeito Mais Fácil (Sem Instalar Nada)

Usar **GitHub Codespaces** = tudo roda na cloud.

---

## PASSO 1: Criar conta GitHub (2 min)

1. Abra: https://github.com/signup
2. Preencha:
   - Email
   - Senha (qualquer uma, segura)
   - Username (ex: seu_nome_123)
3. Clicar "Create account"
4. Verificar email
5. **✅ Conta criada**

---

## PASSO 2: Fazer Fork do Projeto (1 min)

Vou colocar código pronto no meu GitHub, você faz fork (cópia pra você).

**Você faz:**
1. Abra: https://github.com/seu_user/no-rats (seu repo)
   - Se não tiver repo criado, create no GitHub
   
2. Ou, se quiser usar um repo público já pronto:
   - Abra: https://github.com/exemplo/no-rats-mvp (exemplo)
   - Clique "Fork" (canto superior direito)
   - Pronto! Você tem cópia

**✅ Repo criado**

---

## PASSO 3: Abrir Codespaces (1 min)

1. No seu repo GitHub
2. Clique "Code" (botão verde)
3. Vá para aba "Codespaces"
4. Clique "+ Create codespace on main"
5. Aguarde 2-3 min (ambiente criando)
6. Vai abrir um VS Code no browser

**✅ Ambiente pronto no browser**

---

## PASSO 4: Rodar Backend no Codespaces (3 min)

No terminal (parte inferior do VS Code):

```bash
# Terminal já abre na raiz. Vá para backend:
cd backend

# Criar venv
python -m venv venv
source venv/bin/activate

# Instalar
pip install -r requirements.txt

# Migrations
python manage.py migrate
python manage.py load_achievements

# Rodar
python manage.py runserver 0.0.0.0:8000
```

**VS Code vai perguntar:** "Forward port 8000?"
- Clique "Yes"
- Vai abrir URL pública do backend

**✅ Backend rodando na cloud**

---

## PASSO 5: Rodar Frontend no Codespaces (2 min)

Novo terminal (clique "+" no terminal):

```bash
cd frontend

npm install

npm run dev
```

**VS Code vai perguntar:** "Forward port 5173?"
- Clique "Yes"
- Vai abrir URL pública do frontend

**✅ Frontend rodando na cloud**

---

## PASSO 6: Testar no Browser (3 min)

1. VS Code → aba "Ports"
2. Vê 2 URLs:
   - `localhost:5173` → Frontend
   - `localhost:8000` → Backend

3. Clique em "5173" → abre nova aba
4. Fazer:
   - Criar conta
   - Login
   - Setup rooms
   - Criar tarefa
   - Completar tarefa
   - Ver XP atualizar

**✅ Tudo funciona!**

---

## PASSO 7: Deploy Permanente na Cloud (15 min)

Codespaces é temporário. Depois vamos pra Railway/Vercel (permanente).

Mas por enquanto: **TUDO ESTÁ FUNCIONANDO NA CLOUD!**

---

## 🎯 Resumo

| Passo | O quê | Tempo |
|-------|-------|-------|
| 1 | Conta GitHub | 2 min |
| 2 | Fork projeto | 1 min |
| 3 | Abrir Codespaces | 3 min |
| 4 | Backend rodando | 3 min |
| 5 | Frontend rodando | 2 min |
| 6 | Testar no browser | 3 min |
| **Total** | | **14 min** |

---

## ⚠️ Se Ficar Preso

```
Erro ao fazer git clone?
→ Normalmente já está no Codespaces, só abra terminal

Erro ao fazer pip install?
→ Copiar erro completo e pedir ajuda

Erro ao npm run dev?
→ Tente: npm cache clean --force && npm install

Port 8000 não abre?
→ Ir em VS Code → Ports tab → adicionar 8000 manualmente
```

---

## 🎉 Depois de Tudo Funcionar

Quando você confirmar que browser mostra dashboard completo:

**Aí fazemos:**
1. ✅ Push para GitHub (código fica salvo)
2. ✅ Deploy permanente Railway + Vercel
3. ✅ URL fixa pra compartilhar com amigos

---

**Você quer tentar isso? É muito mais simples!**

1. Clique: https://github.com/signup (se não tiver conta)
2. Cria repo "no-rats"
3. Upload dos arquivos (ou git push se souber)
4. Abre Codespaces
5. Roda backend + frontend

**Confirme quando estiver pronto pro Passo 1!**
