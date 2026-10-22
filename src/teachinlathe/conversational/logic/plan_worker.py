"""The process the Conversational tab's slow work runs in, off the GUI thread.

A Profile Roughing plan checks every move against the insert and takes up to
a second, and generating a program's G-code plans each of its roughings. On the GUI thread that stalls the screen - an opening program's
slide stops halfway - and a Python thread would not help: shapely 1.8 holds
the GIL through its geometry. So it runs in a process of its own, started
once with the application (BackgroundPlanner) and fed through a pipe.

This module is both ends:

* run as ``python3 -m teachinlathe.conversational.logic.plan_worker``, it is
  the worker: it reads requests from stdin and writes answers to stdout, one
  at a time, until stdin closes - which it does when the application ends,
  however it ends;
* BackgroundPlanner is the application's side, a QObject whose ``finished``
  is emitted on the GUI thread.

A request is (id, job, args), an answer (id, ok, result or error text), each
pickled behind its length. Jobs are looked up by name in ``_jobs``.
"""

from __future__ import annotations

import logging
import os
import pickle
import struct
import subprocess
import sys
import threading
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

log = logging.getLogger(__name__)

_HEADER = struct.Struct("!I")


def _jobs():
    from teachinlathe.conversational.gcode.operations.profile_roughing_preview import (
        build_profile_roughing_preview,
    )
    return {"profile_roughing_preview": build_profile_roughing_preview,
            "generate_gcode": _generate_gcode}


def _generate_gcode(program, gcode_dir, json_path, tools):
    """ConversationalUseCase.gcode_job's program built into its .ngc; the
    path. Profile Roughing plans already worked out for previews are reused."""
    from teachinlathe.conversational.gcode import build_ngc_from_program
    return build_ngc_from_program(program, output_dir=gcode_dir, source_json=json_path,
                                  tools=tools)


def _read_frame(stream):
    header = stream.read(_HEADER.size)
    if len(header) < _HEADER.size:
        return None
    (size,) = _HEADER.unpack(header)
    body = stream.read(size)
    if len(body) < size:
        return None
    return pickle.loads(body)


def _write_frame(stream, value):
    data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    stream.write(_HEADER.pack(len(data)) + data)
    stream.flush()


def main() -> int:
    """The worker: answer requests until stdin closes."""
    requests, answers = sys.stdin.buffer, sys.stdout.buffer
    # stdout is the answers' channel: anything printed goes to stderr instead
    sys.stdout = sys.stderr
    jobs = _jobs()
    while True:
        request = _read_frame(requests)
        if request is None:
            return 0
        request_id, job, args = request
        try:
            answer = (request_id, True, jobs[job](*args))
        except Exception as error:      # reported back, the worker goes on
            answer = (request_id, False, f"{type(error).__name__}: {error}")
        _write_frame(answers, answer)




class BackgroundPlanner(QObject):
    """The application's side of the worker.

    ``submit(channel, job, *args)`` returns a request id; ``finished(id, ok,
    result)`` follows on the GUI thread. Requests on one channel coalesce: one
    is worked on at a time, and of those that arrive meanwhile only the last
    is kept - a value being typed in does not queue a plan per keystroke.
    """

    finished = pyqtSignal(int, bool, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._next_id = 1
        self._process: Optional[subprocess.Popen] = None
        # per channel: the request being worked on, and the one waiting
        self._busy: Dict[str, int] = {}
        self._waiting: Dict[str, Tuple[int, str, tuple]] = {}
        self._channel_of: Dict[int, str] = {}
        self._start()
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop)

    def _start(self):
        try:
            self._process = subprocess.Popen(
                [sys.executable, "-m", __name__],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=os.environ.copy())
        except OSError as error:
            log.error("could not start the planning worker: %s", error)
            self._process = None
            return
        threading.Thread(target=self._read, args=(self._process,), daemon=True,
                         name="plan-worker-reader").start()
        log.info("planning worker started, pid %d", self._process.pid)

    def stop(self):
        process, self._process = self._process, None
        if process is not None and process.stdin:
            try:
                process.stdin.close()       # the worker ends at EOF
            except OSError:
                pass

    def submit(self, channel: str, job: str, *args) -> int:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            self._channel_of[request_id] = channel
            if channel in self._busy:
                dropped = self._waiting.pop(channel, None)
                if dropped is not None:
                    self._channel_of.pop(dropped[0], None)
                self._waiting[channel] = (request_id, job, args)
                return request_id
            self._busy[channel] = request_id
        self._send(request_id, job, args)
        return request_id

    def _send(self, request_id, job, args):
        if self._process is None or self._process.poll() is not None:
            log.warning("planning worker not running, starting it again")
            self._start()
        try:
            _write_frame(self._process.stdin, (request_id, job, args))
        except (OSError, AttributeError, ValueError) as error:
            log.error("planning worker unreachable: %s", error)
            self._done(request_id, False, f"planning worker unreachable: {error}")

    def _read(self, process):
        """On a thread of its own: the worker's answers, as they come."""
        while True:
            try:
                answer = _read_frame(process.stdout)
            except Exception as error:
                log.error("bad answer from the planning worker: %s", error)
                answer = None
            if answer is None:
                break
            self._done(*answer)
        # the worker is gone: what it was working on gets no answer from it
        if process is self._process:
            with self._lock:
                lost = list(self._busy.values())
            for request_id in lost:
                self._done(request_id, False, "the planning worker stopped")

    def _done(self, request_id, ok, result):
        with self._lock:
            channel = self._channel_of.pop(request_id, None)
            following = None
            if channel is not None and self._busy.get(channel) == request_id:
                following = self._waiting.pop(channel, None)
                if following is None:
                    self._busy.pop(channel, None)
                else:
                    self._busy[channel] = following[0]
        # emitted from the reader thread: Qt queues it to the GUI thread
        self.finished.emit(request_id, bool(ok), result)
        if following is not None:
            self._send(*following)


if __name__ == "__main__":
    sys.exit(main())
