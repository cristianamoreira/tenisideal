# No Rats — Upload + Run (3 Cliques, 10 min)

Você já tem tudo no seu PC. Vamos só mandar pro GitHub e rodar na cloud.

---

## PASSO 1: GitHub (2 min)

### 1.1 Criar repo

1. Abra: https://github.com/new
2. Preencha:
   - Repository name: `no-rats`
   - Description: `No Rats - Gamified household tasks`
   - Public (sim)
   - ✅ NÃO marque "Initialize with README"
3. Clique "Create repository"

**✅ Repo criado vazio**

---

## PASSO 2: Upload dos arquivos (3 min)

### 2.1 Via GitHub Web (sem git)

1. Seu repo GitHub → Clique "Add file" → "Upload files"

2. Ou, arraste/solte a pasta completa:
   - Selecione tudo em: `~/no-rats-project`
   - Arraste pra janela do repo GitHub
   - Clique "Commit changes"

**✅ Arquivos no GitHub**

---

## PASSO 3: Abrir Codespaces (1 min)

1. Seu repo GitHub
2. Clique "< > Code" (verde)
3. Aba "Codespaces"
4. Clique "+ Create codespace on main"
5. Aguarde 3 min (vai abrir VS Code no browser)

**✅ Ambiente pronto**

---

## PASSO 4: Terminal 1 - Backend (3 min)

```bash
cd backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py load_achievements

python manage.py runserver 0.0.0.0:8000
```

**VS Code avisa: "Portar 8000?"**
- Clique "Yes"

**✅ Backend rodando**

---

## PASSO 5: Terminal 2 - Frontend (2 min)

Clique "+" no terminal pra novo:

```bash
cd frontend

npm install

npm run dev
```

**VS Code avisa: "Portar 5173?"**
- Clique "Yes"

**✅ Frontend rodando**

---

## PASSO 6: Testar (2 min)

VS Code → Aba "Ports" → Clique em 5173

Deve abrir dashboard. Fazer:
- ✅ Criar conta
- ✅ Login
- ✅ Setup rooms
- ✅ Criar tarefa
- ✅ Completar (XP atualiza)

**✅ TUDO FUNCIONA!**

---

## Resumo Rápido

| Passo | Ação | Tempo |
|-------|------|-------|
| 1 | Criar repo GitHub vazio | 2 min |
| 2 | Upload arquivos (drag/drop) | 3 min |
| 3 | Abrir Codespaces | 3 min |
| 4 | Backend: `python manage.py runserver` | 3 min |
| 5 | Frontend: `npm run dev` | 2 min |
| 6 | Testar no browser | 2 min |
| **Total** | | **15 min** |

---

## 🎯 Checklist

- [ ] Repo GitHub criado
- [ ] Arquivos uploaded
- [ ] Codespaces aberto
- [ ] Backend terminal rodando
- [ ] Frontend terminal rodando
- [ ] Browser mostra dashboard
- [ ] Criar conta funciona
- [ ] Tarefa + complete = XP atualiza

---

## Pronto?

Confirme quando:
1. ✅ Repo criado no GitHub
2. ✅ Arquivos uploaded
3. ✅ Codespaces aberto

Aí eu guio os próximos passos!
