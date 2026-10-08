# -*- coding: utf-8 -*-
"""
Testes do solver de Sudoku por Programação Inteira (sudoku_mip.py).

Executar:
    python -m unittest -v          # sem dependências extras
    pytest -v                      # se o pytest estiver instalado
"""

import unittest
from pathlib import Path

from mip import OptimizationStatus

from sudoku_mip import (
    N,
    construir_modelo,
    enumerar_solucoes,
    grade_como_string,
    ler_grade,
    resolver,
    verificar,
)

EXEMPLOS = Path(__file__).parent / "exemplos"

CLASSICO = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
CLASSICO_SOLUCAO = ("534678912672195348198342567859761423426853791"
                    "713924856961537284287419635345286179")

DIFICIL = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
DIFICIL_SOLUCAO = ("812753649943682175675491283154237896369845721"
                   "287169534521974368438526917796318452")


class TestLeitura(unittest.TestCase):
    def test_string_de_81_caracteres(self):
        grade = ler_grade(CLASSICO)
        self.assertEqual(len(grade), N)
        self.assertTrue(all(len(linha) == N for linha in grade))
        self.assertEqual(grade[0][:3], [5, 3, 0])
        self.assertEqual(grade[8][8], 9)

    def test_arquivo_com_separadores(self):
        texto = (EXEMPLOS / "classico.txt").read_text(encoding="utf-8")
        self.assertEqual(ler_grade(texto), ler_grade(CLASSICO))

    def test_zero_e_outros_simbolos_de_vazio(self):
        com_zero = CLASSICO.replace(".", "0")
        com_underscore = CLASSICO.replace(".", "_")
        self.assertEqual(ler_grade(com_zero), ler_grade(CLASSICO))
        self.assertEqual(ler_grade(com_underscore), ler_grade(CLASSICO))

    def test_quantidade_errada_de_simbolos(self):
        with self.assertRaises(ValueError):
            ler_grade(CLASSICO[:-1])
        with self.assertRaises(ValueError):
            ler_grade(CLASSICO + "1")

    def test_ida_e_volta(self):
        self.assertEqual(grade_como_string(ler_grade(CLASSICO)), CLASSICO)


class TestModelo(unittest.TestCase):
    def test_tamanho_do_modelo(self):
        """729 variáveis binárias e 4 × 81 = 324 restrições."""
        m, x = construir_modelo(ler_grade(CLASSICO))
        self.assertEqual(len(x), 9 * 9 * 9)
        self.assertEqual(m.num_cols, 729)
        self.assertEqual(m.num_rows, 4 * 81)

    def test_grupos_de_restricoes(self):
        m, _ = construir_modelo(ler_grade(CLASSICO))
        nomes = [c.name for c in m.constrs]
        for prefixo in ("celula_", "linha_", "coluna_", "subquadrado_"):
            self.assertEqual(sum(n.startswith(prefixo) for n in nomes), 81, prefixo)

    def test_nomes_e_tipo_das_variaveis(self):
        m, x = construir_modelo(ler_grade(CLASSICO))
        self.assertEqual(x[5, 1, 1].name, "x_5_1_1")
        self.assertEqual(x[9, 9, 9].name, "x_9_9_9")
        for var in x.values():
            # O CBC armazena variáveis BINARY como inteiras com limites [0, 1]
            self.assertIn(var.var_type, ("B", "I"))
            self.assertEqual(var.ub, 1.0)
            self.assertIn(var.lb, (0.0, 1.0))

    def test_pistas_fixadas_em_um(self):
        grade = ler_grade(CLASSICO)
        _, x = construir_modelo(grade)
        fixadas = {(k, i, j) for (k, i, j), v in x.items() if v.lb == 1}
        esperadas = {(grade[i - 1][j - 1], i, j)
                     for i in range(1, N + 1) for j in range(1, N + 1)
                     if grade[i - 1][j - 1]}
        self.assertEqual(fixadas, esperadas)
        self.assertEqual(len(fixadas), 30)


class TestResolucao(unittest.TestCase):
    def test_classico(self):
        status, solucao, _ = resolver(ler_grade(CLASSICO))
        self.assertEqual(status, OptimizationStatus.OPTIMAL)
        self.assertEqual(grade_como_string(solucao), CLASSICO_SOLUCAO)
        self.assertTrue(verificar(solucao, ler_grade(CLASSICO)))

    def test_dificil(self):
        status, solucao, _ = resolver(ler_grade(DIFICIL))
        self.assertEqual(status, OptimizationStatus.OPTIMAL)
        self.assertEqual(grade_como_string(solucao), DIFICIL_SOLUCAO)
        self.assertTrue(verificar(solucao, ler_grade(DIFICIL)))

    def test_17_pistas(self):
        grade = ler_grade((EXEMPLOS / "17_pistas.txt").read_text(encoding="utf-8"))
        status, solucao, _ = resolver(grade)
        self.assertEqual(status, OptimizationStatus.OPTIMAL)
        self.assertTrue(verificar(solucao, grade))

    def test_grade_vazia_tem_solucao(self):
        grade = ler_grade("." * 81)
        status, solucao, _ = resolver(grade)
        self.assertEqual(status, OptimizationStatus.OPTIMAL)
        self.assertTrue(verificar(solucao))

    def test_inviavel(self):
        """Dois 5 na mesma linha: nenhuma atribuição satisfaz as restrições."""
        grade = ler_grade((EXEMPLOS / "inviavel.txt").read_text(encoding="utf-8"))
        status, solucao, _ = resolver(grade)
        self.assertEqual(status, OptimizationStatus.INFEASIBLE)
        self.assertIsNone(solucao)


class TestUnicidade(unittest.TestCase):
    def test_classico_e_unico(self):
        self.assertEqual(len(enumerar_solucoes(ler_grade(CLASSICO), maximo=2)), 1)

    def test_grade_vazia_tem_varias_solucoes(self):
        solucoes = enumerar_solucoes(ler_grade("." * 81), maximo=3)
        self.assertEqual(len(solucoes), 3)
        self.assertEqual(len({grade_como_string(s) for s in solucoes}), 3)
        self.assertTrue(all(verificar(s) for s in solucoes))


class TestVerificacao(unittest.TestCase):
    def test_detecta_solucao_invalida(self):
        solucao = ler_grade(CLASSICO_SOLUCAO)
        solucao[0][0], solucao[0][1] = solucao[0][1], solucao[0][0]   # troca duas células
        self.assertFalse(verificar(solucao))

    def test_detecta_pista_desrespeitada(self):
        solucao = ler_grade(CLASSICO_SOLUCAO)
        grade = ler_grade(CLASSICO)
        grade[0][2] = 9                                              # pista falsa
        self.assertFalse(verificar(solucao, grade))


if __name__ == "__main__":
    unittest.main(verbosity=2)
