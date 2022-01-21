# Python CLIs

- Using Python 3.9.
- Scripts should be executable, with `bash` shebangs. See
  [the Python script template](lib/__script_template.py) for an example. Library files should
  not have shebangs and not be executable.
- Scripts should only live in the project root, **_not_** in `lib/`. Only library code should live
  in `lib/`.

# Testing

Simply call `pytest` from the root of the project.
