# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

# We will use Stéphane Klein fork of flake8 until it not merged into flake8.
# This version includes last version of pep8.
# See: https://bitbucket.org/tarek/flake8/issue/23/use-pep8-configuration-file
from flake8_harobed import pyflakes, pep8, mccabe, util

# Monkey-patching is a big evil (don't do this),
# but hardcode is a much more bigger evil. Hate hardcore!
from monkey_patching import pyflakes_check, mccabe_get_code_complexity
pyflakes.check = pyflakes_check
mccabe.get_code_complexity = mccabe_get_code_complexity


settings = sublime.load_settings("Flake8Lint.sublime-settings")


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
            self.errors.append(
                (self.line_offset + line_number, offset, text)
            )
        return code


class Flake8LintCommand(sublime_plugin.TextCommand):
    """
    Do flake8 lint on current file.
    """
    def run(self, edit):
        """
        Run flake8 lint.
        """
        # current file name
        filename = self.view.file_name()

        # check if active view contains file
        if not filename:
            return

        # check only Python files
        if not self.view.match_selector(0, 'source.python'):
            return

        # save file if dirty
        if self.view.is_dirty():
            self.view.run_command('save')

        # skip file check if 'flake8: noqa' header is set
        if util.skip_file(filename):
            return

        # place for warnings =)
        warnings = []

        # lint with pyflakes
        if settings.get('pyflakes', True):
            warnings.extend(pyflakes.checkPath(filename))

        # lint with pep8
        if settings.get('pep8', True):
            pep8style = pep8.StyleGuide(
                select=settings.get('select', []),
                ignore=settings.get('ignore', []),
                reporter=Pep8Report
            )

            pep8style.input_file(filename)
            warnings.extend(pep8style.options.report.errors)

        # check complexity
        complexity = settings.get('complexity', -1)
        if complexity > -1:
            warnings.extend(mccabe.get_module_complexity(filename, complexity))

        # show errors
        if warnings:
            self.warnings = warnings
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
            if util.skip_line(line_text):
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
