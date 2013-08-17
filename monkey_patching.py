# -*- coding: utf-8 -*-
"""
Flake8 linters monkey-patching.
"""
try:
    import ast
except ImportError:   # Python 2.5
    from flake8.util import ast
from mccabe import McCabeChecker


def get_code_complexity(code, threshold=7, filename='stdin'):
    """
    This is a monkey-patch for flake8.pyflakes.check.
    Return array of errors instead of print them into STDERR.
    """
    try:
        tree = compile(code, filename, "exec", ast.PyCF_ONLY_AST)
    except SyntaxError:
        # return [(value.lineno, value.offset, value.args[0])]
        # be silent when error, or else syntax errors are reported twice
        return []

    complexity = []
    McCabeChecker.max_complexity = threshold
    for lineno, offset, text, check in McCabeChecker(tree, filename).run():
        complexity.append((lineno, offset, text))
    return complexity
