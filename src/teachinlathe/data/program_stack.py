import os
import re
from dataclasses import dataclass

from PyQt5.QtCore import QObject
from qtpyvcp.utilities.info import Info

from .program_runtime import ProgramRuntimeSnapshot


SUBROUTINE_CALL_PATTERN = re.compile(r"o<([^>]+)>\s+call\b", re.IGNORECASE)


@dataclass(frozen=True)
class ProgramStackFrameView:
    file_path: str
    content: str
    line_number: int


@dataclass(frozen=True)
class ProgramCallStackView:
    frames: tuple[ProgramStackFrameView, ...]
    active_file_path: str
    active_content: str
    motion_line: int


class ProgramCallStackResolver(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._info = Info()
        self._file_cache = {}

    def build_view(self, snapshot: ProgramRuntimeSnapshot):
        if snapshot.call_level <= 0 or not snapshot.call_stack:
            return None

        stack_frames = []
        for frame in snapshot.call_stack:
            content = self.read_file_content(frame.filename)
            if not content:
                return None
            stack_frames.append(ProgramStackFrameView(
                file_path=frame.filename,
                content=content,
                line_number=frame.line,
            ))

        active_source = snapshot.call_stack[-1]
        active_source_content = stack_frames[-1].content
        active_path, _ = self.resolve_subroutine_from_line(
            active_source.filename,
            active_source.line,
            active_source_content,
        )
        if not active_path and active_source.subname:
            active_path, _ = self.resolve_subroutine_by_name(active_source.subname)

        active_content = self.read_file_content(active_path)
        if not active_path or not active_content:
            return None

        return ProgramCallStackView(
            frames=tuple(stack_frames),
            active_file_path=active_path,
            active_content=active_content,
            motion_line=snapshot.motion_line,
        )

    def read_file_content(self, file_path):
        if not file_path:
            return ''
        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            return ''

        cached = self._file_cache.get(file_path)
        if cached and cached[0] == mtime:
            return cached[1]

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as handle:
                content = handle.read()
        except Exception:
            return ''

        self._file_cache[file_path] = (mtime, content)
        return content

    def resolve_subroutine_from_line(self, file_path, line_number, content=None):
        content = content if content is not None else self.read_file_content(file_path)
        if not content:
            return '', ''

        for candidate_line in (line_number, line_number + 1, line_number - 1):
            if candidate_line <= 0:
                continue
            line = self.get_line_text(content, candidate_line)
            match = SUBROUTINE_CALL_PATTERN.search(line)
            if match:
                return self.resolve_subroutine_by_name(match.group(1).strip())
        return '', ''

    def resolve_subroutine_by_name(self, sub_name):
        if not sub_name:
            return '', ''

        search_dirs = []
        for search_dir in self._info.getSubroutineSearchDirs():
            if not search_dir:
                continue
            normalized_dir = os.path.abspath(os.path.expanduser(search_dir))
            if normalized_dir not in search_dirs:
                search_dirs.append(normalized_dir)

        candidates = [
            f'{sub_name}.ngc',
            f'{sub_name}.nc',
            f'{sub_name}.gcode',
            f'{sub_name}.NGC',
            f'{sub_name}.NC',
            f'{sub_name}.GCODE',
        ]

        for search_dir in search_dirs:
            for candidate in candidates:
                candidate_path = os.path.join(search_dir, candidate)
                if os.path.isfile(candidate_path):
                    return candidate_path, sub_name

        return '', sub_name

    @staticmethod
    def get_line_text(content, line_number):
        if line_number <= 0:
            return ''
        lines = content.splitlines()
        if line_number > len(lines):
            return ''
        return lines[line_number - 1]
