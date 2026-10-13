import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import "../touchable_input"

// Add or edit a turning tool. The form is on the left, the insert as it
// will sit in the holder on the right. Everything is written to `editor`
// (TurningToolEditorViewModel) as it changes; the top bar's Save keeps it
// and Back throws it away.
Item {
    id: root

    property var editor: null

    QwertyKeyboardDialog { id: keyboard }

    readonly property int labelWidth: 150
    readonly property int fieldWidth: 220

    // Whole degrees as typed; a half only where the corner makes one (72.5
    // either side of a 35° VBMT held square).
    function angleText(v) { return v === null || v === undefined ? "" : String(Number(Number(v).toFixed(2))) }

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

    // An angle, through the numpad. Committing writes to the editor, which
    // may move the other angle too - so the value is bound back to the
    // editor afterwards, rather than left at what was typed.
    component AngleField: NumpadField {
        id: field
        property var read: function() { return 0 }
        property var write: function(v) {}
        Layout.preferredWidth: root.fieldWidth
        fontPixelSize: Theme.fontTitle
        formatter: root.angleText
        enabled: root.editor ? root.editor.anglesEditable : false
        opacity: enabled ? 1.0 : 0.6
        value: read()
        onOpenRequested: numpad.openFor(field, settingName, description)
        onValueCommitted: function(v) {
            if (v !== null) write(v)
            value = Qt.binding(read)
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
                        text: "Insert"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontLarge
                        font.bold: true
                    }

                    FormRow {
                        label: "Type"
                        Choice {
                            model: root.editor ? root.editor.families : []
                            currentIndex: root.editor ? root.editor.familyIndex : -1
                            onActivated: function(index) { root.editor.setFamily(index) }
                        }
                    }
                    FormRow {
                        label: "Size"
                        Choice {
                            model: root.editor ? root.editor.sizeCodes : []
                            currentIndex: root.editor ? root.editor.sizeIndex : -1
                            onActivated: function(index) { root.editor.setSize(index) }
                        }
                    }
                    FormRow {
                        label: "Nose radius"
                        Choice {
                            model: root.editor ? root.editor.noseRadiusCodes : []
                            currentIndex: root.editor ? root.editor.noseRadiusIndex : -1
                            onActivated: function(index) { root.editor.setNoseRadius(index) }
                        }
                    }

                    Item { Layout.preferredHeight: Theme.spacingSmall }
                    Text {
                        text: "Angles"
                        color: Theme.foreground
                        font.pixelSize: Theme.fontLarge
                        font.bold: true
                    }
                    FormRow {
                        label: "Front angle (°)"
                        AngleField {
                            settingName: "cutting_tool.front_angle"
                            description: "Front angle (°)"
                            read: function() { return root.editor ? root.editor.frontAngle : null }
                            write: function(v) { root.editor.setFrontAngle(v) }
                        }
                    }
                    FormRow {
                        label: "Back angle (°)"
                        AngleField {
                            settingName: "cutting_tool.back_angle"
                            description: "Back angle (°)"
                            read: function() { return root.editor ? root.editor.backAngle : null }
                            write: function(v) { root.editor.setBackAngle(v) }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: root.labelWidth + root.fieldWidth + Theme.spacing
                        wrapMode: Text.WordWrap
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontSmall
                        text: !root.editor ? ""
                              : root.editor.isRound
                                ? "A round insert has no corner: orientation 9, angles set independently."
                              : !root.editor.anglesEditable
                                ? "Front = back = (180° − " + root.editor.cornerAngle + "° corner) / 2"
                                : "Both from the Z axis: front + " + root.editor.cornerAngle + "° corner + back = 180°"
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

        InsertPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
