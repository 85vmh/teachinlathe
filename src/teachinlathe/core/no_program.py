"""The program loaded when there is to be none.

LinuxCNC cannot close a program: its Python module has no program_close,
``program_open("")`` fails ("can't open"), and the task never clears
``stat.file`` - a reset of the interpreter even opens it again. Opening an
empty program in its place is the one way to have nothing loaded: a program
deleted from the disk is not left as the machine's, for the Run button and the
backplot to read again.
"""

import os

#: An empty program (it ends at once), loaded for none.
NO_PROGRAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "no_program.ngc")


def loaded_program(machine_file: str) -> str:
    """The program the machine has loaded (``stat.file``), as an absolute
    path - or "" for none, the empty one loaded in its place included."""
    if not machine_file:
        return ""
    path = os.path.abspath(machine_file)
    return "" if path == NO_PROGRAM else path
