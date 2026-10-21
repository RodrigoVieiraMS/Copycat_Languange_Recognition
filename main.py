#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Maquina de Turing Deterministica de Fita Unica
Disciplina: Aspectos Teoricos da Computacao  -  Prof. Rafael Teixeira de Araujo
Equipe 4 - Reconhecedor da linguagem copia  L = { ww | w em {a,b}* }
"""

import argparse
import os
import sys
import time

LIMITE_PADRAO = 100_000
DIRECOES = ("R", "L", "S")


class ErroConfiguracao(Exception):
    pass


class ErroEntrada(Exception):
    pass


# ----------------------------------------------------------------------
#  Fita infinita
# ----------------------------------------------------------------------
class Fita:
    def __init__(self, entrada, branco):
        self.branco = branco
        self.celulas = {i: s for i, s in enumerate(entrada) if s != branco}
        self.cabecote = 0
        self.menor = 0
        self.maior = max(len(entrada) - 1, 0)

    def ler(self):
        return self.celulas.get(self.cabecote, self.branco)

    def escrever(self, simbolo):
        if simbolo == self.branco:
            self.celulas.pop(self.cabecote, None)
        else:
            self.celulas[self.cabecote] = simbolo

    def mover(self, direcao):
        if direcao == "R":
            self.cabecote += 1
        elif direcao == "L":
            self.cabecote -= 1
        self.menor = min(self.menor, self.cabecote)
        self.maior = max(self.maior, self.cabecote)

    def conteudo(self):
        if not self.celulas:
            return ""
        ini, fim = min(self.celulas), max(self.celulas)
        return "".join(self.celulas.get(i, self.branco) for i in range(ini, fim + 1))

    def desenhar_quotado(self, margem=1):
        ini = min(self.menor, self.cabecote) - margem
        fim = max(self.maior, self.cabecote) + margem
        celulas = [self.celulas.get(i, self.branco) for i in range(ini, fim + 1)]
        linha = "  ".join(f'"{c}"' for c in celulas)
        pos_cab = self.cabecote - ini
        seta = " " * (5 * pos_cab + 1) + "^"
        return linha, seta


# ----------------------------------------------------------------------
#  Maquina de Turing (definicao + leitura do arquivo)
# ----------------------------------------------------------------------
class MaquinaTuring:
    def __init__(self):
        self.estados = []
        self.alfabeto_entrada = []
        self.alfabeto_fita = []
        self.branco = "B"
        self.estado_inicial = ""
        self.estados_finais = []
        self.delta = {}

    @classmethod
    def carregar(cls, caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                linhas = f.read().splitlines()
        except FileNotFoundError:
            raise ErroConfiguracao(f"Arquivo '{caminho}' nao encontrado.")
        except OSError as e:
            raise ErroConfiguracao(f"Nao foi possivel ler '{caminho}': {e}")

        dados = []
        for n, bruta in enumerate(linhas, start=1):
            texto = bruta.strip().lstrip("\ufeff")
            if not texto or texto.startswith(";"):
                continue
            dados.append((n, texto))

        if len(dados) < 6:
            raise ErroConfiguracao(
                "Cabecalho incompleto: esperado 6 linhas (estados, alfabeto de entrada, "
                "alfabeto da fita, branco, estado inicial, estados finais)."
            )

        def lista(item):
            n, texto = item
            partes = [p.strip() for p in texto.split(",")]
            if any(p == "" for p in partes):
                raise ErroConfiguracao(f"Linha {n}: elemento vazio na lista '{texto}'.")
            return partes

        m = cls()
        m.estados = lista(dados[0])
        m.alfabeto_entrada = lista(dados[1])
        m.alfabeto_fita = lista(dados[2])
        branco = lista(dados[3])
        if len(branco) != 1:
            raise ErroConfiguracao(f"Linha {dados[3][0]}: deve haver exatamente 1 simbolo de branco.")
        m.branco = branco[0]
        inicial = lista(dados[4])
        if len(inicial) != 1:
            raise ErroConfiguracao(f"Linha {dados[4][0]}: deve haver exatamente 1 estado inicial.")
        m.estado_inicial = inicial[0]
        m.estados_finais = lista(dados[5])

        m._validar_cabecalho()

        for n, texto in dados[6:]:
            m._ler_transicao(n, texto)
        return m

    def _validar_cabecalho(self):
        if len(set(self.estados)) != len(self.estados):
            raise ErroConfiguracao("A lista de estados tem nomes repetidos.")
        if self.branco not in self.alfabeto_fita:
            raise ErroConfiguracao(f"O branco '{self.branco}' precisa estar no alfabeto da fita.")
        if self.branco in self.alfabeto_entrada:
            raise ErroConfiguracao("O branco nao pode fazer parte do alfabeto de entrada.")
        for s in self.alfabeto_entrada:
            if s not in self.alfabeto_fita:
                raise ErroConfiguracao(f"Simbolo de entrada '{s}' nao esta no alfabeto da fita.")
        if self.estado_inicial not in self.estados:
            raise ErroConfiguracao(f"Estado inicial '{self.estado_inicial}' nao esta na lista de estados.")
        for f in self.estados_finais:
            if f not in self.estados:
                raise ErroConfiguracao(f"Estado final '{f}' nao esta na lista de estados.")

    def _ler_transicao(self, n, texto):
        partes = [p.strip() for p in texto.split(",")]
        if len(partes) != 5:
            raise ErroConfiguracao(
                f"Linha {n}: transicao mal formada '{texto}'. "
                "Formato: Origem, Le, Escreve, Direcao[R/L/S], Destino"
            )
        origem, le, escreve, direcao, destino = partes
        direcao = direcao.upper()
        if origem not in self.estados:
            raise ErroConfiguracao(f"Linha {n}: estado de origem '{origem}' nao declarado.")
        if destino not in self.estados:
            raise ErroConfiguracao(f"Linha {n}: estado de destino '{destino}' nao declarado.")
        if le not in self.alfabeto_fita:
            raise ErroConfiguracao(f"Linha {n}: simbolo lido '{le}' nao esta no alfabeto da fita.")
        if escreve not in self.alfabeto_fita:
            raise ErroConfiguracao(f"Linha {n}: simbolo escrito '{escreve}' nao esta no alfabeto da fita.")
        if direcao not in DIRECOES:
            raise ErroConfiguracao(f"Linha {n}: direcao '{direcao}' invalida (use R, L ou S).")
        chave = (origem, le)
        if chave in self.delta:
            raise ErroConfiguracao(
                f"Linha {n}: transicao duplicada para ({origem}, {le}) - "
                "a maquina precisa ser DETERMINISTICA."
            )
        self.delta[chave] = (escreve, direcao, destino)

    def resumo(self):
        return (
            f"Estados ({len(self.estados)}): {', '.join(self.estados)}\n"
            f"Alfabeto de entrada: {', '.join(self.alfabeto_entrada)}\n"
            f"Alfabeto da fita: {', '.join(self.alfabeto_fita)}   (branco = {self.branco})\n"
            f"Estado inicial: {self.estado_inicial}   Finais: {', '.join(self.estados_finais)}\n"
            f"Transicoes: {len(self.delta)}"
        )


# ----------------------------------------------------------------------
#  Resultado e execucao
# ----------------------------------------------------------------------
class Resultado:
    ACEITA = "ACEITA"
    REJEITA = "REJEITA"
    LIMITE = "LIMITE_EXCEDIDO"

    def __init__(self, veredito, passos, estado, fita_final, motivo):
        self.veredito = veredito
        self.passos = passos
        self.estado = estado
        self.fita_final = fita_final
        self.motivo = motivo


def simular(maquina, entrada, max_passos=LIMITE_PADRAO, trace=True, pausa=0.0, saida=print, observador=None):
    for s in entrada:
        if s not in maquina.alfabeto_entrada:
            raise ErroEntrada(
                f"Simbolo '{s}' da entrada nao pertence ao alfabeto de entrada "
                f"{{{', '.join(maquina.alfabeto_entrada)}}}."
            )

    fita = Fita(entrada, maquina.branco)
    estado = maquina.estado_inicial
    passos = 0

    AC_OES_MOV = {"R": "andou para a DIREITA (→)",
                  "L": "andou para a ESQUERDA (←)",
                  "S": "ficou parado (·)"}

    def imprimir(dados=None, inicial=False):
        linha, seta = fita.desenhar_quotado()
        if inicial:
            saida(f'Passo {passos:>4} | estado: "{estado}"   (configuracao inicial)')
        else:
            saida(f'Passo {passos:>4} | estado: "{estado}"')
        saida(f'  Fita: {linha}')
        saida(f'        {seta}')
        if dados:
            lido, esc, direcao, dest, orig = dados
            esc_verbo = "escreveu" if lido != esc else "manteve"
            saida(f'  Aplicado: d("{orig}", "{lido}") = ("{esc}", {direcao}, "{dest}")')
            saida(f'  → leu "{lido}", {esc_verbo} "{esc}", {AC_OES_MOV[direcao]}, foi para "{dest}"')
        if inicial:
            saida(f'  → cabecote na posicao 0, estado inicial "{estado}"')
        saida("")
        if pausa:
            time.sleep(pausa)

    if trace:
        saida("=" * 64)
        saida(f'Entrada: "{entrada}"  (tamanho {len(entrada)})')
        saida("=" * 64)
        imprimir(inicial=True)

    if observador:
        observador(passos, estado, fita, None)

    while True:
        if estado in maquina.estados_finais:
            return Resultado(Resultado.ACEITA, passos, estado, fita.conteudo(),
                             f"chegou ao estado final '{estado}'")

        simbolo = fita.ler()
        regra = maquina.delta.get((estado, simbolo))

        if regra is None:
            if estado == "q_rejeita":
                motivo = "chegou ao estado de rejeicao 'q_rejeita'"
            else:
                motivo = f"sem transicao para ({estado}, {simbolo}) - maquina travou"
            return Resultado(Resultado.REJEITA, passos, estado, fita.conteudo(), motivo)

        if passos >= max_passos:
            return Resultado(Resultado.LIMITE, passos, estado, fita.conteudo(),
                             f"limite de {max_passos} passos atingido (possivel loop infinito)")

        escreve, direcao, destino = regra
        origem = estado
        fita.escrever(escreve)
        fita.mover(direcao)
        estado = destino
        passos += 1
        if observador:
            observador(passos, estado, fita, (simbolo, escreve, direcao, destino, origem))
        if trace:
            imprimir(dados=(simbolo, escreve, direcao, destino, origem))


# ----------------------------------------------------------------------
#  Constantes visuais
# ----------------------------------------------------------------------
COR = {"bg": "#eef2f8", "card": "#ffffff", "azul": "#1f3a5f", "azul2": "#2f5d9e", "txt": "#1c2433",
       "mut": "#6b7686", "linha": "#d8dfeb", "ok": "#1e8e3e", "okbg": "#e3f4e8", "bad": "#c5221f",
       "badbg": "#fde7e6", "warn": "#9a5b00", "warnbg": "#fff1d6"}

GUIA_GRAFICO = [
    ("h", "Como ler o diagrama de estados\n"),
    ("b", "Círculo"), ("t", " = um estado (a \"situação\" em que a máquina está).\n"),
    ("b", "Seta"), ("t", " = uma regra, no formato "), ("m", "leitura/escrita,direção"), ("t", ".\n\n"),
    ("h", "O que significa cada parte de uma seta\n"),
    ("t", "Toda seta do diagrama tem o formato "), ("m", "leitura/escrita,direção"), ("t", ".\n"),
    ("t", "Exemplo: uma seta rotulada "), ("m", "a/X,R"), ("t", " deve ser lida assim:\n"),
    ("t", "    "), ("m", "a"), ("t", "  → símbolo LIDO da fita (o que o cabeçote está vendo);\n"),
    ("t", "    "), ("m", "/"), ("t", "  → separador (\"lê / escreve\");\n"),
    ("t", "    "), ("m", "X"), ("t", "  → símbolo ESCRITO na fita, no lugar do lido;\n"),
    ("t", "    "), ("m", ","), ("t", "  → separador;\n"),
    ("t", "    "), ("m", "R"), ("t", "  → direção do cabeçote: "), ("m", "R"), ("t", "=direita, "),
    ("m", "L"), ("t", "=esquerda, "), ("m", "S"), ("t", "=parado.\n"),
    ("t", "Ou seja: "), ("m", "a/X,R"), ("t", " significa \"se ler 'a', escreva 'X' e ande para a direita\".\n"),
    ("t", "Quando os dois símbolos são iguais (ex.: "), ("m", "b/b,R"), ("t", "), é porque a máquina só anda, "
     "sem alterar a letra.\n\n"),
    ("b", "Seta saindo de um ponto preto"), ("t", " = onde tudo começa (estado inicial).\n"),
    ("b", "Seta que volta no mesmo círculo"), ("t", " = a máquina continua sem mudar de situação.\n"),
    ("b", "Círculo duplo verde"), ("t", " = aceita.   "), ("b", "Círculo vermelho"), ("t", " = rejeita.\n"),
    ("b", "Cores"), ("t", ": azul = achar o meio, amarelo = rebobinar, verde = comparar metades.\n\n"),
    ("t", "Siga as setas para entender: "), ("m", "abab"),
    ("t", " começa em q0, passa pelo azul, pelo amarelo e pelo verde até q_aceita.\n\n"),
    ("h", "Resumo da estratégia\n"),
    ("b", "Fase 1 (achar o meio): "), ("t",
     "marca uma letra da ponta esquerda e uma da ponta direita, repetindo. As marcas se encontram no centro. "
     "Se sobrar uma letra sozinha, o tamanho é ÍMPAR e a resposta é NÃO.\n"),
    ("b", "Fase 2 (comparar): "), ("t",
     "pega a 1ª letra da esquerda, lembra qual era (estado q6 ou q7) e confere com a 1ª letra da direita. "
     "Iguais: marca as duas com Z e repete. Diferentes: NÃO. Acabou tudo igual: SIM.\n"),
]


# ----------------------------------------------------------------------
#  Interface grafica didatica
# ----------------------------------------------------------------------
def abrir_interface(arquivo_padrao):
    import tkinter as tk
    from tkinter import filedialog, ttk

    MAX_LINHAS = 20000
    MAX_SNAPS = 5000
    pasta = os.path.dirname(os.path.abspath(arquivo_padrao))

    root = tk.Tk()
    root.title("Simulador de Maquina de Turing - Equipe 4  |  L = { ww }")
    root.geometry("1120x960")
    root.minsize(940, 720)
    root.configure(bg=COR["bg"])

    est = ttk.Style()
    try:
        est.theme_use("clam")
    except tk.TclError:
        pass
    fonte = ("Segoe UI", 10)
    est.configure(".", font=fonte, background=COR["bg"], foreground=COR["txt"])
    est.configure("TNotebook", background=COR["bg"], borderwidth=0)
    est.configure("TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10, "bold"), background="#dde5f2",
                  foreground=COR["azul"], borderwidth=0)
    est.map("TNotebook.Tab", background=[("selected", COR["card"])], foreground=[("selected", COR["azul2"])])
    est.configure("Card.TFrame", background=COR["card"])
    est.configure("Bg.TFrame", background=COR["bg"])
    est.configure("TLabel", background=COR["card"])
    est.configure("Accent.TButton", background=COR["azul2"], foreground="white", font=("Segoe UI", 11, "bold"),
                  padding=(18, 8), borderwidth=0)
    est.map("Accent.TButton", background=[("active", COR["azul"])])
    est.configure("Soft.TButton", background="#e4ebf7", foreground=COR["azul"], padding=(10, 6), borderwidth=0)
    est.map("Soft.TButton", background=[("active", "#cdd9ee")])
    est.configure("Chip.TButton", background="#e4ebf7", foreground=COR["azul"], padding=(12, 5),
                  font=("Consolas", 11, "bold"), borderwidth=0)
    est.map("Chip.TButton", background=[("active", "#bcd0ee")])
    est.configure("Treeview", rowheight=26, font=("Segoe UI", 10), background="#ffffff", fieldbackground="#ffffff")
    est.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#dde5f2", foreground=COR["azul"])

    topo = tk.Frame(root, bg=COR["azul"])
    topo.pack(fill="x")
    tk.Label(topo, text="Simulador de Maquina de Turing", bg=COR["azul"], fg="white",
             font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
    tk.Label(topo, text="Reconhecedor de  L = { ww | w \u2208 {a,b}* }   \u00b7   determin\u00edstica, fita \u00fanica   \u00b7   Equipe 4",
             bg=COR["azul"], fg="#b9c9e4", font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(0, 12))

    abas = ttk.Notebook(root)
    abas.pack(fill="both", expand=True, padx=14, pady=12)

    def nova_aba(titulo):
        f = ttk.Frame(abas, style="Card.TFrame", padding=14)
        abas.add(f, text=titulo)
        return f

    aba_sim = nova_aba("Simulador")
    aba_diag = nova_aba("Diagrama")

    v_arquivo = tk.StringVar(value=arquivo_padrao)
    v_cadeia = tk.StringVar()
    v_limite = tk.StringVar(value=str(LIMITE_PADRAO))

    # =====================================================  ABA SIMULADOR
    linha1 = ttk.Frame(aba_sim, style="Card.TFrame")
    linha1.pack(fill="x")
    ttk.Label(linha1, text="Digite a cadeia (letras a e b):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    caixa = ttk.Frame(linha1, style="Card.TFrame")
    caixa.pack(fill="x", pady=(4, 0))
    entrada = tk.Entry(caixa, textvariable=v_cadeia, font=("Consolas", 18), relief="solid", bd=1,
                       highlightthickness=2, highlightbackground=COR["linha"], highlightcolor=COR["azul2"])
    entrada.pack(side="left", fill="x", expand=True, ipady=6)
    ttk.Button(caixa, text="EXECUTAR", style="Accent.TButton", command=lambda: executar()).pack(side="left", padx=(10, 0))
    ttk.Button(caixa, text="Limpar", style="Soft.TButton", command=lambda: limpar()).pack(side="left", padx=(8, 0))

    ex = ttk.Frame(linha1, style="Card.TFrame")
    ex.pack(fill="x", pady=(8, 0))
    ttk.Label(ex, text="Exemplos:", foreground=COR["mut"]).pack(side="left", padx=(0, 6))
    for e_ in ("abab", "abaaba", "abba", "aba", "aa", "a"):
        ttk.Button(ex, text=e_, style="Chip.TButton",
                   command=lambda s=e_: (v_cadeia.set(s), executar())).pack(side="left", padx=3)
    ttk.Button(ex, text="vazia", style="Chip.TButton",
               command=lambda: (v_cadeia.set(""), executar())).pack(side="left", padx=3)

    banner = tk.Label(aba_sim, text="Escolha um exemplo ou digite uma cadeia e clique em EXECUTAR",
                      font=("Segoe UI", 13, "bold"), bg="#eef2f8", fg=COR["mut"], pady=10)
    banner.pack(fill="x", pady=(10, 6))

    # ---- Tabela estatica das 4 fases ----
    resumo_frame = ttk.Frame(aba_sim, style="Card.TFrame")
    resumo_frame.pack(fill="x")
    ttk.Label(resumo_frame, text="Resumo das 4 fases da execucao",
              font=("Segoe UI", 11, "bold"), foreground=COR["azul"]).pack(anchor="w")
    tabela_fases = ttk.Treeview(resumo_frame,
                                columns=("fase", "descricao", "status", "passos"),
                                show="headings", height=4)
    tabela_fases.heading("fase", text="Fase")
    tabela_fases.heading("descricao", text="O que acontece")
    tabela_fases.heading("status", text="Status")
    tabela_fases.heading("passos", text="Passos")
    tabela_fases.column("fase", width=170, anchor="w")
    tabela_fases.column("descricao", width=560, anchor="w")
    tabela_fases.column("status", width=130, anchor="center")
    tabela_fases.column("passos", width=90, anchor="center")
    tabela_fases.tag_configure("ok", background=COR["okbg"], foreground=COR["ok"])
    tabela_fases.tag_configure("bad", background=COR["badbg"], foreground=COR["bad"])
    tabela_fases.tag_configure("warn", background=COR["warnbg"], foreground=COR["warn"])
    tabela_fases.tag_configure("skip", foreground=COR["mut"])
    tabela_fases.pack(fill="x", pady=(4, 0))

    # ---- Explicacao breve ----
    explic_frame = tk.Frame(aba_sim, bg="#f4f7fc", highlightthickness=1, highlightbackground=COR["linha"])
    explic_frame.pack(fill="x", pady=(8, 0))
    explic_res = tk.Label(explic_frame, text="O resultado e a explicacao aparecem aqui depois de executar.",
                          wraplength=1040, justify="left", anchor="w",
                          font=("Segoe UI", 11), bg="#f4f7fc", fg=COR["mut"],
                          padx=12, pady=8)
    explic_res.pack(fill="x")

    # ==================================================================
    #  NOVO: Legenda dos simbolos que aparecem na fita
    # ==================================================================
    legenda_frame = ttk.Frame(aba_sim, style="Card.TFrame")
    legenda_frame.pack(fill="x", pady=(10, 0))
    ttk.Label(legenda_frame, text="O que significa cada símbolo que aparece na fita",
              font=("Segoe UI", 11, "bold"), foreground=COR["azul"]).grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

    SIMBOLOS_INFO = [
        ("B", "Branco (blank) — casa vazia, sem letra gravada"),
        ("a", "Letra 'a' original da cadeia, ainda não processada"),
        ("b", "Letra 'b' original da cadeia, ainda não processada"),
        ("X", "Era 'a' da 1ª metade — marca de processamento"),
        ("Y", "Era 'b' da 1ª metade — marca de processamento"),
        ("U", "Era 'a' da 2ª metade — marca de processamento"),
        ("V", "Era 'b' da 2ª metade — marca de processamento"),
        ("Z", "Posição já CONFERIDA na comparação das metades"),
    ]
    for i, (s_, desc) in enumerate(SIMBOLOS_INFO):
        r = i // 2 + 1
        c = (i % 2) * 2
        tk.Label(legenda_frame, text=f'"{s_}"', width=4, bg="#f7f9fd", fg=COR["azul2"],
                 font=("Consolas", 11, "bold"), relief="solid", bd=1).grid(
            row=r, column=c, padx=(0, 6), pady=2, sticky="w")
        ttk.Label(legenda_frame, text=desc, font=("Segoe UI", 9)).grid(
            row=r, column=c + 1, sticky="w", padx=(0, 30), pady=2)

    ttk.Label(legenda_frame,
              text="Como ler a fita: cada símbolo entre aspas ocupa uma célula separada. "
                   "Quando aparecem juntos (ex.: \"B\"  \"a\"  \"b\"), NÃO existe um 'símbolo BA' — "
                   "são três células vizinhas: branco, 'a', 'b'. O '^' embaixo indica onde está o cabeçote.",
              foreground=COR["mut"], font=("Segoe UI", 9), wraplength=1040).grid(
        row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

    # ---- Trace detalhado ----
    trace_frame = ttk.Frame(aba_sim, style="Card.TFrame")
    trace_frame.pack(fill="both", expand=True, pady=(10, 0))
    ttk.Label(trace_frame, text="Trace detalhado (passo a passo da fita)",
              font=("Segoe UI", 11, "bold"), foreground=COR["azul"]).pack(anchor="w")
    trace_txt = tk.Text(trace_frame, font=("Consolas", 10), wrap="none",
                        relief="flat", bg="#fbfcfe", height=10)
    sb_y = ttk.Scrollbar(trace_frame, orient="vertical", command=trace_txt.yview)
    sb_x = ttk.Scrollbar(trace_frame, orient="horizontal", command=trace_txt.xview)
    trace_txt.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
    sb_y.pack(side="right", fill="y")
    sb_x.pack(side="bottom", fill="x")
    trace_txt.pack(fill="both", expand=True, pady=(4, 0))

    # ---- Historico (bottom) ----
    hq = ttk.Frame(aba_sim, style="Card.TFrame")
    hq.pack(side="bottom", fill="x", pady=(10, 0))
    hcab = ttk.Frame(hq, style="Card.TFrame")
    hcab.pack(fill="x")
    ttk.Label(hcab, text="Historico das cadeias testadas", font=("Segoe UI", 10, "bold"),
              foreground=COR["azul"]).pack(side="left")
    ttk.Label(hcab, text="  (duplo clique numa linha para rodar de novo)", foreground=COR["mut"]).pack(side="left")
    tabela = ttk.Treeview(hq, columns=("n", "cadeia", "res", "passos", "evo"), show="headings", height=3)
    for col, titulo, larg, anc in (("n", "#", 40, "center"), ("cadeia", "Cadeia", 170, "w"),
                                   ("res", "Resultado", 110, "center"), ("passos", "Passos", 70, "center"),
                                   ("evo", "Evolucao da fita (marcas)", 600, "w")):
        tabela.heading(col, text=titulo)
        tabela.column(col, width=larg, anchor=anc, stretch=(col == "evo"))
    tabela.tag_configure("ok", background=COR["okbg"], foreground=COR["ok"])
    tabela.tag_configure("bad", background=COR["badbg"], foreground=COR["bad"])
    tabela.tag_configure("warn", background=COR["warnbg"], foreground=COR["warn"])
    sbh = ttk.Scrollbar(hq, orient="vertical", command=tabela.yview)
    tabela.configure(yscrollcommand=sbh.set)
    ttk.Button(hcab, text="Limpar historico", style="Soft.TButton",
               command=lambda: tabela.delete(*tabela.get_children())).pack(side="right")
    sbh.pack(side="right", fill="y")
    tabela.pack(fill="x", pady=(4, 0))
    contador = {"n": 0}

    def reexecutar(_e=None):
        sel = tabela.selection()
        if sel:
            c = tabela.item(sel[0], "values")[1]
            v_cadeia.set("" if c.startswith("(vazia") else c)
            executar()

    tabela.bind("<Double-1>", reexecutar)

    # ---- Rodape ----
    rod = ttk.Frame(aba_sim, style="Card.TFrame")
    rod.pack(side="bottom", fill="x", pady=(6, 0))
    ttk.Label(rod, text="Maquina:", foreground=COR["mut"]).pack(side="left")
    tk.Entry(rod, textvariable=v_arquivo, relief="flat", state="readonly", readonlybackground=COR["card"],
             fg=COR["mut"], width=48).pack(side="left", padx=6)

    def procurar():
        c = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if c:
            v_arquivo.set(c)

    ttk.Button(rod, text="Trocar...", style="Soft.TButton", command=procurar).pack(side="left")
    ttk.Label(rod, text="   Limite de passos:", foreground=COR["mut"]).pack(side="left")
    tk.Entry(rod, textvariable=v_limite, width=8, relief="solid", bd=1).pack(side="left", padx=4)

    def mostrar_trace(texto):
        trace_txt.configure(state="normal")
        trace_txt.delete("1.0", "end")
        trace_txt.insert("end", texto)
        trace_txt.configure(state="disabled")

    def mostrar_banner(texto, fg, bg):
        banner.configure(text=texto, fg=fg, bg=bg)

    def executar(_e=None):
        cadeia = v_cadeia.get().strip()
        if cadeia.lower() in ("\u03b5", "eps", "epsilon"):
            cadeia = ""
        try:
            limite = int(v_limite.get())
            if limite < 1:
                raise ValueError
        except ValueError:
            mostrar_banner("Limite de passos invalido (use um numero inteiro positivo)", COR["warn"], COR["warnbg"])
            return
        try:
            maquina = MaquinaTuring.carregar(v_arquivo.get().strip())
        except ErroConfiguracao as e:
            mostrar_banner("Erro no arquivo da maquina", COR["warn"], COR["warnbg"])
            mostrar_trace(str(e))
            return

        linhas, snaps = [], []
        fases_dados = {"fase1": [], "rebobinar": [], "fase2": []}

        def obs(passo, estado, fita, regra):
            if estado in ("q0", "q1", "q2", "q3"):
                fases_dados["fase1"].append(passo)
            elif estado == "q4":
                fases_dados["rebobinar"].append(passo)
            elif estado in ("q5", "q6", "q7"):
                fases_dados["fase2"].append(passo)
            if len(snaps) < MAX_SNAPS:
                ini = min(fita.menor, fita.cabecote) - 1
                fim = max(fita.maior, fita.cabecote) + 1
                cel = "".join(fita.celulas.get(p, fita.branco) for p in range(ini, fim + 1))
                snaps.append((passo, estado, ini, cel, fita.cabecote - ini, regra))

        try:
            r = simular(maquina, cadeia, limite, trace=True, saida=linhas.append, observador=obs)
        except ErroEntrada as e:
            mostrar_banner("Cadeia invalida: use apenas as letras do alfabeto (a e b)", COR["warn"], COR["warnbg"])
            mostrar_trace(str(e))
            return

        if len(linhas) > MAX_LINHAS:
            m_ = MAX_LINHAS // 2
            linhas = linhas[:m_] + [f"\n... {len(linhas) - MAX_LINHAS} linhas omitidas ...\n"] + linhas[-m_:]
        mostrar_trace("\n".join(linhas + [
            "-" * 64,
            f'RESULTADO : {r.veredito}',
            f'Motivo    : {r.motivo}',
            f'Passos    : {r.passos}',
            f'Fita final: "{r.fita_final}"',
        ]))

        evo = []
        for (p_, e_, ini_, cel_, cab_, rg_) in snaps:
            if p_ == 0 or e_ in ("q0", "q5") or p_ == snaps[-1][0]:
                s_ = cel_.strip(maquina.branco) or "\u03b5"
                if not evo or evo[-1] != s_:
                    evo.append(s_)
        txt_evo = "  \u2192  ".join(evo)
        if len(snaps) < r.passos + 1:
            txt_evo += "  ..."
        contador["n"] += 1
        rotulo_res, tag = {Resultado.ACEITA: ("ACEITA \u2713", "ok"),
                           Resultado.REJEITA: ("REJEITA \u2717", "bad")}.get(
            r.veredito, ("LIMITE", "warn"))
        tabela.insert("", 0,
                      values=(contador["n"], cadeia if cadeia else "(vazia)",
                              rotulo_res, r.passos, txt_evo),
                      tags=(tag,))

        rot = f"'{cadeia}'" if cadeia else "(cadeia vazia)"
        if r.veredito == Resultado.ACEITA:
            mostrar_banner(f"{rot}  \u2192  ACEITA   \u2713   ({r.passos} passos)", COR["ok"], COR["okbg"])
        elif r.veredito == Resultado.REJEITA:
            mostrar_banner(f"{rot}  \u2192  REJEITA   \u2717   ({r.passos} passos)", COR["bad"], COR["badbg"])
        else:
            mostrar_banner(f"{rot}  \u2192  LIMITE DE PASSOS EXCEDIDO", COR["warn"], COR["warnbg"])

        for row in tabela_fases.get_children():
            tabela_fases.delete(row)

        fases_info = [
            ("fase1", "1. Achar o meio",
             "Marca um par de letras das pontas (esquerda + direita) e repete ate o centro. "
             "Se sobrar 1 letra sozinha, o tamanho e IMPAR \u2192 rejeita."),
            ("rebobinar", "2. Rebobinar",
             "Volta o cabecote ao inicio da fita para comecar a comparacao."),
            ("fase2", "3. Comparar as metades",
             "Compara letra a letra as duas metades. Marca cada par conferido com Z. "
             "Se achar diferenca \u2192 rejeita."),
        ]
        for chave, nome, descr in fases_info:
            ps = fases_dados[chave]
            if ps:
                dur = f"{ps[-1] - ps[0] + 1} passos"
                status = "\u2713 executada"
                tag_f = "ok"
            else:
                dur = "\u2014"
                status = "\u2014 nao atingida"
                tag_f = "skip"
            tabela_fases.insert("", "end", values=(nome, descr, status, dur), tags=(tag_f,))

        if r.veredito == Resultado.ACEITA:
            status, tag_f = "\u2713 ACEITA", "ok"
        elif r.veredito == Resultado.REJEITA:
            status, tag_f = "\u2717 REJEITA", "bad"
        else:
            status, tag_f = "\u26a0 LIMITE", "warn"
        tabela_fases.insert("", "end",
                            values=("4. Resultado", r.motivo, status, f"{r.passos} passos totais"),
                            tags=(tag_f,))

        c_nome = cadeia if cadeia else "(vazia)"
        if r.veredito == Resultado.ACEITA:
            texto_expl = (f"\u2713 A cadeia '{c_nome}' PERTENCE a L = {{ ww | w \u2208 {{a,b}}* }}. "
                          f"As duas metades sao identicas. A maquina chegou a q_aceita em {r.passos} passos.")
            cor_fg = COR["ok"]
        elif r.veredito == Resultado.REJEITA:
            if not fases_dados["rebobinar"]:
                razao = ("O tamanho da cadeia e IMPAR (a fase 1 nao encontrou o centro exato), "
                         "entao ela nao pode ser da forma ww.")
            elif not fases_dados["fase2"]:
                razao = "A comparacao das metades nao pode ser concluida."
            else:
                razao = ("As duas metades NAO sao iguais (a fase 3 encontrou uma diferenca).")
            texto_expl = (f"\u2717 A cadeia '{c_nome}' NAO pertence a L. {razao} "
                          f"Total: {r.passos} passos. Motivo: {r.motivo}.")
            cor_fg = COR["bad"]
        else:
            texto_expl = (f"\u26a0 Limite de {r.passos} passos excedido para '{c_nome}'. "
                          "Pode haver loop infinito.")
            cor_fg = COR["warn"]
        explic_res.configure(text=texto_expl, fg=cor_fg)

        abas.select(aba_sim)

    def limpar():
        v_cadeia.set("")
        mostrar_banner("Escolha um exemplo ou digite uma cadeia e clique em EXECUTAR", COR["mut"], "#eef2f8")
        mostrar_trace("")
        explic_res.configure(
            text="O resultado e a explicacao aparecem aqui depois de executar.", fg=COR["mut"])
        for row in tabela_fases.get_children():
            tabela_fases.delete(row)
        entrada.focus_set()

    # =====================================================  ABA DIAGRAMA
    caminho_png = os.path.join(pasta, "diagrama_estados.png")
    zoom = {"f": 3, "img": None}

    barra_d = ttk.Frame(aba_diag, style="Card.TFrame")
    barra_d.pack(fill="x")
    ttk.Label(barra_d, text="Diagrama de estados da maquina",
              font=("Segoe UI", 10, "bold")).pack(side="left")
    ttk.Button(barra_d, text="Reduzir", style="Soft.TButton",
               command=lambda: mudar_zoom(+1)).pack(side="right")
    ttk.Button(barra_d, text="Ampliar", style="Soft.TButton",
               command=lambda: mudar_zoom(-1)).pack(side="right", padx=6)

    explic_diag = tk.Text(aba_diag, wrap="word", relief="flat", bg=COR["card"],
                          padx=18, pady=14, font=("Segoe UI", 11), height=15,
                          highlightthickness=1, highlightbackground=COR["linha"])
    explic_diag.tag_configure("h", font=("Segoe UI", 13, "bold"), foreground=COR["azul"],
                              spacing1=8, spacing3=6)
    explic_diag.tag_configure("b", font=("Segoe UI", 11, "bold"), foreground=COR["azul2"])
    explic_diag.tag_configure("t", foreground=COR["txt"], spacing3=3)
    explic_diag.tag_configure("m", font=("Consolas", 11, "bold"), foreground="#7a1f6b")
    for tag, txt in GUIA_GRAFICO:
        explic_diag.insert("end", txt, tag)
    explic_diag.configure(state="disabled")
    explic_diag.pack(side="bottom", fill="x", pady=(10, 0))

    quadro_d = ttk.Frame(aba_diag, style="Card.TFrame")
    quadro_d.pack(fill="both", expand=True, pady=(8, 0))
    cv = tk.Canvas(quadro_d, bg="white", highlightthickness=0)
    sy = ttk.Scrollbar(quadro_d, orient="vertical", command=cv.yview)
    sx = ttk.Scrollbar(quadro_d, orient="horizontal", command=cv.xview)
    cv.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
    sy.pack(side="right", fill="y")
    sx.pack(side="bottom", fill="x")
    cv.pack(fill="both", expand=True)

    def desenhar_diagrama():
        cv.delete("all")
        if not os.path.exists(caminho_png):
            cv.create_text(20, 20, anchor="nw", font=("Segoe UI", 12), fill=COR["bad"],
                           text="Arquivo diagrama_estados.png nao encontrado na pasta do projeto.")
            return
        try:
            base = tk.PhotoImage(file=caminho_png)
            zoom["img"] = base.subsample(zoom["f"], zoom["f"]) if zoom["f"] > 1 else base
            cv.create_image(0, 0, anchor="nw", image=zoom["img"])
            cv.configure(scrollregion=(0, 0, zoom["img"].width(), zoom["img"].height()))
        except tk.TclError as e:
            cv.create_text(20, 20, anchor="nw", text=f"Nao foi possivel abrir a imagem: {e}")

    def mudar_zoom(delta):
        zoom["f"] = max(1, min(4, zoom["f"] + delta))
        desenhar_diagrama()

    desenhar_diagrama()

    entrada.bind("<Return>", executar)
    entrada.focus_set()
    root.mainloop()


def principal(argv=None):
    ap = argparse.ArgumentParser(description="Simulador de Maquina de Turing deterministica (fita unica).")
    ap.add_argument("arquivo", nargs="?", default=None,
                    help="arquivo .txt da maquina (omita tudo para abrir a interface grafica)")
    ap.add_argument("entrada", nargs="?", default=None,
                    help="cadeia de entrada (omita para digitar; Enter vazio = cadeia vazia)")
    ap.add_argument("-m", "--max-passos", type=int, default=LIMITE_PADRAO,
                    help=f"limite maximo de passos (padrao {LIMITE_PADRAO})")
    ap.add_argument("-q", "--silencioso", action="store_true", help="nao imprime o trace")
    ap.add_argument("-d", "--delay", type=float, default=0.0, help="pausa (s) entre passos do trace")
    args = ap.parse_args(argv)

    if args.arquivo is None:
        padrao = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maquina_ww.txt")
        try:
            abrir_interface(padrao)
            return 0
        except ImportError:
            print("[AVISO] tkinter nao encontrado; usando o modo terminal.")
            args.arquivo = padrao

    try:
        maquina = MaquinaTuring.carregar(args.arquivo)
    except ErroConfiguracao as e:
        print(f"[ERRO DE CONFIGURACAO] {e}", file=sys.stderr)
        return 2

    print(maquina.resumo())

    entrada = args.entrada
    if entrada is None:
        entrada = input("\nDigite a cadeia de entrada (Enter = vazia): ").strip()

    try:
        r = simular(maquina, entrada, args.max_passos, trace=not args.silencioso, pausa=args.delay)
    except ErroEntrada as e:
        print(f"[ERRO DE ENTRADA] {e}", file=sys.stderr)
        return 2

    print("-" * 64)
    print(f"RESULTADO : {r.veredito}")
    print(f"Motivo    : {r.motivo}")
    print(f"Passos    : {r.passos}")
    print(f"Fita final: '{r.fita_final}'")
    return 0 if r.veredito == Resultado.ACEITA else 1


if __name__ == "__main__":
    sys.exit(principal())