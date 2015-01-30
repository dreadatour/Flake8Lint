# -*- coding: utf-8 -*-
"""
Flake8 lint worker.
"""
from __future__ import print_function
import os
import sys

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

try:
    from io import TextIOWrapper
except ImportError:
    pass

# Add 'contrib' to sys.path to simulate installation of package 'flake8'
# and it's dependencies: 'pyflake', 'pep8', 'mccabe' and 'pep8-naming'
CONTRIB_PATH = os.path.join(os.path.dirname(__file__), 'contrib')
if CONTRIB_PATH not in sys.path:
    sys.path.insert(0, CONTRIB_PATH)

import ast
import mccabe
import pep8
import pep8ext_naming
import pyflakes.api
from pep257 import PEP257Checker
from pyflakes import checker as pyflakes_checker

from flake8._pyflakes import patch_pyflakes
patch_pyflakes()


if sys.platform.startswith('win'):
    DEFAULT_CONFIG_FILE = os.path.expanduser(r'~\.flake8')
else:
    DEFAULT_CONFIG_FILE = os.path.join(
        os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
        'flake8'
    )
CONFIG_FILES = ('setup.cfg', 'tox.ini', '.pep8')


class Pep8Report(pep8.BaseReport):
    """
    Collect all check results.
    """
    def __init__(self, options):
        """
        Initialize reporter.
        """
        super(Pep8Report, self).__init__(options)
        # errors "collection"
        self.errors = []

    def error(self, line_number, offset, text, check):
        """
        Get error and save it into errors collection.
        """
        code = super(Pep8Report, self).error(line_number, offset, text, check)
        if code:
            self.errors.append((self.line_offset + line_number, offset, text))
        return code


class FlakesReporter(object):
    """
    Formats the results of pyflakes to the linter.
    Example at 'pyflakes.reporter.Reporter' class.
    """
    def __init__(self):
        """
        Construct a Reporter.
        """
        # errors "collection"
        self.errors = []

    def unexpectedError(self, filename, msg):  # noqa
        """
        An unexpected error occurred trying to process filename.
        """
        self.errors.append((0, 0, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):  # noqa
        """
        There was a syntax errror in filename.
        """
        line = text.splitlines()[-1]
        if offset is not None:
            offset = offset - (len(text) - len(line))
            self.errors.append((lineno, offset, msg))
        else:
            self.errors.append((lineno, 0, msg))

    def flake(self, msg):
        """
        Pyflakes found something wrong with the code.
        """
        # unused import has no col attr, seems buggy... this fixes it
        col = getattr(msg, 'col', 0)
        self.errors.append(
            (msg.lineno, col, msg.flake8_msg % msg.message_args)
        )


def load_flake8_config(filename, global_config=False, project_config=False):
    """
    Returns flake8 settings from config file.

    More info: http://flake8.readthedocs.org/en/latest/config.html
    """
    parser = RawConfigParser()

    # check global config
    if global_config and os.path.isfile(DEFAULT_CONFIG_FILE):
        parser.read(DEFAULT_CONFIG_FILE)

    # search config in filename dir and all parent dirs
    if project_config:
        parent = tail = os.path.abspath(filename)
        while tail:
            if parser.read([os.path.join(parent, fn) for fn in CONFIG_FILES]):
                break
            parent, tail = os.path.split(parent)

    result = {}
    if parser.has_section('flake8'):
        options = (
            ('ignore', 'ignore', 'list'),
            ('select', 'select', 'list'),
            ('exclude', 'ignore_files', 'list'),
            ('max_line_length', 'pep8_max_line_length', 'int')
        )
        for config, plugin, option_type in options:
            if not parser.has_option('flake8', config):
                config = config.replace('_', '-')
            if parser.has_option('flake8', config):
                if option_type == 'list':
                    option_value = parser.get('flake8', config).strip()
                    if option_value:
                        result[plugin] = option_value.split(',')
                elif option_type == 'int':
                    option_value = parser.get('flake8', config).strip()
                    if option_value:
                        result[plugin] = parser.getint('flake8', config)
    return result


def lint(lines, settings):
    """
    Run flake8 lint with internal interpreter.
    """
    warnings = []

    # lint with pep8
    if settings.get('pep8', True):
        pep8style = pep8.StyleGuide(
            reporter=Pep8Report,
            ignore=['DIRTY-HACK'],  # PEP8 error will never starts like this
            max_line_length=settings.get('pep8_max_line_length')
        )
        pep8style.input_file(filename=None, lines=lines.splitlines(True))
        warnings.extend(pep8style.options.report.errors)

    if settings.get('pep257', False):
        for error in PEP257Checker().check_source(lines, ''):
            warnings.append((
                getattr(error, 'line', 0),
                0,
                getattr(error, 'message', '')
            ))

    try:
        tree = compile(lines, '', 'exec', ast.PyCF_ONLY_AST, True)
    except (SyntaxError, TypeError):
        (exc_type, exc) = sys.exc_info()[:2]
        if len(exc.args) > 1:
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
        else:
            offset = (1, 0)

        warnings.append((
            offset[0],
            offset[1] or 0,
            'E901 %s: %s' % (exc_type.__name__, exc.args[0])
        ))
    else:
        # lint with pyflakes
        if settings.get('pyflakes', True):
            builtins = settings.get('builtins')
            if builtins:  # builtins is extended
                # some magic (ok, ok, monkey-patching) goes here
                pyflakes.checker.Checker.builtIns = (
                    pyflakes.checker.Checker.builtIns.union(builtins)
                )
            w = pyflakes_checker.Checker(tree)
            w.messages.sort(key=lambda m: m.lineno)

            reporter = FlakesReporter()
            for warning in w.messages:
                reporter.flake(warning)
            warnings.extend(reporter.errors)

        # lint with naming
        if settings.get('naming', True):
            checker = pep8ext_naming.NamingChecker(tree, None)
            for error in checker.run():
                warnings.append(error[0:3])

        try:
            complexity = int(settings.get('complexity', -1))
        except (TypeError, ValueError):
            complexity = -1

        # check complexity
        if complexity > -1:
            mccabe.McCabeChecker.max_complexity = complexity
            checker = mccabe.McCabeChecker(tree, None)
            for error in checker.run():
                warnings.append(error[0:3])

    return sorted(warnings, key=lambda e: '{0:09d}{1:09d}'.format(e[0], e[1]))


def lint_external(lines, settings, interpreter, linter):
    """
    Run flake8 lint with external interpreter.
    """
    import subprocess

    # first argument is interpreter
    arguments = [interpreter, linter]

    # do we need to run pyflake lint
    if settings.get('pyflakes', True):
        arguments.append('--pyflakes')
        builtins = settings.get('builtins')
        if builtins:
            arguments.append('--builtins')
            arguments.append(','.join(builtins))

    # do we need to run pep8 lint
    if settings.get('pep8', True):
        arguments.append('--pep8')
        max_line_length = settings.get('pep8_max_line_length', 79)
        arguments.append('--pep8-max-line-length')
        arguments.append(str(max_line_length))

    # do we need to run pep257 lint
    if settings.get('pep257', False):
        arguments.append('--pep257')

    # do we need to run naming lint
    if settings.get('naming', True):
        arguments.append('--naming')

    # do we need to run complexity check
    complexity = settings.get('complexity', -1)
    arguments.extend(('--complexity', str(complexity)))

    # place for warnings =)
    warnings = []

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # run subprocess
    proc = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=startupinfo
    )
    result = proc.communicate(input=lines.encode('utf-8'))[0]

    # parse STDOUT for warnings and errors
    for line in result.splitlines():
        line = line.decode('utf-8').strip()
        warning = line.split(':', 2)
        if len(warning) == 3:
            try:
                warnings.append((int(warning[0]), int(warning[1]), warning[2]))
            except (TypeError, ValueError):
                print("Flake8Lint ERROR: {0}".format(line))
        else:
            print("Flake8Lint ERROR: {0}".format(line))

    # and return them =)
    return warnings


if __name__ == "__main__":
    import argparse

    # parse arguments
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('--pyflakes', action='store_true',
                            help="run pyflakes lint")
    arg_parser.add_argument('--builtins',
                            help="python builtins extend")
    arg_parser.add_argument('--pep8', action='store_true',
                            help="run pep8 lint")
    arg_parser.add_argument('--pep257', action='store_true',
                            help="run pep257 lint")
    arg_parser.add_argument('--naming', action='store_true',
                            help="run naming lint")
    arg_parser.add_argument('--complexity', type=int,
                            help="check complexity")
    arg_parser.add_argument('--pep8-max-line-length', type=int, default=79,
                            help="pep8 max line length")

    lint_settings = arg_parser.parse_args().__dict__

    if lint_settings.get('builtins'):
        lint_settings['builtins'] = lint_settings['builtins'].split(',')

    if '' == ''.encode():  # Python 2: implicit encoding
        stdin_lines = sys.stdin.read()
    else:  # Python 3
        stdin_lines = TextIOWrapper(sys.stdin.buffer, errors='ignore').read()

    # run lint and print errors
    for lint_warning in lint(stdin_lines, lint_settings):
        try:
            print("%d:%d:%s" % lint_warning)
        except Exception:
            print(lint_warning)
        sys.stdout.flush()
