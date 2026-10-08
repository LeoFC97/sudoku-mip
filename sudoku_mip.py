#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sudoku_mip.py — Resolve qualquer Sudoku 9×9 por Programação Linear Inteira
usando o Python-MIP (solver CBC).

MODELO
======
Variáveis de decisão (9 × 9 × 9 = 729 binárias)

    x_K_i_j ∈ {0, 1}   x_K_i_j = 1  se o número K aparece na célula (i, j)

        K = número   (1..9)
        i = linha    (1..9)
        j = coluna   (1..9)

Pistas (células já preenchidas no enunciado)

    Se a célula (i, j) já contém o número K, a variável x_K_i_j é FIXADA
    em 1 (limite inferior = limite superior = 1). As demais variáveis dessa
    célula ficam iguais a 0 por consequência da restrição (1).

Restrições (4 grupos × 81 = 324 igualdades)

    (1) Célula       Σ_K x_K_i_j = 1              ∀ i, j      → 81 restrições
    (2) Linha        Σ_j x_K_i_j = 1              ∀ K, i      → 81 restrições
    (3) Coluna       Σ_i x_K_i_j = 1              ∀ K, j      → 81 restrições
    (4) Subquadrado  Σ_{(i,j) ∈ Q} x_K_i_j = 1    ∀ K, Q      → 81 restrições
                     (Q percorre os 9 subquadrados 3×3)

Função objetivo

    Nenhuma — é um problema de VIABILIDADE. Qualquer solução inteira que
    satisfaça as 324 restrições é uma solução do Sudoku.

USO
===
    python sudoku_mip.py exemplos/classico.txt          # problema em arquivo
    python sudoku_mip.py -                              # problema pela entrada padrão
    python sudoku_mip.py --string "53..7....6..195..."  # problema como texto
    python sudoku_mip.py --exemplo                      # exemplo embutido
    python sudoku_mip.py exemplos/classico.txt --lp modelo.lp   # exporta o modelo (formato LP)
    python sudoku_mip.py exemplos/classico.txt --unica          # verifica unicidade da solução

Formato de entrada: 81 símbolos, em uma ou em várias linhas. Dígitos 1–9 são
pistas; os símbolos 0 . _ * ? marcam célula vazia; espaços e os separadores
| - + = são ignorados.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, List, Optional, Tuple

from mip import BINARY, Model, OptimizationStatus, SearchEmphasis, Var, xsum

# ---------------------------------------------------------------------------
# Dimensões e índices
# ---------------------------------------------------------------------------
N = 9                       # dimensão da grade (9×9)
B = 3                       # dimensão do subquadrado (3×3)
VALORES = range(1, N + 1)   # K: números 1..9
LINHAS = range(1, N + 1)    # i: linhas 1..9
COLUNAS = range(1, N + 1)   # j: colunas 1..9

# Os 9 subquadrados 3×3, numerados de 1 a 9 (da esquerda para a direita e de
# cima para baixo). Cada um é o par (linhas, colunas) que o compõe.
SUBQUADRADOS: List[Tuple[range, range]] = [
    (range(bi * B + 1, bi * B + B + 1), range(bj * B + 1, bj * B + B + 1))
    for bi in range(B)
    for bj in range(B)
]

Grade = List[List[int]]                        # 9 listas de 9 inteiros; 0 = vazio
Variaveis = Dict[Tuple[int, int, int], Var]    # (K, i, j) -> x_K_i_j

SIMBOLOS_VAZIO = set("0._*?")

STATUS_COM_SOLUCAO = (OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE)


# ---------------------------------------------------------------------------
# Leitura e formatação da grade
# ---------------------------------------------------------------------------
def ler_grade(texto: str) -> Grade:
    """Converte um texto em uma grade 9×9 (0 = célula vazia).

    Aceita qualquer disposição com 81 símbolos: 9 linhas de 9, uma única
    linha de 81, com ou sem espaços e separadores (| - + =).
    """
    simbolos: List[int] = []
    for ch in texto:
        if ch.isdigit():
            simbolos.append(int(ch))          # '0' também cai aqui -> vazio
        elif ch in SIMBOLOS_VAZIO:
            simbolos.append(0)
        # qualquer outro caractere (espaço, quebra de linha, | - + =) é ignorado
    if len(simbolos) != N * N:
        raise ValueError(
            f"Esperados {N * N} símbolos (dígitos ou marcas de vazio), "
            f"encontrados {len(simbolos)}."
        )
    return [simbolos[r * N:(r + 1) * N] for r in range(N)]


def formatar_grade(grade: Grade, vazio: str = ".") -> str:
    """Devolve a grade como texto, com os subquadrados separados."""
    linhas = []
    for r in range(N):
        if r and r % B == 0:
            linhas.append("------+-------+------")
        celulas = [str(v) if v else vazio for v in grade[r]]
        linhas.append(" | ".join(" ".join(celulas[c:c + B]) for c in range(0, N, B)))
    return "\n".join(linhas)


def grade_como_string(grade: Grade) -> str:
    """Devolve a grade como uma única linha de 81 caracteres ('.' = vazio)."""
    return "".join(str(v) if v else "." for linha in grade for v in linha)


def lado_a_lado(esq: str, dir_: str, titulo_esq: str, titulo_dir: str,
                sep: str = "      ") -> str:
    """Coloca dois blocos de texto lado a lado, com títulos."""
    le, ld = esq.splitlines(), dir_.splitlines()
    largura = max(len(l) for l in le)
    saida = [f"{titulo_esq:<{largura}}{sep}{titulo_dir}"]
    saida += [f"{a:<{largura}}{sep}{b}" for a, b in zip(le, ld)]
    return "\n".join(saida)


# ---------------------------------------------------------------------------
# Modelo de Programação Inteira
# ---------------------------------------------------------------------------
def construir_modelo(grade: Grade) -> Tuple[Model, Variaveis]:
    """Monta o modelo PLI do Sudoku: 729 variáveis binárias e 324 restrições.

    Devolve o modelo e o dicionário de variáveis x[(K, i, j)].
    """
    m = Model("sudoku")                        # sem função objetivo: viabilidade
    m.verbose = 0
    m.emphasis = SearchEmphasis.FEASIBILITY    # queremos apenas uma solução viável

    # ---- 729 variáveis binárias x_K_i_j -----------------------------------
    x: Variaveis = {
        (k, i, j): m.add_var(name=f"x_{k}_{i}_{j}", var_type=BINARY)
        for k in VALORES
        for i in LINHAS
        for j in COLUNAS
    }

    # ---- Pistas: variáveis fixadas em 1 ------------------------------------
    for i in LINHAS:
        for j in COLUNAS:
            k = grade[i - 1][j - 1]
            if k:
                x[k, i, j].lb = 1              # lb = ub = 1  ⇒  x_K_i_j = 1

    # ---- (1) Em cada célula aparece exatamente 1 número -------- 81 restrições
    for i in LINHAS:
        for j in COLUNAS:
            m += xsum(x[k, i, j] for k in VALORES) == 1, f"celula_{i}_{j}"

    # ---- (2) Em cada linha o número K aparece exatamente 1 vez - 81 restrições
    for k in VALORES:
        for i in LINHAS:
            m += xsum(x[k, i, j] for j in COLUNAS) == 1, f"linha_{k}_{i}"

    # ---- (3) Em cada coluna o número K aparece exatamente 1 vez  81 restrições
    for k in VALORES:
        for j in COLUNAS:
            m += xsum(x[k, i, j] for i in LINHAS) == 1, f"coluna_{k}_{j}"

    # ---- (4) Em cada subquadrado o número K aparece exatamente 1 vez  81 restr.
    for k in VALORES:
        for q, (li, lj) in enumerate(SUBQUADRADOS, start=1):
            m += xsum(x[k, i, j] for i in li for j in lj) == 1, f"subquadrado_{k}_{q}"

    return m, x


def extrair_solucao(x: Variaveis) -> Grade:
    """Lê os valores das variáveis e devolve a grade resolvida."""
    solucao = [[0] * N for _ in range(N)]
    for (k, i, j), var in x.items():
        if var.x is not None and var.x > 0.5:
            solucao[i - 1][j - 1] = k
    return solucao


def resolver(grade: Grade, max_segundos: float = 60.0, verbose: bool = False,
             arquivo_lp: Optional[str] = None
             ) -> Tuple[OptimizationStatus, Optional[Grade], Model]:
    """Resolve o Sudoku `grade`.

    Devolve (status, solucao, modelo). `solucao` é None se o problema for
    inviável (pistas incompatíveis) ou se o limite de tempo for atingido.
    """
    m, x = construir_modelo(grade)
    m.verbose = int(verbose)
    if arquivo_lp:
        m.write(arquivo_lp)
    status = m.optimize(max_seconds=max_segundos)
    solucao = extrair_solucao(x) if status in STATUS_COM_SOLUCAO else None
    return status, solucao, m


def enumerar_solucoes(grade: Grade, maximo: int = 2,
                      max_segundos: float = 60.0) -> List[Grade]:
    """Devolve até `maximo` soluções distintas do Sudoku `grade`.

    Depois de cada solução encontrada, acrescenta ao modelo um corte que a
    exclui — a soma das 81 variáveis que valem 1 nessa solução deve ser ≤ 80 —
    e resolve novamente. Serve para verificar se a solução é única.
    (Esses cortes são extras; o modelo básico continua com 324 restrições.)
    """
    m, x = construir_modelo(grade)
    solucoes: List[Grade] = []
    while len(solucoes) < maximo:
        status = m.optimize(max_seconds=max_segundos)
        if status not in STATUS_COM_SOLUCAO:
            break
        sol = extrair_solucao(x)
        solucoes.append(sol)
        m += xsum(x[sol[i - 1][j - 1], i, j] for i in LINHAS for j in COLUNAS) <= N * N - 1
    return solucoes


# ---------------------------------------------------------------------------
# Verificação independente do solver
# ---------------------------------------------------------------------------
def verificar(solucao: Grade, grade: Optional[Grade] = None) -> bool:
    """Confere se `solucao` é um Sudoku completo e válido e, se `grade` for
    dada, se ela respeita todas as pistas do problema."""
    alvo = set(VALORES)
    for r in range(N):
        if set(solucao[r]) != alvo:                                   # linhas
            return False
        if {solucao[c][r] for c in range(N)} != alvo:                 # colunas
            return False
    for li, lj in SUBQUADRADOS:                                       # subquadrados
        if {solucao[i - 1][j - 1] for i in li for j in lj} != alvo:
            return False
    if grade is not None:                                             # pistas
        for r in range(N):
            for c in range(N):
                if grade[r][c] and grade[r][c] != solucao[r][c]:
                    return False
    return True


# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------
EXEMPLO = """
5 3 . | . 7 . | . . .
6 . . | 1 9 5 | . . .
. 9 8 | . . . | . 6 .
------+-------+------
8 . . | . 6 . | . . 3
4 . . | 8 . 3 | . . 1
7 . . | . 2 . | . . 6
------+-------+------
. 6 . | . . . | 2 8 .
. . . | 4 1 9 | . . 5
. . . | . 8 . | . 7 9
"""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve um Sudoku 9×9 por Programação Inteira (Python-MIP / CBC).",
        epilog=("Formato de entrada: 81 símbolos em uma ou várias linhas. Dígitos 1-9 são "
                "pistas; 0 . _ * ? marcam célula vazia; espaços e | - + = são ignorados."),
    )
    parser.add_argument("arquivo", nargs="?",
                        help="arquivo com o problema ('-' para ler da entrada padrão)")
    parser.add_argument("-s", "--string", metavar="TEXTO",
                        help="problema como texto (por exemplo, 81 caracteres)")
    parser.add_argument("--exemplo", action="store_true",
                        help="resolve o exemplo embutido")
    parser.add_argument("--lp", metavar="ARQ",
                        help="grava o modelo no formato LP (para inspeção)")
    parser.add_argument("--unica", action="store_true",
                        help="verifica se a solução encontrada é a única")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="mostra o log do solver CBC")
    parser.add_argument("--tempo", type=float, default=60.0, metavar="SEG",
                        help="limite de tempo do solver em segundos (padrão: 60)")
    args = parser.parse_args(argv)

    # ---- origem do problema -------------------------------------------------
    if args.exemplo:
        texto = EXEMPLO
    elif args.string:
        texto = args.string
    elif args.arquivo == "-" or (args.arquivo is None and not sys.stdin.isatty()):
        texto = sys.stdin.read()
    elif args.arquivo:
        with open(args.arquivo, encoding="utf-8") as f:
            texto = f.read()
    else:
        parser.error("informe um arquivo, --string, --exemplo ou envie o problema pela entrada padrão")

    try:
        grade = ler_grade(texto)
    except ValueError as erro:
        parser.error(str(erro))
    n_pistas = sum(1 for linha in grade for v in linha if v)

    # ---- resolução ----------------------------------------------------------
    inicio = time.perf_counter()
    status, solucao, m = resolver(grade, max_segundos=args.tempo,
                                  verbose=args.verbose, arquivo_lp=args.lp)
    tempo = time.perf_counter() - inicio

    print(f"Modelo : {m.num_cols} variáveis binárias, {m.num_rows} restrições, "
          f"{n_pistas} variáveis fixadas em 1 (pistas)")
    print(f"Status : {status.name}   (tempo de resolução: {tempo:.3f} s)")
    if args.lp:
        print(f"Modelo gravado em: {args.lp}")
    print()

    if solucao is None:
        print(formatar_grade(grade))
        print()
        if status == OptimizationStatus.INFEASIBLE:
            print("O problema é INVIÁVEL: as pistas são incompatíveis entre si, "
                  "não existe solução.")
        else:
            print(f"Nenhuma solução encontrada (status {status.name}).")
        return 1

    print(lado_a_lado(formatar_grade(grade), formatar_grade(solucao), "Problema", "Solução"))
    print()
    print(f"Solução em 81 caracteres: {grade_como_string(solucao)}")
    ok = verificar(solucao, grade)
    print("Verificação independente :", "OK — solução válida e compatível com as pistas"
          if ok else "FALHOU")

    if args.unica:
        solucoes = enumerar_solucoes(grade, maximo=2, max_segundos=args.tempo)
        if len(solucoes) == 1:
            print("Unicidade                : a solução é ÚNICA")
        else:
            print("Unicidade                : existe MAIS DE UMA solução; outra solução:")
            print()
            print(formatar_grade(solucoes[1]))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
