import os
import subprocess
import sys


def _linuxcnc_tcl_dir():
    return os.getenv("LINUXCNC_TCL_DIR", "/usr/lib/tcltk/linuxcnc")


def _halshow_command():
    return ["tclsh", os.path.join(_linuxcnc_tcl_dir(), "bin", "halshow.tcl")]


def _calibration_command():
    command = ["tclsh", os.path.join(_linuxcnc_tcl_dir(), "bin", "emccalib.tcl")]
    ini_file = os.getenv("INI_FILE_NAME")
    if ini_file:
        command.extend(["-ini", ini_file])
    return command


DEBUG_TOOL_COMMANDS = {
    "halshow": _halshow_command,
    "halmeter": lambda: ["halmeter"],
    "halscope": lambda: ["halscope"],
    "classicladder": lambda: ["classicladder"],
    "status": lambda: ["linuxcnctop"],
    "linuxcnctop": lambda: ["linuxcnctop"],
    "calibration": _calibration_command,
}


def launch_debug_tool(tool_name):
    command_factory = DEBUG_TOOL_COMMANDS.get(tool_name)
    if command_factory is None:
        valid_tools = ", ".join(sorted(DEBUG_TOOL_COMMANDS))
        raise ValueError(f"Unknown debug tool '{tool_name}'. Valid tools: {valid_tools}")

    command = command_factory()
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        valid_tools = ", ".join(sorted(DEBUG_TOOL_COMMANDS))
        print(f"Usage: teachinlathe-tool <tool>\nValid tools: {valid_tools}", file=sys.stderr)
        return 2

    try:
        launch_debug_tool(args[0])
    except FileNotFoundError as exc:
        print(f"Could not launch '{args[0]}': {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
