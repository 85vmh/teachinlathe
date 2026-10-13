import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import "../touchable_input"

// Add or edit a threading tool, laid out as TurningToolEditor is: the form
// on the left, the orientation in the middle, the insert as it will sit in
// the holder on the right. Everything is written to `editor`
// (ThreadingToolEditorViewModel) as it changes; the top bar's Save keeps it
// and Back throws it away.
Item {
    id: root

    property var editor: null

    QwertyKeyboardDialog { id: keyboard }

    readonly property int labelWidth: 150
    readonly property int fieldWidth: 220

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
                            model: root.editor ? root.editor.handTexts : []
                            currentIndex: root.editor ? root.editor.handIndex : -1
                            onActivated: function(index) { root.editor.setHand(index) }
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
                        label: "Pitch"
                        Choice {
                            model: root.editor ? root.editor.pitchTexts : []
                            currentIndex: root.editor ? root.editor.pitchIndex : -1
                            onActivated: function(index) { root.editor.setPitch(index) }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: root.labelWidth + root.fieldWidth + Theme.spacing
                        wrapMode: Text.WordWrap
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontSmall
                        text: "A full-profile insert cuts one pitch. An ER (external) is held at orientation 6, an IR (internal) at 8."
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

        ThreadingToolPreview {
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
        }
    }
}
