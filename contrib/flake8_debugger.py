import ast
import tokenize

from sys import stdin

__version__ = '1.4.0'

DEBUGGER_ERROR_CODE = 'T002'


class DebugStatementChecker(object):
    name = 'flake8-debugger'
    version = __version__

    def __init__(self, tree, filename='(none)', builtins=None):
        self.tree = tree
        self.filename = (filename == 'stdin' and stdin) or filename

    def run(self):
        if self.filename == stdin:
            noqa = get_noqa_lines(self.filename)
        else:
            with open(self.filename, 'r') as file_to_check:
                noqa = get_noqa_lines(file_to_check.readlines())

        errors = check_tree_for_debugger_statements(self.tree, noqa)

        for error in errors:
            yield (error.get("line"), error.get("col"), error.get("message"), type(self))


def get_noqa_lines(code):
    tokens = tokenize.generate_tokens(lambda L=iter(code): next(L))
    noqa = [token[2][0] for token in tokens if token[0] == tokenize.COMMENT and (token[1].endswith('noqa') or (isinstance(token[0], str) and token[0].endswith('noqa')))]
    return noqa


def check_code_for_debugger_statements(code):
    tree = ast.parse(code)
    noqa = get_noqa_lines(code.split("\n"))
    return check_tree_for_debugger_statements(tree, noqa)


def format_debugger_message(item_type, item_found, name_used):
    return '{0} {1} for {2} found as {3}'.format(DEBUGGER_ERROR_CODE, item_type, item_found, name_used)


def check_tree_for_debugger_statements(tree, noqa):
    errors = []
    debugger_states = {
        'pdb': {
            'found': False,
            'name': None,
            'trace_method': 'set_trace'
        },
        'ipdb': {
            'found': False,
            'name': None,
            'trace_method': 'set_trace'
        },
        'IPython.terminal.embed': {
            'found': False,
            'name': None,
            'trace_method': 'InteractiveShellEmbed'
        },
        'IPython.frontend.terminal.embed': {
            'found': False,
            'name': None,
            'trace_method': 'InteractiveShellEmbed'
        }
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            debuggers_found_here = {}
            for debugger in debugger_states.keys():
                debuggers_found_here[debugger] = False

            if hasattr(node, 'module') and node.module not in debugger_states.keys():
                continue
            elif hasattr(node, 'module'):
                debuggers_found_here[node.module] = True
                debugger_states[node.module]['name'] = node.module
                debugger_states[node.module]['found'] = True

            module_names = (hasattr(node, 'names') and [module_name.name for module_name in node.names]) or []
            if isinstance(node, ast.Import):
                for debugger in debugger_states.keys():
                    if debugger in module_names:
                        index = module_names.index(debugger)
                        if hasattr(node.names[index], 'asname'):
                            debugger_states[debugger]['name'] = node.names[index].asname or debugger
                            debugger_states[debugger]['found'] = True
                            debuggers_found_here[debugger] = True

            elif isinstance(node, ast.ImportFrom):
                trace_methods = [debugger_states[debugger]['trace_method'] for debugger in debugger_states if debugger_states[debugger]['found']]
                traces_found = filter(lambda trace: trace in module_names, trace_methods)
                if not traces_found:
                    continue
                for trace in traces_found:
                    trace_index = trace in module_names and module_names.index(trace)
                    if hasattr(node.names[trace_index], 'asname'):
                        for debugger in debugger_states:
                            if debuggers_found_here[debugger]:
                                debugger_states[debugger]['trace_method'] = node.names[trace_index].asname or debugger_states[debugger]['trace_method']

            if node.lineno not in noqa:
                for debugger in debugger_states.keys():
                    if debuggers_found_here[debugger]:
                        errors.append({
                            'message': format_debugger_message('import', debugger, debugger_states[debugger]['name']),
                            'line': node.lineno,
                            'col': node.col_offset,
                        })

        elif isinstance(node, ast.Call) and node.lineno not in noqa:
            trace_methods = [debugger_states[debugger]['trace_method'] for debugger in debugger_states if debugger_states[debugger]['found']]
            if (getattr(node.func, 'attr', None) in trace_methods or getattr(node.func, 'id', None) in trace_methods):
                debugger_name = None
                for debugger in debugger_states.keys():
                    if (
                        (
                            (hasattr(node.func, 'value') and node.func.value.id == debugger_states[debugger]['name']) or
                            (hasattr(node.func, 'id') and node.func.id == debugger_states[debugger]['trace_method'])
                        ) and debugger_states[debugger]['found']
                    ):
                        debugger_name = debugger_states[debugger]['name']
                        break
                if not debugger_name:
                    debuggers_found = [debugger_states[debugger]['name'] for debugger in debugger_states if debugger_states[debugger]['found']]
                    if len(debuggers_found) == 1:
                        debugger_name = debuggers_found[0]
                    else:
                        debugger_name = 'debugger'
                set_trace_name = hasattr(node.func, 'attr') and node.func.attr or hasattr(node.func, 'id') and node.func.id
                errors.append({
                    "message": format_debugger_message('trace method', debugger_name, set_trace_name),
                    "line": node.lineno,
                    "col": node.col_offset
                })
    return errors
