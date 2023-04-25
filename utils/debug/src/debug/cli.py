"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mdebug` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``debug.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``debug.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import re

import typer
from typer import Argument

from debug import Debug

app = typer.Typer()
app = Debug()


# @app.command()
def debug(
    module: str = typer.Argument(
        ..., help='name of python module or file to run, ex: unittest'),
    args: str = Argument(
        None, help='optional arg to pass to model. '
        + 'if running the unittest module, '
        + 'this will be the path to run unittest discovery from'),
) -> None:
    """
    Run a python module with this module used as the default debugger.
    Currently supports only running python modules and not scripts (*.py).

    Example usages:
    debug unittest  # like running `python -m unittest`
    debug unittest ~/module   # like running `cd ~/module; python -m unittest`
    debug graph  # like running `python -m graph`
    """
    args = re.sub('_', '_ ', args)
    args = args.split('_')
    print(args)
    Debug()(module, args)


if __name__ == '__main__':
    Debug()
