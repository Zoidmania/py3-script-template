#!/usr/bin/env python3

"""
[This is a skeleton template for scripts written in this library. Follows Google's Python style
guide. See https://click.palletsprojects.com/en/8.0.x/ for more details.]

[Init Date]
[Author]
"""

__author__  = "[Author <email>]"
__status__  = "[status]"
__date__    = "[Last Mod Date]"

import click

from lib.utils import CONTEXT_SETTINGS
from lib.utils import LOGGER
FORCE = False
"""bool: Global flags handled by cli()."""


## [put non-CLI helper functions here]


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, help="Show verbose output. Pass again for debug.")
@click.option('-f', '--force', is_flag=True, help="Skip asking to overwrite output.")
@click.option(
    '-l',
    '--save-logs',
    'save_logs',
    type=click.Path(),
    help="Capture logging output (at whatever verbosity level) to the specified path."
)
def cli(verbose, force, save_logs):
    """[Write a high-level description of the script here. Keep it short; 1 sentence. Only the
    first sentence will appear in the shorthand docs.]

    [Write the rest of the description here. Appears in full help doc, rather than inline lists.]

    \f

    [Everything under the ``\\f`` is omitted from the help doc.]

    This function serves as the entrypoint for the program when called on the CLI. It also handles
    global flag ``verbose``.

    Args:
        verbose (int): if 1, pretty-print output as the command runs. If 2, print debugging output
            in addition to level 1 output. If 0, prints nothing as the command runs. Defaults to 0.
        force (bool): if True, skip asking for permission to overwrite a file with output. Defaults
            to False.
        save_logs (str): a path to write captured logging output to.
    """
    # do this before anything else
    import logging

    from lib.utils import capture_logs

    global FORCE
    global LOGGER

    if verbose == 1:
        LOGGER.setLevel(logging.INFO)
        LOGGER.info("Verbose output is on!")
    elif verbose > 1:
        LOGGER.setLevel(logging.DEBUG)
        LOGGER.debug("Debug output is on!")

    if verbose and force:
        LOGGER.warning("Forced overwrite is on!")
    elif verbose and not force:
        LOGGER.info("Forced overwrite is off!")

    FORCE = force

    if save_logs:
        capture_logs(save_logs, force=FORCE)


## [place sub commands here]


@cli.command('sub_command', context_settings=CONTEXT_SETTINGS)
@click.option(
    '-a', # short name
    '--opt1', # long name
    'opt1s', # function arg name
    multiple=True, # set this to enable passing this option multiple times, turns into a list
    type=click.Path(exists=True), # set a type, defaults to string
    help="This is a help string" # options may have help strings
)
@click.option(
    '-b',
    '--opt2',
    'opt2',
    help="This is a help string"
)
@click.argument('arg1', type=click.Path(exists=True))
@click.argument('arg2', type=click.Path())
def sub_command_cli(opt1s, opt2, arg1, arg2):
    """[Write a high-level description of the command here. Keep it short; 1 sentence. Only the
    first sentence will appear in the shorthand docs.]

    [Write the rest of the description here. Appears in full help doc, rather than inline lists.]

    \f

    [Everything under the ``\\f`` is omitted from the help doc.]

    Args:
        opt1s (list): [some description here]
        opt1 (str): [some description here]
        arg1 (str): [some description here]
        arg2 (str): [some description here]
    """
    pass


if __name__ == '__main__':

    ## program proper

    cli()
