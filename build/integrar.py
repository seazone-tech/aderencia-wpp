#!/usr/bin/env python3
"""Insere a aba Monitoramento no index.html a partir de um base SEM a aba (index_base.html)
+ o fragmento gerado (pulso_fragmento.html). Escreve o index.html final na raiz do repo.
Uso: python build/integrar.py <caminho_index_saida>"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(BASE), "index.html")
idx = open(f"{BASE}/index_base.html").read()
frag = open(f"{BASE}/pulso_fragmento.html").read()

assert "tab-pl" not in idx, "index_base já contém a aba (deveria ser o dash SEM Monitoramento)"
old_ad = '<button class="tab-btn active" onclick="sw(\'ad\',this)">Aderência WPP</button>'
assert old_ad in idx, "âncora do botão Aderência WPP não encontrada no base"
new_ad = ('<button class="tab-btn active" onclick="sw(\'pl\',this)">Monitoramento</button>\n'
          '  <button class="tab-btn" onclick="sw(\'ad\',this)">Aderência WPP</button>')
idx = idx.replace(old_ad, new_ad, 1).replace('<div id="tab-ad" class="tp active">', '<div id="tab-ad" class="tp">', 1)
i = idx.index("<script>")
idx = idx[:i] + frag + "\n\n" + idx[i:]
open(out, "w").write(idx)
print("index.html gerado com a aba Monitoramento:", out)
