#!/usr/bin/env python3

"""
Finds and copies files from one directory to another.

10 Mar, 2022
Leland E. Vakarian
"""

__author__ = "Leland E. Vakarian"
__status__  = "production"
__date__    = "11 Mar, 2022"


import click
import multiprocessing


## Globals


from lib.utils import CONTEXT_SETTINGS
FORCE = False
SAVE_LOGS = None


## Helpers


def _copy_safe(path, source_dir=None, output_dir=None):
    import logging

    logger = logging.getLogger("rich")

    try:

        _copy(path, source_dir, output_dir)

    except Exception as e:

        logger.error(f'Job failed: {e}')


def _copy(path, source_dir, output_dir):
    import logging
    import os
    import pathlib

    logger = logging.getLogger("rich")

    logger.debug(f"Copying: {path}")

    with open(path, 'rb') as f:
        doc = f.read()

    p = pathlib.Path(path)
    sd = pathlib.Path(source_dir)

    basename = p.parts[-1]
    sub_path = p.parts[len(sd.parts):-1]
    output_path = os.path.join(output_dir, *sub_path)

    # preserve subpaths from input
    try:
        os.makedirs(output_path)
        logger.debug(f">>> Created path: {output_path}")
    except FileExistsError:
        logger.debug(f">>> Path already existed: {output_path}")

    full_output_path = os.path.join(output_path, basename)
    with open(full_output_path, "wb") as f:
        f.write(doc)

    logger.debug(f">>> Wrote {full_output_path}")


## CLI Functions


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, help="Show verbose output. Pass again for debug.")
@click.option('-f', '--force', is_flag=True, help="Skip asking to overwrite logs.")
@click.option(
    '-l',
    '--save-logs',
    'save_logs',
    type=click.Path(),
    help="Capture logging output (at whatever verbosity level) to the specified path."
)
@click.option(
    '-n', '--num-threads', type=int, default=multiprocessing.cpu_count(),
    help=(
        "Number of threads to execute in parallel. Defaults to number of available CPU threads "
        f"({multiprocessing.cpu_count()} on this machine)."
    )
)
@click.option('-r', '--recursive', is_flag=True, help="Scan subdirectories as well.")
@click.option(
    '--extension', 'ftype', type=str, help="Only operate on files with the given extension."
)
@click.argument('source-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def cli(ctx, verbose, force, save_logs, num_threads, recursive, ftype, source_dir, output_dir):
    """Multiprocessing file copier.

    Local copies only. Reads whole file into memory and write to the specified output directory,
    preserving sub-paths from the input location.

    Note that overwriting files in the OUTPUT-DIR is forced. The `-f` option only applies to an
    outputted log file (`--save-logs`).

    \b
    Args:
        SOURCE-DIR is a path to the file(s) to copy.
        OUTPUT-DIR is a path to place the output of this command.

    \f

    This function serves as the entrypoint for the program when called on the CLI. It also handles
    global flag ``verbose``.

    Args:
        verbose (int): if 1, pretty-print output as the command runs. If 2, print debugging output
            in addition to level 1 output. If 0, prints nothing as the command runs. Defaults to 0.
        force (bool): if True, skip asking for permission to overwrite a file with output. Defaults
            to False.
        save_logs (str): a path to write captured logging output to.
        recursive (bool): if True, check subdirectories as well. Defaults to False.
        ftype (str): a file extension to filter by; only copy files ending with the given extension.
    """

    from functools import partial
    from multiprocessing import Pool
    import logging

    from rich.progress import BarColumn
    from rich.progress import Progress
    from rich.progress import TaskID
    from rich.progress import TextColumn
    from rich.progress import TimeRemainingColumn
    from rich.progress import TimeElapsedColumn

    from lib.utils import check_capture_logs
    from lib.utils import configure_logger
    from lib.utils import count_dir_files
    from lib.utils import P_PREFIX
    from lib.utils import print_params_debug
    from lib.utils import walk_files

    ## configure

    global FORCE
    global SAVE_LOGS

    FORCE = force
    SAVE_LOGS = save_logs

    configure_logger(verbose=verbose, force=force, record=bool(SAVE_LOGS))
    check_capture_logs(save_logs, force=force)

    print_params_debug(ctx)

    logger = logging.getLogger("rich")

    ## spool progress bar

    progress = Progress(

        # can display arbitrary text, here used as a descriptor of the task progress
        TextColumn(P_PREFIX + "[bold blue]{task.fields[filename]}", justify="right"),

        # separator symbol, can be anything (i like pipes)
        "|",

        # the actual progress bar
        BarColumn(bar_width=None),
        "|",

        # an indicator of the progress as a percentage, requires knowing completion target
        "[progress.percentage]{task.percentage:>3.1f}%",
        "|",

        # built-in column type that displays total time elapsed since calling start_task()
        TimeElapsedColumn(),
        "|",

        # built-in column type that displays instantaneous estimated time remaining
        TimeRemainingColumn(),

        # hide progress display when in silent mode
        disable=not logger.isEnabledFor(logging.INFO)
    )

    logger.info("Spooling...")
    total_jobs = count_dir_files(source_dir, ftype=ftype, recursive=recursive)

    ## start operation

    logger.info(
        f"Starting copy-oa job for {total_jobs} files over {num_threads} threads."
    )

    pool = Pool(processes=num_threads)
    for _ in progress.track(
        pool.imap_unordered(

            partial(_copy_safe, source_dir=source_dir, output_dir=output_dir),

            # generator that yields path strings
            walk_files(source_dir, ftype=ftype, recursive=recursive),

            # each thread gets a queue of `chunksize` jobs
            chunksize=10
        ),
        description="Running parallelized merge jobs",
        total=total_jobs
    ):
        pass # neat trick: https://stackoverflow.com/a/40133278/2610790

    pool.close()
    pool.join()

    logger.info("Job pool complete.")


if __name__ == '__main__':

    cli()
