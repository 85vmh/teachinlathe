import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property string fileContent: ""
    property string emptyText: ""

    color: "#1e1e1e"

    readonly property int lineCount: Math.max(1, fileContent === "" ? 1 : fileContent.split("\n").length)
    readonly property string lineNumberText: {
        var lines = []
        for (var i = 1; i <= lineCount; ++i) {
            lines.push(i)
        }
        return lines.join("\n")
    }

    Component.onCompleted: fsBridge.attachHighlighter(codeArea.textDocument)

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
                color: "#252526"

                Text {
                    id: lineNumbers
                    x: 0
                    y: 10
                    width: parent.width - 10
                    horizontalAlignment: Text.AlignRight
                    text: root.lineNumberText
                    color: "#858585"
                    font.family: "monospace"
                    font.pixelSize: 13
                    wrapMode: Text.NoWrap
                }

                Rectangle {
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: "#333333"
                }
            }

            Item {
                id: viewport
                width: Math.max(root.width - 56, codeArea.paintedWidth + 24)
                height: Math.max(root.height, codeArea.paintedHeight + 20)

                TextEdit {
                    id: codeArea
                    x: 12
                    y: 10
                    width: Math.max(1, paintedWidth)
                    height: Math.max(1, paintedHeight)
                    readOnly: true
                    text: root.fileContent
                    color: "#d4d4d4"
                    textFormat: TextEdit.PlainText
                    font.family: "monospace"
                    font.pixelSize: 13
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: true
                    selectionColor: "#264F78"
                    selectedTextColor: "#ffffff"
                    cursorVisible: false
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.fileContent === ""
                    text: root.emptyText
                    color: "#444444"
                    font.pixelSize: 16
                }
            }
        }
    }
}
