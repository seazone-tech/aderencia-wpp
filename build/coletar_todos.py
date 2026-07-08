#!/usr/bin/env python3
"""Casa inventário -> chat_ids do Timelines e puxa mensagens 7d de todos.
Robusto: retry/backoff, cache da listagem de chats, salvamento incremental (retomável)."""
import json, subprocess, urllib.parse, time, os, sys

import os
SCR = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("TIMELINES_TOKEN") or subprocess.check_output(["security","find-generic-password","-s","timelines-api-key","-w"]).decode().strip()
BASE = "https://app.timelines.ai/integrations/api"
AFTER = "2026-06-30"
CHATMAP = f"{SCR}/chatmap.json"
OUT = f"{SCR}/todos_7d.json"

def api(path, tries=6):
    url = f"{BASE}{path}"
    for a in range(tries):
        p = subprocess.run(["curl", "-s", "--max-time", "60", "-w", "\n%{http_code}",
                            "-H", f"Authorization: Bearer {TOKEN}", url], capture_output=True, text=True)
        out = p.stdout or ""
        nl = out.rfind("\n")
        body, code = (out[:nl], out[nl+1:].strip()) if nl >= 0 else (out, "")
        if code == "200" and body.strip():
            try: return json.loads(body)
            except Exception: pass
        time.sleep((10 if code == "429" else 3) * (a + 1))
    return None

def norm(s): return " ".join((s or "").lower().split())

inv = json.load(open(f"{SCR}/inventario_grupos.json"))
alvo = {}
for spot, grupos in inv.items():
    for nome, tipo in grupos:
        alvo[norm(nome)] = (spot, tipo, nome)

# 1) chatmap (cache)
if os.path.exists(CHATMAP):
    nome2chat = json.load(open(CHATMAP))
    print(f"chatmap em cache: {len(nome2chat)} grupos")
else:
    nome2chat, page = {}, 1
    while True:
        d = api(f"/chats?group=true&page={page}")
        if d is None: print(f"falha ao listar page {page}", file=sys.stderr); break
        data = d.get("data", {}); chats = data.get("chats", [])
        for c in chats:
            nome2chat[norm(c.get("name"))] = {"id": c["id"], "last": c.get("last_message_timestamp")}
        if not data.get("has_more_pages"): break
        page += 1; time.sleep(0.3)
    json.dump(nome2chat, open(CHATMAP, "w"), ensure_ascii=False)
    print(f"chatmap salvo: {len(nome2chat)} grupos ({page} páginas)")

# 2) casar
casados = []
for nkey, (spot, tipo, nome) in alvo.items():
    c = nome2chat.get(nkey)
    if c: casados.append((spot, tipo, nome, c["id"], c.get("last")))
print(f"casados: {len(casados)}/{len(alvo)}")

# 3) coleta incremental (retomável)
out = json.load(open(OUT)) if os.path.exists(OUT) else {}
done = set(out.keys())
for k, (spot, tipo, nome, cid, lastts) in enumerate(casados):
    if str(cid) in done: continue
    msgs, pg = [], 1
    ok = True
    while True:
        qs = urllib.parse.urlencode({"after": AFTER, "sorting_order": "asc", "page": pg})
        d = api(f"/chats/{cid}/messages?{qs}")
        if d is None: ok = False; break
        data = d.get("data", {})
        msgs += data.get("messages", [])
        if not data.get("has_more_pages"): break
        pg += 1; time.sleep(0.3)
    if not ok: print(f"falha no chat {cid} ({nome}) — pulando", file=sys.stderr); continue
    out[str(cid)] = {"spot": spot, "tipo": tipo, "nome": nome, "chat_id": cid,
                     "last_message_timestamp": lastts, "messages": msgs}
    if (k + 1) % 15 == 0:
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print(f"  ...{k+1}/{len(casados)} (salvo parcial)")
    time.sleep(0.35)

json.dump(out, open(OUT, "w"), ensure_ascii=False)
tot = sum(len(v["messages"]) for v in out.values())
print(f"\nOK: {len(out)} grupos | {tot} mensagens (7d)")
