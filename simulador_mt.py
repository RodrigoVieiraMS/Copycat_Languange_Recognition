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
    python simulador_mt.py maquina_ww.txt abab
    python simulador_mt.py maquina_ww.txt            (pergunta a cadeia; Enter = vazia)
    python simulador_mt.py maquina_ww.txt abab -q    (sem trace, so o resultado)
    python simulador_mt.py maquina_ww.txt abab -m 500   (limite de 500 passos)
    python simulador_mt.py maquina_ww.txt abab -d 0.3   (pausa de 0,3 s por passo)
"""

import argparse
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
def principal(argv=None):
    ap = argparse.ArgumentParser(description="Simulador de Maquina de Turing deterministica (fita unica).")
    ap.add_argument("arquivo", help="arquivo .txt com a definicao da maquina")
    ap.add_argument("entrada", nargs="?", default=None,
                    help="cadeia de entrada (omita para digitar; Enter vazio = cadeia vazia)")
    ap.add_argument("-m", "--max-passos", type=int, default=LIMITE_PADRAO,
                    help=f"limite maximo de passos (padrao {LIMITE_PADRAO})")
    ap.add_argument("-q", "--silencioso", action="store_true", help="nao imprime o trace")
    ap.add_argument("-d", "--delay", type=float, default=0.0, help="pausa (s) entre passos do trace")
    args = ap.parse_args(argv)

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
