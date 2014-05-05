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

# Add 'contrib' to sys.path to simulate installation of package 'flake8'
# and it's dependencies: 'pyflake', 'pep8' and 'mccabe'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'contrib'))


import pyflakes.api
import mccabe
import pep8
from pep8 import readlines
from flake8.engine import _flake8_noqa

# Monkey-patching is a big evil (don't do this),
# but hardcode is a much more bigger evil. Hate hardcore!
try:
    from .monkey_patching import get_code_complexity
except (ValueError, SystemError):
    from monkey_patching import get_code_complexity
mccabe.get_code_complexity = get_code_complexity

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


def skip_file(path):
    """
    Returns True if line with special commit is found in path:
    # flake8 : noqa
    """
    try:
        return _flake8_noqa(''.join(readlines(path))) is not None
    except (OSError, IOError):
        return True


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

    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process filename.
        """
        self.errors.append((0, 0, msg))

    def syntaxError(self, filename, msg, lineno, offset, text):
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


def lint(filename, settings):
    """
    Run flake8 lint with internal interpreter.
    """
    # check if active view contains file
    if not filename or not os.path.exists(filename):
        return

    # place for warnings =)
    warnings = []

    # lint with pyflakes
    if settings.get('pyflakes', True):
        builtins = settings.get('builtins')
        if builtins:  # builtins is extended
            # some magic (ok, ok, monkey-patching) goes here
            old_builtins = pyflakes.checker.Checker.builtIns
            pyflakes.checker.Checker.builtIns = old_builtins.union(builtins)

        flakes_reporter = FlakesReporter()
        pyflakes.api.checkPath(filename, flakes_reporter)
        warnings.extend(flakes_reporter.errors)

    # lint with pep8
    if settings.get('pep8', True):
        pep8style = pep8.StyleGuide(
            reporter=Pep8Report,
            ignore=['DIRTY-HACK'],  # PEP8 error will never starts like this
            max_line_length=settings.get('pep8_max_line_length')
        )
        pep8style.input_file(filename)
        warnings.extend(pep8style.options.report.errors)

    # check complexity
    try:
        complexity = int(settings.get('complexity', -1))
    except (TypeError, ValueError):
        complexity = -1

    if complexity > -1:
        warnings.extend(mccabe.get_module_complexity(filename, complexity))

    return warnings


def lint_external(filename, settings, interpreter, linter):
    """
    Run flake8 lint with external interpreter.
    """
    import subprocess

    # check if active view contains file
    if not filename or not os.path.exists(filename):
        return

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

    # do we need to run complexity check
    complexity = settings.get('complexity', -1)
    arguments.extend(('--complexity', str(complexity)))

    # last argument is script to check filename
    arguments.append(filename)

    # place for warnings =)
    warnings = []

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # run subprocess
    proc = subprocess.Popen(arguments, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=startupinfo)

    # parse STDOUT for warnings and errors
    for line in proc.stdout:
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
    parser = argparse.ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument('--pyflakes', action='store_true',
                        help="run pyflakes lint")
    parser.add_argument('--builtins', help="python builtins extend")
    parser.add_argument('--pep8', action='store_true',
                        help="run pep8 lint")
    parser.add_argument('--complexity', type=int, help="check complexity")
    parser.add_argument('--pep8-max-line-length', type=int, default=79,
                        help="pep8 max line length")

    settings = parser.parse_args().__dict__
    filename = settings.pop('filename')

    if settings.get('builtins'):
        settings['builtins'] = settings['builtins'].split(',')

    # run lint and print errors
    for warning in lint(filename, settings):
        try:
            print("%d:%d:%s" % warning)
        except Exception:
            print(warning)
        sys.stdout.flush()
