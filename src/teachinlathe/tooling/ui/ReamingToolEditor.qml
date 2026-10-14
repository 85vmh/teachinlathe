import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import touchable_input 1.0

// Add or edit a reamer, laid out as DrillingToolEditor is: the form on the
// left, the reamer as it sits on the right. There is no orientation to pick
// - a reamer is always at 7, on the axis pointing -Z - and, its end being
// flat and its flutes always a small right-hand helix, no point angle or
// twist either. Everything is written to `editor`
// (ReamingToolEditorViewModel) as it changes; the top bar's Save keeps it
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

    // Two buttons, one of them chosen: CW/CCW.
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
                        text: "Reamer"
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
                            settingName: "reamer.diameter"
                            description: "Reamer diameter (mm)"
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

                    Item { Layout.preferredHeight: Theme.spacingSmall }
                    FormRow {
                        label: "Spindle direction"
                        SpindleDirectionPicker {
                            clockwise: root.editor ? root.editor.clockwise : null
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

        ReamingToolPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
