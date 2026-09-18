#!/usr/bin/env python3
"""Puxa os eventos do funil do GA4 e atualiza painel_semanal_tenisideal.csv.

Reaproveita a MESMA conta de serviço do Google já usada pelos outros scripts
(credenciais.json / secret GOOGLE_CREDENTIALS). Não usa biblioteca extra do GA:
fala direto com a Analytics Data API (v1beta) via requests.

O que faz:
- Busca, por dia, a contagem dos eventos do funil (first_visit, quiz_started,
  quiz_completed, click_afiliado, email_capturado).
- Agrupa por semana começando na segunda-feira.
- Preenche as colunas B-F de cada semana no painel_semanal_tenisideal.csv,
  preservando o cabeçalho, a linha de Exemplo, as colunas de fórmula (% ...)
  e o que você já escreveu em Postagens/Observações.
- Imprime um resumo dos últimos 28 dias com as taxas do funil (pra decisão
  rápida de impulsionar ou não).

Requisitos (setup uma vez só — ver README no fim do arquivo):
- GA4_PROPERTY_ID : o Property ID NUMÉRICO (ex.: 123456789), NÃO o G-XXXX.
- credenciais.json: conta de serviço com acesso de Leitor na propriedade GA4.
- API "Google Analytics Data API" ativada no projeto do Google Cloud.

Uso:
    GA4_PROPERTY_ID=123456789 python3 puxar_metricas_ga4.py
    # opcional: DIAS=90 para puxar um período maior (padrão 60)
"""
import csv
import os
import sys
from datetime import date, datetime, timedelta

import requests
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

EVENTOS = ["first_visit", "quiz_started", "quiz_completed",
           "click_afiliado", "email_capturado"]
# ordem das colunas B..F no painel
COLUNAS_EVENTO = {
    "first_visit": 1,        # Visitas
    "quiz_started": 2,       # Quiz iniciados
    "quiz_completed": 3,     # Quiz completos
    "click_afiliado": 4,     # Cliques COMPRAR
    "email_capturado": 5,    # Emails capturados
}
PAINEL = "painel_semanal_tenisideal.csv"
API = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"


def _segunda(d):
    """Segunda-feira da semana de uma data (date)."""
    return d - timedelta(days=d.weekday())


def puxar(property_id, dias):
    creds = Credentials.from_service_account_file(
        "credenciais.json",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    creds.refresh(GoogleAuthRequest())

    body = {
        "dateRanges": [{"startDate": f"{dias}daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "date"}, {"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {"values": EVENTOS},
            }
        },
        "limit": 100000,
    }
    resp = requests.post(
        API.format(pid=property_id),
        headers={"Authorization": f"Bearer {creds.token}"},
        json=body, timeout=60)
    if resp.status_code != 200:
        sys.exit(f"Erro do GA4 ({resp.status_code}): {resp.text[:500]}")

    # dia (date) -> {evento: contagem}
    por_dia = {}
    for row in resp.json().get("rows", []):
        dia = row["dimensionValues"][0]["value"]       # YYYYMMDD
        evt = row["dimensionValues"][1]["value"]
        n = int(row["metricValues"][0]["value"])
        d = datetime.strptime(dia, "%Y%m%d").date()
        por_dia.setdefault(d, {}).setdefault(evt, 0)
        por_dia[d][evt] += n

    # agrupa por segunda-feira
    por_semana = {}
    for d, evts in por_dia.items():
        seg = _segunda(d)
        alvo = por_semana.setdefault(seg, {e: 0 for e in EVENTOS})
        for e, n in evts.items():
            alvo[e] = alvo.get(e, 0) + n
    return por_semana


# Layout da linha: A=semana, B..F=eventos, G..I=%, J=postagens, K=observações.
LARGURA = 11
COL_PCT = 6          # G, H, I
COL_POSTAGENS = 9    # J
COL_OBS = 10         # K


def _pct(a, b):
    """Percentual pronto pra leitura, em pt-BR ('11,5%'). Vazio se não dá pra dividir."""
    if not b:
        return ""
    return f"{a / b * 100:.1f}".replace(".", ",") + "%"


def _num(v):
    try:
        return int(str(v).strip() or 0)
    except ValueError:
        return 0


def _e_resto_de_formula(campo):
    """O painel antigo gravava fórmulas sem escapar a vírgula, então cada fórmula
    virava vários campos ao reler. Reconhece esses cacos pra poder descartá-los."""
    c = campo.strip()
    return "IF(" in c or (c.endswith(")") and "/" in c)


def _limpar(row):
    """Normaliza uma linha do painel para [semana, 5 eventos, postagens, obs]."""
    campos = [c for c in row if not _e_resto_de_formula(c)]
    while len(campos) < 8:
        campos.append("")
    if len(campos) > 8:                      # sobrou lixo no meio: fica com as pontas
        campos = campos[:6] + campos[-2:]
    return campos


def _monta(semana, eventos, postagens="", obs=""):
    v, qs, qc, cl, em = (eventos.get(e, 0) for e in EVENTOS)
    return [semana, v, qs, qc, cl, em,
            _pct(qs, v), _pct(qc, qs), _pct(cl, qc), postagens, obs]


def atualizar_painel(por_semana):
    if not os.path.exists(PAINEL):
        print(f"(aviso) {PAINEL} não encontrado — pulei a atualização do painel.")
        return 0
    with open(PAINEL, newline="", encoding="utf-8") as f:
        linhas = list(csv.reader(f))
    if not linhas:
        print(f"(aviso) {PAINEL} está vazio — pulei a atualização.")
        return 0

    cabecalho, exemplo, por_seg = linhas[0][:LARGURA], [], {}
    while len(cabecalho) < LARGURA:
        cabecalho.append("")

    for row in linhas[1:]:
        if not row or not row[0].strip():
            continue
        semana, *resto = _limpar(row)
        eventos = dict(zip(EVENTOS, (_num(x) for x in resto[:5])))
        postagens, obs = resto[5], resto[6]
        if semana.strip().lower().startswith("exemplo"):
            exemplo.append(_monta(semana, eventos, postagens, obs))
            continue
        try:
            d = datetime.strptime(semana.strip(), "%Y-%m-%d").date()
        except ValueError:
            continue
        # o painel foi criado com rótulos em terça; normaliza p/ a segunda da semana
        seg = _segunda(d)
        antigo = por_seg.get(seg)
        if antigo:                               # 2 linhas na mesma semana: funde
            eventos = {e: max(eventos[e], antigo["eventos"][e]) for e in EVENTOS}
            postagens = postagens or antigo["postagens"]
            obs = obs or antigo["obs"]
        por_seg[seg] = {"eventos": eventos, "postagens": postagens, "obs": obs}

    # cria as linhas das semanas que têm dados mas ainda não estão no painel
    for seg in por_semana:
        por_seg.setdefault(seg, {"eventos": {e: 0 for e in EVENTOS},
                                 "postagens": "", "obs": ""})

    atualizadas = 0
    for seg, info in por_seg.items():
        dados = por_semana.get(seg)
        if not dados:
            continue
        info["eventos"] = {e: dados.get(e, 0) for e in EVENTOS}
        atualizadas += 1

    saida = [cabecalho] + exemplo + [
        _monta(seg.isoformat(), por_seg[seg]["eventos"],
               por_seg[seg]["postagens"], por_seg[seg]["obs"])
        for seg in sorted(por_seg)
    ]
    with open(PAINEL, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(saida)
    return atualizadas


def resumo_28d(por_semana):
    hoje = date.today()
    limite = _segunda(hoje - timedelta(days=27))
    tot = {e: 0 for e in EVENTOS}
    for seg, dados in por_semana.items():
        if seg >= limite:
            for e in EVENTOS:
                tot[e] += dados.get(e, 0)

    def pct(a, b):
        return f"{(a / b * 100):.1f}%" if b else "—"

    v = tot["first_visit"]
    qs = tot["quiz_started"]
    qc = tot["quiz_completed"]
    cl = tot["click_afiliado"]
    em = tot["email_capturado"]

    print("\n=== FUNIL — últimos ~28 dias ===")
    print(f"  Visitas (first_visit)      : {v}")
    print(f"  Quiz iniciados             : {qs}   ({pct(qs, v)} das visitas)")
    print(f"  Quiz completos             : {qc}   ({pct(qc, qs)} de quem iniciou)")
    print(f"  Cliques COMPRAR            : {cl}   ({pct(cl, qc)} de quem completou)")
    print(f"  E-mails capturados         : {em}   ({pct(em, v)} das visitas)")
    print(f"  Conversão visita -> clique : {pct(cl, v)}")
    print("=================================\n")


def main():
    pid = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not pid:
        sys.exit("Faltou GA4_PROPERTY_ID (o número da propriedade, ex.: 123456789). "
                 "Pegue em GA4 > Administrador > Configurações da propriedade > ID da propriedade.")
    dias = int(os.environ.get("DIAS", "60"))
    por_semana = puxar(pid, dias)
    if not por_semana:
        print("Nenhum evento retornado no período. Confira o Property ID e o acesso da conta de serviço.")
        return
    n = atualizar_painel(por_semana)
    print(f"Painel atualizado: {n} semana(s) preenchida(s) em {PAINEL}.")
    resumo_28d(por_semana)


if __name__ == "__main__":
    main()
