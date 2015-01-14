# -*- coding: utf-8 -*-
"""
Override Sublime Text color theme.

Add lint highlight colors and set gutter marks foreground color
for better visibility.

Based on https://github.com/JulianEberius/SublimePythonIDE
"""
import os
from xml.etree import ElementTree

import sublime


DEFAULT_MARK_COLORS = {
    'critical': '#981600',
    'error': '#DA2000',
    'warning': '#EDBA00',
    'gutter': '#FFFFFF',
}

COLOR_SCHEME_PREAMBLE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">"""

COLOR_SCHEME_STYLES = {
    'critical': """
        <dict>
            <key>name</key>
            <string>Python Flake8 Lint Critical</string>
            <key>scope</key>
            <string>flake8lint.mark.critical</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>{0}</string>
            </dict>
        </dict>
    """,
    'error': """
        <dict>
            <key>name</key>
            <string>Python Flake8 Lint Error</string>
            <key>scope</key>
            <string>flake8lint.mark.error</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>{0}</string>
            </dict>
        </dict>
    """,
    'warning': """
        <dict>
            <key>name</key>
            <string>Python Flake8 Lint Warning</string>
            <key>scope</key>
            <string>flake8lint.mark.warning</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>{0}</string>
            </dict>
        </dict>
    """,
    'gutter': """
        <dict>
            <key>name</key>
            <string>Python Flake8 Lint Gutter Mark</string>
            <key>scope</key>
            <string>flake8lint.mark.gutter</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#FFFFFF</string>
            </dict>
        </dict>
    """
}

style_map = {
    'flake8lint.mark.critical': 'critical',
    'flake8lint.mark.error': 'error',
    'flake8lint.mark.warning': 'warning',
    'flake8lint.mark.gutter': 'gutter',
}


def update_color_scheme(settings):
    """
    Modify  the current color scheme to contain Flake8Lint color entries
    as set in Flake8Lint.sublime-settings.

    Asynchronously call generate_color_scheme_async.
    """
    colors = {
        'critical': settings.get('color_critical'),
        'error': settings.get('color_error'),
        'warning': settings.get('color_warning'),
    }

    def generate_color_scheme_async():
        # find and parse current theme
        prefs = sublime.load_settings('Preferences.sublime-settings')
        scheme = prefs.get('color_scheme')

        if scheme is None:
            return

        scheme_text = sublime.load_resource(scheme)
        plist = ElementTree.XML(scheme_text)
        dicts = plist.find('./dict/array')

        # find all style infos in the theme and update if necessary
        theme_was_changed = False
        unknown_styles = set(('critical', 'error', 'warning', 'gutter'))
        for d in dicts.findall('./dict'):
            for c in d.getchildren():
                if c.text and 'flake8lint' in c.text:
                    style = style_map.get(c.text)
                    if style not in DEFAULT_MARK_COLORS:
                        continue

                    color_elem = d.find('./dict/string')
                    found_color = color_elem.text.upper().lstrip('#')
                    our_color = colors.get(style) or DEFAULT_MARK_COLORS[style]
                    target_color = our_color.upper().lstrip('#')

                    if found_color != target_color:
                        theme_was_changed = True
                        color_elem.text = '#' + target_color
                    unknown_styles.discard(style)
                    break

        # add defaults for all styles that were not found
        for style in unknown_styles:
            if style not in DEFAULT_MARK_COLORS:
                continue

            color = colors.get(style) or DEFAULT_MARK_COLORS[style]
            if not color:
                continue

            dicts.append(ElementTree.XML(
                COLOR_SCHEME_STYLES[style].format('#' + color.lstrip('#'))
            ))
            theme_was_changed = True

        # only write new theme if necessary
        if not theme_was_changed:
            return

        # write new theme
        original_name = os.path.splitext(os.path.basename(scheme))[0]
        new_name = original_name + ' (Flake8Lint).tmTheme'
        scheme_path = os.path.join(sublime.packages_path(), 'User', new_name)

        with open(scheme_path, 'w', encoding='utf8') as f:
            f.write(COLOR_SCHEME_PREAMBLE)
            f.write(ElementTree.tostring(plist, encoding='unicode'))

        # ST does not expect platform specific paths here, but only
        # forward-slash separated paths relative to "Packages"
        new_theme_setting = '/'.join(['Packages', 'User', new_name])
        prefs.set('color_scheme', new_theme_setting)
        sublime.save_settings('Preferences.sublime-settings')

    # run async
    sublime.set_timeout_async(generate_color_scheme_async, 0)
