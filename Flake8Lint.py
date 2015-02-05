# -*- coding: utf-8 -*-
"""
Flake8Lint: Sublime Text plugin.
Check Python files with flake8 (PEP8, pyflake and mccabe)
"""
from __future__ import print_function
import fnmatch
import itertools
import os
import re
import sys
import time

import sublime
import sublime_plugin

try:
    from .color_theme import update_color_scheme
    from .lint import lint, lint_external, load_flake8_config
except (ValueError, SystemError):
    from color_theme import update_color_scheme
    from lint import lint, lint_external, load_flake8_config


# copy-pasted from flake8.engine
FLAKE8_NOQA = re.compile(r'flake8[:=]\s*noqa', re.I).search

# copy-pasted from pep8
COMPARE_SINGLETON_REGEX = re.compile(r'(?:[=!]=)\s*(?:None|False|True)')
COMPARE_NEGATIVE_REGEX = re.compile(r'\b(?:not)\s+[^\[({ ]+\s+(?:in|is)\s')
COMPARE_TYPE_REGEX = re.compile(
    r'(?:[=!]=|is(?:\s+not)?)\s*type(?:s.\w+Type|\s*\(\s*([^)]*[^ )])\s*\))'
)

WHITESPACES = (' ', '\t')
OPERATORS = [
    '**=', '//=', '<<=', '>>=', '==', '!=', '<>', '>=', '<=', '*=', '/=', '%=',
    '+=', '-=', '<<', '>>', '&=', '|=', '^=', '**', '//', '=', '>', '<', '&',
    '|', '^', '~', '%', '*', '/', '+', '-'
]

PROJECT_SETTINGS_KEYS = (
    'python_interpreter', 'builtins', 'pyflakes', 'pep8', 'pep257', 'naming',
    'complexity', 'pep8_max_line_length', 'select', 'ignore', 'ignore_files',
    'use_flake8_global_config', 'use_flake8_project_config',
)
FLAKE8_SETTINGS_KEYS = (
    'ignore', 'select', 'ignore_files', 'pep8_max_line_length'
)

ERRORS_IN_VIEWS = {}
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


settings = None


class Flake8LintSettings(object):
    """
    Flake8Lint settings.
    """
    debug = False

    def __init__(self):
        """
        Initialize settings.
        """
        editor_settings = sublime.load_settings('Preferences.sublime-settings')
        editor_settings.clear_on_change('flake8lint-color-scheme')
        editor_settings.add_on_change('flake8lint-color-scheme',
                                      lambda: update_color_scheme(settings))

        self.settings = sublime.load_settings('Flake8Lint.sublime-settings')
        self.settings.clear_on_change('reload')
        self.settings.add_on_change('reload', self.setup)

        self.setup()

    def setup(self):
        """
        Update settings.
        """
        # debug mode (verbose output to ST python console)
        self.debug = bool(self.settings.get('debug', False))

        # run flake8 lint on file saving
        self.lint_on_save = bool(self.settings.get('lint_on_save', True))

        # run flake8 lint on file loading
        self.lint_on_load = bool(self.settings.get('lint_on_load', False))

        # run lint in live mode: lint file (without popup) every XXX ms
        # please, be careful: this may cause performance issues on ST2
        self.live_mode = bool(self.settings.get('live_mode', False))

        # set live mode lint delay, in milliseconds
        try:
            self.live_mode_lint_delay = int(
                self.settings.get('live_mode_lint_delay', 1000)
            )
        except (ValueError, TypeError):
            self.live_mode_lint_delay = 1000

        # set ruler guide based on max line length setting
        self.set_ruler_guide = bool(
            self.settings.get('set_ruler_guide', False)
        )

        # popup a dialog of detected conditions?
        self.popup = bool(self.settings.get('popup', True))

        # highlight detected conditions?
        self.highlight = bool(self.settings.get('highlight', True))

        # highlight type:
        # - "line" to highlight whole line
        # - "error" to highlight error only
        self.highlight_type = self.settings.get('highlight_type')
        if self.highlight_type != 'line':
            self.highlight_type = 'error'

        # color values to highlight detected conditions
        self.highlight_color_critical = self.settings.get(
            'highlight_color_critical', '#981600'
        )
        self.highlight_color_error = self.settings.get(
            'highlight_color_error', '#DA2000'
        )
        self.highlight_color_warning = self.settings.get(
            'highlight_color_warning', '#EDBA00'
        )

        # show a mark in the gutter on all lines with errors/warnings:
        # - "dot", "circle" or "bookmark" to show marks
        # - "theme-alpha", "theme-bright", "theme-dark", "theme-hard"
        #   or "theme-simple" to show icon marks
        # - "" (empty string) to do not show marks
        all_gutter_marks = (
            'dot', 'circle', 'bookmark', 'theme-alpha', 'theme-bright',
            'theme-dark', 'theme-hard', 'theme-simple', ''
        )
        self.gutter_marks = self.settings.get('gutter_marks')
        if self.gutter_marks not in all_gutter_marks:
            self.gutter_marks = 'theme-simple'

        mark_themes_paths = [
            'Packages', os.path.basename(PLUGIN_DIR), 'gutter-themes'
        ]
        if int(sublime.version()) < 3014:
            mark_themes_paths = (
                [os.path.pardir, os.path.pardir] + mark_themes_paths
            )
        self.mark_themes_dir = '/'.join(mark_themes_paths)

        # report successfull (passed) lint
        self.report_on_success = bool(
            self.settings.get('report_on_success', False)
        )

        # blink gutter marks on success
        self.blink_gutter_marks_on_success = bool(
            self.settings.get('blink_gutter_marks_on_success', True)
        )

        # load global flake8 config ("~/.config/flake8")
        self.use_flake8_global_config = bool(
            self.settings.get('use_flake8_global_config', True)
        )

        # load per-project config
        # (i.e. "tox.ini", "setup.cfg" and ".pep8" files)
        self.use_flake8_project_config = bool(
            self.settings.get('use_flake8_project_config', True)
        )

        # set python interpreter (lint files for python >= 2.7):
        # - 'internal' for use internal Sublime Text interpreter (2.6)
        # - 'auto' for search default system python interpreter (default value)
        # - absolute path to python interpreter for define another one
        #   use platform specific notation,
        #   i.e. "C:\\Anaconda\\envs\\py33\\python.exe"
        #   for Windows or then "/home/whatever/pythondist/python" for Unix
        self.python_interpreter = self.settings.get(
            'python_interpreter', 'auto'
        )

        # list of python built-in functions (like '_')
        self.builtins = self.settings.get('builtins') or []

        # turn on pyflakes error lint
        self.pyflakes = bool(self.settings.get('pyflakes', True))

        # turn on pep8 error lint
        self.pep8 = bool(self.settings.get('pep8', True))

        # turn on pep257 error lint
        self.pep257 = bool(self.settings.get('pep257', False))

        # turn on naming error lint
        self.naming = bool(self.settings.get('naming', True))

        # turn off complexity check (set number > 0 to check complexity level)
        try:
            self.complexity = int(self.settings.get('complexity', -1))
        except (ValueError, TypeError):
            self.complexity = -1

        # set desired max line length
        try:
            self.pep8_max_line_length = int(
                self.settings.get('pep8_max_line_length', 79)
            )
        except (ValueError, TypeError):
            self.pep8_max_line_length = 79

        # select errors and warnings (e.g. ["E", "W6"])
        self.select = self.settings.get('select') or []

        # skip errors and warnings (e.g. ["E303", E4", "W"])
        self.ignore = self.settings.get('ignore') or []

        # files to ignore, for example: ["*.mako", "test*.py"]
        self.ignore_files = self.settings.get('ignore_files') or []


def log(msg, level=None):
    """
    Log to ST python console.

    If log level 'debug' (or None) print only if debug setting is enabled.
    """
    if level is None:
        level = 'debug'

    if level == 'debug' and not settings.debug:
        return

    print("[Flake8Lint {0}] {1}".format(level.upper(), msg))


def isspace(symbol):
    """
    Returns `True` if `symbol` is space or tab.
    """
    return symbol in WHITESPACES


def isname(symbol):
    """
    Returns `True` if `symbol` is part of function, class, etc name.
    """
    return bool(re.match(r'[_a-zA-Z0-9]', symbol))


def operator_next(line, col):
    """
    Check if there is an operator in line, starting from `col`.
    Returns operator length if so.
    """
    line_piece = line[col:col + len(OPERATORS[0])]
    for oper in OPERATORS:
        if line_piece.startswith(oper):
            return len(oper)


def operator_prev(line, col):
    """
    Check if there is an operator in line, ends at `col`.
    Returns operator length if so.
    """
    line_piece = line[col - len(OPERATORS[0]):col]
    for oper in OPERATORS:
        if line_piece.endswith(oper):
            return len(oper)


def find_in_string(pattern, line):
    """
    Find pattern in string and return start and end positions.
    """
    match = re.search(r'\b{0}\b'.format(re.escape(pattern)), line)
    if match:
        func_pos = match.span()[0]
        if func_pos > -1:
            return func_pos


def filename_match(filename, patterns):
    """
    Returns `True` if filename is matched with patterns.
    """
    for path_part in filename.split(os.path.sep):
        if any(fnmatch.fnmatch(path_part, pattern) for pattern in patterns):
            return True
    return False


def skip_line_lint(line):
    """
    Check if we need to skip line check.

    Returns `True` if line ends with '# noqa' or '# NOQA' comment.
    """
    def _noqa(line):
        """
        Check if line ends with 'noqa' comment.
        """
        return line.strip().lower().endswith('# noqa')

    skip = _noqa(line)

    if not skip:
        i = line.rfind(' #')
        skip = _noqa(line[:i]) if i > 0 else False

    return skip


class SublimeStatusBar(object):
    """
    Functions for update Sublime statusbar.

    This is dummy class: simply group all statusbar methods together.
    """
    @staticmethod
    def update(view):
        """
        Update status bar with error.
        """
        # get view errors (exit if no errors found)
        view_errors = ERRORS_IN_VIEWS.get(view.id())
        if view_errors is None:
            return

        # get view selection (exit if no selection)
        view_selection = view.sel()
        if not view_selection:
            return

        current_line = SublimeView.get_current_line(view)
        if current_line is None:
            return

        if current_line in view_errors:
            # there is an error on current line
            errors = view_errors[current_line]
            view.set_status('flake8-tip', 'flake8: %s' % ' / '.join(errors))
        else:
            # no errors - clear statusbar
            SublimeStatusBar.clear(view)

    @staticmethod
    def clear(view):
        """
        Clear status bar flake8 error.
        """
        view.erase_status('flake8-tip')


class SublimeView(object):
    """
    Functions for Sublime view.

    This is dummy class: simply group all view methods together.
    """
    @staticmethod
    def view_settings(view):
        """
        Returns dict with view settings.

        Settings are taken from (see README for more info):
        - ST plugin settings (global, user, project)
        - flake8 settings (global, project)
        """
        result = {}

        # get settings from global (user) plugin settings
        view_settings = view.settings().get('flake8lint') or {}
        for param in PROJECT_SETTINGS_KEYS:
            result[param] = view_settings.get(param, getattr(settings, param))

        global_config = result.get('use_flake8_global_config', True)
        project_config = result.get('use_flake8_project_config', True)

        if global_config or project_config:
            filename = os.path.abspath(view.file_name())

            flake8_config = load_flake8_config(filename, global_config,
                                               project_config)
            for param in FLAKE8_SETTINGS_KEYS:
                if param in flake8_config:
                    result[param] = flake8_config.get(param)

        return result

    @staticmethod
    def get_current_line(view):
        """
        Get current line (line under cursor).
        """
        view_selection = view.sel()

        if not view_selection:
            return None

        point = view_selection[0].end()
        position = view.rowcol(point)

        return position[0]

    @staticmethod
    def set_ruler_guide(view):
        """
        Set view ruler guide.
        """
        if not view.match_selector(0, 'source.python'):
            return

        log("set view ruler guide")

        view_settings = SublimeView.view_settings(view)
        max_line_length = view_settings.get('pep8_max_line_length', 79)

        try:
            max_line_length = int(max_line_length)
        except (TypeError, ValueError):
            log("can't parse 'pep8_max_line_length' setting", level='error')
            max_line_length = 79

        view.settings().set('rulers', [max_line_length])
        log("view ruler guide is set to {0}".format(max_line_length))


class LintReport(object):
    """
    Show window with lint report.
    """
    view = None
    errors_list = []
    errors_to_show = []
    regions = {}

    gutter_mark = ''
    gutter_mark_success = ''
    select = []
    ignore = []
    is_highlight = False
    is_popup = False

    def __init__(self, view, errors_list, view_settings, quiet=False):
        self.view = view
        self.errors_list = errors_list
        self.errors_to_show = []
        self.regions = {'critical': [], 'error': [], 'warning': []}

        self.prepare_settings(view_settings)
        self.prepare_errors(errors_list)

        if self.errors_list:
            self.show_errors(quiet=quiet)
        else:
            self.report_success(quiet=quiet)

    def get_gutter_mark(self):
        """
        Returns gutter mark icon or empty string if marks are disabled.
        """
        # ST does not expect platform specific paths here, but only
        # forward-slash separated paths relative to "Packages"
        self.gutter_mark_success = '/'.join(
            [settings.mark_themes_dir, 'success']
        )
        if int(sublime.version()) >= 3014:
            self.gutter_mark_success += '.png'

        self.gutter_mark = ''

        mark_type = settings.gutter_marks
        if mark_type in ('dot', 'circle', 'bookmark', 'cross'):
            self.gutter_mark = mark_type
        elif mark_type.startswith('theme-'):
            theme = mark_type[6:]
            if theme not in ('alpha', 'bright', 'dark', 'hard', 'simple'):
                log("unknown gutter mark theme: '{0}'".format(mark_type))
                return

            # ST does not expect platform specific paths here, but only
            # forward-slash separated paths relative to "Packages"
            self.gutter_mark = '/'.join(
                [settings.mark_themes_dir, '{0}-{{0}}'.format(theme)]
            )
            if int(sublime.version()) >= 3014:
                self.gutter_mark += '.png'

    def prepare_settings(self, view_settings):
        """
        Get view lint settings.
        """
        self.get_gutter_mark()

        self.select = view_settings.get('select') or []
        self.ignore = view_settings.get('ignore') or []
        self.is_highlight = settings.highlight
        self.is_popup = settings.popup

        log("'select' setting: {0}".format(self.select))
        log("'ignore' setting: {0}".format(self.ignore))
        log("'is_highlight' setting: {0}".format(self.is_highlight))
        log("'is_popup' setting: {0}".format(self.is_popup))

    def error_region(self, full_line_text, line_point, error_msg, error_col):
        """
        Add error region to regions list.
        """
        error_code, error_text = error_msg.split(' ', 1)

        line_text = full_line_text.rstrip('\r\n')
        line_length = len(line_text)

        # highlight whole line by default
        start = line_point
        end = line_point + line_length

        # -- PEP8 -------------------------------------------------------------
        if error_code in ('E101', 'E111', 'E112', 'E113', 'E121', 'E122',
                          'E123', 'E124', 'E125', 'E126', 'E127', 'E128',
                          'E129', 'E131', 'W191'):
            # E101 indentation contains mixed spaces and tabs
            # E111 indentation is not a multiple of four
            # E112 expected an indented block
            # E113 unexpected indentation
            # E121 continuation line under-indented for hanging indent
            # E122 continuation line missing indentation or outdented
            # E123 closing bracket does not match indentation
            #      of opening bracket's line
            # E124 closing bracket does not match visual indentation
            # E125 continuation line with same indent as next logical line
            # E126 continuation line over-indented for hanging indent
            # E127 continuation line over-indented for visual indent
            # E128 continuation line under-indented for visual indent
            # E129 visually indented line with same indent as next logical line
            # E131 continuation line unaligned for hanging indent
            # W191 indentation contains tabs
            start = line_point
            end = line_point + line_length - len(line_text.lstrip())
        elif error_code in ('E201', 'E211', 'E221', 'E222', 'E223', 'E224',
                            'E241', 'E242', 'E251', 'E271', 'E272', 'E273',
                            'E274'):
            # E201 whitespace after 'XXX'
            # E211 whitespace before 'XXX'
            # E221 multiple spaces before operator
            # E222 multiple spaces after operator
            # E223 tab before operator
            # E224 tab after operator
            # E241 multiple spaces after 'XXX'
            # E242 tab after 'XXX'
            # E251 unexpected spaces around keyword / parameter equals
            # E271 multiple spaces after keyword
            # E272 multiple spaces before keyword
            # E273 tab after keyword
            # E274 tab before keyword
            tail = line_text[error_col:]
            start = line_point + error_col
            end = start + sum(1 for __ in itertools.takewhile(isspace, tail))
        elif error_code in ('E202', 'E203'):
            # E202 whitespace before 'XXX'
            # E203 whitespace before 'XXX'
            head = line_text[:error_col + 1][::-1]
            end = line_point + error_col + 1
            start = end - sum(1 for __ in itertools.takewhile(isspace, head))
        elif error_code in ('E225', 'E226', 'E227', 'E228'):
            # E225 missing whitespace around operator
            # E226 missing whitespace around arithmetic operator
            # E227 missing whitespace around bitwise or shift operator
            # E228 missing whitespace around modulo operator
            head = operator_next(line_text, error_col)
            if head:
                start = line_point + error_col
                end = start + head
            else:
                tail = operator_prev(line_text, error_col)
                if tail:
                    end = line_point + error_col
                    start = end - tail
        elif error_code == 'E231':
            # E231 missing whitespace after 'XXX'
            if line_text[error_col] in ',;:':
                start = line_point + error_col
                end = start + 1
        elif error_code == 'E261':
            # E261 at least two spaces before inline comment
            tail = line_text[error_col:]
            start = line_point + error_col
            end = start + sum(1 for __ in itertools.takewhile(isspace, tail))
            if end == start:
                end = line_point + line_length
        elif error_code in ('E262', 'E265'):
            # E262 inline comment should start with '# '
            # E265 block comment should start with '# '
            start = line_point + error_col
            end = line_point + line_length
        elif error_code == 'W291':
            # W291 trailing whitespace
            start = line_point + len(line_text.rstrip())
            end = line_point + line_length
        elif error_code in ('W292', 'W293'):
            # W292 no newline at end of file
            # W293 blank line contains whitespace
            pass  # whole line is highlighted by default
        elif error_code in ('E301', 'E302', 'E303', 'E304'):
            # E301 expected 1 blank line, found XXX
            # E302 expected 2 blank lines, found XXX
            # E303 too many blank lines (XXX)
            # E304 blank lines found after function decorator
            pass  # whole line is highlighted by default
            # TODO: highlight blank lines if any
        elif error_code == 'W391':
            # W391 blank line at end of file
            start = line_point
            end = line_point + len(full_line_text)
        elif error_code == 'E401':
            # E401 multiple imports on one line
            pass  # whole line is highlighted by default
        elif error_code == 'E501':
            # E501 line too long (XXX > YYY characters)
            start = line_point + error_col
            end = line_point + line_length
        elif error_code == 'E502':
            # E502 the backslash is redundant between brackets
            if line_text[error_col] == '\\':
                start = line_point + error_col
                end = start + 1
        elif error_code == 'W601':
            # W601 .has_key() is deprecated, use 'in'
            if line_text[error_col:].startswith('.has_key('):
                start = line_point + error_col + 1
                end = start + 7
        elif error_code == 'W602':
            # W602 deprecated form of raising exception
            pass  # whole line is highlighted by default
        elif error_code == 'W603':
            # W603 '<>' is deprecated, use '!='
            if line_text[error_col:].startswith('<>'):
                start = line_point + error_col
                end = start + 2
        elif error_code == 'W604':
            # W604 backticks are deprecated, use 'repr()'
            pass  # whole line is highlighted by default
        elif error_code == 'E701':
            # E701 multiple statements on one line (colon)
            if line_text[error_col] == ':':
                start = line_point + error_col
                end = line_point + line_length
        elif error_code == 'E702':
            # E702 multiple statements on one line (semicolon)
            if line_text[error_col] == ';':
                start = line_point + error_col
                end = line_point + line_length
        elif error_code == 'E703':
            # E703 statement ends with a semicolon
            if line_text[error_col] == ';':
                start = line_point + error_col
                end = start + 1
        elif error_code in ('E711', 'E712'):
            # E711 comparison to None should be 'XXX'
            # E712 comparison to None should be 'XXX'
            match = COMPARE_SINGLETON_REGEX.search(line_text[error_col:])
            if match:
                start = line_point + error_col
                end = start + len(match.group(0))
        elif error_code in ('E713', 'E714'):
            # E713 test for membership should be 'not in'
            # E714 test for object identity should be 'is not'
            match = COMPARE_NEGATIVE_REGEX.search(line_text[error_col:])
            if match:
                start = line_point + error_col
                end = start + len(match.group(0)) - 1
        elif error_code == 'E721':
            # E721 do not compare types, use 'isinstance()'
            match = COMPARE_TYPE_REGEX.search(line_text[error_col:])
            if match:
                start = line_point + error_col
                end = start + len(match.group(0))

        # -- pyflakes ---------------------------------------------------------
        elif error_code == 'F401':
            # F401 UnusedImport
            obj_len = error_text[1:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[1:obj_len + 1]
                obj_pos = find_in_string(obj_name, line_text)
                if obj_pos:
                    start = line_point + obj_pos
                    end = start + obj_len
        elif error_code == 'F402':
            # F402 ImportShadowedByLoopVar
            obj_len = error_text[8:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[8:obj_len + 8]
                obj_pos = find_in_string(obj_name, line_text)
                if obj_pos:
                    start = line_point + obj_pos
                    end = start + obj_len
        elif error_code == 'F403':
            # F403 ImportStarUsed'
            match = re.search(r'\bimport\s+\*', line_text)
            if match:
                obj_start, obj_end = match.span()
                if obj_start > -1:
                    start = line_point + obj_start
                    end = line_point + obj_end
        elif error_code == 'F404':
            # F404 LateFutureImport
            pass  # whole line is highlighted by default
        elif error_code == 'F810':
            # F810 Redefined
            pass  # whole line is highlighted by default
        elif error_code == 'F811':
            # F811 RedefinedWhileUnused
            obj_len = error_text[24:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[24:obj_len + 24]
                obj_pos = find_in_string(obj_name, line_text)
                if obj_pos:
                    start = line_point + obj_pos
                    end = start + obj_len
        elif error_code == 'F812':
            # F812 RedefinedInListComp
            obj_len = error_text[30:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[30:obj_len + 30]
                if line_text[error_col:error_col + obj_len] == obj_name:
                    start = line_point + error_col
                    end = start + obj_len
        elif error_code == 'F821':
            # F821 UndefinedName
            obj_len = error_text[16:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[16:obj_len + 16]
                if line_text[error_col:error_col + obj_len] == obj_name:
                    start = line_point + error_col
                    end = start + obj_len
        elif error_code == 'F822':
            # F822 UndefinedExport
            pass  # whole line is highlighted by default
            # TODO: can't write correct regex because of indeterminacy
        elif error_code == 'F823':
            # F823 UndefinedLocal
            obj_len = error_text[16:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[16:obj_len + 16]
                if line_text[error_col:error_col + obj_len] == obj_name:
                    start = line_point + error_col
                    end = start + obj_len
        elif error_code == 'F831':
            # F831 DuplicateArgument
            pass  # whole line is highlighted by default
            # TODO: maybe we need regex with 'find two vars in parenthesis'?
        elif error_code == 'F841':
            # F841 UnusedVariable
            obj_len = error_text[16:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[16:obj_len + 16]
                if line_text[error_col:error_col + obj_len] == obj_name:
                    start = line_point + error_col
                    end = start + obj_len

        # -- mccabe -----------------------------------------------------------
        elif error_code == 'C901':
            # C901 'XXX' is too complex (YYY)
            obj_len = error_text[1:].find("'")
            if obj_len > 0:  # not -1 here, we need at least one sybmol
                obj_name = error_text[1:obj_len + 1]
                obj_pos = find_in_string(obj_name, line_text)
                if obj_pos:
                    start = line_point + obj_pos
                    end = start + obj_len

        # -- pep8-naming ------------------------------------------------------
        elif error_code in ('N801', 'N802', 'N806'):
            # N801 class names should use CapWords convention
            # N802 function name should be lowercase
            # N806 variable in function should be lowercase
            tail = line_text[error_col:]
            start = line_point + error_col
            end = start + sum(1 for __ in itertools.takewhile(isname, tail))
        elif error_code in ('N803', 'N804', 'N805'):
            # N803 argument name should be lowercase
            # N804 first argument of a classmethod should be named 'cls'
            # N805 first argument of a method should be named 'self'
            pass  # whole line is highlighted by default
            # TODO: maybe we need regex with 'find vars in parenthesis'?
        elif error_code == 'N811':
            # N811 constant imported as non constant
            pass  # whole line is highlighted by default
            # TODO: we need to fix pep8-naming for error column detect
        elif error_code == 'N812':
            # N812 lowercase imported as non lowercase
            pass  # whole line is highlighted by default
            # TODO: we need to fix pep8-naming for error column detect
        elif error_code == 'N813':
            # N813 camelcase imported as lowercase
            pass  # whole line is highlighted by default
            # TODO: we need to fix pep8-naming for error column detect
        elif error_code == 'N814':
            # N814 camelcase imported as constant
            pass  # whole line is highlighted by default
            # TODO: we need to fix pep8-naming for error column detect

        if start == end:
            start = line_point
            end = line_point + line_length

        return start, end

    def prepare_errors(self, errors_list):
        """
        Filter errors list.
        """
        log("prepare flake8 lint errors")

        view_errors = {}
        errors_shown = set()

        errors_list_filtered = []

        for error in errors_list:
            log("error to show: {0}".format(error))
            if error in errors_shown:
                log("skip error: already shown")
            errors_shown.add(error)

            error_line = error[0] - 1
            error_col = error[1]
            error_text = error[2]

            # get error line
            line_point = self.view.text_point(error_line, 0)
            full_line = self.view.full_line(line_point)
            full_line_text = self.view.substr(full_line)
            line_text = full_line_text.rstrip('\r\n')

            # skip line if 'noqa' defined
            if skip_line_lint(line_text):
                log("skip '{0}' in line {1} due to 'noqa' comment".format(
                    error_text, error_line
                ))
                continue

            # parse error line to get error code
            error_code, __ = error_text.split(' ', 1)

            # check if user has a setting for select only errors to show
            if self.select:
                if not [c for c in self.select if error_code.startswith(c)]:
                    log("error does not fit in 'select' settings")
                    continue

            # check if user has a setting for ignore some errors
            if self.ignore:
                if [c for c in self.ignore if error_code.startswith(c)]:
                    log("error does fit in 'ignore' settings")
                    continue

            # add error to filtered errors list
            errors_list_filtered.append(error)

            # build error text
            self.errors_to_show.append([
                error_text,
                u'{0}: {1}'.format(error_line + 1, line_text.strip()),
            ])

            # prepare errors regions
            if self.is_highlight or self.gutter_mark:
                if settings.highlight_type == 'line':
                    start = line_point
                    end = line_point + len(line_text)
                else:
                    start, end = self.error_region(
                        full_line_text, line_point, error_text, error_col
                    )

                if error_code[0] == 'F':
                    regions_list = self.regions['critical']
                elif error_code[0] == 'E':
                    regions_list = self.regions['error']
                else:
                    regions_list = self.regions['warning']

                regions_list.append(sublime.Region(start, end))

            # save errors for each line in view to special dict
            view_errors.setdefault(error_line, []).append(error_text)

        # save errors
        self.errors_list = errors_list_filtered
        ERRORS_IN_VIEWS[self.view.id()] = view_errors

    def show_errors(self, quiet=False):
        """
        Show all errors.
        """
        log("show flake8 lint errors")

        # this is fallback to default colors if our color scheme was not loaded
        prefs = sublime.load_settings('Preferences.sublime-settings')
        color_scheme = prefs.get('color_scheme')
        if color_scheme and '(Flake8Lint)' in color_scheme:
            scope_name = 'flake8lint.mark.{0}'
        else:
            log("use default colors because our color scheme was not loaded")
            scope_name = 'invalid.deprecated'

        # highlight error regions if defined
        if self.is_highlight:
            for level in ('warning', 'error', 'critical'):
                if not self.regions[level]:
                    continue

                log("highlight errors in view (regions: {0})".format(level))

                self.view.add_regions(
                    'flake8lint-{0}'.format(level),
                    self.regions[level],
                    scope_name.format(level),
                    self.gutter_mark.format(level),
                    sublime.DRAW_OUTLINED
                )

        elif self.gutter_mark:
            for level in ('warning', 'error', 'critical'):
                if not self.regions[level]:
                    continue

                log("highlight errors in view (marks: {0})".format(level))

                self.view.add_regions(
                    'flake8lint-{0}'.format(level),
                    self.regions[level],
                    scope_name.format('gutter'),
                    self.gutter_mark.format(level),
                    sublime.HIDDEN
                )

        if self.is_popup and not quiet:
            log("show popup window with errors")
            # view errors window
            window = self.view.window()
            if not window:
                return
            window.show_quick_panel(self.errors_to_show, self.error_selected)

    def error_selected(self, item_selected):
        """
        Error was selected - go to error.
        """
        if item_selected == -1:
            log("close errors popup window")
            return

        log("error was selected from popup window: scroll to line")

        # get error region
        error = self.errors_list[item_selected]
        region_begin = self.view.text_point(error[0] - 1, error[1])

        # go to error
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(region_begin, region_begin))

        self.view.window().focus_view(self.view)
        self.view.show_at_center(region_begin)

        # work around sublime bug with caret position not refreshing
        # see also: https://github.com/SublimeTextIssues/Core/issues/485
        bug_key = 'selection_bug_demo_workaround_regions_key'
        self.view.add_regions(bug_key, [], 'no_scope', '', sublime.HIDDEN)
        self.view.erase_regions(bug_key)

        SublimeStatusBar.update(self.view)

    def report_success(self, quiet=False):
        """
        Blink with gutter marks (success report).
        """
        if quiet:
            return

        if settings.report_on_success:
            log("Report about lint success")
            sublime.message_dialog('Flake8 Lint: SUCCESS')

        if settings.blink_gutter_marks_on_success:
            log("Blink gutter marks about lint success")
            self.view.add_regions(
                'flake8lint-success',
                self.view.lines(sublime.Region(0, self.view.size())),
                'flake8lint.mark.gutter',
                self.gutter_mark_success,
                sublime.HIDDEN
            )
            sublime.set_timeout(
                lambda: self.view.erase_regions('flake8lint-success'),
                300
            )


class Flake8Lint(object):
    """
    Lint functions.

    This is dummy class: simply group all lint methods together.
    """
    @staticmethod
    def wait_and_lint(view):
        """
        Set rullers and run file lint after file was loaded.
        """
        window = sublime.active_window()
        if not window:
            return

        window_views = (window_view.id() for window_view in window.views())
        if view.id() not in window_views:  # view is preview
            # FIXME: that if view will closed while we wait for it?
            sublime.set_timeout(
                lambda: Flake8Lint.wait_and_lint(view), 300
            )
            return

        log("run lint by 'on_load' hook")
        Flake8Lint.do_lint(view)

    @staticmethod
    def on_file_load(view=None, retry=False):
        """
        Run actions on file load.
        Wait until file was finally loaded and run actions if needed.
        """
        set_ruler_guide = settings.set_ruler_guide
        lint_on_load = settings.lint_on_load

        if not (set_ruler_guide or lint_on_load):
            return  # no need to do anything

        log("wait until file was loaded")
        if not retry:  # first run - wait a little bit
            sublime.set_timeout(
                lambda: Flake8Lint.on_file_load(view, True), 100
            )
            return

        if view is None:
            window = sublime.active_window()
            if not window:
                return

            view = window.active_view()
            if not view:
                return

        if view.is_loading():  # view is still running - wait again
            sublime.set_timeout(
                lambda: Flake8Lint.on_file_load(view, True), 100
            )
            return

        if view.window() is None:  # view window is not initialized - wait...
            sublime.set_timeout(
                lambda: Flake8Lint.on_file_load(view, True), 100
            )
            return

        if view.window().active_view().id() != view.id():
            log("view is not active anymore, forget about lint")
            return  # not active anymore, don't lint it!

        if set_ruler_guide:
            SublimeView.set_ruler_guide(view)
        else:
            log("do not set ruler guide due to plugin settings")

        if lint_on_load:
            Flake8Lint.wait_and_lint(view)
        else:
            log("skip lint by 'on_load' hook due to plugin settings")

    @staticmethod
    def cleanup(view):
        """
        Clear regions and statusbar.
        """
        # we need to always clear regions. three situations here:
        # - we need to clear regions with fixed previous errors
        # - is user will turn off 'highlight' in settings and then run lint
        # - user adds file with errors to 'ignore_files' list
        for level in ('warning', 'error', 'critical', 'success'):
            view.erase_regions('flake8lint-{0}'.format(level))

        # we need to always erase status too. same situations.
        view.erase_status('flake8-tip')

    @staticmethod
    def do_lint(view, quiet=False):
        """
        Do view lint.
        """
        log("run flake8 lint")

        # check if view is scratch
        if view.is_scratch():
            log("skip lint because view is scratch")
            Flake8Lint.cleanup(view)
            return  # do not lint scratch views

        # check if active view contains file
        filename = view.file_name()
        if not filename:
            log("skip view: filename is empty")
            Flake8Lint.cleanup(view)
            return

        filename = os.path.abspath(filename)

        # check only Python files
        if not view.match_selector(0, 'source.python'):
            log("skip file: view source type is not 'python'")
            Flake8Lint.cleanup(view)
            return

        # get view settings
        view_settings = SublimeView.view_settings(view)

        # skip files by pattern
        patterns = view_settings.get('ignore_files')
        log("ignore file patterns: {0}".format(patterns))
        if patterns:
            # add file basename to check list
            paths = [os.path.basename(filename)]

            # add file relative paths to check list
            for folder in sublime.active_window().folders():
                folder_name = folder.rstrip(os.path.sep) + os.path.sep
                if filename.startswith(folder_name):
                    paths.append(filename[len(folder_name):])

            try:
                if any(filename_match(path, patterns) for path in set(paths)):
                    message = "File '{0}' lint was skipped by 'ignore' setting"
                    print(message.format(filename))
                    Flake8Lint.cleanup(view)
                    return
            except (TypeError, ValueError):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "'ignore_files' option is not a list of file masks"
                )

        if int(sublime.version()) >= 3000:
            set_timeout = sublime.set_timeout_async
        else:
            set_timeout = sublime.set_timeout

        set_timeout(
            lambda: Flake8Lint.async_lint(view, view_settings, quiet=quiet), 0
        )

    @staticmethod
    def async_lint(view, view_settings, quiet=False):
        """
        Do view lint asynchronously.
        """
        # try to get interpreter
        interpreter = view_settings.get('python_interpreter', 'auto')
        log("python interpreter: {0}".format(interpreter))

        lines = view.substr(sublime.Region(0, view.size()))

        # skip file check if 'noqa' for whole file is set
        if FLAKE8_NOQA(lines) is not None:
            log("skip file: 'noqa' is set")
            Flake8Lint.cleanup(view)
            return

        start_time = time.time()
        if not interpreter or interpreter == 'internal':
            # if interpreter is Sublime Text internal python - lint file
            log("interpreter is internal")
            errors_list = lint(lines, view_settings)
        else:
            # else - check interpreter
            log("interpreter is external")
            if interpreter == 'auto':
                if os.name == 'nt':
                    interpreter = 'pythonw'
                else:
                    interpreter = 'python'
                log("guess interpreter: '{0}'".format(interpreter))
            elif not os.path.exists(interpreter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "python interpreter '%s' is not found" % interpreter
                )

            # build linter path for Packages Manager installation
            linter = os.path.join(PLUGIN_DIR, 'lint.py')
            log("linter file: {0}".format(linter))

            # build linter path for installation from git
            if not os.path.exists(linter):
                linter = os.path.join(
                    sublime.packages_path(), 'Python Flake8 Lint', 'lint.py')
                log("linter is not exists, try this: {0}".format(linter))

            if not os.path.exists(linter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "sorry, can't find correct plugin path"
                )

            # and lint file in subprocess
            log("interpreter is external")
            errors_list = lint_external(lines, view_settings,
                                        interpreter, linter)

        if not errors_list:
            errors_list = []

        lint_time = time.time() - start_time
        log("lint time: {0:.3f}ms".format(lint_time))
        log("lint errors found: {0}".format(len(errors_list)))

        # clean regions and statusbar
        Flake8Lint.cleanup(view)
        # show errors
        LintReport(view, errors_list, view_settings, quiet=quiet)


class Flake8NextErrorCommand(sublime_plugin.TextCommand):
    """
    Jump to next lint error command.
    """
    def run(self, edit):
        """
        Jump to next lint error.
        """
        log("jump to next lint error")

        view_errors = ERRORS_IN_VIEWS.get(self.view.id())
        if not view_errors:
            log("no view errors found")
            return

        # get view selection (exit if no selection)
        view_selection = self.view.sel()
        if not view_selection:
            return

        current_line = SublimeView.get_current_line(self.view)
        if current_line is None:
            return

        next_line = None
        for i, error_line in enumerate(sorted(view_errors.keys())):
            if i == 0:
                next_line = error_line
            if error_line > current_line:
                next_line = error_line
                break

        log("jump to line {0}".format(next_line))

        point = self.view.text_point(next_line, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point)


class Flake8LintCommand(sublime_plugin.TextCommand):
    """
    Do flake8 lint on current file.
    """
    def run(self, edit):
        """
        Run flake8 lint.
        """
        Flake8Lint.do_lint(self.view)


class Flake8LintBackground(sublime_plugin.EventListener):
    """
    Listen to Siblime Text events.
    """
    def __init__(self, *args, **kwargs):
        super(Flake8LintBackground, self).__init__(*args, **kwargs)

        self._last_selected_line = None
        self._latest_keypresses = {}

        if int(sublime.version()) >= 3000:
            self.set_timeout = sublime.set_timeout_async
        else:
            self.set_timeout = sublime.set_timeout

    def on_load(self, view):
        """
        Do lint on file load.
        """
        Flake8Lint.on_file_load(view)

    def on_post_save(self, view):
        """
        Do lint on file save.
        """
        if view.is_scratch():
            log("skip lint because view is scratch")
            return  # do not lint scratch views

        if settings.lint_on_save:
            log("run lint by 'on_post_save' hook")
            Flake8Lint.do_lint(view)
        else:
            log("skip lint by 'on_post_save' hook due to plugin settings")

    def on_selection_modified(self, view):
        """
        Selection was modified: update status bar.
        """
        if view.is_scratch():
            return  # do not lint scratch views

        current_line = SublimeView.get_current_line(view)

        if current_line is None:
            if self._last_selected_line is not None:  # line was selected
                self._last_selected_line = None
                SublimeStatusBar.clear(view)

        elif current_line != self._last_selected_line:  # line was changed
            self._last_selected_line = current_line
            log("update statusbar")
            SublimeStatusBar.update(view)

    def on_modified(self, view):
        """
        View was modified: run delayed lint if needed.
        """
        if settings.live_mode:
            self.delayed_lint(view)

    def delayed_lint(self, view):
        """
        Lint view delayed.
        """
        keypress_time = time.time()
        view_id = view.id()
        self._latest_keypresses[view_id] = keypress_time

        def callback():
            """
            Live mode lint delay callback.
            Run lint if no key pressed after timeout was set.
            """
            if self._latest_keypresses.get(view_id, None) == keypress_time:
                log("run delayed lint (live_mode)")
                Flake8Lint.do_lint(view, quiet=True)

        self.set_timeout(callback, settings.live_mode_lint_delay)


def plugin_loaded():
    """
    Do some staff when 'plugin was loaded' event appears.
    """
    global settings

    settings = Flake8LintSettings()

    log("plugin was loaded")

    update_color_scheme(settings)
    Flake8Lint.on_file_load()


# backwards compatibility with Sublime 2:
# sublime.version isn't available at module import time in Sublime 3
if sys.version_info[0] == 2:
    plugin_loaded()
