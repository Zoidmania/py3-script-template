# Python CLIs

- Using Python 3.10
- Scripts should be executable, with `bash` shebangs. Library files should not have shebangs and not
  be executable.
- Scripts should only live in the project root, **_not_** in `lib/`. Only library code should live
  in `lib/`.

## Dependencies

At a minimum, install `click==8.0.x`. At time of writing, we're using Click 8.0.

Others I've included since I use them commonly:

- `openpyxl` for Excel workbook manipulation
- `pytest` for testing
- `pytz` for timezone handling
- `rich` for fancy terminal output and logging

You can forgo the above dependencies, but `lib/utils.py` relies on these dependencies for its
functions, especially `rich` since it's used for logging (used throughout).

### Why Don't You Use X?

I used to use a few dependencies, but I no longer gravitate to them:

- I don't use `tabulate` and `tqdm` anymore since their functionality is baked into `rich`.
  - `tabulate` was great, but `rich` has all the same features.
  - `rich` is as performant as `tqdm` now, so there's no reason to include a separate library for
    progress bars.

## Installation

Simple:

```bash
python -m venv venv --prompt="whatever"
source venv/bin/activate
pip install -r requirements.txt
```

## Testing

Simply call `pytest` from the root of the project.
