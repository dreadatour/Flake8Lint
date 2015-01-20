# -*- coding: utf-8 -*-
"""
Flake8 lint helpers.
"""
import mccabe
import pep8ext_naming
from pep8 import readlines

try:
    import ast
except ImportError:  # Python 2.5
    from flake8.util import ast


def compile_file(filename):
    """
    Compile file and return AST tree.
    """
    try:
        lines = readlines(filename)
    except IOError:
        return
    else:
        code = ''.join(lines)

    try:
        return compile(code, '', 'exec', ast.PyCF_ONLY_AST, True)
    except (SyntaxError, TypeError):
        return


def lint_mccabe(filename, tree, threshold=7):
    """
    Lint file with mccabe complexity check.
    """
    mccabe.McCabeChecker.max_complexity = threshold
    checker = mccabe.McCabeChecker(tree, filename)

    return ((err[0], err[1], err[2]) for err in checker.run())


def lint_pep8_naming(filename, tree):
    """
    Lint file with pep8-naming.
    """
    checker = pep8ext_naming.NamingChecker(tree, filename)

    return ((err[0], err[1], err[2]) for err in checker.run())
