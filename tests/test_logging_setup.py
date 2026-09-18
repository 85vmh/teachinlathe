"""Tests for the application's logging setup.

The point of interest is the level: the package logger must carry its own,
because root defaults to WARNING and an INFO record would otherwise be dropped
before any handler - including the in-app event log - ever saw it.
"""

import logging
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe import logging_setup  # noqa: E402


@pytest.fixture
def app_logger(tmp_path):
    """Configure logging into a temp file, and undo it afterwards."""
    log = logging.getLogger(logging_setup.ROOT_LOGGER_NAME)
    saved_handlers, saved_level = list(log.handlers), log.level
    saved_flag = getattr(log, "_teachinlathe_configured", False)
    log.handlers = []
    log._teachinlathe_configured = False

    path = tmp_path / "teachinlathe.log"
    yield logging_setup.configure(log_file=str(path)), path

    for handler in log.handlers:
        handler.close()
    log.handlers, log.level = saved_handlers, saved_level
    log._teachinlathe_configured = saved_flag


def test_package_logger_carries_its_own_level(app_logger):
    log, _ = app_logger
    # Not left to root (WARNING), or every log.info would be dropped.
    assert log.level == logging.DEBUG
    assert log.level != logging.getLogger().level or logging.getLogger().level == logging.DEBUG


def test_info_records_reach_the_root_handlers(app_logger):
    """This is what feeds app_state.StoreLogHandler, which listens on root."""
    _, _ = app_logger
    root = logging.getLogger()
    seen = []

    class Capture(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())

    handler = Capture()
    handler.setLevel(logging.INFO)
    root.addHandler(handler)
    try:
        logging.getLogger("teachinlathe.some.module").info("hello")
    finally:
        root.removeHandler(handler)

    assert "hello" in seen


def test_records_are_written_to_the_log_file(app_logger):
    _, path = app_logger
    logging.getLogger("teachinlathe.writer").warning("on disk")
    for handler in logging.getLogger(logging_setup.ROOT_LOGGER_NAME).handlers:
        handler.flush()
    assert "on disk" in path.read_text()


def test_configure_is_idempotent(app_logger):
    log, path = app_logger
    before = len(log.handlers)
    logging_setup.configure(log_file=str(path))
    assert len(log.handlers) == before


def test_set_level_changes_what_is_recorded(app_logger):
    log, _ = app_logger
    logging_setup.set_level("ERROR")
    assert log.level == logging.ERROR
    assert not log.isEnabledFor(logging.INFO)

    logging_setup.set_level("debug")           # case does not matter
    assert log.isEnabledFor(logging.DEBUG)


def test_a_bad_level_name_is_rejected(app_logger):
    with pytest.raises(ValueError, match="not a log level"):
        logging_setup.set_level("chatty")


def test_unwritable_log_file_does_not_stop_logging(tmp_path):
    log = logging.getLogger(logging_setup.ROOT_LOGGER_NAME)
    saved_handlers, saved_flag = list(log.handlers), getattr(log, "_teachinlathe_configured", False)
    log.handlers = []
    log._teachinlathe_configured = False
    try:
        logging_setup.configure(log_file=str(tmp_path / "no" / "such" / "dir" / "x.log"))
        # The console handler is still there, so the application still logs.
        assert any(isinstance(h, logging.StreamHandler) for h in log.handlers)
    finally:
        log.handlers, log._teachinlathe_configured = saved_handlers, saved_flag


def test_coloured_formatter_leaves_the_record_unchanged(app_logger):
    record = logging.LogRecord("n", logging.ERROR, "f.py", 1, "boom", None, None)
    formatted = logging_setup.ColouredFormatter("%(levelname)s %(message)s").format(record)
    assert "boom" in formatted
    # The record itself must survive for the other handlers.
    assert record.levelname == "ERROR"
