Python Flake8 Lint
==================

Python Flake8 Lint is a Sublime Text 2 plugin for check Python files against some of the style conventions in **[PEP8](http://www.python.org/dev/peps/pep-0008/)**, **[PyFlakes](https://launchpad.net/pyflakes)** and **[mccabe](http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html)**.

Based on **[bitbucket.org/tarek/flake8](https://bitbucket.org/tarek/flake8)**.


Lint tools
----------

**[Flake8](http://pypi.python.org/pypi/flake8)** (used in "Python Flake8 Lint") is a wrapper around these tools:

* **[pep8](http://pypi.python.org/pypi/pep8)** is a tool to check your Python code against some of the style conventions in [PEP8](http://www.python.org/dev/peps/pep-0008/).

* **[PyFlakes](https://launchpad.net/pyflakes)** checks only for logical errors in programs; it does not perform any check on style.

* **[mccabe](http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html)** is a code complexity checker. It is quite useful to detect over-complex code. According to McCabe, anything that goes beyond 10 is too complex. See [Cyclomatic_complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity).


Install
-------

**With the Package Control plug-in:** The easiest way to install Python Flake8 Lint is through Package Control, which can be found at this site: http://wbond.net/sublime_packages/package_control

Once you install Package Control, restart ST2 and bring up the Command Palette (Command+Shift+P on OS X, Control+Shift+P on Linux/Windows). Select "Package Control: Install Package", wait while Package Control fetches the latest package list, then select Python Flake8 Lint when the list appears. The advantage of using this method is that Package Control will automatically keep Python Flake8 Lint up to date with the latest version.

**Manual installation:** Download the latest source from [GitHub](https://github.com/dreadatour/Flake8Lint/zipball/master), unzip it and rename the folder to "Python Flake8 Lint". Put this folder into your ST2 "Packages" directory.

Or clone the repository to your ST2 "Packages" directory:

    git clone git://github.com/dreadatour/Flake8Lint.git "Python Flake8 Lint"

The "Packages" directory is located at:

* OS X:

        ~/Library/Application Support/Sublime Text 2/Packages/

* Linux:

        ~/.config/sublime-text-2/Packages/

* Windows:

        %APPDATA%/Sublime Text 2/Packages/


Config
------

Default Python Flake8 Lint config: "Preferences" -> "Package Settings" -> "Python Flake8 Lint" -> "Settings - Default"

	{
		// run flake8 lint on file saving
		"lint_on_save": true,

		// popup a dialog of detected conditions?
		"popup": true,

		// highlight detected conditions?
		"highlight": true,

		// set python interpreter (lint files for python >= 2.7):
		// - 'internal' for use internal Sublime Text 2 interpreter (2.6)
		// - 'auto' for search default system python interpreter (default value)
		// - absolute path to python interpreter for define another one
		"python_interpreter": "auto",

		// turn on pyflakes error lint
		"pyflakes": true,
		// turn on pep8 error lint
		"pep8": true,
		// turn off complexity check (set number > 0 to check complexity level)
		"complexity": -1,

		// set desired max line length
		"pep8_max_line_length": 79,

		// select errors and warnings (e.g. ["E", "W6"])
		"select": [],
		//skip errors and warnings (e.g. ["E303", E4", "W"])
		"ignore": [],

		// files to ignore, for example: ["*.mako", "test*.py"]
		"ignore_files": []
	}

To change default settings, go to "Preferences" -> "Package Settings" -> "Python Flake8 Lint" -> "Settings - User" and paste default config to the opened file and make your changes.


Note
----

Pep8 ignores "E24" errors by default. This plugin will not ignore them.

If you're not agree with this plugin, please, add next string in your config:

    "ignore": ["E24"]


Features / Usage
----------------

Automatically check Python files with flake8 lint tool and show window with error list:

[![Error list](http://habrastorage.org/storage2/5ac/5f2/ded/5ac5f2ded857d962d1ca78da087a65f7.png)](http://habrastorage.org/storage2/5ac/5f2/ded/5ac5f2ded857d962d1ca78da087a65f7.png)

And move to error line/char on select.
