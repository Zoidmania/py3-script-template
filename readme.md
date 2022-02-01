# Python CLIs

- Using Python 3.10
- Scripts should be executable, with `bash` shebangs. Library files should not have shebangs and not
  be executable.
- Scripts should only live in the project root, **_not_** in `lib/`. Only library code should live
  in `lib/`.

## Dependencies

At a minimum, `click`. At time of writing, we're using Click 8.

Other I've included since I use them commonly:

- openpyxl
- pytest
- pytz
- rich

## Testing

Simply call `pytest` from the root of the project.
