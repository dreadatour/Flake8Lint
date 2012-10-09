# -*- coding: utf-8 -*-
import os

import sublime
import sublime_plugin

from flake8_harobed.util import skip_line
from lint import lint, lint_external


settings = sublime.load_settings("Flake8Lint.sublime-settings")


class Flake8LintCommand(sublime_plugin.TextCommand):
    """
    Do flake8 lint on current file.
    """
    def run(self, edit):
        """
        Run flake8 lint.
        """
        # current file name
        filename = os.path.abspath(self.view.file_name())

        # check if active view contains file
        if not filename:
            return

        # check only Python files
        if not self.view.match_selector(0, 'source.python'):
            return

        # save file if dirty
        if self.view.is_dirty():
            self.view.run_command('save')

        # try to get interpreter
        interpreter = settings.get('python_interpreter', 'auto')

        if not interpreter or interpreter == 'internal':
            # if interpreter is Sublime Text 2 internal python - lint file
            self.warnings = lint(filename, settings)
        else:
            # else - check interpreter
            if interpreter == 'auto':
                interpreter = 'python'
            elif not os.path.exists(interpreter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "python interpreter '%s' is not found" % interpreter
                )

            # TODO: correct linter path handle
            # build linter path for Packages Manager installation
            linter = os.path.join(
                sublime.packages_path(), 'Python Flake8 Lint', 'lint.py')

            # build linter path for installation from git
            if not os.path.exists(linter):
                linter = os.path.join(
                    sublime.packages_path(), 'Flake8Lint', 'lint.py')

            if not os.path.exists(linter):
                sublime.error_message(
                    "Python Flake8 Lint error:\n"
                    "sorry, can't find correct plugin path"
                )

            # and lint file in subprocess
            self.warnings = lint_external(filename, settings,
                                          interpreter, linter)

        # show errors
        if self.warnings:
            self.show_errors()

    def show_errors(self):
        """
        Show all errors.
        """
        errors = []

        for e in self.warnings:
            # get error line
            line = self.view.full_line(self.view.text_point(e[0] - 1, 0))
            line_text = self.view.substr(line).strip()
            # skip line if 'NOQA' defined
            if skip_line(line_text):
                continue
            # build line error message
            error = [e[2], u'{0}: {1}'.format(e[0], line_text)]
            if error not in errors:
                errors.append([e[2], u'{0}: {1}'.format(e[0], line_text)])

        # view errors window
        self.view.window().show_quick_panel(errors, self.error_selected)

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
        error = self.warnings[item_selected]
        region_begin = self.view.text_point(error[0] - 1, error[1])

        # go to error
        selection.add(sublime.Region(region_begin, region_begin))
        self.view.show_at_center(region_begin)


class Flake8LintBackground(sublime_plugin.EventListener):
    """
    Listen to Siblime Text 2 events.
    """
    def on_post_save(self, view):
        """
        Do lint on file save if not denied in settings.
        """
        if settings.get('lint_on_save', True):
            view.run_command('flake8_lint')
