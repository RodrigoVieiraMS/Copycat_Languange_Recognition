# Simulador de Máquina de Turing — Equipe 4
**Disciplina:** Aspectos Teóricos da Computação — Prof. Rafael Teixeira de Araújo
**Tema:** Reconhecedor de Linguagem Cópia — `L = { ww | w ∈ {a,b}* }`
**Linguagem do código:** Python 3 (sem bibliotecas externas)

---

# PARTE 1 — Como rodar e como funciona o arquivo

## 1.1 Arquivos do projeto

| Arquivo | Para que serve |
|---|---|
| `simulador_mt.py` | **Motor do simulador**: fita infinita, leitura/validação do `.txt`, execução, trace e limite de passos |
| `maquina_ww.txt` | **A MT da equipe** (regras de transição no layout exato do enunciado) |
| `testes.py` | Bateria de testes automáticos (casos fixos + teste exaustivo + erros + loop) |
| `gerar_diagrama.py` | Gera o diagrama de estados (`diagrama_estados.png`) a partir do próprio `.txt` |
| `diagrama_estados.png/.svg` | Grafo de estados pronto para o slide |
| `REVISAO_PROJETO.pdf` | Revisão completa: teoria, código, perguntas de arguição e o que estudar |

## 1.2 Requisitos
- **Python 3.8 ou superior.** Nada para instalar (só biblioteca padrão).
- (Opcional) Graphviz (`dot`) apenas se quiser regerar o diagrama.

## 1.3 Como rodar

```bash
# Forma geral
python simulador_mt.py <arquivo_da_maquina.txt> [cadeia] [opções]

# Exemplos
python simulador_mt.py maquina_ww.txt abab          # ACEITA  (w = ab)
python simulador_mt.py maquina_ww.txt abba          # REJEITA
python simulador_mt.py maquina_ww.txt aba           # REJEITA (tamanho ímpar)
python simulador_mt.py maquina_ww.txt               # pergunta a cadeia (Enter vazio = cadeia vazia ε)
python simulador_mt.py maquina_ww.txt abaaba -q     # sem trace, só o resultado
python simulador_mt.py maquina_ww.txt abab -d 0.3   # trace com pausa de 0,3 s por passo (bom para a apresentação)
python simulador_mt.py maquina_ww.txt abab -m 20    # limite de 20 passos (demonstra o aborto por loop/limite)

# Rodar todos os testes
python testes.py
```

> No Windows use `python` ou `py` no lugar de `python3`. Para testar a cadeia vazia, rode **sem** passar a cadeia e aperte Enter (PowerShell costuma descartar `""` como argumento).

### Opções

| Opção | Significado |
|---|---|
| `-q`, `--silencioso` | não imprime o passo a passo |
| `-m N`, `--max-passos N` | limite máximo de passos (padrão **100000**, como pede o enunciado) |
| `-d S`, `--delay S` | pausa de S segundos entre passos do trace |

### Códigos de saída
`0` = aceita · `1` = rejeita ou limite excedido · `2` = erro de configuração/entrada

## 1.4 O que o programa imprime (trace)

A cada passo aparecem: **nº do passo**, **estado atual**, **transição aplicada**, a **fita** e uma **seta `^` sob a célula onde está o cabeçote**. Exemplo real (`aba`, rejeitada):

```
Passo     0 | estado: q0        <- configuracao inicial
    B a b a B
      ^
Passo     1 | estado: q1        <- d(q0,a) = (q1,X,R)
    B X b a B
        ^
 ...
Passo    12 | estado: q_rejeita <- d(q2,Y) = (q_rejeita,Y,S)
    B X Y U B B
        ^
----------------------------------------------------------------
RESULTADO : REJEITA
Motivo    : chegou ao estado de rejeicao 'q_rejeita'
Passos    : 12
Fita final: 'XYU'
```

Os `B` nas pontas mostram a fita crescendo dinamicamente com brancos.

## 1.5 Como o arquivo `.txt` funciona (layout do enunciado)

O simulador **não tem nenhuma regra fixa no código**: tudo vem do arquivo. Linhas que começam com `;` são comentários; linhas vazias são ignoradas. As **6 primeiras linhas úteis** são o cabeçalho, nesta ordem; depois vêm as transições.

| # | Conteúdo | No nosso arquivo |
|---|---|---|
| 1 | Lista de estados (separados por vírgula) | `q0,q1,q2,q3,q4,q5,q6,q7,q_aceita,q_rejeita` |
| 2 | Alfabeto de entrada | `a,b` |
| 3 | Alfabeto da fita | `a,b,X,Y,U,V,Z,B` |
| 4 | Símbolo de branco | `B` |
| 5 | Estado inicial | `q0` |
| 6 | Estados finais (aceitação/parada) | `q_aceita` |
| 7+ | Transições: `Origem, Lê, Escreve, Direção, Destino` | `q0,a,X,R,q1` … |

- **Direção:** `R` (direita), `L` (esquerda) ou `S` (fica parado).
- `q0,a,X,R,q1` significa: *no estado q0 lendo `a`, escreva `X`, mova à direita e vá para q1.*
- **Aceitar:** chegar a um estado final → para e aceita.
- **Rejeitar:** a máquina **trava** (não existe transição para o par estado/símbolo) em estado não final. Nós ainda criamos o estado `q_rejeita` (sem transições de saída) para o diagrama ficar explícito.
- **Loop:** se passar do limite de passos → aborta com `LIMITE_EXCEDIDO`.

### Validações que o parser faz (tratamento de erros)
Arquivo inexistente · cabeçalho incompleto · transição com ≠ 5 campos · estado de origem/destino não declarado · símbolo fora do alfabeto da fita · direção inválida · **transição duplicada (garante determinismo)** · branco fora do alfabeto da fita ou dentro do alfabeto de entrada · estado inicial/final inexistente · cadeia de entrada com símbolo fora do alfabeto. Cada erro informa o **número da linha**.

## 1.6 Como a máquina `maquina_ww.txt` funciona

**Ideia:** não sabemos onde fica o meio da cadeia, então **primeiro achamos o meio** e **depois comparamos as duas metades** símbolo a símbolo. Tudo é feito **marcando a própria entrada** (nenhuma célula extra é usada além das duas pontas em branco) — ou seja, a MT é, na prática, um **autômato linearmente limitado**.

**Símbolos auxiliares**

| Símbolo | Significado |
|---|---|
| `X` / `Y` | `a` / `b` da **1ª metade** (já marcado) |
| `U` / `V` | `a` / `b` da **2ª metade** (já marcado) |
| `Z` | posição **já comparada** |
| `B` | branco |

**Fase 1 — achar o meio** (estados q0 → q1 → q2 → q3 → q0 …)
Marca o primeiro símbolo livre da esquerda (`a→X`, `b→Y`), corre até o fim, e marca o último símbolo livre da direita (`a→U`, `b→V`). Repete. Se na hora de marcar o da direita só encontrar marcas da esquerda, **sobrou um símbolo sem par ⇒ tamanho ímpar ⇒ rejeita**. Quando o q0 enxerga `U/V`, não há mais símbolo livre: as metades estão definidas.

**Rebobinar** (q4): volta até o branco da esquerda e dá um passo à direita.

**Fase 2 — comparar** (q5, q6, q7)
q5 pega o primeiro símbolo não comparado da 1ª metade, marca com `Z` e **lembra qual era no estado** (q6 = era `a`, q7 = era `b`). Anda à direita pulando `X,Y,Z` até o primeiro `U/V` ainda não comparado. Se for do **mesmo tipo** (q6 com `U`, q7 com `V`) marca `Z` e rebobina; se for diferente ⇒ **rejeita**. Quando q5 só enxerga `Z` até o branco ⇒ tudo coincidiu ⇒ **aceita**.

**Estados**

| Estado | Papel |
|---|---|
| `q0` | marca o 1º símbolo livre da esquerda; se vir `B` (fita vazia) aceita ε; se vir `U/V` termina a Fase 1 |
| `q1` | vai até o fim da fita |
| `q2` | acha e marca o último símbolo livre da direita; vê `X/Y` ⇒ ímpar ⇒ rejeita |
| `q3` | volta até a parte já marcada da esquerda |
| `q4` | rebobina até o começo da fita |
| `q5` | início da comparação; pega o próximo símbolo da 1ª metade |
| `q6` / `q7` | "lembram" `a` / `b` e conferem na 2ª metade |
| `q_aceita` | estado final |
| `q_rejeita` | rejeição (sem transições de saída) |

**Exemplo — `abab`:** `abab → XbaV → XYUV` (Fase 1) `→ ZYZV → ZZZZ` (Fase 2) ⇒ **ACEITA em 39 passos**.

## 1.7 Casos de borda (importante para a arguição)

- **Cadeia vazia (ε) é ACEITA**: `w ∈ {a,b}*` admite `w = ε`, então `ε = εε ∈ L` (1 passo).
- **Tamanho ímpar é sempre rejeitado.**
- ⚠️ **O exemplo do enunciado `ababaabab` tem 9 símbolos (ímpar), logo NÃO pertence a L — nossa MT o rejeita corretamente.** Provavelmente é erro de digitação do enunciado. Convém avisar o professor e mostrar isso na apresentação (a MT rejeita em 75 passos).
- Nº de passos para cadeia aceita `ww` com `|w| = n ≥ 1`: **6n² + 6n + 3** → custo **O(n²)** (comprovado nos testes).
- Com o limite padrão de 100000 passos, a maior cadeia `ww` aceita tem **256 símbolos** (n=128 → 99075 passos). Acima disso use `-m` para aumentar o limite.
- O branco do enunciado é `B`; por isso as marcas usam `X,Y,U,V,Z` (nunca `B`).

---

# PARTE 2 — Texto para os slides (15 minutos)

> Sugestão: ~13 slides, ~1 min cada. Texto já enxuto para colar. Os trechos em *itálico* são sugestão de fala, não precisam ir no slide.

---

### Slide 1 — Capa *(0:30)*
**Simulador de Máquina de Turing Determinística de Fita Única**
Reconhecedor da Linguagem Cópia: `L = { ww | w ∈ {a,b}* }`
Equipe 4 — [nomes dos integrantes]
Aspectos Teóricos da Computação — Prof. Rafael Teixeira de Araújo

---

### Slide 2 — O problema *(1:00)*
**Reconhecer cadeias que são uma palavra seguida dela mesma**
- ✅ Pertencem: `ε`, `aa`, `abab`, `abaaba`, `bbabba`
- ❌ Não pertencem: `a`, `ab`, `aba`, `abba`, `aabb`
- Cada símbolo da 2ª metade precisa ser **igual**, **na mesma ordem**, ao da 1ª metade
- Desafio: **não sabemos onde fica o meio**

*Fala: lembrar que `ε ∈ L`, pois w pode ser vazio.*

---

### Slide 3 — Por que é interessante (teoria) *(1:00)*
- `{wwᴿ}` (espelho) → **Livre de Contexto**: uma **pilha** (LIFO) casa perfeitamente
- `{ww}` (cópia) → **não é livre de contexto**: precisaria de **fila** (FIFO); as dependências se **cruzam**
- `{ww}` é **Sensível ao Contexto** (Tipo 1) → reconhecida por um **Autômato Linearmente Limitado**
- Nossa MT usa **apenas o espaço da entrada**: marca os símbolos sobre a própria fita

---

### Slide 4 — Arquitetura do simulador *(1:00)*
```
arquivo .txt ──► Parser + Validação ──► MaquinaTuring (δ)
                                              │
 cadeia de entrada ──► Fita ──► Laço de simulação ──► Resultado
                                   │
                                   └──► Trace no console
```
- **Nenhuma regra no código**: tudo lido do `.txt` (layout do enunciado)
- Máquina **determinística**: `δ(estado, símbolo) → (escreve, direção, novo estado)`
- Linguagem: Python 3

---

### Slide 5 — Defesa da arquitetura: a fita infinita *(1:30)*
**Estrutura de dados: dicionário esparso `{posição → símbolo}`**
- Posições são **inteiros quaisquer** (…, −2, −1, 0, 1, 2, …) ⇒ cresce para **os dois lados**
- **Sem limite de array**: não há tamanho pré-alocado
- Célula nunca escrita = **branco `B`** implícito (não ocupa memória)
- Escrever `B` **remove** a chave ⇒ **sem vazamento de memória**
- Leitura/escrita em **O(1)**
- Memória ∝ nº de células **não brancas**, não ao quanto o cabeçote andou

*Fala: alternativa seria deque/duas listas; escolhemos o dicionário pela simplicidade do índice negativo.*

---

### Slide 6 — Mecanismo de parada *(1:00)*
| Situação | Resultado |
|---|---|
| Chega a **estado final** | **ACEITA** |
| **Não há transição** para (estado, símbolo) | **REJEITA** (máquina trava) |
| Passa de **100.000 passos** | **ABORTA** — possível loop infinito |
- Limite configurável (`-m`)
- Validações: arquivo, estados, símbolos, direção, **determinismo**, entrada fora do alfabeto

---

### Slide 7 — Estratégia da MT *(1:00)*
**Duas fases, tudo marcando a própria entrada**
1. **Achar o meio**: marca um símbolo da esquerda e um da direita, repetindo até se encontrarem
   - sobrou um sozinho ⇒ tamanho ímpar ⇒ **rejeita**
2. **Comparar**: pega o 1º símbolo da 1ª metade, **lembra no estado**, confere com o 1º da 2ª metade; repete
   - diferente ⇒ **rejeita** · tudo igual ⇒ **aceita**

Marcas: `X,Y` (a,b da 1ª metade) · `U,V` (a,b da 2ª metade) · `Z` (comparado)

---

### Slide 8 — Passo a passo com `abab` *(1:30)*
| Momento | Fita | Passo |
|---|---|---|
| Início | `abab` | 0 |
| 1ª rodada da Fase 1 | `XbaV` | 9 |
| Fim da Fase 1 (metades definidas) | `XYUV` | 16 |
| 1ª comparação ok (a = a) | `ZYZV` | 26 |
| 2ª comparação ok (b = b) | `ZZZZ` | 34 |
| **ACEITA** | `ZZZZ` | 39 |

Contra-exemplo `abba`: `XYVU` → compara `a` com `V` (b) ⇒ **REJEITA** (passo 23)

---

### Slide 9 — Diagrama de estados *(1:30)*
*(inserir `diagrama_estados.png`)*
- **Azul** (q0–q3): Fase 1 — achar o meio
- **Amarelo** (q4): rebobinar
- **Verde** (q5–q7): Fase 2 — comparar (`q6` lembra `a`, `q7` lembra `b`)
- **q_aceita** (duplo círculo) e **q_rejeita**
- Rótulo `lê/escreve,dir` · `=` significa "reescreve o mesmo símbolo"

---

### Slide 10 — Tabela de estados *(0:45)*
| Estado | Função |
|---|---|
| q0 | marca 1º livre da esquerda; vazio ⇒ aceita |
| q1 | vai ao fim da fita |
| q2 | marca último livre da direita; ímpar ⇒ rejeita |
| q3 | volta à parte marcada |
| q4 | rebobina ao início |
| q5 | pega próximo símbolo da 1ª metade |
| q6 / q7 | lembram `a` / `b` e comparam |

10 estados · 8 símbolos de fita · 46 transições

---

### Slide 11 — Execução ao vivo *(2:00)*
| Entrada | Esperado | Passos |
|---|---|---|
| `abab` | ✅ aceita | 39 |
| `abaaba` | ✅ aceita | 75 |
| `ε` (vazia) | ✅ aceita | 1 |
| `abba` | ❌ rejeita (metades diferentes) | 23 |
| `aba` | ❌ rejeita (tamanho ímpar) | 12 |
| `ababaabab` | ❌ rejeita (9 símbolos — ímpar) | 75 |
| `abc` | ⚠️ erro: símbolo fora do alfabeto | — |
| `abab -m 20` | ⏹ limite de passos excedido | 20 |

*Rodar:* `python simulador_mt.py maquina_ww.txt abab -d 0.3`

---

### Slide 12 — Testes e complexidade *(1:00)*
- Teste **exaustivo**: **8.191 cadeias** de `{a,b}*` (tamanho 0 a 12) comparadas com verificação independente ⇒ **0 divergências**
- Tempo: **O(n²)** — cadeia aceita `ww` com |w| = n gasta **6n² + 6n + 3** passos
- Espaço: **O(n)** — só a entrada, sem células extras (comportamento de ALL)
- Limite de 100.000 passos comporta cadeias de até **256 símbolos**

---

### Slide 13 — Conclusão *(0:45)*
- Simulador **genérico**: qualquer MT determinística de fita única, via `.txt`
- Fita infinita **sem vazamento**, parada correta, trace completo, validações
- MT `{ww}` **correta** (provada por teste exaustivo) e **O(n²)**
- Nota: o exemplo `ababaabab` do enunciado tem tamanho ímpar — a máquina o rejeita

---

### Slide 14 — Perguntas *(sobra do tempo)*
**Obrigado! Dúvidas?**
