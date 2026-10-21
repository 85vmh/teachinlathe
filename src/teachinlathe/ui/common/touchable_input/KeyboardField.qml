// KeyboardField.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

TextField {
    id: root

    property string titleText: ""
    property int hAlign: Text.AlignLeft
    property int fontPixelSize: 20
    property bool commitUpdatesText: true

    signal openRequested(Item field)
    signal valueCommitted(string value)

    property bool keyboardActive: false

    readOnly: true
    activeFocusOnPress: false
    focus: false
    cursorDelegate: null
    selectByMouse: false

    implicitHeight: Theme.inputHeight
    horizontalAlignment: hAlign
    verticalAlignment: Text.AlignVCenter
    font.pixelSize: fontPixelSize
    color: "transparent"
    selectedTextColor: "transparent"
    selectionColor: "transparent"

    Item {
        id: contentClip
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        clip: true

        readonly property bool textOverflows: displayText.paintedWidth > width

        Text {
            id: displayText
            anchors.fill: parent
            text: root.text.length > 0 ? root.text : root.placeholderText
            color: root.text.length > 0 ? Theme.foregroundStrong : Theme.foregroundFaint
            font: root.font
            horizontalAlignment: contentClip.textOverflows ? Text.AlignLeft : root.hAlign
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideNone
            clip: true
        }

        Rectangle {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: 24
            visible: root.text.length > 0 && contentClip.textOverflows
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Theme.surface }
            }
        }
    }

    background: Rectangle {
        radius: 2
        border.width: (root.keyboardActive || root.activeFocus) ? 2 : 1
        border.color: (root.keyboardActive || root.activeFocus) ? Theme.focusBorder : Theme.outline
        color: Theme.surface
    }

    onActiveFocusChanged: if (activeFocus) Qt.inputMethod.hide()

    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.keyboardActive
        onTapped: {
            root.forceActiveFocus()
            root.keyboardActive = true
            root.openRequested(root)
        }
        onPressedChanged: if (pressed) Qt.inputMethod.hide()
    }

    function commit(value) {
        var v = String(value)
        if (root.commitUpdatesText && root.text !== v)
            root.text = v
        root.valueCommitted(v)
        return true
    }

    function defocus() {
        root.focus = false
        root.keyboardActive = false
    }
}
