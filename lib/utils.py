"""Utility functions.

Leland E. Vakarian
20 Jan, 2022
"""

__author__ = "Leland E. Vakarian"


from datetime import datetime

from click.core import Context

## Config

CAPTURE_LOGS_ALLOWED = False
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=100)

def configure_logger(verbose=False, force=False, record=False):
    """Configures logging.

    Defined before anything else because logger configuration should be handled first.

    Since logging is handled through ``rich``, we need to enable recording when the logger is
    instantiated. A separate call to the console object the the logger's handler uses writes the
    logs to a file.

    Args:
        verbose (bool): whether verbose output should be emitted.
        force (bool): whether forced file overwrite is enabled.
        record (bool): whether to record logs to a file location.
    """
    import logging
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.theme import Theme

    theme = Theme({
        "logging.level.debug": "bright_magenta",
        "logging.level.info": "bright_green",
        "logging.level.warning": "bright_yellow",
        "logging.level.error": "bright_red",
        "logging.level.critical": "white on red",
    })
    console = Console(theme=theme, record=record)

    # Remove all existing handlers so we can reconfigure the logger with subsequent calls to this
    # function. See https://stackoverflow.com/a/12158233/2610790.
    for handler in logging.root.handlers:
        logging.root.removeHandler(handler)

    handler = RichHandler(markup=True, rich_tracebacks=True, console=console)
    logging.basicConfig(
        level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[handler,]
    )

    logger = logging.getLogger("rich")

    # https://docs.python.org/3/library/logging.html#logging.Logger.setLevel
    if verbose == 1:
        logger.setLevel(logging.INFO)
        logger.info("Verbose output is on!")
    elif verbose > 1:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug output is on!")
    else:
        logger.setLevel(51)

    if verbose and force:
        logger.warning("Forced overwrite is on!")
    elif verbose and not force:
        logger.info("Forced overwrite is off!")

configure_logger()


## Utilities


def capture_logs(path: str):
    """Captures logging output to the specified path.

    Args:
        path (str): a path to write the logs.
    """
    import logging
    import os

    global CAPTURE_LOGS_ALLOWED

    logger = logging.getLogger("rich")

    if not CAPTURE_LOGS_ALLOWED:
        logger.error(f"Can't write logs to {path}! Skipping!")
        return

    console = get_logger_console()
    if console:

        if os.path.dirname(path):

            if os.path.exists(os.path.dirname(path)):

                # clears the recording buffer after writing
                console.save_text(path)
            else:
                logger.error("Parent directory to the given path doesn't exist!")
        else:
            logger.error("Can't write to local directory!")
    else:
        logger.error("No console to capture output from!")


def check_capture_logs(path: str, force=False):
    """Checks if a file exists at the specified output path, and whether to ask the user before
    overwriting it.

    Args:
        path (str): a path to write the logs, or none.
        force (bool): if True, skip asking for permission to overwrite a file with output. Defaults
            to False.
    """

    import logging
    import os

    global CAPTURE_LOGS_ALLOWED

    logger = logging.getLogger("rich")

    if not path:
        return

    if user_allows_file_overwrite(path, force):

        CAPTURE_LOGS_ALLOWED = True
        if os.path.exists(path):
            os.remove(path)

    else:

        logger.info(f"User chose to not overwrite existing log output file.")


def count_file_lines(path: str) -> int:
    """Counts the number of lines in a file.

    This method is capable of handling extremely large files with a streaming solution. Credit to
    https://stackoverflow.com/a/27518377/2610790. Speed is decent; on a Threadripper 3995WX,
    counting a file with roughly 3 million lines takes about 2 seconds.

    Args:
        path (str): a path to any file.

    Returns:
        int: the number of lines within the given file.
    """

    import os

    assert os.path.isfile(path), "Path must be a file!"

    def _make_gen(reader):
        b = reader(1024 * 1024)
        while b:
            yield b
            b = reader(1024 * 1024)

    f = open(path, 'rb')
    f_gen = _make_gen(f.raw.read)
    return sum(buf.count(b'\n') for buf in f_gen)


def count_dir_files(path: str) -> int:
    """Counts the number of files in a directory.

    This method is capable of handling extremely large directories with a streaming solution. See
    https://docs.python.org/3/library/os.html#os.scandir for details.

    Args:
        path (str): a path to any directory.

    Returns:
        int: the number of lines within the given file.
    """

    import os

    assert os.path.isdir(path), "Path must be a directory!"

    num_files = 0
    for path in os.scandir(path):
        if path.is_file():
            num_files += 1

    return num_files


def datetime_is_naive(d: datetime) -> bool:
    """Determines whether a datetime isn't localized.

    See https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive.

    Args:
        d (datetime.datetime): an object to check.

    Returns:
        bool: True if the datetime isn't localized.
    """
    return d.tzinfo is None or d.tzinfo.utcoffset(d) is None


def get_logger_console():
    # find the console for the rich handler
    import logging
    logger = logging.getLogger("rich")
    handler = get_logger_handler()
    try:
        console = handler.console
        return console
    except:
        logger.error("Can't find global console to capture logs!")


def get_logger_handler():
    # find the rich handler for the root logger
    import logging

    from rich.logging import RichHandler

    handler = None
    for handler in logging.root.handlers:
        if type(handler) == RichHandler:
            break
    return handler


def logger_get_level_name() -> str:
    """Gets the name of the output level of the global logger.

    Generally follows the rules for logging.getLevelName(). If the value is higher than any of the
    built-in levels, "SILENT" is returned.

    Returns:
        str: the name of the output level of the global logger.
    """
    import logging

    logger = logging.getLogger("rich")

    level = logger.getEffectiveLevel()
    if level > 50:
        return "SILENT"
    else:
        return logging.getLevelName(level)


def logger_set_level(level: int) -> int:
    """Sets the root logger to debug level and returns the previous level.

    Args:
        level (int): new logging level to set the root logger to.

    Returns:
        int: the previous logging level.
    """

    import logging

    logger = logging.getLogger("rich")

    prev_level = logger.getEffectiveLevel()
    logger.setLevel(level)

    return prev_level


def open_json_blob(path: str) -> dict:
    """A standard way to load a unicode JSON blob from disk, using the built-in ``json`` module.

    Args:
        path (str): a path to a location on disk.

    Returns:
        dict: a Python dictionary representation of the JSON data.
    """
    import json

    with open(path, 'r', encoding='utf-8') as f:
        doc = json.loads(f.read())

    return doc


def prettify_long_path(path: str) -> str:
    """Condenses absolute path names for pretty-printing."""
    import os
    return f"/.../{os.path.basename(path)}" if os.path.basename(path) != path else path


def print_params_debug(ctx: Context):
    """Prints parameter values to the console for debug.

    Args:
        ctx (click.core.Context): a context object for a called click command.
    """
    import logging

    from rich import box
    from rich.table import Table

    logger = logging.getLogger("rich")

    if logger.getEffectiveLevel() > 10:
        return

    console = get_logger_console()

    console.rule(f"[bright_magenta]'{str(ctx.command)}' Command Parameters")

    if not ctx.params:

        logger.debug("No parameters for this command!")

    else:

        table = Table(title="Command Parameters", box=box.SIMPLE)

        table.add_column("Param Name", justify="left", style="cyan", no_wrap=True)
        table.add_column("Param Source", justify="left", style="green", no_wrap=True)
        table.add_column("Param Type", justify="left", style="magenta", no_wrap=True)
        table.add_column("Param Value", justify="right", style="white", no_wrap=False)

        for param, value in ctx.params.items():
            table.add_row(param, str(ctx.get_parameter_source(param)), str(type(value)), str(value))

        console.print(table)

    console.rule()


def read_datetime(x) -> datetime:
    """Builds a datetime object from an ISO-formatted string, or standardizes an existing
    ``datetime`` object.

    If no timezone is provided, UTC is assumed.

    Args:
        s (str|datetime.datetime): an ISO-formatted string to read, or a ``datetime`` object.

    Returns:
        datetime: a tz-aware ``datetime``, or ``None`` if bad input.
    """
    from datetime import datetime
    import pytz

    if type(x) == type(datetime.now()):
        d = x
    elif type(x) == str:
        d = datetime.fromisoformat(x)
    else:
        return None

    if datetime_is_naive(d):
        d.replace(tzinfo=pytz.utc)

    return d


def slugify(value: str, allow_unicode=False) -> str:
    """Sanitizes a string so that it is suitable for use as a file name.

    Operations:
        - Convert spaces or repeated dashes to single dashes.
        - Remove characters that aren't alphanumerics, underscores, or hyphens. Convert to
          lowercase. Also strip leading and trailing whitespace, dashes, and underscores.

    Taken from https://github.com/django/django/blob/master/django/utils/text.py.

    Args:
        value (str): the value to sanitize.
        allow_unicode (bool): Convert to ASCII if False.

    Returns:
        str: a slugified string value.
    """
    import logging
    import re
    import unicodedata

    logger = logging.getLogger("rich")

    logger.debug(f"Slugify input: {value}.")

    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value).strip('-_')

    logger.debug(f"Slugify output: {value}.")

    return value


def sorted_dicts_are_equal(a: dict, b: dict) -> bool:
    """Sorts list-like elements of a dictionary before determining equivalence.

    Dictionary equivalence depends on the values of their keys. Order matters for list-like values.

    Does not modify the original object.

    Args:
        a (dict-like): a generic dict-like object.
        b (dict-like): another generic dict-like object.

    Returns:
        bool: whether the dicts are equivalent, discounting list order.
    """

    bools = []
    for key in a:
        if key in b:
            if type(a[key]) == list and type(b[key]) == list:
                bools.append(sorted(a[key]) == sorted(b[key]))
            else:
                bools.append(a[key] == b[key])
        else:
            bools.append(False)

    return all(bools)


def user_allows_dir_overwrite(path: str, force=False) -> bool:
    """Interactively checks to see if the user wants to overwrite the directory at the given path.

    Set ``force`` to ``True`` to bypass interactively asking on the CLI, and assume "it's OK to
    overwrite".

    Args:
        path (str): a string containing a dir location.
        force (bool): skip this check and assert "OK" if True.

    Returns:
        bool: indication of whether writing a file to this path is "OK". If no file existed at the
        path, the assumption is "OK".
    """
    import logging
    import os
    import sys

    import click

    logger = logging.getLogger("rich")

    warning = click.style("WARNING", fg='bright_yellow')

    if os.path.isdir(path) and any(os.scandir(path)):

        if not force:

            if logger.isEnabledFor(logging.ERROR):
                ans = click.confirm((
                    f"           {warning}  Directory at '{path}' isn't empty. Do you want to "
                    "potentially overwrite the files within?"
                ))
            else:
                ans = click.confirm(f"Overwrite '{path}'?")

            if ans:
                logger.warning("Overwriting file!")
            else:
                logger.error("Canceling due to denied overwrite.")
                return False

    return True


def user_allows_file_overwrite(path: str, force=False) -> bool:
    """Interactively checks to see if the user wants to overwrite a file at the given path.

    Set ``force`` to ``True`` to bypass interactively asking on the CLI, and assume "it's OK to
    overwrite".

    Args:
        path (str): a string containing a file location.
        force (bool): skip this check and assert "OK" if True.

    Returns:
        bool: indication of whether writing a file to this path is "OK". If no file existed at the
        path, the assumption is "OK".
    """
    import logging
    import os
    import sys

    import click

    logger = logging.getLogger("rich")

    warning = click.style("WARNING", fg='bright_yellow')

    if os.path.isfile(path):

        if not force:

            if logger.isEnabledFor(logging.ERROR):
                ans = click.confirm((
                    f"           {warning}  A file exists at the path '{path}'. Do you really want "
                    "to overwrite it?"
                ))
            else:
                ans = click.confirm(f"Overwrite '{path}'?")

            if ans:
                logger.warning("Overwriting file!")
            else:
                logger.error("Canceling due to denied overwrite.")
                return False

    return True


def write_json_blob(doc: dict, path: str, force=False):
    """Writes a JSON document in a consistent manner, using the standard ``json`` module.

    Args:
        doc (dict): a dictionary to translate into JSON.
        path (str): a path to write the JSON blob.
        force (bool): skip asking for permission to overwrite.
    """
    import logging
    import json
    import os
    import sys

    logger = logging.getLogger("rich")

    try:
        if os.path.dirname(path):
            assert os.path.exists(os.path.dirname(path))
    except AssertionError:
        logger.error(f"Directory {os.path.dirname(path)} doesn't exist!")
        sys.exit()

    if force or user_allows_file_overwrite(path):
        with open(path, 'w', encoding='utf-8') as f:
            blob = json.dumps(doc, ensure_ascii=False)
            f.write(blob)
