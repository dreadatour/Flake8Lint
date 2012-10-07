Flake8Lint
=========

Flake8Lint is a Sublime Text 2 plugin for check Python files against some of the style conventions in **[PEP8](http://www.python.org/dev/peps/pep-0008/)**, **[PyFlakes](https://launchpad.net/pyflakes)** and **[mccabe](http://nedbatchelder.com/blog/200803/python_code_complexity_microtool.html)**.

Based on **[bitbucket.org/tarek/flake8](https://bitbucket.org/tarek/flake8)**.

Install
-------

Download the latest source from [GitHub](https://github.com/dreadatour/Flake8Lint/zipball/master) and copy *Flake8Lint* folder to your ST2 "Packages" directory.

Or clone the repository to your ST2 "Packages" directory:

    git clone git://github.com/dreadatour/Flake8Lint.git


The "Packages" directory is located at:

* OS X:

        ~/Library/Application Support/Sublime Text 2/Packages/

* Linux:

        ~/.config/sublime-text-2/Packages/

* Windows:

        %APPDATA%/Sublime Text 2/Packages/

Config
------

Default Flake8Lint config: "Preferences" -> "Package Settings" -> "Flake8Lint" -> "Settings - Default"

	{
		// run flake8 lint on file saving
		"lint_on_save": true,

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

		// select errors and warnings (e.g. ["E", "W6"])
		"select": [],
		//skip errors and warnings (e.g. ["E303", E4", "W"])
		"ignore": []
	}

To change default settings, go to "Preferences" -> "Package Settings" -> "Flake8Lint" -> "Settings - User" and paste default config to opened file.

Features / Usage
----------------

Automatically check Python files with flake8 lint tool and show window with error list:

[![Error list](http://habrastorage.org/storage2/5ac/5f2/ded/5ac5f2ded857d962d1ca78da087a65f7.png)](http://habrastorage.org/storage2/5ac/5f2/ded/5ac5f2ded857d962d1ca78da087a65f7.png)

And move to error line/char on select.
