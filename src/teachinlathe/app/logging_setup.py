"""Application logging.

Modules ask for their logger the plain way::

    import logging
    log = logging.getLogger(__name__)

and :func:`configure` - called once from ``main()`` - attaches the handlers to
the ``teachinlathe`` logger that all of those sit under.

Two things here are not decoration:

* **The level is set on the package logger, not left to root.** Root defaults
  to WARNING, and a logger with no level of its own inherits it, so every
  ``log.info`` would be dropped before any handler saw it. The in-app event
  log (``app_state.StoreLogHandler``, which listens on root at INFO) would
  then show nothing.
* **Propagation is left on**, so records still reach root and that event log.
"""

from __future__ import annotations

import logging
import os
import sys

#: Every logger in the application sits under this one.
ROOT_LOGGER_NAME = "teachinlathe"

DEFAULT_LOG_FILE = "~/teachinlathe.log"

CONSOLE_FORMAT = "[%(name)s][%(levelname)s]  %(message)s (%(filename)s:%(lineno)d)"
FILE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

#: ANSI colours per level, used only when stderr is a terminal.
LEVEL_COLOURS = {
    logging.DEBUG: "\033[36m",      # cyan
    logging.INFO: "\033[32m",       # green
    logging.WARNING: "\033[33m",    # yellow
    logging.ERROR: "\033[31m",      # red
    logging.CRITICAL: "\033[1;31m",  # bold red
}
RESET = "\033[0m"


class ColouredFormatter(logging.Formatter):
    """Console formatter that tints the level name."""

    def format(self, record: logging.LogRecord) -> str:
        colour = LEVEL_COLOURS.get(record.levelno, "")
        original = record.levelname
        if colour:
            record.levelname = "{}{}{}".format(colour, original, RESET)
        try:
            return super().format(record)
        finally:
            record.levelname = original


def configure(level: str = "DEBUG", log_file: str | None = None) -> logging.Logger:
    """Attach console and file handlers to the application logger.

    Safe to call more than once: the handlers are only added the first time,
    so a second call just updates the level.
    """
    log = logging.getLogger(ROOT_LOGGER_NAME)
    log.setLevel(_level_from_name(level))

    if getattr(log, "_teachinlathe_configured", False):
        return log

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(
        ColouredFormatter(CONSOLE_FORMAT) if _stderr_is_a_terminal()
        else logging.Formatter(CONSOLE_FORMAT))
    log.addHandler(console)

    path = os.path.expanduser(log_file or DEFAULT_LOG_FILE)
    try:
        # Truncated per run: a log that only covers the
        # session being debugged is the one worth reading.
        handler = logging.FileHandler(path, mode="w")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(FILE_FORMAT))
        log.addHandler(handler)
    except OSError:
        log.warning("could not open log file '%s'; logging to the console only",
                    path, exc_info=True)

    log._teachinlathe_configured = True
    log.debug("logging configured at %s, file: %s", level, path)
    return log


def set_level(level: str) -> None:
    """Change the application-wide log level."""
    logging.getLogger(ROOT_LOGGER_NAME).setLevel(_level_from_name(level))


def _level_from_name(name: str) -> int:
    if isinstance(name, int):
        return name
    resolved = logging.getLevelName(str(name).upper())
    if not isinstance(resolved, int):
        raise ValueError("not a log level: {!r}".format(name))
    return resolved


def _stderr_is_a_terminal() -> bool:
    try:
        return bool(sys.stderr.isatty())
    except (AttributeError, ValueError):
        return False
