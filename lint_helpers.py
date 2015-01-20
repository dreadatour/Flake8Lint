# -*- coding: utf-8 -*-
"""
Flake8 lint helpers.
"""
import tokenize
import pep8ext_naming
from mccabe import McCabeChecker

try:
    import ast
except ImportError:   # Python 2.5
    from flake8.util import ast

try:
    from io import TextIOWrapper
except ImportError:
    pass

if '' == ''.encode():
    # Python 2: implicit encoding.
    def readlines(filename):
        """Read the source code."""
        with open(filename, 'rU') as f:
            return f.readlines()
else:
    # Python 3
    def readlines(filename):
        """Read the source code."""
        try:
            with open(filename, 'rb') as f:
                (coding, lines) = tokenize.detect_encoding(f.readline)
                f = TextIOWrapper(f, coding, line_buffering=True)
                return [l.decode(coding) for l in lines] + f.readlines()
        except (LookupError, SyntaxError, UnicodeError):
            # Fall back if file encoding is improperly declared
            with open(filename, encoding='latin-1') as f:
                return f.readlines()


def compile_file(filename):
    """
    Compile file and return AST tree.
    """
    try:
        lines = readlines(filename)
    except IOError:
        return

    try:
        return compile(lines, filename, "exec", ast.PyCF_ONLY_AST)
    except (SyntaxError, TypeError):
        return


def lint_mccabe(filename, tree, threshold=7):
    """
    Lint file with mccabe complexity check.
    """
    complexity = []
    McCabeChecker.max_complexity = threshold
    for lineno, offset, text, check in McCabeChecker(tree, filename).run():
        complexity.append((lineno, offset, text))
    return complexity


def lint_pep8_naming(filename, tree):
    """
    Lint file with pep8-naming.
    """
    warnings = []
    checker = pep8ext_naming.NamingChecker(tree, filename)
    for lineno, col_offset, msg, __ in checker.run():
        warnings.append((lineno, col_offset, msg))
    return warnings
