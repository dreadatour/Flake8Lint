# -*- coding: utf-8 -*-
import _ast
import sys

from flake8_harobed.pyflakes import Checker
from flake8_harobed.util import skip_warning

try:
    from compiler import parse   # noqa
    iter_child_nodes = None  # noqa
except ImportError:
    from ast import parse, iter_child_nodes  # noqa
from flake8_harobed.mccabe import PathGraphingAstVisitor, WARNING_CODE


def pyflakes_check(codeString, filename='(code)'):
    """
    This is a monkey-patch for flake8.pyflakes.check.

    Return array of errors instead of print them into STDERR.
    """
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError:
        # Return syntax error
        value = sys.exc_info()[1]
        return [(value.lineno, value.offset, value.args[0])]
    else:
        # Okay, it's syntactically valid.  Now check it.
        w = Checker(tree, filename)
        sorting = [(msg.lineno, msg) for msg in w.messages]
        sorting.sort()
        w.messages = [msg for index, msg in sorting]

        result = []
        for warn in w.messages:
            if skip_warning(warn):
                continue
            result.append((warn.lineno, 0, warn.message % warn.message_args))
        return result


def mccabe_get_code_complexity(code, min=7, filename='stdin'):
    """
    This is a monkey-patch for flake8.pyflakes.check.

    Return array of errors instead of print them into STDERR.
    """
    result = []
    try:
        ast = parse(code)
    except (AttributeError, SyntaxError):
        value = sys.exc_info()[1]
        return [(value.lineno, value.offset, value.args[0])]

    visitor = PathGraphingAstVisitor()
    visitor.preorder(ast, visitor)
    for graph in visitor.graphs.values():
        if graph is None or graph.complexity() < min:
            continue
        result.append((graph.lineno, 0, '%s %r is too complex (%d)' % (
            WARNING_CODE, graph.entity, graph.complexity()
        )))
    return result
