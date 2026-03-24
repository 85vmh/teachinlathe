import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    property var viewModel
    property string content: ""
    property bool editable: false
    property int highlightLine: 0
    property color highlightColor: "#3A86FF"
    property int highlightWidth: 1
    property bool centerOnHighlight: false
    property int linesBelowHighlight: 0
    property string emptyText: ""
    signal contentEdited(string text)

    color: "#ffffff"

    readonly property int lineCount: Math.max(1, content === "" ? 1 : content.split("\n").length)
    readonly property string lineNumberText: {
        var lines = []
        for (var i = 1; i <= lineCount; ++i) {
            lines.push(i)
        }
        return lines.join("\n")
    }

    function lineStartPosition(lineNumber) {
        if (lineNumber <= 1) {
            return 0
        }
        var target = Math.max(1, lineNumber)
        var seen = 1
        for (var i = 0; i < editor.text.length; ++i) {
            if (editor.text.charAt(i) === "\n") {
                seen += 1
                if (seen === target) {
                    return i + 1
                }
            }
        }
        return editor.text.length
    }

    function syncHighlight() {
        if (highlightLine <= 0) {
            highlightRect.visible = false
            return
        }
        var rect = editor.positionToRectangle(lineStartPosition(highlightLine))
        if (!rect || rect.height <= 0) {
            highlightRect.visible = false
            return
        }
        highlightRect.visible = true
        highlightRect.y = editor.y + rect.y - 2
        highlightRect.height = rect.height + 4
        if (centerOnHighlight) {
            var target = highlightRect.y - (flick.height / 2) + (highlightRect.height / 2)
            flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, target))
        } else if (linesBelowHighlight > 0) {
            var lineStep = rect.height
            var targetBottom = flick.height - ((linesBelowHighlight + 1) * lineStep)
            var targetY = highlightRect.y - targetBottom
            flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, targetY))
        }
    }

    onContentChanged: {
        if (editor.text !== content) {
            editor.text = content
            Qt.callLater(syncHighlight)
        }
    }
    onHighlightLineChanged: Qt.callLater(syncHighlight)
    onWidthChanged: Qt.callLater(syncHighlight)
    onHeightChanged: Qt.callLater(syncHighlight)

    Component.onCompleted: {
        if (viewModel) {
            viewModel.attachHighlighter(editor.textDocument)
        }
        if (editor.text !== content) {
            editor.text = content
        }
        Qt.callLater(syncHighlight)
    }

    Flickable {
        id: flick
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: contentRow.width
        contentHeight: Math.max(viewport.height, contentRow.height)

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

        Row {
            id: contentRow
            spacing: 0

            Rectangle {
                width: 56
                height: Math.max(viewport.height, lineNumbers.paintedHeight + 20)
                color: "#f5f5f5"

                Text {
                    id: lineNumbers
                    x: 0
                    y: 10
                    width: parent.width - 10
                    horizontalAlignment: Text.AlignRight
                    text: root.lineNumberText
                    color: "#9e9e9e"
                    font.family: "DejaVu Sans Mono"
                    font.pixelSize: 16
                    wrapMode: Text.NoWrap
                }

                Rectangle {
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: "#e0e0e0"
                }
            }

            Item {
                id: viewport
                width: Math.max(root.width - 56, editor.paintedWidth + 24)
                height: Math.max(root.height, editor.paintedHeight + 20)

                Rectangle {
                    id: highlightRect
                    x: 0
                    width: viewport.width - 1
                    visible: false
                    color: "transparent"
                    border.color: root.highlightColor
                    border.width: root.highlightWidth
                    z: 2
                }

                TextEdit {
                    id: editor
                    x: 12
                    y: 10
                    width: Math.max(1, paintedWidth)
                    height: Math.max(1, paintedHeight)
                    readOnly: !root.editable
                    text: root.content
                    color: "#2e2e2e"
                    textFormat: TextEdit.PlainText
                    font.family: "DejaVu Sans Mono"
                    font.pixelSize: 16
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: root.editable
                    selectionColor: "#264F78"
                    selectedTextColor: "#ffffff"
                    cursorVisible: root.editable
                    persistentSelection: root.editable
                    z: 1

                    onTextChanged: {
                        if (root.editable && text !== root.content) {
                            root.contentEdited(text)
                        }
                        Qt.callLater(root.syncHighlight)
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.content === ""
                    text: root.emptyText
                    color: "#9e9e9e"
                    font.pixelSize: 16
                }
            }
        }
    }
}
