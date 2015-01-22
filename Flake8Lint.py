# -*- coding: utf-8 -*-
"""
Flake8Lint: Sublime Text plugin.
Check Python files with flake8 (PEP8, pyflake and mccabe)
"""
from __future__ import print_function
import fnmatch
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


FLAKE8_NOQA = re.compile(r'flake8[:=]\s*noqa', re.I).search

PROJECT_SETTINGS_KEYS = (
    'python_interpreter', 'builtins', 'pyflakes', 'pep8', 'naming',
    'complexity', 'pep8_max_line_length', 'select', 'ignore', 'ignore_files',
    'use_flake8_global_config', 'use_flake8_project_config',
)
FLAKE8_SETTINGS_KEYS = (
    'ignore', 'select', 'ignore_files', 'pep8_max_line_length'
)

ERRORS_IN_VIEWS = {}
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

ERROR_LEVELS = ('warning', 'error', 'critical')

MARK_TYPES = ('dot', 'circle', 'bookmark', 'cross')
MARK_THEMES = ('alpha', 'bright', 'dark', 'hard', 'simple')


SETTINGS = {}
DEBUG_ENABLED = False


def log(msg, level=None):
    """
    Log to ST python console.

    If log level 'debug' (or None) print only if debug setting is enabled.
    """
    if level is None:
        level = 'debug'

    if level == 'debug' and not DEBUG_ENABLED:
        return

    print("[Flake8Lint {0}] {1}".format(level.upper(), msg))


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
            if param in view_settings:
                result[param] = view_settings.get(param)
            elif SETTINGS.has(param):
                result[param] = SETTINGS.get(param)

        global_config = result.get('use_flake8_global_config', False)
        project_config = result.get('use_flake8_project_config', False)

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
        self.show_errors(quiet=quiet)

    def get_gutter_mark(self):
        """
        Returns gutter mark icon or empty string if marks are disabled.
        """
        mark_type = str(SETTINGS.get('gutter_marks', ''))

        if mark_type in MARK_TYPES:
            return mark_type

        if mark_type.startswith('theme-'):
            theme = mark_type[6:]
            if theme in MARK_THEMES:
                mark_themes_paths = [
                    'Packages', os.path.basename(PLUGIN_DIR), 'gutter-themes'
                ]
                if int(sublime.version()) < 3014:
                    mark_themes_paths = (
                        [os.path.pardir, os.path.pardir] + mark_themes_paths
                    )

                # ST does not expect platform specific paths here, but only
                # forward-slash separated paths relative to "Packages"
                mark_themes_dir = '/'.join(mark_themes_paths)
                mark = '/'.join([mark_themes_dir, '{0}-{{0}}'.format(theme)])

                if int(sublime.version()) >= 3014:
                    mark += '.png'

                return mark
            else:
                log("unknown gutter mark theme: '{0}'".format(mark_type))

        return ''

    def prepare_settings(self, view_settings):
        """
        Get view lint settings.
        """
        self.gutter_mark = self.get_gutter_mark()

        self.select = view_settings.get('select') or []
        self.ignore = view_settings.get('ignore') or []
        self.is_highlight = SETTINGS.get('highlight', False)
        self.is_popup = SETTINGS.get('popup', True)

        log("'select' setting: {0}".format(self.select))
        log("'ignore' setting: {0}".format(self.ignore))
        log("'is_highlight' setting: {0}".format(self.is_highlight))
        log("'is_popup' setting: {0}".format(self.is_popup))

    def add_region(self, line_text, line_point, error_code, error_col):
        """
        Add error region to regions list.
        """
        line_length = len(line_text)

        # calculate error highlight start and end positions
        start = line_point + line_length - len(line_text.lstrip())
        end = line_point + line_length

        # small tricks
        if error_code == 'E501':
            # too long lines: highlight only the rest of line
            start = line_point + error_col
        # TODO: add another tricks like 'E303 too many blank lines'

        if error_code[0] == 'F':
            regions_list = self.regions['critical']
        elif error_code[0] == 'E':
            regions_list = self.regions['error']
        else:
            regions_list = self.regions['warning']

        regions_list.append(sublime.Region(start, end))

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
                self.add_region(line_text, line_point, error_code, error_col)

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
            for level in ERROR_LEVELS:
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
            for level in ERROR_LEVELS:
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
        set_ruler_guide = SETTINGS.get('set_ruler_guide', False)
        lint_on_load = SETTINGS.get('lint_on_load', False)

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
        for level in ERROR_LEVELS:
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

        lint_time = time.time() - start_time
        log("lint time: {0:.3f}ms".format(lint_time))
        log("lint errors found: {0}".format(len(errors_list)))

        Flake8Lint.cleanup(view)  # clean regions and statusbar

        # show errors
        if errors_list:
            LintReport(view, errors_list, view_settings, quiet=quiet)
        elif SETTINGS.get('report_on_success', False):
            sublime.message_dialog('Flake8 Lint: SUCCESS')


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

        if SETTINGS.get('lint_on_save', True):
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
        if SETTINGS.get('live_mode', False):
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

        self.set_timeout(callback, SETTINGS.get('live_mode_lint_delay', 1000))


def plugin_loaded():
    """
    Load plugin settings when 'plugin was loaded' event appears.
    """
    global SETTINGS
    global DEBUG_ENABLED

    SETTINGS = sublime.load_settings("Flake8Lint.sublime-settings")

    if SETTINGS.get('debug', False):
        DEBUG_ENABLED = True
        log("plugin was loaded")

    update_color_scheme(SETTINGS)
    Flake8Lint.on_file_load()


# backwards compatibility with Sublime 2:
# sublime.version isn't available at module import time in Sublime 3
if sys.version_info[0] == 2:
    plugin_loaded()
