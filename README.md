Python Flake8 Lint
==================

Python Flake8 Lint is a Sublime Text 2/3 plugin for check Python files against some of the style conventions in **[PEP8](http://www.python.org/dev/peps/pep-0008/)**, **[PEP257](http://www.python.org/dev/peps/pep-0257/)**, **[PyFlakes](https://launchpad.net/pyflakes)**, **[mccabe](http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html)** and **[pep8-naming](https://github.com/flintwork/pep8-naming)**.

Based on **[bitbucket.org/tarek/flake8](https://bitbucket.org/tarek/flake8)**.


Lint tools
----------

**[Flake8](http://pypi.python.org/pypi/flake8)** (used in "Python Flake8 Lint") is a wrapper around these tools:

* **[pep8](http://pypi.python.org/pypi/pep8)** is a tool to check your Python code against some of the style conventions in [PEP8](http://www.python.org/dev/peps/pep-0008/).

* **[PyFlakes](https://launchpad.net/pyflakes)** checks only for logical errors in programs; it does not perform any check on style.

* **[mccabe](http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html)** is a code complexity checker. It is quite useful to detect over-complex code. According to McCabe, anything that goes beyond 10 is too complex. See [Cyclomatic_complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity).

There are additional tools used to lint Python files:

* **[pep257](http://pypi.python.org/pypi/pep257)** is a static analysis tool for checking compliance with Python [PEP257](http://www.python.org/dev/peps/pep-0257/). This lint tool is disabled by default.

* **[pep8-naming](https://github.com/flintwork/pep8-naming)** is a naming convention checker for Python.


Install
-------

**With the Package Control plug-in:** The easiest way to install Python Flake8 Lint is through Package Control, which can be found at this site: http://wbond.net/sublime_packages/package_control

Once you install Package Control, restart Sublime Text and bring up the Command Palette (<kbd>Command</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> on OS X, <kbd>Control</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> on Linux/Windows). Select "Package Control: Install Package", wait while Package Control fetches the latest package list, then select Python Flake8 Lint when the list appears. The advantage of using this method is that Package Control will automatically keep Python Flake8 Lint up to date with the latest version.

**Manual installation:** Download the latest source from [GitHub](https://github.com/dreadatour/Flake8Lint/zipball/master), unzip it and rename the folder to "Python Flake8 Lint". Put this folder into your Sublime Text "Packages" directory.

Or clone the repository to your Sublime Text "Packages" directory:

    git clone git://github.com/dreadatour/Flake8Lint.git "Python Flake8 Lint"

The "Packages" directory is located at:

* Sublime Text 2
    * OS X: `~/Library/Application Support/Sublime Text 2/Packages/`
    * Linux: `~/.config/sublime-text-2/Packages/`
    * Windows: `%APPDATA%/Sublime Text 2/Packages/`
* Sublime Text 3
    * OS X: `~/Library/Application Support/Sublime Text 3/Packages/`
    * Linux: `~/.config/sublime-text-3/Packages/`
    * Windows: `%APPDATA%/Sublime Text 3/Packages/`


Plugin config
-------------

Default "Python Flake8 Lint" plugin config: <kbd>Preferences</kbd>-><kbd>Package Settings</kbd>-><kbd>Python Flake8 Lint</kbd>-><kbd>Settings - Default</kbd>

```JavaScript
{
	// run flake8 lint on file saving
	"lint_on_save": true,
	// run flake8 lint on file loading
	"lint_on_load": false,

	// run lint in live mode: lint file (without popup) every XXX ms
	// please, be careful: this may cause performance issues on ST2
	"live_mode": false,
	// set live mode lint delay, in milliseconds
	"live_mode_lint_delay": 1000,

	// set ruler guide based on max line length setting
	"set_ruler_guide": false,

	// popup a dialog of detected conditions?
	"popup": true,
	// highlight detected conditions?
	"highlight": true,

	// highlight type:
	// - "line" to highlight whole line
	// - "error" to highlight error only
	"highlight_type": "error",

	// color values to highlight detected conditions
	"highlight_color_critical": "#981600",
	"highlight_color_error": "#DA2000",
	"highlight_color_warning": "#EDBA00",

	// show a mark in the gutter on all lines with errors/warnings:
	// - "dot", "circle" or "bookmark" to show marks
	// - "theme-alpha", "theme-bright", "theme-dark", "theme-hard" or "theme-simple" to show icon marks
	// - "" (empty string) to do not show marks
	"gutter_marks": "theme-simple",

	// report successfull (passed) lint
	"report_on_success": false,

    // blink gutter marks on success (will not blink with live mode check)
    // this icon is not depends on 'gutter_marks' settings
    // please, be careful: this may cause performance issues on ST2
    "blink_gutter_marks_on_success": true,

	// load global flake8 config ("~/.config/flake8")
	"use_flake8_global_config": true,
	// load per-project config (i.e. "tox.ini", "setup.cfg" and ".pep8" files)
	"use_flake8_project_config": true,

	// set python interpreter (lint files for python >= 2.7):
	// - 'internal' for use internal Sublime Text interpreter (2.6)
	// - 'auto' for search default system python interpreter (default value)
	// - absolute path to python interpreter for define another one
	//   use platform specific notation, i.e. "C:\\Anaconda\\envs\\py33\\python.exe"
	//   for Windows or then "/home/whatever/pythondist/python" for Unix
	"python_interpreter": "auto",

	// list of python built-in functions (like '_')
	"builtins": [],

	// turn on pyflakes error lint
	"pyflakes": true,
	// turn on pep8 error lint
	"pep8": true,
	// turn on pep257 error lint
	"pep257": false,
	// turn on naming error lint
	"naming": true,
	// turn off complexity check (set number > 0 to check complexity level)
	"complexity": -1,

	// set desired max line length
	"pep8_max_line_length": 79,

	// select errors and warnings (e.g. ["E", "W6"])
	"select": [],
	// skip errors and warnings (e.g. ["E303", E4", "W"])
	"ignore": [],

	// files to ignore, for example: ["*.mako", "test*.py"]
	"ignore_files": []
}
```

To change default settings, go to <kbd>Preferences</kbd>-><kbd>Package Settings</kbd>-><kbd>Python Flake8 Lint</kbd>-><kbd>Settings - User</kbd> and paste default config to the opened file and make your changes.


Flake8 config
-------------

"Python Flake8 Lint" plugin will load config in this order:

1. ST plugin global settings.
2. ST plugin user settings.
3. ST project settings.
4. Global flake8 settings (see also: [Flake8 docs: global config](http://flake8.readthedocs.org/en/latest/config.html#global)):
    - ~/.config/flake8
5. Flake8 project settings (see also: [Flake8 docs: per-project config](http://flake8.readthedocs.org/en/latest/config.html#per-project)):
    - tox.ini
    - setup.cfg
    - .pep8

All settings are inherited, e.g. you can define only one setting in project config file, all other will be inherited from plugin config. If one of the options (e.g. 'ignore' param) will be defined in several config files, only last one will be taken.

There are few "Python Flake8 Lint" plugin options to control flake8 configs:

- "**use_flake8_global_config**" option is used to enable or disable global flake8 config (i.e. "~/.config/flake8" file)
- "**use_flake8_project_config**" option is used to enable or disable local (project) config (i.e. "tox.ini", "setup.cfg" and ".pep8" files)


Project Flake8 config
---------------------

You could define per-project config for "Python Flake8 Lint". Use <kbd>Project</kbd>-><kbd>Edit Project</kbd> menu and add the `flake8lint` section in `settings` as shown below:

```JavaScript
{
	"folders":
	[
		{
			"path": "/path/to/project"
		}
	],
	"settings": {
		"flake8lint": {
			"python_interpreter": "auto",
			"builtins": [],
			"pyflakes": true,
			"pep8": true,
			"naming": true,
			"complexity": -1,
			"pep8_max_line_length": 79,
			"select": [],
			"ignore": [],
			"ignore_files": []
		}
	}
}
```


Note
----

Pep8 ignores "E123", "E226" and "E24" errors by default. This plugin will not ignore them.

If you're not agree with this plugin, please, add next string in your config:

    "ignore": ["E123", "E226", "E24"]


Features / Usage
----------------

Automatically check Python files with flake8 lint tool and show window with error list:

[![Error list](http://habrastorage.org/files/c24/bad/d90/c24badd902b542f292be3f11c8542dc6.png)](http://habrastorage.org/files/c24/bad/d90/c24badd902b542f292be3f11c8542dc6.png)

And move to error line/char on select.

Use these keys (by default) to run lint:

* OS X: <kbd>Ctrl+Super+8</kbd>
* Linux: <kbd>Ctrl+Alt+8</kbd>
* Windows: <kbd>Ctrl+Alt+Shift+8</kbd>

Use these keys (by default) to jump to next lint error:

* OS X: <kbd>Ctrl+Super+9</kbd>
* Linux: <kbd>Ctrl+Alt+9</kbd>
* Windows: <kbd>Ctrl+Alt+Shift+9</kbd>
