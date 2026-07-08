#!/usr/bin/env python3
"""Aba Monitoramento v7: cards executivos + matriz por fase (colunas) com detalhe INLINE compacto
(abre no próprio card do spot) + assuntos. Correções Bluezone (cores por tema, faróis forma+aria, foco)."""
import json, html, os
from collections import defaultdict

import os
SCR = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(f"{SCR}/metricas.json"))
grupos, por_tipo = M["grupos"], M["por_tipo"]
assuntos = json.load(open(f"{SCR}/assuntos_top10.json")) if os.path.exists(f"{SCR}/assuntos_top10.json") else []
ader = json.load(open(f"{SCR}/aderencia.json")) if os.path.exists(f"{SCR}/aderencia.json") else {}

def esc(s): return html.escape(str(s))
def fmt(h, base="resposta"):
    if h is None: return "—"
    if base == "leadtime": return f"{h/24:.0f}d" if h >= 24 else f"{h:.0f}h"
    if h < 1: return f"{h*60:.0f}min"
    return f"{h:.1f}h"
def ader_cell(spot):
    a = ader.get(spot)
    if not a: return '<span class="plz-ad plz-dim" aria-hidden="true">—</span>'
    if a["sem_grupo"]: return '<span class="plz-ad plz-ze" role="img" aria-label="aderência: sem grupo">s/g</span>'
    p = a["pct"]; c = "plz-hi" if p >= 60 else ("plz-md" if p >= 40 else "plz-lo")
    return f'<span class="plz-ad {c}" role="img" aria-label="aderência {p} por cento">{p}%</span>'

TIPOS_SLA = ["Seazone Oficial", "Conselho Fiscal", "Obra", "Condomínio", "Engenharia", "Jurídico"]
ABREV3 = {"Seazone Oficial": "Ofi", "Conselho Fiscal": "Cns", "Obra": "Obr", "Condomínio": "Cnd", "Engenharia": "Eng", "Jurídico": "Jur"}
SEM_SLA = [t for t in por_tipo if t not in TIPOS_SLA]
FASES = ["Pré-obra", "Obra", "Operação", "?"]
GRID = "grid-template-columns:150px 24px 44px repeat(5,24px) 30px 1fr"

subj_por_spot = defaultdict(list)
for a in assuntos:
    for s in a.get("spots", []): subj_por_spot[s].append(a)

def card(t):
    v = por_tipo.get(t)
    if not v: return ""
    base = v["base"]
    if v["n_fora"] is None:
        num = f'<div class="plz-kpi-n plz-dim">{v["n"]}</div><div class="plz-kpi-s">grupos · sem SLA</div>'
    else:
        cor = "plz-red" if v["n_fora"] else "plz-grn"
        pv = fmt(v["pior_val"], base) if v["pior_val"] is not None else "—"
        pior = f'<div class="plz-kpi-p">pior: {esc(v["pior_spot"])} · {pv}</div>' if v["n_fora"] else '<div class="plz-kpi-p">todos no prazo</div>'
        num = f'<div class="plz-kpi-n {cor}">{v["n_fora"]}<span>/{v["n"]}</span></div><div class="plz-kpi-s">fora da SLA · {v["sla"]}</div>{pior}'
    return f'<div class="plz-kpi"><div class="plz-kpi-t">{esc(t)}</div>{num}</div>'
cards = "".join(card(t) for t in TIPOS_SLA)
cards_sem = "".join(card(t) for t in SEM_SLA)

by_spot = defaultdict(list)
for g in grupos: by_spot[g["spot"]].append(g)
spot_fase = {g["spot"]: g["fase"] for g in grupos}

def detalhe_inline(s):
    gs = sorted(by_spot[s], key=lambda g: TIPOS_SLA.index(g["tipo"]) if g["tipo"] in TIPOS_SLA else 99)
    linhas = ""
    for g in gs:
        lead = fmt(g["lead_h"], "leadtime")
        resp = (fmt(g["resp_med"]) + " / " + fmt(g.get("max_espera"))) if (g["n_resp"] or g.get("max_espera")) else "—"
        sit = ('<span class="plz-chip plz-dim">sem SLA</span>' if g.get("fora") is None
               else f'<span class="plz-chip {"plz-ze" if g["fora"] else "plz-hi"}">{"fora" if g["fora"] else "ok"}</span>')
        linhas += (f'<div class="plz-grp"><div class="plz-grln"><b>{esc(g["tipo"])}</b> {sit}</div>'
                   f'<div class="plz-grsub">últ {lead} · {g["total"]} msgs ({g["sea"]}S/{g["ext"]}E) · resposta {resp}</div></div>')
    subj = subj_por_spot.get(s, [])
    subj_html = ""
    if subj:
        lis = "".join(f'<li>{esc(a["titulo"])} <span class="plz-dim">({esc((a.get("relevancia") or "").lower())})</span></li>' for a in subj[:6])
        subj_html = f'<div class="plz-subj"><b>Assuntos:</b><ul>{lis}</ul></div>'
    return f'<div class="plz-detail">{linhas}{subj_html}</div>'

def spot_block(s):
    gmap = {}
    for g in by_spot[s]:
        k = g["tipo"]
        if k not in gmap or (g.get("fora") and not gmap[k].get("fora")): gmap[k] = g
    cells = []
    for t in TIPOS_SLA:
        g = gmap.get(t)
        if not g: cells.append('<span class="plz-dot plz-gry" aria-hidden="true">·</span>')
        elif g.get("fora"): cells.append(f'<span class="plz-dot plz-red" role="img" aria-label="{esc(t)}: fora da SLA">▲</span>')
        else: cells.append(f'<span class="plz-dot plz-grn" role="img" aria-label="{esc(t)}: ok">●</span>')
    cells.insert(1, ader_cell(s))
    dots = "".join(cells)
    nfora = sum(1 for g in gmap.values() if g.get("fora"))
    badge = f'<span class="plz-badge plz-ze">{nfora}</span>' if nfora else '<span class="plz-badge plz-hi">ok</span>'
    return (f'<details class="plz-spot"><summary class="plz-srow" style="{GRID}">'
            f'<span class="plz-sname">{esc(s)}</span>{dots}{badge}</summary>{detalhe_inline(s)}</details>')

def fase_block(f):
    spots = sorted({s for s, ff in spot_fase.items() if ff == f})
    if not spots: return ""
    fora_spots = sum(1 for s in spots if any(g.get("fora") for g in by_spot[s]))
    labels = f'<span>{ABREV3["Seazone Oficial"]}</span><span>Ofi&nbsp;%</span>' + "".join(f'<span>{ABREV3[t]}</span>' for t in TIPOS_SLA[1:])
    head = f'<div class="plz-mhead" style="{GRID}"><span>{f} · {len(spots)} · {fora_spots} fora</span>{labels}<span></span></div>'
    return f'<div class="plz-fasecol">{head}' + "".join(spot_block(s) for s in spots) + '</div>'
fases_html = '<div class="plz-fases">' + "".join(fase_block(f) for f in FASES) + '</div>'

relcls = {"alta": "plz-ze", "media": "plz-lo", "média": "plz-lo", "baixa": "plz-md"}
items = ""
for i, a in enumerate(assuntos[:10], 1):
    rel = (a.get("relevancia") or "media").lower()
    items += (f'<div class="plz-ass"><div class="plz-rank">{i}</div><div>'
        f'<div class="plz-atitle">{esc(a.get("titulo",""))} <span class="plz-chip {relcls.get(rel,"plz-lo")}">{esc(rel)}</span> '
        f'<span class="plz-dim" style="font-size:10.5px">{a.get("mencoes","?")} menç.</span></div>'
        f'<div class="plz-adesc">{esc(a.get("descricao",""))}</div>'
        f'<div class="plz-agrp">{esc(" · ".join(a.get("spots", [])[:5]))}</div></div></div>')

CSS = """<style id="plz-style">
#tab-pl{padding:4px 20px 28px;
 --plz-danger:#B91C1C;--plz-danger-bg:rgba(185,28,28,.12);--plz-success:#15803D;--plz-success-bg:rgba(21,128,61,.12);
 --plz-warn:#92400E;--plz-warn-bg:rgba(146,64,14,.12);--plz-info:#0E7490;--plz-info-bg:rgba(14,116,144,.12)}
@media(prefers-color-scheme:dark){#tab-pl{--plz-danger:#F87171;--plz-danger-bg:rgba(248,113,113,.16);--plz-success:#4ADE80;--plz-success-bg:rgba(74,222,128,.16);--plz-warn:#FBBF24;--plz-warn-bg:rgba(251,191,36,.16);--plz-info:#38BDF8;--plz-info-bg:rgba(56,189,248,.16)}}
:root[data-theme="dark"] #tab-pl{--plz-danger:#F87171;--plz-danger-bg:rgba(248,113,113,.16);--plz-success:#4ADE80;--plz-success-bg:rgba(74,222,128,.16);--plz-warn:#FBBF24;--plz-warn-bg:rgba(251,191,36,.16);--plz-info:#38BDF8;--plz-info-bg:rgba(56,189,248,.16)}
:root[data-theme="light"] #tab-pl{--plz-danger:#B91C1C;--plz-danger-bg:rgba(185,28,28,.12);--plz-success:#15803D;--plz-success-bg:rgba(21,128,61,.12);--plz-warn:#92400E;--plz-warn-bg:rgba(146,64,14,.12);--plz-info:#0E7490;--plz-info-bg:rgba(14,116,144,.12)}
#tab-pl .plz-hdt{font-size:16px;font-weight:600;margin:14px 0 2px}#tab-pl .plz-hds{font-size:11px;color:var(--muted)}
#tab-pl h3.plz-h{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:22px 0 8px;font-weight:700}
#tab-pl .plz-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(124px,1fr));gap:9px}
#tab-pl .plz-kpi{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:8px 10px}
#tab-pl .plz-kpi-t{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase}
#tab-pl .plz-kpi-n{font-size:21px;font-weight:800;line-height:1.1;margin-top:2px}#tab-pl .plz-kpi-n span{font-size:13px;color:var(--muted);font-weight:600}
#tab-pl .plz-red{color:var(--plz-danger)}#tab-pl .plz-grn{color:var(--plz-success)}#tab-pl .plz-gry{color:var(--border)}
#tab-pl .plz-kpi-s{font-size:10.5px;color:var(--muted);margin-top:1px}#tab-pl .plz-kpi-p{font-size:10.5px;margin-top:5px;opacity:.9}
#tab-pl .plz-fases{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
#tab-pl .plz-fasecol{flex:1 1 430px;min-width:0}
#tab-pl .plz-mhead{display:grid;gap:5px;padding:8px 12px 2px 26px;font-size:9px;color:var(--muted);font-weight:700;text-transform:uppercase;border-bottom:2px solid var(--border)}
#tab-pl .plz-mhead span{text-align:center}#tab-pl .plz-mhead span:first-child{text-align:left;font-size:11.5px;text-transform:none}
#tab-pl .plz-spot{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-top:5px}
#tab-pl .plz-spot[open]{border-color:var(--teal)}
#tab-pl .plz-spot summary{list-style:none;cursor:pointer;padding:7px 12px 7px 26px;position:relative}
#tab-pl .plz-spot summary::-webkit-details-marker{display:none}
#tab-pl .plz-spot summary:hover{background:var(--rhov)}
#tab-pl .plz-spot summary:focus-visible{outline:2px solid var(--teal);outline-offset:-2px;border-radius:8px}
#tab-pl .plz-srow{display:grid;gap:5px;align-items:center}
#tab-pl .plz-sname{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#tab-pl .plz-sname::before{content:"▸";color:var(--muted);font-size:10px;position:absolute;left:12px}
#tab-pl .plz-spot[open] .plz-sname::before{content:"▾"}
#tab-pl .plz-dot{text-align:center;font-size:12px}
#tab-pl .plz-ad{font-size:9.5px;font-weight:700;text-align:center;padding:1px 3px;border-radius:9999px}
#tab-pl .plz-badge{font-size:10px;font-weight:700;text-align:center;padding:1px 0;border-radius:9999px}
#tab-pl .plz-badge.plz-ze{background:var(--plz-danger-bg);color:var(--plz-danger)}#tab-pl .plz-badge.plz-hi{background:var(--plz-success-bg);color:var(--plz-success)}
#tab-pl .plz-detail{padding:2px 12px 10px 26px;border-top:1px solid var(--border);margin-top:2px}
#tab-pl .plz-grp{padding:6px 0;border-bottom:1px solid var(--border)}#tab-pl .plz-grp:last-of-type{border-bottom:none}
#tab-pl .plz-grln{font-size:12px}#tab-pl .plz-grsub{font-size:11px;color:var(--muted);margin-top:1px}
#tab-pl .plz-subj{margin-top:8px;font-size:12px}#tab-pl .plz-subj ul{margin:4px 0 0 16px}#tab-pl .plz-subj li{margin:2px 0}
#tab-pl .plz-num{text-align:right;font-variant-numeric:tabular-nums}#tab-pl .plz-dim{color:var(--muted)}
#tab-pl .plz-chip{display:inline-block;padding:1px 8px;border-radius:9999px;font-size:10px;font-weight:700;white-space:nowrap}
#tab-pl .plz-hi{background:var(--plz-success-bg);color:var(--plz-success)}#tab-pl .plz-md{background:var(--plz-info-bg);color:var(--plz-info)}
#tab-pl .plz-lo{background:var(--plz-warn-bg);color:var(--plz-warn)}#tab-pl .plz-ze{background:var(--plz-danger-bg);color:var(--plz-danger)}
#tab-pl .plz-assg{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:2px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:4px}
#tab-pl .plz-ass{display:flex;gap:10px;padding:9px 11px}
#tab-pl .plz-rank{flex:0 0 22px;height:22px;border-radius:9999px;background:var(--navy);color:var(--teal);font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center}
#tab-pl .plz-atitle{font-weight:600;font-size:12.5px}#tab-pl .plz-adesc{color:var(--muted);font-size:11.5px;margin:2px 0 3px;line-height:1.4}
#tab-pl .plz-agrp{color:var(--muted);font-size:10.5px;font-weight:600;opacity:.85}
#tab-pl details.plz-more{margin-top:8px}#tab-pl details.plz-more>summary{cursor:pointer;font-size:12px;color:var(--muted);font-weight:600}
#tab-pl .plz-note{font-size:11px;color:var(--muted);line-height:1.55;margin-top:12px}
</style>"""

FRAG = CSS + f"""
<div id="tab-pl" class="tp active">
  <h2 class="plz-hdt">Monitoramento dos Grupos — Todos os Spots</h2>
  <div class="plz-hds">Timelines (WhatsApp) · últimos 7 dias · {len(grupos)} grupos · atualizado 07/07/2026 · clique num spot para detalhes</div>

  <h3 class="plz-h">📋 Relatório executivo — fora da SLA por tipo</h3>
  <div class="plz-cards">{cards}</div>
  <details class="plz-more"><summary>+ tipos sem SLA definida (Gestão SPE, Aprovação, Outros…)</summary>
  <div class="plz-cards" style="margin-top:8px">{cards_sem}</div></details>

  <h3 class="plz-h">🏗️ Por fase — faróis por tipo (Ofi·Cns·Obr·Cnd·Eng·Jur) + aderência · clique no spot</h3>
  {fases_html}
  <div class="plz-note">● ok · ▲ fora da SLA · · sem grupo. <b>Ofi %</b> = aderência WPP do grupo Oficial (🟢 ≥60% · 🔵 ≥40% · 🟠 &lt;40% · s/g). <b>Fase</b> vem do estágio real de entrega/operação do cadastro SZI (habite-se + início de operação) — por isso Urubici está em Operação. Tempo de resposta em horas úteis (9h–18h, seg–sex).</div>

  <h3 class="plz-h">🔥 Top 10 assuntos da parte externa (todos os spots)</h3>
  <div class="plz-assg">{items}</div>
</div>"""

open(f"{SCR}/pulso_fragmento.html", "w").write(FRAG)
print("aba v7 gerada:", f"({len(FRAG)} bytes)", "| spots:", len(by_spot))
