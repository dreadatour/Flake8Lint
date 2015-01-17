# -*- coding: utf-8 -*-
"""
Flake8Lint sublime helpers.
"""
import os
from fnmatch import fnmatch


def filename_match(filename, patterns):
    """
    Returns `True` if filename is matched with patterns.
    """
    for path_part in filename.split(os.path.sep):
        if any(fnmatch(path_part, pattern) for pattern in patterns):
            return True
    return False


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


def skip_line_lint(line):
    """
    Check if we need to skip line check.

    Returns `True` if line ends with '# noqa' or '# NOQA' comment.
    """
    def _noqa(line):
        return line.strip().lower().endswith('# noqa')

    skip = _noqa(line)

    if not skip:
        i = line.rfind(' #')
        skip = _noqa(line[:i]) if i > 0 else False

    return skip


def view_is_preview(window, view):
    """
    Returns `True` if view is in preview mode (e.g. "Goto Anything").
    """
    window_views = (
        window_view.id()
        for window_view in window.views()
    )
    return bool(view.id() not in window_views)
