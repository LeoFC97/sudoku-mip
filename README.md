# Sudoku por Programação Inteira (Python-MIP)

Resolve **qualquer Sudoku 9×9** formulando-o como um problema de Programação
Linear Inteira e resolvendo-o com o [Python-MIP](https://www.python-mip.com/)
(solver CBC, incluído no pacote).

## Modelo matemático

### Variáveis de decisão — 729 binárias

$$
x_{K,i,j} =
\begin{cases}
1, & \text{se o número } K \text{ aparece na célula } (i, j) \\
0, & \text{caso contrário}
\end{cases}
\qquad K, i, j \in \{1, \dots, 9\}
$$

No código cada variável recebe o nome `x_K_i_j` (por exemplo, `x_5_1_1` = "o
número 5 está na linha 1, coluna 1").

### Pistas — variáveis fixadas em 1

Para cada célula $(i, j)$ já preenchida com o número $K$ no enunciado, a
variável correspondente é fixada: $x_{K,i,j} = 1$. No código isso é feito pelos
limites da variável (`lb = ub = 1`), sem acrescentar restrições ao modelo. As
demais variáveis daquela célula ficam automaticamente iguais a 0 por causa da
restrição (1).

### Restrições — 4 grupos × 81 = 324 igualdades

| # | Grupo | Restrição | Para todo | Qtde |
|---|-------|-----------|-----------|------|
| 1 | Em cada célula aparece exatamente 1 número | $\displaystyle\sum_{K=1}^{9} x_{K,i,j} = 1$ | $i, j$ | 81 |
| 2 | Em cada linha o número $K$ aparece exatamente 1 vez | $\displaystyle\sum_{j=1}^{9} x_{K,i,j} = 1$ | $K, i$ | 81 |
| 3 | Em cada coluna o número $K$ aparece exatamente 1 vez | $\displaystyle\sum_{i=1}^{9} x_{K,i,j} = 1$ | $K, j$ | 81 |
| 4 | Em cada subquadrado o número $K$ aparece exatamente 1 vez | $\displaystyle\sum_{(i,j)\in Q} x_{K,i,j} = 1$ | $K$, subquadrado $Q$ | 81 |

O subquadrado $Q_{a,b}$ ($a, b \in \{0,1,2\}$) é o conjunto de células
$\{(i,j) : 3a < i \le 3a+3,\; 3b < j \le 3b+3\}$.

### Função objetivo

Não há: trata-se de um **problema de viabilidade**. Qualquer solução inteira
que satisfaça as 324 restrições é uma solução do Sudoku. Por isso o modelo é
criado com `Model("sudoku")` sem objetivo e com
`emphasis = SearchEmphasis.FEASIBILITY`.

Se as pistas forem incompatíveis entre si, o solver devolve o status
`INFEASIBLE` — o Sudoku não tem solução.

## Estrutura do projeto

```
sudoku-mip/
├── sudoku_mip.py          # modelo + solver + interface de linha de comando
├── sudoku_mip.ipynb       # a mesma solução em formato notebook (Jupyter/Colab), já executado
├── test_sudoku_mip.py     # 18 testes (unittest / pytest)
├── requirements.txt
├── README.md
└── exemplos/
    ├── classico.txt         # exemplo clássico (30 pistas)
    ├── classico_modelo.lp   # o modelo desse exemplo exportado (729 variáveis, 324 restrições)
    ├── dificil.txt          # "o Sudoku mais difícil do mundo" (Arto Inkala, 21 pistas)
    ├── 17_pistas.txt        # Sudoku com o mínimo de pistas para solução única
    ├── vazio.txt            # grade vazia (infinitas soluções — demonstra --unica)
    └── inviavel.txt         # pistas incompatíveis (dois 5 na linha 1) → INFEASIBLE
```

O notebook `sudoku_mip.ipynb` é autocontido (não depende de `sudoku_mip.py`) e pode ser
aberto diretamente no Google Colab — a primeira célula instala o Python-MIP se necessário.

## Instalação

Requer Python 3.8+.

```bash
pip install -r requirements.txt      # instala o Python-MIP (já traz o solver CBC)
```

## Uso

```bash
python sudoku_mip.py exemplos/classico.txt            # problema em arquivo
python sudoku_mip.py -                                # problema pela entrada padrão
python sudoku_mip.py --string "53..7....6..195...."   # problema como texto (81 caracteres)
python sudoku_mip.py --exemplo                        # exemplo embutido
python sudoku_mip.py exemplos/classico.txt --unica    # verifica se a solução é única
python sudoku_mip.py exemplos/classico.txt --lp modelo.lp   # exporta o modelo em formato LP
python sudoku_mip.py exemplos/classico.txt --verbose  # mostra o log do CBC
```

**Formato de entrada**: 81 símbolos, em uma ou em várias linhas. Dígitos `1`–`9`
são pistas; `0 . _ * ?` marcam célula vazia; espaços e os separadores `| - + =`
são ignorados. Os três formatos abaixo são equivalentes:

```
53..7....                5 3 . | . 7 . | . . .
6..195...                6 . . | 1 9 5 | . . .
.98....6.                . 9 8 | . . . | . 6 .
8...6...3                ------+-------+------
4..8.3..1                8 . . | . 6 . | . . 3        53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79
7...2...6                4 . . | 8 . 3 | . . 1
.6....28.                7 . . | . 2 . | . . 6
...419..5                ------+-------+------
....8..79                . 6 . | . . . | 2 8 .
                         . . . | 4 1 9 | . . 5
                         . . . | . 8 . | . 7 9
```

### Exemplo de saída

```
$ python sudoku_mip.py exemplos/classico.txt --unica
Modelo : 729 variáveis binárias, 324 restrições, 30 variáveis fixadas em 1 (pistas)
Status : OPTIMAL   (tempo de resolução: 0.739 s)

Problema                   Solução
5 3 . | . 7 . | . . .      5 3 4 | 6 7 8 | 9 1 2
6 . . | 1 9 5 | . . .      6 7 2 | 1 9 5 | 3 4 8
. 9 8 | . . . | . 6 .      1 9 8 | 3 4 2 | 5 6 7
------+-------+------      ------+-------+------
8 . . | . 6 . | . . 3      8 5 9 | 7 6 1 | 4 2 3
4 . . | 8 . 3 | . . 1      4 2 6 | 8 5 3 | 7 9 1
7 . . | . 2 . | . . 6      7 1 3 | 9 2 4 | 8 5 6
------+-------+------      ------+-------+------
. 6 . | . . . | 2 8 .      9 6 1 | 5 3 7 | 2 8 4
. . . | 4 1 9 | . . 5      2 8 7 | 4 1 9 | 6 3 5
. . . | . 8 . | . 7 9      3 4 5 | 2 8 6 | 1 7 9

Solução em 81 caracteres: 534678912672195348198342567859761423426853791713924856961537284287419635345286179
Verificação independente : OK — solução válida e compatível com as pistas
Unicidade                : a solução é ÚNICA
```

### Uso como biblioteca

```python
from sudoku_mip import ler_grade, resolver, verificar, formatar_grade

grade = ler_grade("8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..")
status, solucao, modelo = resolver(grade)

print(status.name)                 # OPTIMAL
print(formatar_grade(solucao))
print(verificar(solucao, grade))   # True
```

## Como o código monta o modelo (`construir_modelo`)

```python
m = Model("sudoku")                              # sem função objetivo
m.emphasis = SearchEmphasis.FEASIBILITY

# 729 variáveis binárias
x = {(k, i, j): m.add_var(name=f"x_{k}_{i}_{j}", var_type=BINARY)
     for k in VALORES for i in LINHAS for j in COLUNAS}

# pistas: fixadas em 1
for i in LINHAS:
    for j in COLUNAS:
        k = grade[i - 1][j - 1]
        if k:
            x[k, i, j].lb = 1                    # lb = ub = 1  ⇒  x_K_i_j = 1

# (1) célula: 81 restrições
for i in LINHAS:
    for j in COLUNAS:
        m += xsum(x[k, i, j] for k in VALORES) == 1, f"celula_{i}_{j}"

# (2) linha: 81 restrições
for k in VALORES:
    for i in LINHAS:
        m += xsum(x[k, i, j] for j in COLUNAS) == 1, f"linha_{k}_{i}"

# (3) coluna: 81 restrições
for k in VALORES:
    for j in COLUNAS:
        m += xsum(x[k, i, j] for i in LINHAS) == 1, f"coluna_{k}_{j}"

# (4) subquadrado: 81 restrições
for k in VALORES:
    for q, (li, lj) in enumerate(SUBQUADRADOS, start=1):
        m += xsum(x[k, i, j] for i in li for j in lj) == 1, f"subquadrado_{k}_{q}"
```

As restrições recebem nomes (`celula_1_1`, `linha_5_1`, `coluna_5_1`,
`subquadrado_5_1`, …) para que o modelo exportado com `--lp` seja legível — o
arquivo gerado tem exatamente 81 restrições de cada grupo e as pistas aparecem
na seção `Bounds` como `1 <= x_K_i_j <= 1`.

## Verificação de unicidade (`--unica`)

Um bom Sudoku tem solução única. Para verificar, depois de encontrar uma
solução o programa acrescenta ao modelo um **corte** que a exclui,

$$
\sum_{(i,j)} x_{\,s_{ij},\,i,\,j} \le 80 ,
$$

em que $s_{ij}$ é o número que a solução encontrada colocou na célula $(i,j)$,
e resolve novamente. Se o novo modelo for inviável, a solução é única; caso
contrário, a segunda solução é mostrada. (A função `enumerar_solucoes` usa a
mesma ideia para listar várias soluções.) Esse corte é adicional — o modelo
básico continua com as 324 restrições.

## Testes

```bash
python -m unittest -v      # ou: pytest -v
```

Os testes conferem o tamanho do modelo (729 variáveis, 81 restrições em cada um
dos 4 grupos), a fixação das pistas, a leitura dos vários formatos de entrada,
a solução dos exemplos (comparada com a solução conhecida), a detecção de
problema inviável e a verificação de unicidade.
