#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Maquina de Turing Deterministica de Fita Unica
Disciplina: Aspectos Teoricos da Computacao  -  Prof. Rafael Teixeira de Araujo
Equipe 4 - Reconhecedor da linguagem copia  L = { ww | w em {a,b}* }

Requisitos do trabalho atendidos:
  * Fita infinita nos dois sentidos, crescendo dinamicamente, preenchida com B.
  * NENHUMA regra hardcoded: tudo vem de um arquivo .txt (layout do enunciado).
  * Trace passo a passo no console (estado atual + posicao do cabecote).
  * Aceita / rejeita / para; limite maximo de passos (padrao 100.000) contra loops.

Uso:
    python main.py                           (abre a INTERFACE GRAFICA)
    python main.py maquina_ww.txt abab
    python main.py maquina_ww.txt            (pergunta a cadeia; Enter = vazia)
    python main.py maquina_ww.txt abab -q    (sem trace, so o resultado)
    python main.py maquina_ww.txt abab -m 500   (limite de 500 passos)
    python main.py maquina_ww.txt abab -d 0.3   (pausa de 0,3 s por passo)
"""

import argparse
import os
import sys
import time

LIMITE_PADRAO = 100_000
DIRECOES = ("R", "L", "S")


# ----------------------------------------------------------------------
#  Erros
# ----------------------------------------------------------------------
class ErroConfiguracao(Exception):
    """Erro de formato ou de consistencia no arquivo .txt da maquina."""


class ErroEntrada(Exception):
    """A cadeia de entrada contem simbolos fora do alfabeto de entrada."""


# ----------------------------------------------------------------------
#  Fita infinita
# ----------------------------------------------------------------------
class Fita:
    """
    Fita infinita nos dois sentidos.

    Estrutura de dados: dicionario ESPARSO  { posicao_inteira : simbolo }.
      - Qualquer inteiro (positivo, zero ou negativo) e uma posicao valida,
        entao nao existe limite de array nem indice negativo problematico.
      - Posicao que nunca foi escrita nao ocupa memoria: ler devolve o branco.
      - Escrever o branco REMOVE a chave, logo a memoria usada e proporcional
        ao numero de celulas nao brancas, nunca ao tanto que o cabecote andou.
      - Leitura e escrita sao O(1).
    Alem do dicionario guardamos [menor, maior] posicao ja visitada, apenas
    para o trace saber que trecho da fita imprimir.
    """

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
        # 'S' (stay): fica no lugar
        self.menor = min(self.menor, self.cabecote)
        self.maior = max(self.maior, self.cabecote)

    def conteudo(self):
        """Conteudo nao branco da fita, da primeira a ultima celula usada."""
        if not self.celulas:
            return ""
        ini, fim = min(self.celulas), max(self.celulas)
        return "".join(self.celulas.get(i, self.branco) for i in range(ini, fim + 1))

    def desenhar(self, margem=1):
        """Devolve (linha_da_fita, linha_do_cabecote) para o trace."""
        ini = min(self.menor, self.cabecote) - margem
        fim = max(self.maior, self.cabecote) + margem
        celulas = [self.celulas.get(i, self.branco) for i in range(ini, fim + 1)]
        linha = " ".join(celulas)
        seta = " " * (2 * (self.cabecote - ini)) + "^"
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
        self.delta = {}  # (estado, simbolo) -> (novo_simbolo, direcao, novo_estado)

    # ---------------- leitura do arquivo ----------------
    @classmethod
    def carregar(cls, caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                linhas = f.read().splitlines()
        except FileNotFoundError:
            raise ErroConfiguracao(f"Arquivo '{caminho}' nao encontrado.")
        except OSError as e:
            raise ErroConfiguracao(f"Nao foi possivel ler '{caminho}': {e}")

        # Linhas que comecam com ';' sao comentarios. Linhas vazias sao ignoradas.
        dados = []  # (numero_da_linha, texto)
        for n, bruta in enumerate(linhas, start=1):
            texto = bruta.strip().lstrip("\ufeff")
            if not texto or texto.startswith(";"):
                continue
            dados.append((n, texto))

        if len(dados) < 6:
            raise ErroConfiguracao(
                "Cabecalho incompleto: esperado estados, alfabeto de entrada, "
                "alfabeto da fita, branco, estado inicial e estados finais "
                f"(6 linhas) - encontradas apenas {len(dados)}."
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

    # ---------------- resumo ----------------
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


def simular(maquina, entrada, max_passos=LIMITE_PADRAO, trace=True, pausa=0.0, saida=print):
    """Executa a maquina sobre 'entrada' e devolve um objeto Resultado."""
    for s in entrada:
        if s not in maquina.alfabeto_entrada:
            raise ErroEntrada(
                f"Simbolo '{s}' da entrada nao pertence ao alfabeto de entrada "
                f"{{{', '.join(maquina.alfabeto_entrada)}}}."
            )

    fita = Fita(entrada, maquina.branco)
    estado = maquina.estado_inicial
    passos = 0

    def imprimir(rotulo_transicao=""):
        linha, seta = fita.desenhar()
        saida(f"Passo {passos:>5} | estado: {estado:<10}{rotulo_transicao}")
        saida(f"    {linha}")
        saida(f"    {seta}")
        if pausa:
            time.sleep(pausa)

    if trace:
        saida("=" * 64)
        saida(f"Entrada: '{entrada}'  (tamanho {len(entrada)})")
        saida("=" * 64)
        imprimir("<- configuracao inicial")

    while True:
        # 1) estado final => aceita e para
        if estado in maquina.estados_finais:
            return Resultado(Resultado.ACEITA, passos, estado, fita.conteudo(),
                             f"chegou ao estado final '{estado}'")

        simbolo = fita.ler()
        regra = maquina.delta.get((estado, simbolo))

        # 2) sem transicao definida => a maquina trava => rejeita
        if regra is None:
            if estado == "q_rejeita":
                motivo = "chegou ao estado de rejeicao 'q_rejeita'"
            else:
                motivo = f"sem transicao para ({estado}, {simbolo}) - maquina travou"
            return Resultado(Resultado.REJEITA, passos, estado, fita.conteudo(), motivo)

        # 3) limite de passos => provavel loop infinito
        if passos >= max_passos:
            return Resultado(Resultado.LIMITE, passos, estado, fita.conteudo(),
                             f"limite de {max_passos} passos atingido (possivel loop infinito)")

        # 4) aplica a transicao: escreve, move, muda de estado
        escreve, direcao, destino = regra
        rotulo = f"d({estado},{simbolo}) = ({destino},{escreve},{direcao})"
        fita.escrever(escreve)
        fita.mover(direcao)
        estado = destino
        passos += 1
        if trace:
            imprimir(f"<- {rotulo}")


# ----------------------------------------------------------------------
#  Linha de comando
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
#  Interface grafica (tkinter) - abre com:  python main.py
# ----------------------------------------------------------------------
def abrir_interface(arquivo_padrao):
    import os
    import tkinter as tk
    from tkinter import filedialog, ttk

    MAX_LINHAS = 4000  # evita travar a janela com traces gigantes

    janela = tk.Tk()
    janela.title("Simulador de Maquina de Turing - Equipe 4  (L = ww)")
    janela.geometry("820x640")

    v_arquivo = tk.StringVar(value=arquivo_padrao)
    v_cadeia = tk.StringVar()
    v_trace = tk.BooleanVar(value=True)
    v_limite = tk.StringVar(value=str(LIMITE_PADRAO))

    quadro = ttk.Frame(janela, padding=10)
    quadro.pack(fill="x")

    ttk.Label(quadro, text="Arquivo da maquina (.txt):").grid(row=0, column=0, sticky="w")
    ttk.Entry(quadro, textvariable=v_arquivo, width=60).grid(row=0, column=1, sticky="we", padx=6)

    def procurar():
        c = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if c:
            v_arquivo.set(c)

    ttk.Button(quadro, text="Procurar...", command=procurar).grid(row=0, column=2)

    ttk.Label(quadro, text="Cadeia de entrada:").grid(row=1, column=0, sticky="w", pady=(10, 0))
    entrada = ttk.Entry(quadro, textvariable=v_cadeia, font=("Consolas", 16))
    entrada.grid(row=1, column=1, sticky="we", padx=6, pady=(10, 0))
    quadro.columnconfigure(1, weight=1)

    ttk.Label(quadro, text="(vazio = cadeia vazia)").grid(row=2, column=1, sticky="w", padx=6)

    opcoes = ttk.Frame(janela, padding=(10, 0))
    opcoes.pack(fill="x")
    ttk.Checkbutton(opcoes, text="Mostrar passo a passo (trace)", variable=v_trace).pack(side="left")
    ttk.Label(opcoes, text="   Limite de passos:").pack(side="left")
    ttk.Entry(opcoes, textvariable=v_limite, width=9).pack(side="left", padx=4)

    exemplos = ttk.Frame(janela, padding=(10, 8))
    exemplos.pack(fill="x")
    ttk.Label(exemplos, text="Exemplos:").pack(side="left")
    for ex in ("abab", "abaaba", "abba", "aba", "aa", "a"):
        ttk.Button(exemplos, text=ex, width=7,
                   command=lambda e=ex: (v_cadeia.set(e), executar())).pack(side="left", padx=2)
    ttk.Button(exemplos, text="vazia", width=7,
               command=lambda: (v_cadeia.set(""), executar())).pack(side="left", padx=2)

    botoes = ttk.Frame(janela, padding=(10, 0))
    botoes.pack(fill="x")
    resultado = tk.Label(janela, text="Digite uma cadeia e clique em EXECUTAR", font=("Arial", 15, "bold"),
                         pady=8)

    saida = tk.Text(janela, font=("Consolas", 10), wrap="none", height=18)
    barra = ttk.Scrollbar(janela, command=saida.yview)
    saida.configure(yscrollcommand=barra.set)

    def mostrar(texto):
        saida.configure(state="normal")
        saida.delete("1.0", "end")
        saida.insert("end", texto)
        saida.configure(state="disabled")

    def pintar(texto, cor):
        resultado.configure(text=texto, fg=cor)

    def executar(_evento=None):
        cadeia = v_cadeia.get().strip()
        if cadeia.lower() in ("\u03b5", "eps", "epsilon"):
            cadeia = ""
        try:
            limite = int(v_limite.get())
            if limite < 1:
                raise ValueError
        except ValueError:
            pintar("ERRO: limite de passos invalido", "#b36b00")
            return
        try:
            maquina = MaquinaTuring.carregar(v_arquivo.get().strip())
        except ErroConfiguracao as e:
            pintar("ERRO DE CONFIGURACAO", "#b36b00")
            mostrar(str(e))
            return
        linhas = []
        try:
            r = simular(maquina, cadeia, limite, trace=v_trace.get(), saida=linhas.append)
        except ErroEntrada as e:
            pintar("ERRO DE ENTRADA", "#b36b00")
            mostrar(str(e))
            return
        if len(linhas) > MAX_LINHAS:
            meio = MAX_LINHAS // 2
            linhas = linhas[:meio] + [f"\n... {len(linhas) - MAX_LINHAS} linhas omitidas ...\n"] + linhas[-meio:]
        resumo = [
            "-" * 64,
            f"RESULTADO : {r.veredito}",
            f"Motivo    : {r.motivo}",
            f"Passos    : {r.passos}",
            f"Fita final: '{r.fita_final}'",
        ]
        mostrar("\n".join(linhas + resumo))
        saida.see("end")
        rotulo = f"'{cadeia}'" if cadeia else "(cadeia vazia)"
        if r.veredito == Resultado.ACEITA:
            pintar(f"{rotulo}  ->  ACEITA  ({r.passos} passos)", "#1b7a1b")
        elif r.veredito == Resultado.REJEITA:
            pintar(f"{rotulo}  ->  REJEITA  ({r.passos} passos)", "#b00020")
        else:
            pintar(f"{rotulo}  ->  LIMITE DE PASSOS EXCEDIDO", "#b36b00")

    def limpar():
        v_cadeia.set("")
        resultado.configure(text="Digite uma cadeia e clique em EXECUTAR", fg="black")
        mostrar("")
        entrada.focus_set()

    ttk.Button(botoes, text="EXECUTAR", command=executar).pack(side="left")
    ttk.Button(botoes, text="Limpar", command=limpar).pack(side="left", padx=6)
    resultado.pack(fill="x")
    barra.pack(side="right", fill="y")
    saida.pack(fill="both", expand=True, padx=(10, 0), pady=(0, 10))
    mostrar("")
    entrada.bind("<Return>", executar)
    entrada.focus_set()
    janela.mainloop()


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

    if args.arquivo is None:  # sem argumentos: abre a interface grafica
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
