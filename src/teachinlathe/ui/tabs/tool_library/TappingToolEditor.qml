import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common.touchable_input

// Add or edit a tap, laid out as DrillingToolEditor is: the form on the
// left, the tap as it sits on the right. There is no orientation to pick -
// a tap is always at 7, on the axis pointing -Z. Diameter and pitch are
// typed on the numpad; the pitch offers the usual metric ones first
// (numpad_settings.json: tap.pitch). Everything is written to `editor`
// (TappingToolEditorViewModel) as it changes; the top bar's Save keeps it
// and Back throws it away.
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

    // A length in mm, through the numpad. Committing writes to the editor,
    // which may refuse it - so the value is bound back to the editor
    // afterwards, rather than left at what was typed.
    component LengthField: NumpadField {
        id: field
        property var read: function() { return 0 }
        property var write: function(v) {}
        Layout.preferredWidth: root.fieldWidth
        fontPixelSize: Theme.fontTitle
        formatter: root.mmText
        value: read()
        onOpenRequested: function(field, settingName) { numpad.openFor(field, settingName, description) }
        onValueCommitted: function(v) {
            if (v !== null) write(v)
            value = Qt.binding(read)
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
                        text: "Tap"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontLarge
                        font.bold: true
                    }

                    FormRow {
                        label: "Diameter (mm)"
                        LengthField {
                            settingName: "tap.diameter"
                            description: "Tap diameter (mm)"
                            read: function() { return root.editor ? root.editor.diameter : null }
                            write: function(v) { root.editor.setDiameter(v) }
                        }
                    }
                    FormRow {
                        label: "Pitch (mm)"
                        LengthField {
                            settingName: "tap.pitch"
                            description: "Thread pitch (mm)"
                            read: function() { return root.editor ? root.editor.pitch : null }
                            write: function(v) { root.editor.setPitch(v) }
                        }
                    }
                    FormRow {
                        label: "Thread"
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

        TappingToolPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
