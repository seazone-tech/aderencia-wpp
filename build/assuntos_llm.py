#!/usr/bin/env python3
"""Classifica o Top 10 de assuntos das mensagens externas via LLM Hub da Seazone (OpenAI-compatible).
Env: LLM_HUB_KEY (obrigatório), LLM_HUB_URL (default hub.seazone.dev), LLM_HUB_MODEL (default minimax-m2.5).
Se falhar/sem chave, mantém o assuntos_top10.json existente (snapshot) como fallback."""
import os, json, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("LLM_HUB_KEY", "")
URL = os.environ.get("LLM_HUB_URL", "https://hub.seazone.dev/v1/chat/completions")
MODEL = os.environ.get("LLM_HUB_MODEL", "minimax-m2.5")
OUT = f"{BASE}/assuntos_top10.json"

def keep_fallback(msg):
    print(f"[assuntos_llm] {msg} — mantendo assuntos_top10.json existente", file=sys.stderr)
    sys.exit(0 if os.path.exists(OUT) else 1)

if not KEY:
    keep_fallback("sem LLM_HUB_KEY")

ext = json.load(open(f"{BASE}/ext_por_tipo.json"))
linhas = [f"[{tipo} | {spot}] {txt}" for tipo, msgs in ext.items() for spot, txt in msgs]
corpus = "\n".join(linhas)[:60000]

prompt = (
    "Você recebe mensagens externas (investidores, conselheiros, fornecedores) de grupos de WhatsApp de "
    "empreendimentos imobiliários da Seazone, dos últimos 7 dias. Cada linha vem como [tipo_de_grupo | spot] texto.\n"
    "Destile os TOP 10 ASSUNTOS mais recorrentes/relevantes, agregando todos os spots. Ignore ruído "
    "(bom dia, ok, obrigado, links soltos). Não inclua nomes de pessoas físicas.\n"
    "Responda SOMENTE com um array JSON de 10 objetos, sem texto fora do JSON, cada um com: "
    'titulo (curto), descricao (1 frase), spots (lista, até 6), tipos (lista), mencoes (int), '
    'relevancia ("alta"|"media"|"baixa"). Ordene da maior para a menor relevância.\n\n' + corpus
)
body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2})
try:
    raw = subprocess.check_output(
        ["curl", "-s", "--max-time", "180", "-H", f"Authorization: Bearer {KEY}",
         "-H", "Content-Type: application/json", "-d", body, URL], timeout=200)
    resp = json.loads(raw)
    content = resp["choices"][0]["message"]["content"]
    i, j = content.find("["), content.rfind("]")
    arr = json.loads(content[i:j+1])
    assert isinstance(arr, list) and len(arr) >= 5
    json.dump(arr[:10], open(OUT, "w"), ensure_ascii=False)
    print(f"[assuntos_llm] OK: {len(arr)} assuntos via {MODEL}")
except Exception as e:
    keep_fallback(f"falha na chamada LLM: {e}")
