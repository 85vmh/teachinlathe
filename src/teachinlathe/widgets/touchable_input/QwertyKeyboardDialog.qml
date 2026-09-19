// QwertyKeyboardDialog.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

Popup {
    id: root

    property var targetField: null
    property string titleText: "Enter text"
    property string buffer: ""
    property bool shiftOn: true
    property bool shiftLocked: false
    property bool symbolMode: false
    property bool shiftClickPending: false

    property int keyWidth: 100
    property int keyHeight: 85
    property int horizontalSpacing: 30
    property int verticalSpacing: 20
    property int spaceSideSpacing: 60
    property int popupWidth: 1350
    property int popupHeight: 600
    property int keyboardBottomOffset: 40
    readonly property real rowWidth: keyWidth * 10 + horizontalSpacing * 9
    readonly property real sideKeyWidth: Math.max(
        keyWidth,
        (rowWidth - keyWidth * 7 - horizontalSpacing * 8) / 2
    )
    readonly property real inputButtonWidth: keyWidth + horizontalSpacing + sideKeyWidth
    readonly property real bottomSpaceWidth: rowWidth - sideKeyWidth - inputButtonWidth - spaceSideSpacing * 2

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    parent: Overlay.overlay
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? Math.max(0, parent.height - height - keyboardBottomOffset) : 0
    width: popupWidth
    height: popupHeight
    leftPadding: 18
    rightPadding: 18
    topPadding: 16
    bottomPadding: 16

    background: Rectangle {
        color: Theme.surfaceInverse
        border.color: "#111416"
        border.width: Theme.hairline
        radius: Theme.radiusLarge
    }

    function openFor(field, titleOverride) {
        root.targetField = field
        root.titleText = titleOverride && String(titleOverride).length > 0
                       ? String(titleOverride)
                       : (field && field.titleText ? field.titleText : "Enter text")
        root.buffer = field && field.text !== undefined ? String(field.text) : ""
        root.shiftOn = root.buffer.length === 0
        root.shiftLocked = false
        root.symbolMode = false
        root.shiftClickPending = false
        shiftClickTimer.stop()
        root.open()
    }

    function _appendKey(label) {
        var text = String(label)
        root.buffer += root.symbolMode ? text : (root.shiftOn ? text.toUpperCase() : text.toLowerCase())
        if (!root.symbolMode && !root.shiftLocked)
            root.shiftOn = false
    }

    function _toggleShift() {
        if (root.symbolMode) {
            root.symbolMode = false
            root.shiftOn = true
            root.shiftLocked = false
            root.shiftClickPending = false
            shiftClickTimer.stop()
            return
        }

        if (root.shiftLocked) {
            root.shiftLocked = false
            root.shiftOn = false
            root.shiftClickPending = false
            shiftClickTimer.stop()
            return
        }

        if (root.shiftClickPending) {
            root.shiftLocked = true
            root.shiftOn = true
            root.shiftClickPending = false
            shiftClickTimer.stop()
            return
        }

        root.shiftOn = !root.shiftOn
        root.shiftClickPending = true
        shiftClickTimer.restart()
    }

    function _backspace() {
        root.buffer = root.buffer.slice(0, -1)
    }

    function _clearAll() {
        root.buffer = ""
        root.shiftOn = true
        root.shiftLocked = false
        root.shiftClickPending = false
        shiftClickTimer.stop()
    }

    function _accept() {
        if (root.targetField && root.targetField.commit)
            root.targetField.commit(root.buffer)
        root.close()
    }

    onClosed: {
        if (targetField && targetField.defocus)
            targetField.defocus()
        targetField = null
    }

    Component {
        id: keyButtonComponent

        Button {
            id: keyButton
            property string keyLabel: ""
            property int keyUnits: 1
            width: root.keyWidth * keyUnits + root.horizontalSpacing * (keyUnits - 1)
            height: root.keyHeight
            text: root.symbolMode ? keyLabel : (root.shiftOn ? keyLabel.toUpperCase() : keyLabel.toLowerCase())
            font.pixelSize: keyLabel.length > 1 ? 24 : 36
            font.bold: false

            contentItem: Text {
                text: keyButton.text
                color: Theme.surface
                font: keyButton.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                radius: Theme.radiusLarge
                color: keyButton.pressed ? Theme.keySurfacePressed : Theme.keySurface
                border.width: 0
            }

            onClicked: root._appendKey(keyLabel)
        }
    }

    Timer {
        id: shiftClickTimer
        interval: 350
        repeat: false
        onTriggered: root.shiftClickPending = false
    }

    contentItem: ColumnLayout {
        spacing: root.verticalSpacing

        Label {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.buttonHeightSmall
            text: root.titleText
            font.pixelSize: 26
            font.bold: true
            color: Theme.surface
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        Row {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.rowWidth
            Layout.preferredHeight: Theme.headerHeight
            width: root.rowWidth
            height: Theme.headerHeight
            spacing: root.horizontalSpacing

            TextField {
                id: display
                width: root.rowWidth - root.keyWidth * 3.2 - root.horizontalSpacing * 2
                height: parent.height
                text: root.buffer
                readOnly: true
                font.pixelSize: 26
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                color: Theme.foregroundStrong
                selectionColor: "transparent"
                selectedTextColor: Theme.foregroundStrong
                background: Rectangle {
                    radius: Theme.radiusLarge
                    color: Theme.surfaceAlt
                    border.color: Theme.separator
                    border.width: Theme.hairline
                }
            }

            Button {
                width: root.keyWidth * 1.35
                height: parent.height
                text: "<- Back"
                font.pixelSize: Theme.fontTitle
                contentItem: Text {
                    text: parent.text
                    color: Theme.surface
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                background: Rectangle {
                    radius: Theme.radiusLarge
                    color: parent.pressed ? Theme.keySurfacePressed : Theme.keySurface
                }
                onClicked: root._backspace()
            }

            Button {
                width: root.keyWidth * 1.85
                height: parent.height
                text: "Clear All"
                font.pixelSize: Theme.fontTitle
                contentItem: Text {
                    text: parent.text
                    color: Theme.surface
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
                background: Rectangle {
                    radius: Theme.radiusLarge
                    color: parent.pressed ? Theme.keySurfacePressed : Theme.keySurface
                }
                onClicked: root._clearAll()
            }
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.rowWidth
            Layout.preferredHeight: Theme.hairline
            color: Theme.foregroundSubtle
        }

        Column {
            Layout.alignment: Qt.AlignHCenter
            spacing: root.verticalSpacing

            Repeater {
                model: root.symbolMode
                     ? [ ["1","2","3","4","5","6","7","8","9","0"],
                         ["-","/",";",":","(",")","$","&","@","\""],
                         [".",",","?","!","'"] ]
                     : [ ["q","w","e","r","t","y","u","i","o","p"],
                         ["a","s","d","f","g","h","j","k","l"] ]

                delegate: Row {
                    spacing: root.horizontalSpacing
                    anchors.horizontalCenter: parent.horizontalCenter

                    Repeater {
                        model: modelData
                        delegate: Loader {
                            sourceComponent: keyButtonComponent
                            onLoaded: {
                                item.keyLabel = String(modelData)
                                item.keyUnits = 1
                            }
                        }
                    }
                }
            }

            Row {
                visible: !root.symbolMode
                spacing: root.horizontalSpacing
                anchors.horizontalCenter: parent.horizontalCenter

                Button {
                    width: root.sideKeyWidth
                    height: root.keyHeight
                    text: "Shift"
                    font.pixelSize: 28
                    contentItem: Text {
                        text: parent.text
                        color: Theme.foregroundStrong
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusLarge
                        color: parent.pressed ? Theme.hover
                                             : ((root.shiftOn || root.shiftLocked) ? Theme.outlineDisabled : "#9ca3af")
                        border.width: root.shiftLocked ? 2 : 0
                        border.color: "#2563eb"
                    }
                    onClicked: root._toggleShift()
                }

                Repeater {
                    model: ["z","x","c","v","b","n","m"]
                    delegate: Loader {
                        sourceComponent: keyButtonComponent
                        onLoaded: {
                            item.keyLabel = String(modelData)
                            item.keyUnits = 1
                        }
                    }
                }

                Item {
                    width: root.sideKeyWidth
                    height: root.keyHeight
                }
            }

            Row {
                width: root.rowWidth
                anchors.horizontalCenter: parent.horizontalCenter

                Button {
                    width: root.sideKeyWidth
                    height: root.keyHeight
                    text: root.symbolMode ? "ABC" : "123"
                    font.pixelSize: 24
                    contentItem: Text {
                        text: parent.text
                        color: Theme.surface
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusLarge
                        color: parent.pressed ? Theme.keySurfacePressed : Theme.keySurface
                    }
                    onClicked: root.symbolMode = !root.symbolMode
                }

                Item {
                    width: root.spaceSideSpacing
                    height: root.keyHeight
                }

                Button {
                    width: root.bottomSpaceWidth
                    height: root.keyHeight
                    text: "Space"
                    font.pixelSize: 26
                    contentItem: Text {
                        text: parent.text
                        color: Theme.surface
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusLarge
                        color: parent.pressed ? Theme.keySurfacePressed : Theme.keySurface
                    }
                    onClicked: root.buffer += " "
                }

                Item {
                    width: root.spaceSideSpacing
                    height: root.keyHeight
                }

                Button {
                    width: root.inputButtonWidth
                    height: root.keyHeight
                    text: "Input"
                    font.pixelSize: 24
                    contentItem: Text {
                        text: parent.text
                        color: Theme.surface
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: Theme.radiusLarge
                        color: parent.pressed ? "#2f6ed3" : "#2563eb"
                    }
                    onClicked: root._accept()
                }
            }
        }
    }
}
