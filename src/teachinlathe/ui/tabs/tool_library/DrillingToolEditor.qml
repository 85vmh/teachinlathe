import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import common.touchable_input 1.0

// Add or edit a drill: the form on the left, the drill as it sits on the
// right. There is no orientation to pick - a drill is always at 7, on the
// axis pointing -Z. Everything is
// written to `editor` (DrillingToolEditorViewModel) as it changes; the top
// bar's Save keeps it and Back throws it away.
Item {
    id: root

    property var editor: null

    QwertyKeyboardDialog { id: keyboard }

    readonly property int labelWidth: 150
    readonly property int fieldWidth: 260

    function mmText(v) { return v === null || v === undefined ? "" : String(Number(Number(v).toFixed(3))) }

    SmartNumpadDialog { id: numpad }

    // A label and a control, as one form row.
    component FormRow: RowLayout {
        property alias label: rowLabel.text
        spacing: Theme.spacing
        Layout.fillWidth: true
        Text {
            id: rowLabel
            Layout.preferredWidth: root.labelWidth
            color: Theme.foreground
            font.pixelSize: Theme.fontBody
        }
    }

    component Choice: ComboBox {
        Layout.preferredWidth: root.fieldWidth
        Layout.preferredHeight: Theme.inputHeight
        font.pixelSize: Theme.fontTitle
        contentItem: Text {
            leftPadding: 8
            rightPadding: 8
            text: parent.displayText
            font: parent.font
            color: Theme.foregroundStrong
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        delegate: ItemDelegate {
            width: parent ? parent.width : 0
            height: Theme.inputHeight
            text: modelData
            font.pixelSize: Theme.fontTitle
        }
    }

    // Two buttons, one of them chosen: CW/CCW, right/left hand.
    component Toggle: Row {
        id: toggle
        property var options: []           // [{ text, value }]
        property var chosen: null
        signal picked(var value)
        spacing: Theme.spacingSmall
        Repeater {
            model: toggle.options
            delegate: Rectangle {
                readonly property bool isChosen: toggle.chosen === modelData.value
                width: (root.fieldWidth - Theme.spacingSmall) / 2
                height: Theme.inputHeight
                radius: Theme.radius
                color: isChosen ? Theme.selection : Theme.surface
                border.color: isChosen ? Theme.accent : Theme.outline
                border.width: isChosen ? 2 : 1
                Text {
                    anchors.centerIn: parent
                    text: modelData.text
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody
                    font.bold: parent.isChosen
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: toggle.picked(modelData.value)
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacingLarge

        Rectangle {
            Layout.preferredWidth: formColumn.implicitWidth + 2 * Theme.margin
            Layout.fillHeight: true
            color: Theme.surfaceSunken
            radius: Theme.radius
            border.color: Theme.outline
            border.width: Theme.hairline

            Flickable {
                anchors.fill: parent
                anchors.margins: Theme.margin
                contentHeight: formColumn.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                ColumnLayout {
                    id: formColumn
                    width: parent.width
                    // Rows as far apart as Position At's, for a finger.
                    spacing: 20

                    Text {
                        text: "Drill"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontLarge
                        font.bold: true
                    }

                    FormRow {
                        label: "Diameter (mm)"
                        // Typed on the numpad, which may hold it to what
                        // fits - so bound back to the editor afterwards.
                        NumpadField {
                            id: diameterField
                            Layout.preferredWidth: root.fieldWidth
                            settingName: "drill.diameter"
                            description: "Drill diameter (mm)"
                            fontPixelSize: Theme.fontTitle
                            formatter: root.mmText
                            readonly property var read: function() { return root.editor ? root.editor.diameter : null }
                            value: read()
                            onOpenRequested: numpad.openFor(diameterField, settingName, description)
                            onValueCommitted: function(v) {
                                if (v !== null) root.editor.setDiameter(v)
                                value = Qt.binding(read)
                            }
                        }
                    }
                    FormRow {
                        label: "Tip angle"
                        Choice {
                            model: root.editor ? root.editor.tipAngleTexts : []
                            currentIndex: root.editor ? root.editor.tipAngleIndex : -1
                            onActivated: function(index) { root.editor.setTipAngle(index) }
                        }
                    }
                    FormRow {
                        label: "Twist"
                        Toggle {
                            options: [{ text: "Right hand", value: true }, { text: "Left hand", value: false }]
                            chosen: root.editor ? root.editor.rightHand : null
                            onPicked: function(value) { root.editor.setRightHand(value) }
                        }
                    }

                    Item { Layout.preferredHeight: Theme.spacingSmall }
                    FormRow {
                        label: "Spindle direction"
                        SpindleDirectionPicker {
                            clockwise: root.editor ? root.editor.clockwise : null
                            // A right-hand twist cuts only with M3, a left-hand one only with M4.
                            onlyClockwise: root.editor ? root.editor.rightHand : null
                            onPicked: function(clockwise) { root.editor.setClockwise(clockwise) }
                        }
                    }
                    FormRow {
                        label: "Comment"
                        KeyboardField {
                            Layout.preferredWidth: root.fieldWidth
                            Layout.preferredHeight: Theme.inputHeight
                            fontPixelSize: Theme.fontBody
                            titleText: "Comment"
                            placeholderText: "Optional"
                            maximumLength: root.editor ? root.editor.commentMaxLength : 200
                            text: root.editor ? root.editor.comment : ""
                            commitUpdatesText: false
                            onOpenRequested: function(field) { keyboard.openFor(field, titleText) }
                            onValueCommitted: function(value) { root.editor.setComment(value) }
                        }
                    }
                }
            }
        }

        DrillingToolPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
