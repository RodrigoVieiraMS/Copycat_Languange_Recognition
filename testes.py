#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bateria de testes da Equipe 4  (python testes.py)

1. Casos do enunciado/apresentacao (validos e invalidos).
2. Teste EXAUSTIVO: todas as cadeias de {a,b}* ate tamanho 12 comparadas com
   uma verificacao independente (w == s[:n/2] == s[n/2:]).
3. Tratamento de erros do motor (arquivo inexistente, transicao duplicada,
   estado nao declarado, simbolo fora do alfabeto de entrada...).
4. Limite de passos (loop infinito detectado) com uma MT que nunca para.
5. Fita infinita para a ESQUERDA (cabecote anda alem da posicao 0).
"""
import itertools
import os
import sys
import tempfile

from main import (ErroConfiguracao, ErroEntrada, MaquinaTuring,
                          Resultado, simular)

ARQ = "maquina_ww.txt"
falhas = 0


def check(cond, msg):
    global falhas
    print(("  [OK]   " if cond else "  [FALHA] ") + msg)
    if not cond:
        falhas += 1


def esta_em_L(s):
    n = len(s)
    return n % 2 == 0 and s[: n // 2] == s[n // 2:]


def roda(m, s, **kw):
    return simular(m, s, trace=False, **kw)


m = MaquinaTuring.carregar(ARQ)

# ---------------------------------------------------------------- 1
print("\n1) Casos de apresentacao")
validos = ["", "aa", "bb", "abab", "baba", "aabaab", "abaaba", "abbabb",
           "aaaaaa", "abaabaabaaba"]
invalidos = ["a", "b", "ab", "ba", "aba", "abba", "aab", "abaab", "ababaabab", "aabb", "abbaabb"]
for s in validos:
    check(roda(m, s).veredito == Resultado.ACEITA, f"ACEITA   '{s}'")
for s in invalidos:
    check(roda(m, s).veredito == Resultado.REJEITA, f"REJEITA  '{s}'")

# ---------------------------------------------------------------- 2
print("\n2) Teste exaustivo ate tamanho 12 (todas as cadeias de {a,b}*)")
total = 0
erros = 0
max_passos_vistos = 0
for tam in range(0, 13):
    for tupla in itertools.product("ab", repeat=tam):
        s = "".join(tupla)
        r = roda(m, s)
        esperado = Resultado.ACEITA if esta_em_L(s) else Resultado.REJEITA
        total += 1
        max_passos_vistos = max(max_passos_vistos, r.passos)
        if r.veredito != esperado:
            erros += 1
            print(f"    divergencia em '{s}': MT={r.veredito} esperado={esperado}")
check(erros == 0, f"{total} cadeias testadas, {erros} divergencias (max {max_passos_vistos} passos)")

# ---------------------------------------------------------------- 3
print("\n3) Tratamento de erros")


def tmp(texto):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    f.write(texto)
    f.close()
    return f.name


CAB = "q0,qf\na\na,B\nB\nq0\nqf\n"


def espera_erro(texto, trecho, nome):
    caminho = tmp(texto)
    try:
        MaquinaTuring.carregar(caminho)
        check(False, f"{nome}: deveria ter dado erro")
    except ErroConfiguracao as e:
        check(trecho in str(e), f"{nome}  ->  {e}")
    finally:
        os.unlink(caminho)


try:
    MaquinaTuring.carregar("nao_existe.txt")
    check(False, "arquivo inexistente")
except ErroConfiguracao as e:
    check("nao encontrado" in str(e), f"arquivo inexistente  ->  {e}")

espera_erro(CAB + "q0,a,a,R\n", "mal formada", "transicao com campos faltando")
espera_erro(CAB + "q9,a,a,R,q0\n", "nao declarado", "estado de origem inexistente")
espera_erro(CAB + "q0,a,a,R,q9\n", "nao declarado", "estado de destino inexistente")
espera_erro(CAB + "q0,z,a,R,q0\n", "alfabeto da fita", "simbolo lido fora do alfabeto")
espera_erro(CAB + "q0,a,a,X,q0\n", "invalida", "direcao invalida")
espera_erro(CAB + "q0,a,a,R,q0\nq0,a,B,L,qf\n", "DETERMINISTICA", "nao-determinismo")
espera_erro("q0,qf\na\na,B\n", "incompleto", "cabecalho incompleto")
espera_erro("q0,qf\na,B\na,B\nB\nq0\nqf\n", "branco", "branco no alfabeto de entrada")
espera_erro("q0,qf\na\na,B\nB\nq7\nqf\n", "inicial", "estado inicial inexistente")

try:
    roda(m, "abc")
    check(False, "entrada com simbolo invalido")
except ErroEntrada as e:
    check(True, f"entrada com simbolo invalido  ->  {e}")

# ---------------------------------------------------------------- 4
print("\n4) Limite de passos (loop infinito)")
loop = tmp("q0,qf\na\na,B\nB\nq0\nqf\nq0,B,B,R,q0\nq0,a,a,R,q0\n")
ml = MaquinaTuring.carregar(loop)
os.unlink(loop)
r = simular(ml, "aa", max_passos=1000, trace=False)
check(r.veredito == Resultado.LIMITE and r.passos == 1000, f"loop abortado em {r.passos} passos -> {r.veredito}")
r = simular(ml, "aa", trace=False)
check(r.veredito == Resultado.LIMITE and r.passos == 100000, f"limite padrao = {r.passos} passos")

# ---------------------------------------------------------------- 5
print("\n5) Fita infinita nos dois sentidos")
esq = tmp("q0,q1,qf\na\na,X,B\nB\nq0\nqf\nq0,a,a,L,q1\nq1,B,X,L,q1\n")
me = MaquinaTuring.carregar(esq)
os.unlink(esq)
r = simular(me, "a", max_passos=50, trace=False)
check(r.passos == 50 and "X" * 49 in r.fita_final,
      f"cabecote andou 49 celulas para a ESQUERDA da entrada sem estourar (fita='{r.fita_final[:12]}...')")

# 100000 passos reais com a MT principal rodando uma cadeia grande
s = "ab" * 50
r = roda(m, s + s)
check(r.veredito == Resultado.ACEITA, f"cadeia de tamanho 200 aceita em {r.passos} passos (< 100000)")

print("\n" + ("TODOS OS TESTES PASSARAM" if falhas == 0 else f"{falhas} FALHA(S)"))
sys.exit(1 if falhas else 0)
