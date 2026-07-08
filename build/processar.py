#!/usr/bin/env python3
"""Processa todos_7d.json -> métricas por grupo, agregação por tipo (relatório exec), fases.
Também dumpa textos externos por tipo para classificação de assuntos."""
import json, re, unicodedata
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import os
SCR = os.path.dirname(os.path.abspath(__file__))
AGORA = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
INTERNOS_EXTRA = {"bruna zanella", "sa"}

# SLA em horas; base leadtime|resposta; None = sem SLA
SLA = {
    "Seazone Oficial": (21*24, "21 dias", "leadtime"),
    "Conselho Fiscal": (1, "1h", "resposta"),
    "Obra": (6, "6h", "resposta"),
    "Condomínio": (1, "1h", "resposta"),
    "Engenharia": (1, "1h", "resposta"),
    "Jurídico": (1, "1h", "resposta"),
}
# fases_raw.json já vem com a fase final computada (Pré-obra/Obra/Operação),
# derivada de building_status + delivery_status + approved_operation_start_date.

def is_seazone(m):
    if m.get("from_me"): return True
    nm = (m.get("sender_name") or "").lower().strip()
    return ("seazone" in nm) or ("pmo" in nm) or (nm in INTERNOS_EXTRA)
def parse(ts):
    try: return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S %z")
    except: return None
def business_hours(start, end):
    if not start or not end or end <= start: return 0.0
    t, c = 0.0, start
    while c < end:
        if c.weekday() < 5:
            s = max(c, c.replace(hour=9, minute=0, second=0, microsecond=0))
            e = min(end, c.replace(hour=18, minute=0, second=0, microsecond=0))
            if e > s: t += (e - s).total_seconds()/3600
        c = (c + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return t
def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
def tokens(s):
    s = strip_acc(s).upper()
    s = re.sub(r"\b(SPE|LTDA|EMPREENDIMENTO|EMPREENDIMENTOS|IMOBILIARIOS|CONSTRUCOES|CONSTRUCAO|INCORPORACAO|APART|HOTEL|SPOT|E|DE|DA|DAS|DO|DOS|II|III)\b", " ", s)
    return set(re.findall(r"[A-Z0-9]+", s))

# --- fase por spot ---
fases_raw = json.load(open(f"{SCR}/fases_raw.json"))
razao_tokens = {rz: tokens(rz) for rz in fases_raw}
def fase_do_spot(spot):
    st = tokens(spot)
    best, bestscore = None, 0
    for rz, rtk in razao_tokens.items():
        sc = len(st & rtk)
        # bônus se II/III casam
        spot_u = strip_acc(spot).upper(); rz_u = strip_acc(rz).upper()
        if (" II" in spot_u) != (" II" in rz_u): sc -= 0.5
        if sc > bestscore: bestscore, best = sc, rz
    if best and bestscore >= 1:
        return fases_raw[best], best
    return "?", None

# --- métricas por grupo ---
data = json.load(open(f"{SCR}/todos_7d.json"))
grupos = []
ext_por_tipo = defaultdict(list)  # tipo -> textos externos (para assuntos)
for cid, g in data.items():
    tipo = g["tipo"]; sla = SLA.get(tipo)
    msgs = sorted(g["messages"], key=lambda m: m.get("timestamp") or "")
    ext = [m for m in msgs if not is_seazone(m)]
    for m in ext:
        t = " ".join((m.get("text") or "").split())
        if t: ext_por_tipo[tipo].append((g["spot"], t[:200]))
    lastts = parse(g.get("last_message_timestamp"))
    lead_h = (AGORA - lastts).total_seconds()/3600 if lastts else None
    # tempo sem resposta (horas comerciais)
    resp, pend, i = [], [], 0
    while i < len(msgs):
        if not is_seazone(msgs[i]):
            start = parse(msgs[i]["timestamp"]); j = i
            while j < len(msgs) and not is_seazone(msgs[j]): j += 1
            if j < len(msgs): resp.append(business_hours(start, parse(msgs[j]["timestamp"]))); i = j+1
            else: pend.append(business_hours(start, AGORA)); i = j
        else: i += 1
    max_espera = max(resp + pend) if (resp or pend) else None
    fase, _ = fase_do_spot(g["spot"])
    rec = dict(spot=g["spot"], tipo=tipo, fase=fase, total=len(msgs), sea=len(msgs)-len(ext), ext=len(ext),
               lead_h=lead_h, max_espera=max_espera, resp_med=(sum(resp)/len(resp)) if resp else None,
               n_resp=len(resp), sla=sla)
    if sla:
        sla_h, _, base = sla
        if base == "leadtime":
            rec["realizado"] = lead_h; rec["fora"] = (lead_h is not None and lead_h > sla_h)
        else:
            rec["realizado"] = max_espera; rec["fora"] = (max_espera is not None and max_espera > sla_h)
    else:
        rec["realizado"] = lead_h; rec["fora"] = None
    grupos.append(rec)

# --- agregação por tipo (relatório executivo) ---
por_tipo = {}
for tipo in set(g["tipo"] for g in grupos):
    gs = [g for g in grupos if g["tipo"] == tipo]
    sla = SLA.get(tipo)
    fora = [g for g in gs if g.get("fora")]
    # pior: maior realizado entre os com valor
    com_val = [g for g in gs if g.get("realizado") is not None]
    pior = max(com_val, key=lambda g: g["realizado"]) if com_val else None
    por_tipo[tipo] = dict(tipo=tipo, n=len(gs), sla=(sla[1] if sla else "—"),
        base=(sla[2] if sla else "—"), n_fora=(len(fora) if sla else None),
        pior_spot=(pior["spot"] if pior else None), pior_val=(pior["realizado"] if pior else None))

json.dump({"grupos": grupos, "por_tipo": por_tipo}, open(f"{SCR}/metricas.json", "w"), ensure_ascii=False)
json.dump({k: v for k, v in ext_por_tipo.items()}, open(f"{SCR}/ext_por_tipo.json", "w"), ensure_ascii=False)

# resumo
print("=== RELATÓRIO EXECUTIVO POR TIPO ===")
order = ["Seazone Oficial","Conselho Fiscal","Obra","Condomínio","Engenharia","Jurídico"]
order += [t for t in por_tipo if t not in order]
for t in order:
    if t not in por_tipo: continue
    v = por_tipo[t]
    fora = f"{v['n_fora']} fora SLA" if v['n_fora'] is not None else "sem SLA"
    pv = v['pior_val']
    pvs = (f"{pv/24:.1f}d" if (v['base']=='leadtime' and pv is not None) else (f"{pv:.1f}h úteis" if pv is not None else "—"))
    print(f"  {t:<18} n={v['n']:>2} SLA={v['sla']:<7} {fora:<12} pior: {v['pior_spot']} ({pvs})")
nfases = defaultdict(int)
for g in grupos: nfases[g["fase"]] += 1
print("\nfases:", dict(nfases))
tot_ext = sum(len(v) for v in ext_por_tipo.values())
print("textos externos p/ assuntos:", tot_ext)
