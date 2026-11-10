# Banco de carrosséis pré-aprovados

Carrosséis gerados com a Cristiana no Claude (skills `carrossel-teniscerto` e
`carrossel-estilos`), revisados e aprovados por ela ANTES de entrar aqui.
Nos dias de carrossel (Seg/Sáb), o workflow `conteudo-do-dia.yml` roda
`carrossel_do_banco.py`, que consome o próximo aprovado da fila — só gera
na hora (modo antigo) se o banco estiver vazio.

## Estrutura

    fila.json              ordem de publicação + status
    <id>/                  ex.: 2026-11-c01/
      ├── slide-01.png...  slides na ordem (1080x1350 ou maior)
      └── post.json        {"assunto", "legenda", "tema", "estilo"}

## fila.json

    {"fila": [
      {"id": "2026-11-c01", "status": "aprovado",  "publicado_em": null},
      {"id": "2026-11-c02", "status": "publicado", "publicado_em": "2026-11-10"}
    ]}

- A ORDEM da lista é a ordem de publicação.
- `status`: `aprovado` (pronto) → `publicado` (consumido; nunca repete).
- Quando restarem ≤ 2 aprovados, o e-mail do dia sai com alerta "BANCO ACABANDO".

## Como reabastecer

Abrir o Claude no projeto e pedir: "vamos reabastecer o banco de carrosséis".
A sessão gera ~8 carrosséis com as skills, a Cristiana aprova um a um, e os
aprovados são commitados aqui com a fila atualizada.
