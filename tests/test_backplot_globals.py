"""Every global a backplot function reaches for must exist.

The bug this is here for shipped and broke the plot completely: ``redraw()``
was written from upstream's body, which reads ``linuxcnc`` at module scope.
This module imports ``linuxcnc`` inside each function that needs it, so the
copied body raised ``NameError`` on every frame - and only on a frame, so the
module imported cleanly, every test passed, and the failure appeared as a log
line repeating twenty-five times a second with nothing drawn.

Read from the bytecode rather than the source. ``LOAD_GLOBAL`` is emitted only
for a genuine module-or-builtin lookup: a name bound by a local ``import``
compiles to ``LOAD_FAST``, and one captured from an enclosing function to
``LOAD_DEREF``. An AST version of this test was written first and was worse at
both ends - it flagged every closure capture, and it missed the very bug above,
because a local import elsewhere in the module looked like a module-level name.
"""

import builtins
import dis
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest.importorskip(
    "rs274.glcanon_scene",
    reason="needs a LinuxCNC with the split-out preview renderer")

BACKPLOT = SRC / "teachinlathe" / "widgets" / "backplot"

MODULES = sorted(
    "teachinlathe.widgets.backplot."
    + str(path.relative_to(BACKPLOT).with_suffix("")).replace("/", ".")
    for path in BACKPLOT.rglob("*.py")
    if path.name != "__init__.py"
)


def code_objects(code):
    """``code`` and every code object nested in it - inner functions,
    comprehensions, generator expressions."""
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from code_objects(constant)


def functions_in(module):
    for value in vars(module).values():
        if isinstance(value, types.FunctionType):
            yield value
        elif isinstance(value, type):
            for member in vars(value).values():
                member = getattr(member, "__func__", member)
                if isinstance(member, types.FunctionType):
                    yield member


def unresolved(module):
    missing = []
    for function in functions_in(module):
        if function.__module__ != module.__name__:
            continue            # grafted from upstream; not ours to vouch for
        # Against the function's *own* globals, which is the scope it actually
        # resolves in. A @contextmanager wrapper carries this module's
        # __module__ but contextlib's globals, and checking it against ours
        # reports contextlib's own internals as missing.
        known = set(function.__globals__) | set(dir(builtins))
        for code in code_objects(function.__code__):
            for instruction in dis.get_instructions(code):
                if instruction.opname != "LOAD_GLOBAL":
                    continue
                name = instruction.argval
                if name not in known:
                    missing.append((function.__qualname__, name))
    return missing


@pytest.mark.parametrize("name", MODULES)
def test_every_global_resolves(name):
    module = __import__(name, fromlist=["_"])
    missing = unresolved(module)
    assert not missing, "\n".join(
        "%s() reaches for '%s', which this module does not have"
        % (where, what) for where, what in missing)


def test_the_check_would_have_caught_it():
    """A function written against a module-scope import this module lacks."""
    namespace = {}
    exec("def broken():\n    return linuxcnc.gui_rot_offsets(0, 0, 0)\n",
         namespace)
    module = types.ModuleType("stand_in")
    module.broken = namespace["broken"]
    namespace["broken"].__module__ = "stand_in"

    assert ("broken", "linuxcnc") in unresolved(module)


def test_a_local_import_satisfies_the_check():
    """Which is how every other function in the backplot reaches linuxcnc."""
    namespace = {}
    exec("def fine():\n    import linuxcnc\n    return linuxcnc\n", namespace)
    module = types.ModuleType("stand_in")
    module.fine = namespace["fine"]
    namespace["fine"].__module__ = "stand_in"

    assert unresolved(module) == []
