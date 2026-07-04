import json
import os
import re

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter


G_MODAL_GROUPS = {
    "0": {"4", "10", "28", "30", "52", "53", "92", "92.1", "92.2", "92.3"},
    "1": {"0", "1", "2", "3", "33", "73", "76", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89"},
    "2": {"17", "18", "19", "17.1", "18.1", "19.1"},
    "3": {"90", "91"},
    "4": {"90.1", "91.1"},
    "5": {"93", "94", "95"},
    "6": {"20", "21"},
    "7": {"40", "41", "42", "41.1", "42.1"},
    "8": {"43", "43.1", "49"},
    "10": {"98", "99"},
    "12": {"54", "55", "56", "57", "58", "59", "59.1", "59.2", "59.3"},
    "13": {"61", "61.1", "64"},
    "14": {"96", "97"},
    "15": {"7", "8"},
}

M_MODAL_GROUPS = {
    "4": {"0", "1", "2", "30", "60"},
    "5": {"62", "63", "64", "65", "66", "67", "68"},
    "6": {"6"},
    "7": {"3", "4", "5"},
    "8": {"7", "8", "9"},
    "9": {"48", "49"},
}

COMMENT_PATTERNS = [
    re.compile(r"\([^)]*\)"),
    re.compile(r";.*$"),
]
OWORD_PATTERN = re.compile(r"^\s*O(?:<[^>]+>|\d+(?:\.\d+)?)\b", re.IGNORECASE)
OWORD_KEYWORD_PATTERN = re.compile(r"\b(?:SUB|ENDSUB|CALL)\b", re.IGNORECASE)
WORD_PATTERN = re.compile(r"\b([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))\b", re.IGNORECASE)
NAMED_PARAMETER_PATTERN = re.compile(r"<[^>]+>")
EXPRESSION_PATTERN = re.compile(r"\[[^\]]+\]")
THEME_PATH = os.path.join(os.path.dirname(__file__), "../../../../../configurations/gcode_syntax_theme.json")


def _normalize_code(number_text):
    signless = number_text.lstrip("+")
    if "." in signless:
        integer_part, fractional_part = signless.split(".", 1)
        integer_part = str(int(integer_part or "0"))
        fractional_part = fractional_part.rstrip("0")
        return f"{integer_part}.{fractional_part}" if fractional_part else integer_part
    return str(int(signless or "0"))


def _resolve_g_group(number_text):
    normalized = _normalize_code(number_text)
    if normalized.startswith("38."):
        return "1"
    for group_name, members in G_MODAL_GROUPS.items():
        if normalized in members:
            return group_name
    return None


def _resolve_m_group(number_text):
    normalized = _normalize_code(number_text)
    if normalized in M_MODAL_GROUPS["9"]:
        return "9"
    numeric = int(normalized.split(".", 1)[0])
    if 100 <= numeric <= 199:
        return "10"
    for group_name, members in M_MODAL_GROUPS.items():
        if normalized in members:
            return group_name
    return None


def _load_theme():
    with open(THEME_PATH, "r", encoding="utf-8") as theme_file:
        return json.load(theme_file)


class _DocumentHighlighter(QSyntaxHighlighter):
    def __init__(self, document, parent=None):
        super().__init__(document)
        self._parent = parent
        self._theme = _load_theme()
        self._formats = self._build_formats()

    def _fmt(self, theme_key, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self._theme["palette"][theme_key]))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _build_formats(self):
        formats = {
            "comment": self._fmt("comment", italic=True),
            "oword": self._fmt("oword", bold=True),
            "oword_keyword": self._fmt("oword_keyword", bold=True),
            "named_parameter": self._fmt("named_parameter"),
            "expression": self._fmt("expression"),
            "axis_x_family": self._fmt("axis_x_family"),
            "axis_z_family": self._fmt("axis_z_family"),
            "axis_other_family": self._fmt("axis_other_family"),
            "feed_and_speed": self._fmt("feed_and_speed"),
            "tool": self._fmt("tool"),
            "default_gcode": self._fmt("default_gcode", bold=True),
            "default_mcode": self._fmt("default_mcode", bold=True),
        }

        for group_name, palette_key in self._theme["g_modal_groups"].items():
            formats[f"g_group_{group_name}"] = self._fmt(palette_key, bold=True)

        for group_name, palette_key in self._theme["m_modal_groups"].items():
            formats[f"m_group_{group_name}"] = self._fmt(palette_key, bold=True)

        return formats

    @staticmethod
    def _in_ranges(start, end, ranges):
        return any(start < range_end and end > range_start for range_start, range_end in ranges)

    def _apply_pattern(self, text, pattern, fmt_name, excluded_ranges):
        fmt = self._formats[fmt_name]
        for match in pattern.finditer(text):
            start, end = match.span()
            if self._in_ranges(start, end, excluded_ranges):
                continue
            self.setFormat(start, end - start, fmt)

    def _highlight_comments(self, text):
        comment_ranges = []
        comment_fmt = self._formats["comment"]
        for pattern in COMMENT_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.span()
                comment_ranges.append((start, end))
                self.setFormat(start, end - start, comment_fmt)
        return comment_ranges

    def _highlight_modal_words(self, text, excluded_ranges):
        for match in WORD_PATTERN.finditer(text):
            start, end = match.span()
            if self._in_ranges(start, end, excluded_ranges):
                continue

            letter = match.group(1).upper()
            number_text = match.group(2)

            if letter == "G":
                group_name = _resolve_g_group(number_text)
                format_name = f"g_group_{group_name}" if group_name else "default_gcode"
            elif letter == "M":
                group_name = _resolve_m_group(number_text)
                format_name = f"m_group_{group_name}" if group_name else "default_mcode"
            elif letter in {"X", "U", "I"}:
                format_name = "axis_x_family"
            elif letter in {"Z", "W", "K"}:
                format_name = "axis_z_family"
            elif letter in {"A", "B", "C", "Y", "V", "J", "R"}:
                format_name = "axis_other_family"
            elif letter in {"F", "S"}:
                format_name = "feed_and_speed"
            elif letter in {"T", "H", "D"}:
                format_name = "tool"
            else:
                continue

            self.setFormat(start, end - start, self._formats[format_name])

    def highlightBlock(self, text):
        comment_ranges = self._highlight_comments(text)
        self._apply_pattern(text, OWORD_PATTERN, "oword", comment_ranges)
        self._apply_pattern(text, OWORD_KEYWORD_PATTERN, "oword_keyword", comment_ranges)
        self._apply_pattern(text, NAMED_PARAMETER_PATTERN, "named_parameter", comment_ranges)
        self._apply_pattern(text, EXPRESSION_PATTERN, "expression", comment_ranges)
        self._highlight_modal_words(text, comment_ranges)


class GCodeSyntaxHighlighter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighters = []

    def attach_document(self, text_document):
        if text_document is None:
            return

        alive_highlighters = []
        for highlighter in self._highlighters:
            try:
                if highlighter.document() is text_document:
                    self._highlighters = alive_highlighters + [highlighter]
                    return
                alive_highlighters.append(highlighter)
            except RuntimeError:
                continue

        self._highlighters = alive_highlighters
        self._highlighters.append(_DocumentHighlighter(text_document, self))

    @pyqtSlot(QObject)
    def attach(self, quick_document):
        if quick_document is None:
            return

        text_document = quick_document.textDocument()
        self.attach_document(text_document)
