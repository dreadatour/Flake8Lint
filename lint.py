# -*- coding: utf-8 -*-
import os

# We will use Stéphane Klein fork of flake8 until it not merged into flake8.
# This version includes last version of pep8.
# See: https://bitbucket.org/tarek/flake8/issue/23/use-pep8-configuration-file
from flake8_harobed import pyflakes, pep8, mccabe, util

# Monkey-patching is a big evil (don't do this),
# but hardcode is a much more bigger evil. Hate hardcore!
from monkey_patching import pyflakes_check, mccabe_get_code_complexity
pyflakes.check = pyflakes_check
mccabe.get_code_complexity = mccabe_get_code_complexity


class Pep8Report(pep8.BaseReport):
    """
    Collect all results of the checks.
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


def lint(filename, settings):
    """
    Run flake8 lint with internal interpreter.
    """
    # check if active view contains file
    if not filename or not os.path.exists(filename):
        return

    # skip file check if 'noqa' for whole file is set
    if util.skip_file(filename):
        return

    # place for warnings =)
    warnings = []

    # lint with pyflakes
    if settings.get('pyflakes', True):
        warnings.extend(pyflakes.checkPath(filename))

    # lint with pep8
    if settings.get('pep8', True):
        pep8style = pep8.StyleGuide(reporter=Pep8Report)
        pep8style.input_file(filename)
        warnings.extend(pep8style.options.report.errors)

    # check complexity
    complexity = settings.get('complexity', -1)
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

    # skip file check if 'noqa' for whole file is set
    if util.skip_file(filename):
        return

    # first argument is interpreter
    arguments = [interpreter, linter]

    # do we need to run pyflake lint
    if settings.get('pyflakes', True):
        arguments.append('--pyflakes')

    # do we need to run pep8 lint
    if settings.get('pep8', True):
        arguments.append('--pep8')

    # do we need to run complexity check
    complexity = settings.get('complexity', -1)
    if complexity > 0:
        arguments.extend(('--complexity', str(complexity)))

    # last argument is script to check filename
    arguments.append(filename)

    # place for warnings =)
    warnings = []

    # run subprocess
    proc = subprocess.Popen(arguments, stdout=subprocess.PIPE)

    # parse STDOUT for warnings and errors
    for line in proc.stdout:
        warning = line.strip().split(':', 2)
        if len(warning) == 3:
            warnings.append((int(warning[0]), int(warning[1]), warning[2]))

    # and return them =)
    return warnings


if __name__ == "__main__":
    import argparse

    # parse arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument('--pyflakes', action='store_true',
                        help="run pyflakes lint")
    parser.add_argument('--pep8', action='store_true',
                        help="run pep8 lint")
    parser.add_argument('--complexity', type=int, help="check complexity")

    settings = parser.parse_args().__dict__
    filename = settings.pop('filename')

    # run lint and print errors
    for warning in lint(filename, settings):
        print "%d:%d:%s" % warning
