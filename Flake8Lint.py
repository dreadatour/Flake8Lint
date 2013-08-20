# -*- coding: utf-8 -*-
"""
Flake8Lint: Sublime Text 2 plugin.
Check Python files with flake8 (PEP8, pyflake and mccabe)
"""
import os
import sys
from fnmatch import fnmatch

import sublime
import sublime_plugin

try:
    from .lint import lint, lint_external, skip_file
except ValueError:
    from lint import lint, lint_external, skip_file  # noqa


settings = None
ERRORS_IN_VIEWS = {}
FLAKE_DIR = os.path.dirname(os.path.abspath(__file__))


def plugin_loaded():
    """
    Callback for 'plugin was loaded' event.
    Load settings.
    """
    global settings
    settings = sublime.load_settings("Flake8Lint.sublime-settings")


# Backwards compatibility with Sublime 2
# sublime.version isn't available at module import time in Sublime 3
if sys.version_info[0] == 2:
    plugin_loaded()


def skip_line(line):
    """
    Check if we need to skip line check.
    Line must ends with '# noqa' or '# NOQA' comment.
    """
    return line.strip().lower().endswith('# noqa')


def update_statusbar(view):
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

    # get current line (line under cursor)
    current_line = view.rowcol(view_selection[0].end())[0]

    if current_line in view_errors:
        # there is an error on current line
        errors = view_errors[current_line]
        view.set_status('flake8-tip',
                        'Flake8 lint errors: %s' % ' / '.join(errors))
    else:
        # no errors - clear statusbar
        view.erase_status('flake8-tip')


class Flake8LintCommand(sublime_plugin.TextCommand):
    """
    Do flake8 lint on current file.
    """
    def run(self, edit):
        """
        Run flake8 lint.
        """
        # check if active view contains file
        filename = self.view.file_name()
        if not filename:
            return

        filename = os.path.abspath(filename)

        # check only Python files
        if not self.view.match_selector(0, 'source.python'):
            return

        # skip file check if 'noqa' for whole file is set
        if skip_file(filename):
            return

        # we need to always clear regions. three situations here:
        # - we need to clear regions with fixed previous errors
        # - is user will turn off 'highlight' in settings and then run lint
        # - user adds file with errors to 'ignore_files' list
        self.view.erase_regions('flake8-errors')

        # we need to always erase status too. same situations.
        self.view.erase_status('flake8-tip')

        # skip files by mask
        ignore_files = settings.get('ignore_files')
        if ignore_files:
            basename = os.path.basename(filename)
            try:
                if any(fnmatch(basename, mask) for mask in ignore_files):
                    return
            except (TypeError, ValueError):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "'ignore_files' option is not a list of file masks"
                )

        # save file if dirty
        if self.view.is_dirty():
            self.view.run_command('save')

        # try to get interpreter
        interpreter = settings.get('python_interpreter', 'auto')

        if not interpreter or interpreter == 'internal':
            # if interpreter is Sublime Text 2 internal python - lint file
            self.errors_list = lint(filename, settings)
        else:
            # else - check interpreter
            if interpreter == 'auto':
                if os.name == 'nt':
                    interpreter = 'pythonw'
                else:
                    interpreter = 'python'
            elif not os.path.exists(interpreter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "python interpreter '%s' is not found" % interpreter
                )

            # build linter path for Packages Manager installation
            linter = os.path.join(FLAKE_DIR, 'lint.py')

            # build linter path for installation from git
            if not os.path.exists(linter):
                linter = os.path.join(
                    sublime.packages_path(), 'Python Flake8 Lint', 'lint.py')

            if not os.path.exists(linter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "sorry, can't find correct plugin path"
                )

            # and lint file in subprocess
            self.errors_list = lint_external(filename, settings,
                                             interpreter, linter)

        # show errors
        if self.errors_list:
            self.show_errors()
        elif settings.get('report_on_success', False):
            sublime.message_dialog('Flake8 Lint: SUCCESS')

    def show_errors(self):
        """
        Show all errors.
        """
        errors_to_show = []

        # get select and ignore settings
        select = settings.get('select') or []
        ignore = settings.get('ignore') or []
        is_highlight = settings.get('highlight', False)
        is_popup = settings.get('popup', True)

        regions = []
        view_errors = {}
        errors_list_filtered = []

        for e in self.errors_list:
            current_line = e[0] - 1
            error_text = e[2]

            # get error line
            text_point = self.view.text_point(current_line, 0)
            line = self.view.full_line(text_point)
            full_line_text = self.view.substr(line)
            line_text = full_line_text.strip()

            # skip line if 'noqa' defined
            if skip_line(line_text):
                continue

            # parse error line to get error code
            code, _ = error_text.split(' ', 1)

            # check if user has a setting for select only errors to show
            if select and [c for c in select if code.startswith(c)]:
                continue

            # check if user has a setting for ignore some errors
            if ignore and [c for c in ignore if code.startswith(c)]:
                continue

            # build error text
            error = [error_text, u'{0}: {1}'.format(current_line + 1,
                                                    line_text)]
            # skip if this error is already found (with pep8 or flake8)
            if error in errors_to_show:
                continue
            errors_to_show.append(error)

            # build line error message
            if is_popup:
                errors_list_filtered.append(e)

            # prepare errors regions
            if is_highlight:
                # prepare line
                line_text = full_line_text.rstrip('\r\n')
                line_length = len(line_text)

                # calculate error highlight start and end positions
                start = text_point + line_length - len(line_text.lstrip())
                end = text_point + line_length

                # small tricks
                if code == 'E501':
                    # too long lines: highlight only the rest of line
                    start = text_point + e[1]
                # TODO: add another tricks like 'E303 too many blank lines'

                regions.append(sublime.Region(start, end))

            # save errors for each line in view to special dict
            view_errors.setdefault(current_line, []).append(error_text)

        # renew errors list with selected and ignored errors
        self.errors_list = errors_list_filtered
        # save errors dict
        ERRORS_IN_VIEWS[self.view.id()] = view_errors

        # highlight error regions if defined
        if is_highlight:
            mark = settings.get('gutter_marks', '')
            self.view.add_regions('flake8-errors', regions,
                                  'invalid.deprecated', mark,
                                  sublime.DRAW_OUTLINED)

        if is_popup:
            # view errors window
            window = self.view.window()
            window.show_quick_panel(errors_to_show, self.error_selected)

    def error_selected(self, item_selected):
        """
        Error was selected - go to error.
        """
        if item_selected == -1:
            return

        # reset selection
        selection = self.view.sel()
        selection.clear()

        # get error region
        error = self.errors_list[item_selected]
        region_begin = self.view.text_point(error[0] - 1, error[1])

        # go to error
        selection.add(sublime.Region(region_begin, region_begin))
        self.view.show_at_center(region_begin)
        update_statusbar(self.view)


class Flake8LintBackground(sublime_plugin.EventListener):
    """
    Listen to Siblime Text 2 events.
    """
    def _lintOnLoad(self, view, retry=False):
        """
        Some code to lint file on load.
        """
        if not retry:  # first run - wait a little bit
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 100)
            return

        if view.is_loading():  # view is still running - wait again
            sublime.set_timeout(lambda: self._lintOnLoad(view, True), 100)
            return

        elif view.window().active_view().id() != view.id():
            return  # not active anymore, don't lint it!

        view.run_command("flake8_lint")

    def on_load(self, view):
        """
        Do lint on file load.
        """
        if settings.get('lint_on_load', False):
            self._lintOnLoad(view)

    def on_post_save(self, view):
        """
        Do lint on file save.
        """
        if settings.get('lint_on_save', True):
            view.run_command('flake8_lint')

    def on_selection_modified(self, view):
        """
        Selection was modified: update status bar.
        """
        update_statusbar(view)
