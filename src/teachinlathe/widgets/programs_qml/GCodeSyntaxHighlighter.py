import re

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter


class _DocumentHighlighter(QSyntaxHighlighter):
    def __init__(self, document, parent=None):
        super().__init__(document)
        self._parent = parent
        self._rules = []
        self._comment_rule = None
        self._build_rules()

    def _fmt(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(italic)
        return fmt

    def _build_rules(self):
        comment_fmt = self._fmt("#6A9955")
        label_fmt = self._fmt("#C586C0")
        command_fmt = self._fmt("#C586C0")
        mcode_fmt = self._fmt("#808080")
        x_axis_fmt = self._fmt("#F44747")
        z_axis_fmt = self._fmt("#B65F7A")
        feed_fmt = self._fmt("#4FC1FF")
        oword_fmt = self._fmt("#4FC1FF")

        self._comment_rule = (re.compile(r"\([^)]*\)"), comment_fmt)

        self._rules.extend([
            (re.compile(r"^\s*O\d+(?:\.\d+)?\b", re.IGNORECASE), oword_fmt),
            (re.compile(r"\b(?:SUB|ENDSUB|CALL)\b", re.IGNORECASE), label_fmt),
            (re.compile(r"\bG\d+(?:\.\d+)?\b", re.IGNORECASE), command_fmt),
            (re.compile(r"\bM\d+(?:\.\d+)?\b", re.IGNORECASE), mcode_fmt),
            (re.compile(r"\bT\d+(?:\.\d+)?\b", re.IGNORECASE), command_fmt),
            (re.compile(r"\b[XYAIJCR]-?\d+(?:\.\d+)?\b", re.IGNORECASE), x_axis_fmt),
            (re.compile(r"\b[ZUK]-?\d+(?:\.\d+)?\b", re.IGNORECASE), z_axis_fmt),
            (re.compile(r"\bQ-?\d+(?:\.\d+)?\b", re.IGNORECASE), oword_fmt),
            (re.compile(r"\b[FS]-?\d+(?:\.\d+)?\b", re.IGNORECASE), feed_fmt),
            (re.compile(r"<[^>]+>"), feed_fmt),
            (re.compile(r"\[[^\]]+\]"), label_fmt),
        ])

    def highlightBlock(self, text):
        if self._comment_rule is not None:
            pattern, fmt = self._comment_rule
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class GCodeSyntaxHighlighter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighters = []

    def attach_document(self, text_document):
        if text_document is None:
            return

        for highlighter in self._highlighters:
            if highlighter.document() is text_document:
                return

        self._highlighters.append(_DocumentHighlighter(text_document, self))

    @pyqtSlot(QObject)
    def attach(self, quick_document):
        if quick_document is None:
            return

        text_document = quick_document.textDocument()
        self.attach_document(text_document)
