"""Utility functions.

Leland E. Vakarian
20 Jan, 2022
"""

__author__ = "Leland E. Vakarian"


from datetime import datetime
import logging

import click


## Logging Config


class ColoredLogFormatter(logging.Formatter):


    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)


    def format(self, record):
        import click

        if record.levelname == "DEBUG":
            record.levelname = f"[{click.style(record.levelname, fg='bright_magenta')}]   "
        elif record.levelname == "INFO":
            record.levelname = f"[{click.style(record.levelname, fg='bright_green')}]    "
        elif record.levelname == "WARNING":
            record.levelname = f"[{click.style(record.levelname, fg='bright_yellow')}] "
        elif record.levelname == "ERROR":
            record.levelname = f"[{click.style(record.levelname, fg='bright_red')}]   "
        elif record.levelname == "CRITICAL":
            record.levelname = f"[{click.style(record.levelname, fg='red')}]"

        return logging.Formatter.format(self, record)


class ColorlessLogFormatter(logging.Formatter):


    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)


    def format(self, record):

        if record.levelname == "DEBUG":
            record.levelname = f"[{record.levelname}]   "
        elif record.levelname == "INFO":
            record.levelname = f"[{record.levelname}]    "
        elif record.levelname == "WARNING":
            record.levelname = f"[{record.levelname}] "
        elif record.levelname == "ERROR":
            record.levelname = f"[{record.levelname}]   "
        elif record.levelname == "CRITICAL":
            record.levelname = f"[{record.levelname}]"

        return logging.Formatter.format(self, record)


class FormattedLogger(logging.Logger):


    def __init__(self, name):

        logging.Logger.__init__(self, name, logging.DEBUG)

        console = logging.StreamHandler()
        console.setFormatter(ColoredLogFormatter("%(levelname)s %(message)s"))
        self.addHandler(console)

    def add_fh(self, path):
        fh = logging.FileHandler(path)
        fh.setFormatter(ColorlessLogFormatter("%(levelname)s %(message)s"))
        self.addHandler(fh)


logging.setLoggerClass(FormattedLogger)


## Constants


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=100)
LOGGER = logging.getLogger(__name__)
# https://docs.python.org/3/library/logging.html#logging.Logger.setLevel
LOGGER.setLevel(51) # silent by default
TQDM_PREFIX = "[" + click.style("INFO", fg='bright_green') + "]    "


## Utilities


def capture_logs(path: str, force=False):
    """Captures logging output to the specified path.

    Args:
        path (str): a path to write the JSON blob.
        force (bool): if True, skip asking for permission to overwrite a file with output. Defaults
            to False.
    """
    import os

    global LOGGER

    if os.path.dirname(path):
        assert os.path.exists(os.path.dirname(path))

    if user_allows_file_overwrite(path, force):

        if os.path.exists(path):
            os.remove(path)

        LOGGER.add_fh(path)

    LOGGER.info(f"User chose to not overwrite existing log output file.")


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


def get_tqdm():
    """Determines whether the ``tqdm`` function prints anything.

    Debug mode assumes verbose mode, in addition to debug-only output.

    If in verbose mode, print the ``tqdm`` progress bar as normal. If in quiet or debug mode, print
    nothing.

    Returns:
        Either the standard ``tqdm.tqdm`` progress bar printer, or an override function that prints
        nothing.
    """
    import logging

    global FORCE
    global LOGGER

    def __tqdm(iterable, *args, **kwargs):
        return iterable

    log_level = logger_get_level_name()

    if log_level == "INFO":
        from tqdm import tqdm
    else:
        tqdm = __tqdm

    return tqdm


def logger_get_level_name() -> str:
    """Gets the name of the output level of the global logger.

    Generally follows the rules for logging.getLevelName(). If the value is higher than any of the
    built-in levels, "SILENT" is returned.

    Returns:
        str: the name of the output level of the global logger.
    """
    import logging
    global LOGGER

    level = LOGGER.getEffectiveLevel()
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

    global LOGGER

    prev_level = LOGGER.getEffectiveLevel()
    LOGGER.setLevel(level)

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
    import re
    import unicodedata

    global LOGGER

    LOGGER.debug(f"Slugify input: {value}.")

    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value).strip('-_')

    LOGGER.debug(f"Slugify output: {value}.")

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

    global LOGGER

    warning = "[" + click.style("WARNING", fg='bright_yellow') + "]"

    if os.path.isdir(path) and any(os.scandir(path)):

        if not force:

            if LOGGER.isEnabledFor(logging.ERROR):
                ans = click.confirm((
                    f"{warning}  Directory at '{path}' isn't empty. Do you want to potentially "
                    "overwrite the files within?"
                ))
            else:
                ans = click.confirm(f"Overwrite '{path}'?")

            if ans:
                LOGGER.warning("    Overwriting file!")
            else:
                LOGGER.info("    Canceling due to denied overwrite.")
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

    global LOGGER

    warning = "[" + click.style("WARNING", fg='bright_yellow') + "]"

    if os.path.isfile(path):

        if not force:

            if LOGGER.isEnabledFor(logging.ERROR):
                ans = click.confirm((
                    f"{warning}  A file exists at the path '{path}'. Do you really want to "
                    "overwrite it?"
                ))
            else:
                ans = click.confirm(f"Overwrite '{path}'?")

            if ans:
                LOGGER.warning("    Overwriting file!")
            else:
                LOGGER.info("    Canceling due to denied overwrite.")
                return False

    return True


def write_json_blob(doc: dict, path: str, force=False):
    """Writes a JSON document in a consistent manner, using the standard ``json`` module.

    Args:
        doc (dict): a dictionary to translate into JSON.
        path (str): a path to write the JSON blob.
        force (bool): skip asking for permission to overwrite.
    """
    import json
    import os
    import sys

    global LOGGER

    try:
        if os.path.dirname(path):
            assert os.path.exists(os.path.dirname(path))
    except AssertionError:
        LOGGER.error(f"Directory {os.path.dirname(path)} doesn't exist!")
        sys.exit()

    if force or user_allows_file_overwrite(path):
        with open(path, 'w', encoding='utf-8') as f:
            blob = json.dumps(doc, ensure_ascii=False)
            f.write(blob)

