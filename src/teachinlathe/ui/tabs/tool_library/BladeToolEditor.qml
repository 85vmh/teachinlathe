import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import common.touchable_input 1.0

// Add or edit a blade - parting, grooving, trepanning - laid out as
// TurningToolEditor is: the form on the left, the orientation in the
// middle, the blade as it will sit in the holder on the right. Everything
// is written to `editor` (BladeToolEditorViewModel) as it changes; the top
// bar's Save keeps it and Back throws it away.
//
// Width and radii are typed on the numpad, which offers the usual values
// first (numpad_settings.json: blade.width, blade.corner_radius).
Item {
    id: root

    property var editor: null

    QwertyKeyboardDialog { id: keyboard }

    readonly property int labelWidth: 150
    readonly property int fieldWidth: 160
    readonly property int buttonWidth: 150

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
    // which may hold it to what fits - so the value is bound back to the
    // editor afterwards, rather than left at what was typed.
    component LengthField: NumpadField {
        id: field
        property var read: function() { return 0 }
        property var write: function(v) {}
        Layout.preferredWidth: root.fieldWidth
        fontPixelSize: Theme.fontTitle
        formatter: root.mmText
        value: read()
        onOpenRequested: numpad.openFor(field, settingName, description)
        onValueCommitted: function(v) {
            if (v !== null) write(v)
            value = Qt.binding(read)
        }
    }

    component FormButton: Rectangle {
        id: button
        property alias text: buttonText.text
        signal clicked()
        Layout.preferredWidth: root.buttonWidth
        Layout.preferredHeight: Theme.inputHeight
        radius: Theme.radius
        color: buttonArea.pressed ? Theme.selection : Theme.surface
        border.color: buttonArea.pressed ? Theme.accent : Theme.outline
        border.width: 1
        Text {
            id: buttonText
            anchors.centerIn: parent
            color: Theme.foreground
            font.pixelSize: Theme.fontBody
        }
        MouseArea {
            id: buttonArea
            anchors.fill: parent
            onClicked: button.clicked()
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
                        text: "Blade"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontLarge
                        font.bold: true
                    }

                    FormRow {
                        label: "Width (mm)"
                        LengthField {
                            settingName: "blade.width"
                            description: "Blade width (mm)"
                            read: function() { return root.editor ? root.editor.bladeWidth : null }
                            write: function(v) { root.editor.setBladeWidth(v) }
                        }
                        FormButton {
                            text: "Round tip"
                            onClicked: root.editor.roundTip()
                        }
                    }
                    FormRow {
                        label: "Left radius (mm)"
                        LengthField {
                            settingName: "blade.corner_radius"
                            description: "Left corner radius (mm)"
                            read: function() { return root.editor ? root.editor.leftRadius : null }
                            write: function(v) { root.editor.setLeftRadius(v) }
                        }
                        FormButton {
                            text: "Copy to Right"
                            onClicked: root.editor.copyLeftToRight()
                        }
                    }
                    FormRow {
                        label: "Right radius (mm)"
                        LengthField {
                            settingName: "blade.corner_radius"
                            description: "Right corner radius (mm)"
                            read: function() { return root.editor ? root.editor.rightRadius : null }
                            write: function(v) { root.editor.setRightRadius(v) }
                        }
                        FormButton {
                            text: "Copy to Left"
                            onClicked: root.editor.copyRightToLeft()
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: root.labelWidth + root.fieldWidth + root.buttonWidth
                                             + 2 * Theme.spacing
                        wrapMode: Text.WordWrap
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontSmall
                        text: !root.editor ? ""
                              : "A corner can be at most half the width ("
                                + root.mmText(root.editor.maxRadius) + " mm). Left is the corner on the"
                                + " -Z side at orientations 6 and 8."
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

        Rectangle {
            Layout.preferredWidth: picker.implicitWidth + 2 * Theme.margin
            Layout.fillHeight: true
            color: Theme.surfaceSunken
            radius: Theme.radius
            border.color: Theme.outline
            border.width: Theme.hairline

            OrientationPicker {
                id: picker
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.topMargin: Theme.margin
                cellSize: 72
                title: "Orientation"
                orientation: root.editor ? root.editor.orientation : 0
                allowed: root.editor ? root.editor.allowedOrientations : []
                onPicked: function(picked) { root.editor.setOrientation(picked) }
            }
        }

        BladeToolPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
