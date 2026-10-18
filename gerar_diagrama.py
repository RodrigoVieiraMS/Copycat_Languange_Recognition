#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera diagrama_estados.png (e .svg) a partir do proprio arquivo .txt da maquina.
Uso: python gerar_diagrama.py [maquina_ww.txt]      (requer o programa 'dot' do Graphviz)
Legenda das arestas:  le/escreve,Direcao     ('=' significa 'reescreve o mesmo simbolo')"""
import subprocess
import sys
from collections import OrderedDict

from simulador_mt import MaquinaTuring

arq = sys.argv[1] if len(sys.argv) > 1 else "maquina_ww.txt"
m = MaquinaTuring.carregar(arq)

# agrupa transicoes por (origem, destino)
arestas = OrderedDict()
for (orig, le), (esc, d, dest) in m.delta.items():
    arestas.setdefault((orig, dest), []).append((le, esc, d))

def rotulo(trs):
    ident = OrderedDict()   # direcao -> [simbolos reescritos iguais]
    outros = []
    for le, esc, d in trs:
        if le == esc:
            ident.setdefault(d, []).append(le)
        else:
            outros.append(f"{le}/{esc},{d}")
    partes = [f"{','.join(s)}/=,{d}" for d, s in ident.items()] + outros
    return "\\n".join(partes)

cor = {"q0": "#cfe2f3", "q1": "#cfe2f3", "q2": "#cfe2f3", "q3": "#cfe2f3",
       "q4": "#fff2cc", "q5": "#d9ead3", "q6": "#d9ead3", "q7": "#d9ead3",
       "q_aceita": "#93c47d", "q_rejeita": "#ea9999"}
nomes = {"q0": "q0\\nmarca esq.", "q1": "q1\\nvai ao fim", "q2": "q2\\nmarca dir.",
         "q3": "q3\\nvolta", "q4": "q4\\nrebobina", "q5": "q5\\npega 1o",
         "q6": "q6\\nlembra a", "q7": "q7\\nlembra b",
         "q_aceita": "q_aceita", "q_rejeita": "q_rejeita"}

dot = ['digraph MT {', ' rankdir=LR; nodesep=0.5; ranksep=0.9; pad=0.3;',
       ' node [shape=circle, style=filled, fontname="Helvetica", fontsize=11, margin=0.04];',
       ' edge [fontname="Helvetica", fontsize=10];',
       ' start [shape=point, width=0.12];', f' start -> {m.estado_inicial};']
for e in m.estados:
    forma = "doublecircle" if e in m.estados_finais else "circle"
    dot.append(f' {e} [label="{nomes.get(e, e)}", shape={forma}, fillcolor="{cor.get(e, "white")}"];')
for (o, d), trs in arestas.items():
    dot.append(f' {o} -> {d} [label="{rotulo(trs)}"];')
dot.append(' label="FASE 1 (azul): achar o meio   |   rebobina (amarelo)   |   FASE 2 (verde): comparar as metades";'
           ' labelloc=b; fontname="Helvetica"; fontsize=12;')
dot.append('}')
fonte = "\n".join(dot)
open("diagrama_estados.dot", "w").write(fonte)
for fmt in ("png", "svg"):
    extra = ["-Gdpi=170"] if fmt == "png" else []
    subprocess.run(["dot", f"-T{fmt}", *extra, "diagrama_estados.dot", "-o", f"diagrama_estados.{fmt}"], check=True)
print("Gerados: diagrama_estados.png / .svg / .dot")
