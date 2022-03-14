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


## Lib Functions


def _copy_safe(path, source_dir=None, output_dir=None, overwrite=False):
    import logging

    logger = logging.getLogger("rich")

    try:

        _copy(path, source_dir=source_dir, output_dir=output_dir, overwrite=overwrite)

    except Exception as e:

        logger.error(f'Job failed: {e}')


def _copy(path, source_dir=None, output_dir=None, overwrite=False):
    import logging
    import os
    import pathlib

    logger = logging.getLogger("rich")

    p = pathlib.Path(path)
    sd = pathlib.Path(source_dir)

    basename = p.parts[-1]
    sub_path = p.parts[len(sd.parts):-1]
    output_path = os.path.join(output_dir, *sub_path)

    # preserve subpaths from input
    try:
        os.makedirs(output_path)
        logger.debug(f"Created path: {output_path}")
    except FileExistsError:
        logger.debug(f"Path already existed: {output_path}")

    # check whether to write output
    full_output_path = pathlib.Path(os.path.join(output_path, basename))
    write = False
    if full_output_path.exists():
        if full_output_path.is_dir():
            logger.debug(f"Skipping! Existing directory found at output path: {full_output_path}")
        elif full_output_path.is_file():
            if overwrite:
                logger.debug(f"Overwriting existing file at output path: {full_output_path}")
                write = True
            else:
                logger.debug(f"Skipping! Existing file found at output path: {full_output_path}")
    else:
        write = True

    if write:

        with open(path, 'rb') as f:
            doc = f.read()

        with open(full_output_path, "wb") as f:
            f.write(doc)

        logger.debug(f">>> Wrote {full_output_path}")


## CLI Functions


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, help="Show verbose output. Pass again for debug.")
@click.option('-f', '--force', is_flag=True, help="Overwrite existing files.")
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
@click.option(
    '-b', '--batch-size', type=int, default=100,
    help="Number of jobs each worker thread runs before waiting for the next batch."
)
@click.option('-r', '--recursive', is_flag=True, help="Scan subdirectories as well.")
@click.option(
    '--extension', 'ftype', type=str, help="Only operate on files with the given extension."
)
@click.argument('source-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def cli(
    ctx,
    verbose,
    force,
    save_logs,
    num_threads,
    batch_size,
    recursive,
    ftype,
    source_dir,
    output_dir
):
    """Multiprocessing file copier.

    Local copies only. Reads whole file into memory and write to the specified output directory,
    preserving sub-paths from the input location.

    Note that overwriting files in the OUTPUT-DIR is forced only when the `-f` option is passed.
    Otherwise, files are _not_ overwritten.

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
        num_threads (int): the number of worker threads to parallelize the jobs over. Defaults to
            the number of CPU threads available on the system.
        batch_size (int): the number of jobs each worker thread runs before waiting for the next
            batch. Defaults to 100.
        recursive (bool): if True, check subdirectories as well. Defaults to False.
        ftype (str): a file extension to filter by; only copy files ending with the given extension.
    """
    from functools import partial
    from multiprocessing import Pool
    import logging

    from lib.utils import capture_logs
    from lib.utils import check_capture_logs
    from lib.utils import configure_logger
    from lib.utils import count_dir_files
    from lib.utils import get_std_progress_bar
    from lib.utils import print_params_debug
    from lib.utils import walk_files

    ## configure

    configure_logger(verbose=verbose, force=force, record=bool(save_logs))
    check_capture_logs(save_logs, force=force)

    print_params_debug(ctx)

    logger = logging.getLogger("rich")

    ## spool progress bar

    logger.info("Spooling...")
    progress = get_std_progress_bar()
    total_jobs = count_dir_files(source_dir, ftype=ftype, recursive=recursive)

    ## start main operation

    logger.info(
        f"Starting copy job for {total_jobs} files over {num_threads} threads."
    )

    progress.start()
    pool = Pool(processes=num_threads)
    for _ in progress.track(
        pool.imap_unordered(

            partial(_copy_safe, source_dir=source_dir, output_dir=output_dir, overwrite=force),

            # generator that yields path strings
            walk_files(source_dir, ftype=ftype, recursive=recursive),

            # each thread gets a queue of `chunksize` jobs
            chunksize=batch_size
        ),
        description="Copying files in parallel",
        total=total_jobs
    ):
        pass # neat trick: https://stackoverflow.com/a/40133278/2610790

    pool.close()
    pool.join()

    logger.info("Job pool complete.")

    if save_logs:
        capture_logs(save_logs)


if __name__ == '__main__':

    cli()
