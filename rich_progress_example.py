"""
A rudimentary URL downloader (like wget or curl) to demonstrate Rich progress bars.

Taken from https://github.com/Textualize/rich/blob/master/examples/downloader.py.
"""

import os.path
import sys
from concurrent.futures import as_completed, ThreadPoolExecutor
import signal
from functools import partial
from threading import Event
from typing import Iterable
from urllib.request import urlopen

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
    TimeElapsedColumn,
    SpinnerColumn,
)

# See https://rich.readthedocs.io/en/latest/progress.html#columns for additional column types.
progress = Progress(

    # shows that the progress is actively being worked on (not necessary starting with start_task())
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

    # built-in column type that tracks total size of download as it progresses, assumes steps are in
    # bytes.
    DownloadColumn(),
    "|",

    # built-in column type that tracks instantaneous transfer speed, assumes the steps are bytes.
    TransferSpeedColumn(),
    "|",

    # built-in column type that displays total time elapsed since calling start_task()
    TimeElapsedColumn(),
    "|",

    # built-in column type that displays instantaneous estimated time remaining
    TimeRemainingColumn(),
)


done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()


signal.signal(signal.SIGINT, handle_sigint)


def copy_url(task_id: TaskID, url: str, path: str) -> None:
    """Download data from a url to a local file."""

    # a simple print with no styling/indicators/anything special.
    progress.console.print(f"Working on download job.")

    # prints a well-formatted log message
    progress.console.log(f"Requesting {url}")

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


def download(urls: Iterable[str], dest_dir: str):
    """Download multuple files to the given directory."""

    with progress:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for url in urls:
                filename = url.split("/")[-1]
                dest_path = os.path.join(dest_dir, filename)
                task_id = progress.add_task("download", filename=filename, start=False)
                pool.submit(copy_url, task_id, url, dest_path)


if __name__ == "__main__":
    # Try with https://releases.ubuntu.com/20.04/ubuntu-20.04.3-desktop-amd64.iso
    if sys.argv[1:]:
        download(sys.argv[1:], "./")
    else:
        print("Usage:\n\tpython downloader.py URL1 URL2 URL3 (etc)")