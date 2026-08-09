import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    property var viewModel
    property string content: ""
    property int highlightLine: 0
    property color highlightColor: "#3A86FF"
    property int highlightWidth: 1
    property bool centerOnHighlight: false
    property int linesBelowHighlight: 0
    property string emptyText: ""
    property bool userDetachedFromHighlight: false
    property bool recenterButtonVisible: false
    property bool _programmaticScroll: false
    property bool _userScrollActive: false
    readonly property real _centerTolerance: 2

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

    function _maxContentY() {
        return Math.max(0, flick.contentHeight - flick.height)
    }

    function _clampContentY(value) {
        if (!isFinite(value))
            return 0
        return Math.max(0, Math.min(root._maxContentY(), value))
    }

    function _highlightLineRect() {
        if (highlightLine <= 0)
            return null
        var rect = editor.positionToRectangle(lineStartPosition(highlightLine))
        if (!rect || rect.height <= 0)
            return null
        return rect
    }

    function _applyHighlightRect(rect) {
        highlightRect.visible = true
        highlightRect.y = editor.y + rect.y - 2
        highlightRect.height = rect.height + 4
    }

    function _highlightCenterTarget(rect) {
        if (!rect)
            return flick.contentY
        var lineCenterY = editor.y + rect.y + (rect.height / 2)
        return root._clampContentY(lineCenterY - (flick.height / 2))
    }

    function _isHighlightCentered(rect) {
        if (!rect)
            return true
        return Math.abs(flick.contentY - root._highlightCenterTarget(rect)) <= root._centerTolerance
    }

    function updateRecenterButton() {
        var rect = root._highlightLineRect()
        recenterButtonVisible = centerOnHighlight
            && userDetachedFromHighlight
            && !!rect
            && !root._isHighlightCentered(rect)
    }

    function _setContentYProgrammatically(value) {
        centerAnimation.stop()
        _programmaticScroll = true
        flick.contentY = root._clampContentY(value)
        Qt.callLater(function() {
            root._programmaticScroll = false
            root.updateRecenterButton()
        })
    }

    function centerHighlight(animated) {
        var rect = root._highlightLineRect()
        if (!rect)
            return
        root._applyHighlightRect(rect)
        var target = root._highlightCenterTarget(rect)
        userDetachedFromHighlight = false
        if (!animated || Math.abs(flick.contentY - target) <= root._centerTolerance) {
            root._setContentYProgrammatically(target)
            return
        }
        centerAnimation.stop()
        _programmaticScroll = true
        centerAnimation.from = flick.contentY
        centerAnimation.to = target
        centerAnimation.start()
    }

    function syncHighlight() {
        var rect = root._highlightLineRect()
        if (!rect) {
            highlightRect.visible = false
            recenterButtonVisible = false
            return
        }
        root._applyHighlightRect(rect)
        if (centerOnHighlight && !userDetachedFromHighlight) {
            root.centerHighlight(false)
        } else if (linesBelowHighlight > 0) {
            var lineStep = rect.height
            var targetBottom = flick.height - ((linesBelowHighlight + 1) * lineStep)
            var targetY = highlightRect.y - targetBottom
            root._setContentYProgrammatically(targetY)
        } else {
            root.updateRecenterButton()
        }
    }

    onContentChanged: {
        if (editor.text !== content) {
            userDetachedFromHighlight = false
            editor.text = content
            Qt.callLater(syncHighlight)
        }
    }
    onHighlightLineChanged: Qt.callLater(syncHighlight)
    onCenterOnHighlightChanged: {
        if (centerOnHighlight)
            userDetachedFromHighlight = false
        Qt.callLater(syncHighlight)
    }
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

        onMovementStarted: {
            if (!root._programmaticScroll && root.centerOnHighlight && root.highlightLine > 0)
                root._userScrollActive = true
        }
        onMovementEnded: {
            root._userScrollActive = false
            root.updateRecenterButton()
        }
        onContentYChanged: {
            var userMovement = root._userScrollActive || flick.dragging || flick.flicking || flick.moving
            if (!root._programmaticScroll && userMovement && root.centerOnHighlight && root.highlightLine > 0)
                root.userDetachedFromHighlight = true
            root.updateRecenterButton()
        }
        onContentHeightChanged: Qt.callLater(root.syncHighlight)
        onHeightChanged: Qt.callLater(root.syncHighlight)

        NumberAnimation {
            id: centerAnimation
            target: flick
            property: "contentY"
            duration: 220
            easing.type: Easing.InOutQuad
            onStopped: {
                root._programmaticScroll = false
                root.updateRecenterButton()
            }
        }

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
                    font.pixelSize: 18
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
                    readOnly: true
                    text: root.content
                    color: "#2e2e2e"
                    textFormat: TextEdit.PlainText
                    font.family: "DejaVu Sans Mono"
                    font.pixelSize: 18
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: false
                    selectionColor: "#264F78"
                    selectedTextColor: "#ffffff"
                    cursorVisible: false
                    persistentSelection: false
                    z: 1

                    onTextChanged: Qt.callLater(root.syncHighlight)
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

    Button {
        id: recenterButton
        width: 60
        height: 60
        x: 56 + Math.max(0, (root.width - 56 - width) / 2)
        y: Math.max(0, (root.height - height) / 2)
        visible: root.recenterButtonVisible
        enabled: visible
        hoverEnabled: true
        z: 20
        padding: 0
        onClicked: root.centerHighlight(true)

        background: Rectangle {
            radius: 6
            color: Qt.rgba(46 / 255, 125 / 255, 50 / 255, 0.5)
            border.color: "#2E7D32"
            border.width: 1
        }

        contentItem: Item {
            Image {
                anchors.centerIn: parent
                width: 34
                height: 34
                source: "while_running/images/center_vertical.svg"
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
        }
    }
}
