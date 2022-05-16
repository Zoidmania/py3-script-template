"""Utility functions.

Leland E. Vakarian
20 Jan, 2022
"""

__author__ = "Leland E. Vakarian"


from datetime import datetime

from click.core import Context
from rich.progress import ProgressColumn
from rich.progress_bar import ProgressBar


## Config


CAPTURE_LOGS_ALLOWED = False
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=100)
P_PREFIX = "           [bright_green]INFO[/]     "

def configure_logger(verbose=0, force=False, record=False):
    """Configures logging.

    Defined before anything else because logger configuration should be handled first.

    Since logging is handled through ``rich``, we need to enable recording when the logger is
    instantiated. A separate call to the console object the the logger's handler uses writes the
    logs to a file.

    Args:
        verbose (int): verbosity level, where < 1 is silent, 1 is verbose, and > 1 is debug.
        force (bool): whether forced file overwrite is enabled.
        record (bool): whether to record logs to a file location.
    """
    import logging

    import requests
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
    urllib3_log = logging.getLogger('urllib3')

    # https://docs.python.org/3/library/logging.html#logging.Logger.setLevel
    if verbose == 1:
        logger.setLevel(logging.INFO)
        urllib3_log.setLevel(51)
        logger.info("Verbose output is on!")
    elif verbose > 1:
        logger.setLevel(logging.DEBUG)
        urllib3_log.setLevel(logging.DEBUG)
        logger.debug("Debug output is on!")
    else:
        logger.setLevel(51)

    if verbose and force:
        logger.warning("Forced overwrite is on!")
    elif verbose and not force:
        logger.info("Forced overwrite is off!")

configure_logger()


## Classes


class IndeterminateBarColumn(ProgressColumn):
    """Renders a visual indeterminate progress bar.

    Modification of the built-in `rich.progress.BarColumn` class, using `rich` v12.0.1.

    Args:
        bar_width (Optional[int], optional): Width of bar or None for full width. Defaults to 40.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to
            "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.done".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
    """

    def __init__(
        self,
        bar_width = 40,
        style = "bar.back",
        complete_style = "bar.complete",
        finished_style = "bar.finished",
        pulse_style = "bar.pulse",
        table_column = None,
    ) -> None:
        self.bar_width = bar_width
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> ProgressBar:
        """Gets a progress bar widget for a task."""
        return ProgressBar(
            total=max(0, task.total),
            completed=max(0, task.completed),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=True,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )


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


def count_dir_files(path: str, ftype=None, recursive=False) -> int:
    """Counts the number of files in a directory.

    This method is capable of handling extremely large directories with a streaming solution. See
    https://docs.python.org/3/library/os.html#os.scandir for details.

    Args:
        path (str): a path to any directory.
        ftype (str): only files with an extension matching ``ftype`` will be included in the result
           if populated.
        recursive (bool): if True, check subdirectories as well. Defaults to False.

    Returns:
        int: the number of files within the given dir.
    """

    import os

    assert os.path.isdir(path), "Path must be a directory!"

    num_files = 0
    for path_ in os.scandir(path):
        if path_.is_file():
            if not ftype or (ftype and str(path_.name).endswith(ftype)):
                num_files += 1
        elif recursive and path_.is_dir():
            num_files += count_dir_files(path_, ftype=ftype, recursive=recursive)

    return num_files


def count_dir_files_and_size(path: str, ftype=None, recursive=False) -> int:
    """Counts the number of files in a directory and their total size.

    This method is capable of handling extremely large directories with a streaming solution. See
    https://docs.python.org/3/library/os.html#os.scandir for details.

    Args:
        path (str): a path to any directory.
        ftype (str): only files with an extension matching ``ftype`` will be included in the result
           if populated.
        recursive (bool): if True, check subdirectories as well. Defaults to False.

    Returns:
        2-tuple: (int, int): the number of files within the given dir, and the total size in bytes.
    """

    import os

    assert os.path.isdir(path), "Path must be a directory!"

    num_files = 0
    total_size = 0
    for path_ in os.scandir(path):
        if path_.is_file():
            if not ftype or (ftype and str(path_.name).endswith(ftype)):
                num_files += 1
                total_size += os.path.getsize(path_)

        elif recursive and path_.is_dir():
            num_files_, total_size_ = count_dir_files(path_, ftype=ftype, recursive=recursive)
            num_files += num_files_
            total_size += total_size_

    return num_files, total_size


def datetime_is_naive(d: datetime) -> bool:
    """Determines whether a datetime isn't localized.

    See https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive.

    Args:
        d (datetime.datetime): an object to check.

    Returns:
        bool: True if the datetime isn't localized.
    """
    return d.tzinfo is None or d.tzinfo.utcoffset(d) is None


def generic_object_repr(obj):
    """Builds a `repr` string from a generic object.

    Only works for classes where constructor parameters have a corresponding attribute of the same
    name, much like a `dataclass` would.

    Args:
        obj (*): any object.

    Returns:
        str: a `repr` string suitable for the given object.
    """
    from inspect import Parameter
    from inspect import signature

    sig = signature(obj.__class__)
    cname = obj.__class__.__name__

    args = [Parameter.POSITIONAL_ONLY, Parameter.VAR_POSITIONAL,]
    kwargs = [Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD,]

    rendered_params = []
    for param in sig.parameters:

        attr = getattr(obj, param)

        if sig.parameters[param].kind in args:

            rendered_params.append(sig.parameters[param].replace(name=attr.value))

        elif sig.parameters[param].kind in kwargs:

            rendered_params.append(sig.parameters[param].replace(default=attr.value))

    new_sig = sig.replace(parameters=rendered_params)

    return f"{cname}{str(new_sig)}"

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


def get_file_transfer_progress_bar():
    import logging

    from rich.progress import BarColumn
    from rich.progress import DownloadColumn
    from rich.progress import Progress
    from rich.progress import SpinnerColumn
    from rich.progress import TextColumn
    from rich.progress import TransferSpeedColumn

    global P_PREFIX

    logger = logging.getLogger("rich")

    progress = Progress(
        TextColumn(P_PREFIX + "[bold blue]{task.description}", justify="right"),
        SpinnerColumn(),
        "|",
        BarColumn(bar_width=None),
        "|",
        DownloadColumn(),
        "|",
        TransferSpeedColumn(),
        # hide progress display when in silent mode
        disable=logger.level != logging.INFO
    )

    return progress


def get_indeterminate_progress_bar():
    import logging

    from rich.progress import BarColumn
    from rich.progress import MofNCompleteColumn
    from rich.progress import Progress
    from rich.progress import SpinnerColumn
    from rich.progress import TextColumn
    from rich.progress import TimeRemainingColumn
    from rich.progress import TimeElapsedColumn

    global P_PREFIX

    logger = logging.getLogger("rich")

    progress = Progress(
        TextColumn(P_PREFIX + "[bold blue]{task.description}", justify="right"),
        SpinnerColumn(),
        "|",
        IndeterminateBarColumn(bar_width=None),
        "|",
        TextColumn("[green]{task.completed}", justify="right"),
        "|",
        TimeElapsedColumn(),
        # hide progress display when in silent mode
        disable=logger.level != logging.INFO
    )

    return progress


def get_std_progress_bar():
    import logging

    from rich.progress import BarColumn
    from rich.progress import MofNCompleteColumn
    from rich.progress import Progress
    from rich.progress import SpinnerColumn
    from rich.progress import TextColumn
    from rich.progress import TimeRemainingColumn
    from rich.progress import TimeElapsedColumn

    global P_PREFIX

    logger = logging.getLogger("rich")

    progress = Progress(
        TextColumn(P_PREFIX + "[bold blue]{task.description}", justify="right"),
        SpinnerColumn(),
        "|",
        BarColumn(bar_width=None),
        "|",
        MofNCompleteColumn(),
        "|",
        "[progress.percentage]{task.percentage:>3.1f}%",
        "|",
        TimeElapsedColumn(),
        "|",
        TimeRemainingColumn(),
        # hide progress display when in silent mode
        disable=logger.level != logging.INFO
    )

    return progress


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


def trim_dict(doc):
    """Trims whitespace from all string values in the dictionary.

    Does not trim string keys. Also converts any tuples to lists.

    Args:
        doc (dict): a document to trim.

    Returns:
        dict: a clone of the dictionary with trimmed whitespace for all values of type string.
    """

    for k, v in doc.items():
        if type(v) == str:
            doc[k] = v.strip()
        elif type(v) == list:
            for i in range(len(v)):
                if type(doc[k][i]) == str:
                    doc[k][i] = doc[k][i].strip()
                elif type(doc[k][i]) == dict:
                    doc[k][i] = trim_dict(doc[k][i])
        elif type(v) == tuple:
            new = [x for x in v]
            for i in range(len(new)):
                if type(new[i]) == str:
                    new[i] = new[i].strip()
                elif type(new[i]) == dict:
                    new[i] = trim_dict(new[i])
            doc[k] = new
        elif type(v) == dict:
            doc[k] = trim_dict(v)
    return doc


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


def walk_files(path: str, ftype=None, recursive=False):
    """Generates a list of files in the given directory.

    Args:
        path (str): a path to any directory.
        ftype (str): only files with an extension matching ``ftype`` will be included in the result
           if populated.
        recursive (bool): if True, check subdirectories as well. Defaults to False.

    Yields:
        ``os.DirEntry`` objects matching the input criteria.
    """
    import os

    assert os.path.isdir(path), "Path must be a directory!"

    for path_ in os.scandir(path):

        if path_.is_file():

            if not ftype or (ftype and str(path_.name).endswith(ftype)):

                yield path_

        elif recursive and path_.is_dir():

            yield from walk_files(path_, ftype=ftype, recursive=recursive)


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


