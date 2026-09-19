"""The graft's contract with the LinuxCNC widget it is built from.

``LatheBackplotCanon`` takes ``qt5_graphics.Lcnc_3dGraphics``'s methods and
leaves its ``__init__`` behind - running it would construct the QOpenGLWidget
the graft exists to avoid. So every attribute those methods read as a bare
``self.x`` has to be set by the host instead.

Upstream adding one is invisible until the frame that reads it raises, and
that frame is every frame: the plot renders nothing and the log fills with the
same AttributeError. That is exactly what a LinuxCNC update did with
``show_workpiece`` - ``GlCanonDraw`` reads it through a defensive ``getattr``,
but qt5_graphics overrides the getter with a bare attribute read, and the
graft takes the override.

So this compares the two by parsing them, and fails on the next addition
rather than leaving it to the render loop. Parsing, not importing: the widget
pulls in PyQt and a GL context, and the point is to run everywhere.
"""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

HOST_PATH = (SRC / "teachinlathe" / "widgets" / "backplot"
             / "lathe_backplot_item.py")


def qt5_graphics_path():
    """Where the LinuxCNC preview widget lives, or a skip.

    Found on the import path rather than at a fixed location: a RIP build, a
    package install and a developer's second checkout all put it somewhere
    different, and the one that matters is the one this session would import.
    """
    for entry in sys.path:
        if not entry:
            continue
        candidate = Path(entry) / "qt5_graphics.py"
        if candidate.is_file():
            return candidate
    pytest.skip("qt5_graphics.py is not on the import path")


def self_assignments(tree, class_name, method_name=None):
    """Every ``self.x = ...`` in a class, or in one of its methods."""
    node = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    assert node is not None, "no class %s" % class_name
    if method_name is not None:
        node = next((n for n in node.body
                     if isinstance(n, ast.FunctionDef)
                     and n.name == method_name), None)
        assert node is not None, "no %s.%s" % (class_name, method_name)

    found = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Assign):
            continue
        for target in child.targets:
            if (isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"):
                found.add(target.attr)
    return found


@pytest.fixture(scope="module")
def host_module():
    return ast.parse(HOST_PATH.read_text())


@pytest.fixture(scope="module")
def widget_init_attributes():
    return self_assignments(ast.parse(qt5_graphics_path().read_text()),
                            "Lcnc_3dGraphics", "__init__")


def frozenset_literal(tree, name):
    """The contents of a module-level ``NAME = frozenset({...})``."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name
                   for t in node.targets):
            continue
        return {ast.literal_eval(element)
                for element in node.value.args[0].elts}
    raise AssertionError("no %s in the host module" % name)


# ── the check that would have caught the outage ────────────────────────────

def test_the_host_sets_everything_the_grafted_methods_need(
        host_module, widget_init_attributes):
    """Every attribute the widget's __init__ sets is either set by the host,
    or named in _GRAFT_IGNORES as read only by a widget-only method.

    A failure here names an attribute upstream has started setting. Decide
    which list it belongs in - and if it belongs in neither, the host needs to
    set it, because something in the graft is about to read it.
    """
    ours = self_assignments(host_module, "LatheBackplotCanon")
    ignored = frozenset_literal(host_module, "_GRAFT_IGNORES")

    missing = widget_init_attributes - ours - ignored
    assert not missing, (
        "set by Lcnc_3dGraphics.__init__ and by nothing here: %s"
        % ", ".join(sorted(missing)))


def test_show_workpiece_is_set_by_the_host(host_module,
                                           widget_init_attributes):
    """The one that has already gone wrong, named on its own so the reason it
    matters does not get lost in the set difference above."""
    assert "show_workpiece" in widget_init_attributes, (
        "upstream no longer sets this; the entry here can go")
    assert "show_workpiece" in self_assignments(host_module,
                                                "LatheBackplotCanon")


def test_the_required_list_is_honest(host_module):
    """_GRAFT_REQUIRES is documentation, so it has to describe what is there."""
    ours = self_assignments(host_module, "LatheBackplotCanon")
    for name in frozenset_literal(host_module, "_GRAFT_REQUIRES"):
        assert name in ours, "%s is required but never set" % name


def test_the_ignored_list_is_only_read_by_widget_only_methods(host_module):
    """An attribute is ignorable only while nothing the graft takes reads it.

    Checked by name against the methods the host declares widget-only, so
    moving one out of that set without setting the attribute fails here.
    """
    widget_only = frozenset_literal(host_module, "_WIDGET_ONLY")
    source = qt5_graphics_path().read_text()
    tree = ast.parse(source)
    cls = next(n for n in ast.walk(tree)
               if isinstance(n, ast.ClassDef) and n.name == "Lcnc_3dGraphics")

    for name in frozenset_literal(host_module, "_GRAFT_IGNORES"):
        readers = set()
        for method in cls.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            for node in ast.walk(method):
                if (isinstance(node, ast.Attribute) and node.attr == name
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"):
                    readers.add(method.name)
        assert readers <= widget_only, (
            "%s is ignored but read by %s, which the graft takes"
            % (name, ", ".join(sorted(readers - widget_only))))


# ── the naming that made this confusing in the first place ─────────────────

def test_the_hosts_stock_is_not_called_workpiece(host_module):
    """Upstream's canon has a ``workpieces`` of its own - the outlines that
    ``(WORKPIECE,...)`` comments declared. Two things one letter apart on one
    object is a trap, so ours is ``stock``."""
    ours = self_assignments(host_module, "LatheBackplotCanon")
    assert "stock" in ours
    assert "workpiece" not in ours
    assert "workpieces" not in ours


# ── the log lines, which nothing else exercises ────────────────────────────

def test_the_line_weight_report_formats():
    """It broke once, in the field, by outliving a change to ``text.FONTS``:
    the values became tuples and a ``", ".join`` over them raised inside
    ``realize()``. A format string is code, and this one is run by nothing
    except the machine starting up."""
    from teachinlathe.widgets.backplot.lathe_backplot_item import (
        line_weight_report)

    for expanded in (0.0, 3.0):
        message = line_weight_report(expanded)
        assert message.startswith("backplot line weights:")
        assert "%" not in message, "an unsubstituted placeholder"


def test_the_report_names_every_font_actually_used():
    from teachinlathe.widgets.backplot.actors import text
    from teachinlathe.widgets.backplot.lathe_backplot_item import (
        line_weight_report)

    message = line_weight_report(0.0)
    for name in text.FONTS:
        assert text.description_of(name) in message


def test_the_report_says_which_line_path_is_in_use():
    from teachinlathe.widgets.backplot.lathe_backplot_item import (
        line_weight_report)

    assert "native GL lines" in line_weight_report(0.0)
    assert "quads" in line_weight_report(3.0)


# ── a poll that changes nothing visible must not redraw ────────────────────

def fingerprint_body():
    """The tuple that decides whether a poll redraws.

    Read out of the source rather than by calling poll(), which wants a live
    linuxcnc.stat. Two traps, both of which this test fell into before it
    checked anything: ``fingerprint = (`` also matches the empty tuple the
    constructor seeds - hence the newline in the search - and a bare ``)``
    search for the close finds the one inside ``soft_limits()``, returning a
    slice that trivially satisfies every assertion below.
    """
    source = HOST_PATH.read_text()
    start = source.index("fingerprint = (\n")
    end = source.index("\n        )", start)
    body = source[start:end]
    assert "soft_limits" in body, "the slice missed the tuple"
    return body


def test_velocity_is_not_in_the_redraw_fingerprint():
    """Nothing draws it - the DRO overlay that would is off - and it changes
    on every poll while the machine moves, so it alone forced a full redraw
    twenty-five times a second for an unchanged picture."""
    assert "current_vel" not in fingerprint_body()


def test_the_positions_are_rounded_to_the_pixel_grid():
    body = fingerprint_body()
    assert "_on_pixel_grid(source.actual_position" in body
    assert "_on_pixel_grid(source.joint_actual_position" in body


def test_the_fingerprint_still_carries_what_does_change_the_picture():
    """Quantising must not turn into dropping: the trace's point count, the
    offsets, homing and the limits all move what is drawn."""
    body = fingerprint_body()
    for field in ("logger.npts", "soft_limits", "homed", "g5x_offset",
                  "g92_offset", "limit", "tool_in_spindle", "motion_mode"):
        assert field in body, field


@pytest.mark.parametrize("quantum,moved,expected", [
    (0.01, 0.004, False),      # under half a pixel - the same grid cell
    (0.01, 0.02, True),        # two pixels
    (0.0, 1e-9, True),         # unmeasurable frame: never quantise
])
def test_pixel_grid_rounding(quantum, moved, expected):
    """A move too small to show must compare equal, and an unmeasurable frame
    must fall back to redrawing rather than freeze the plot."""
    from teachinlathe.widgets.backplot.lathe_backplot_item import (
        _on_pixel_grid)

    before = (1.0, 2.0, 3.0)
    after = (1.0 + moved, 2.0, 3.0)
    changed = _on_pixel_grid(before, quantum) != _on_pixel_grid(after, quantum)
    assert changed is expected


def test_pixel_grid_keeps_every_axis():
    from teachinlathe.widgets.backplot.lathe_backplot_item import (
        _on_pixel_grid)

    position = tuple(float(n) for n in range(9))
    assert len(_on_pixel_grid(position, 0.5)) == 9
    assert len(_on_pixel_grid(position, 0.0)) == 9
