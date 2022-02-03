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
FORCE = False
SAVE_LOGS = None
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
@click.pass_context
def cli(ctx, verbose, force, save_logs):
    """Example functions.

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

    from lib.utils import check_capture_logs
    from lib.utils import configure_logger
    from lib.utils import print_params_debug

    global FORCE
    global SAVE_LOGS

    FORCE = force
    SAVE_LOGS = save_logs

    configure_logger(verbose=verbose, force=force, record=bool(SAVE_LOGS))
    check_capture_logs(save_logs, force=force)

    print_params_debug(ctx)


## [place sub commands here]


@cli.command('download', context_settings=CONTEXT_SETTINGS)
@click.argument('url', type=str)
@click.argument('dest_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def download_cli(ctx, url, dest_dir):
    """Downloads a file at the given URL to the specified directory.

    Mainly to demonstrate how to construct a complex progress bar.

    \f

    Args:
        url (str): [some description here]
        dest_dir (str): [some description here]
    """
    from functools import partial
    import logging
    import os.path
    import sys
    import signal
    from threading import Event
    from urllib.request import urlopen

    from rich.progress import BarColumn
    from rich.progress import DownloadColumn
    from rich.progress import TaskID
    from rich.progress import TextColumn
    from rich.progress import TimeRemainingColumn
    from rich.progress import TransferSpeedColumn
    from rich.progress import TimeElapsedColumn
    from rich.progress import SpinnerColumn

    from lib.utils import capture_logs
    from lib.utils import get_progress
    from lib.utils import print_params_debug
    from lib.utils import user_allows_file_overwrite

    global FORCE
    global SAVE_LOGS

    print_params_debug(ctx)

    logger = logging.getLogger("rich")

    done_event = Event()

    def handle_sigint(signum, frame):
        done_event.set()

    # See https://rich.readthedocs.io/en/latest/progress.html#columns for additional column types.
    progress = get_progress()(

        # shows that the progress is actively being worked on (not necessary starting with
        # start_task())
        SpinnerColumn(),

        # can display arbitrary text, here used as a descriptor of the task progress
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),

        # separator symbol, can be anything (i like pipes)
        "|",

        # the actual progress bar
        BarColumn(bar_width=None),
        "|",

        # an indicator of the progress as a percentage, requires knowing completion target
        "[progress.percentage]{task.percentage:>3.1f}%",
        "|",

        # built-in column type that tracks total size of download as it progresses, assumes steps
        # are in bytes.
        DownloadColumn(),
        "|",

        # built-in column type that tracks instantaneous transfer speed, assumes the steps are
        # bytes.
        TransferSpeedColumn(),
        "|",

        # built-in column type that displays total time elapsed since calling start_task()
        TimeElapsedColumn(),
        "|",

        # built-in column type that displays instantaneous estimated time remaining
        TimeRemainingColumn(),
    )

    signal.signal(signal.SIGINT, handle_sigint)

    def _download(task_id: TaskID, url: str, path: str) -> None:
        """Download data from a url to a local file."""

        response = urlopen(url)

        # This will break if the response doesn't contain content length
        progress.update(task_id, total=int(response.info()["Content-length"]))

        with open(path, "wb") as dest_file:

            progress.start_task(task_id)
            for data in iter(partial(response.read, 32768), b""):

                dest_file.write(data)
                progress.update(task_id, advance=len(data))

                if done_event.is_set():
                    return

        progress.console.log(f"Downloaded {path}")

    filename = url.split("/")[-1]
    dest_path = os.path.join(dest_dir, filename)
    if user_allows_file_overwrite(dest_path, force=FORCE):
        with progress:
            task_id = progress.add_task("download", filename=filename, start=False)
            _download(task_id, url, dest_path)

    if SAVE_LOGS:
        capture_logs(SAVE_LOGS)


@cli.command("logging", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def logging_cli(ctx):
    """Example logging output at various levels."""

    import logging

    from lib.utils import capture_logs
    from lib.utils import print_params_debug

    global SAVE_LOGS

    print_params_debug(ctx)

    logger = logging.getLogger("rich")

    logger.info("Hello, World!")
    logger.warning("Something's funky!")
    logger.debug("foo bar baz")
    logger.error("Server is shutting down!")
    logger.critical("Yowza!")
    logger.info("[blink]This text is blinking![/] Neat huh?", extra={"markup": True})

    if SAVE_LOGS:
        capture_logs(SAVE_LOGS)


if __name__ == '__main__':

    ## program proper

    cli()
