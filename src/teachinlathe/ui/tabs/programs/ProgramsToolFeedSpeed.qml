import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

// Sits between the top bar and the backplot. Shows, each in its own box, the
// spindle state, the movement speed and the current / upcoming tool.
// Calculations live in the view model; this component only displays
// formatted values.
Item {
    id: root

    required property var viewModel

    // --- Metrics -----------------------------------------------------------
    property int inputHeight: 40
    property int cssInputHeight: 30
    property int cssSpacing: 6
    property int boxPadding: Theme.spacingSmall
    property int boxHorizontalPadding: 16
    property int labelWidth: 80
    property int valueBoxWidth: 100
    property int unitsWidth: 72
    // Every box is as tall as the spindle's in CSS mode, the tallest content
    // (the RPM and the surface speed, one over the other).
    readonly property int boxHeight: 2 * root.cssInputHeight + root.cssSpacing + 2 * root.boxPadding

    implicitHeight: root.boxHeight
    implicitWidth: boxesRow.implicitWidth

    // One of the boxes: the card styling around a row of content.
    component Box: Rectangle {
        default property alias content: contentRow.data
        Layout.preferredHeight: root.boxHeight
        Layout.preferredWidth: contentRow.implicitWidth + 2 * root.boxHorizontalPadding
        color: Theme.hover
        border.color: Theme.separator
        border.width: Theme.hairline
        radius: Theme.radius

        RowLayout {
            id: contentRow
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: root.boxHorizontalPadding
            spacing: Theme.spacingSmall
        }
    }

    RowLayout {
        id: boxesRow
        anchors.fill: parent
        spacing: Theme.spacingSmall

        // ---- Spindle ------------------------------------------------------
        Box {
            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: Theme.buttonHeight
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: "S"
                    color: Theme.foreground
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
                    text: "(" + (root.viewModel.spindleOverridePercent) + "%)"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }
            }

            // RPM mode — single box, same height as the feed box.
            RowLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: !(root.viewModel.spindleIsCss)
                spacing: Theme.spacingSmall

                OutlinedValue {
                    Layout.preferredWidth: root.valueBoxWidth
                    Layout.preferredHeight: root.inputHeight
                    fontSize: 25
                    text: root.viewModel.spindleRpmText
                }

                Text {
                    Layout.preferredWidth: root.unitsWidth
                    text: "RPM"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontTitle
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // CSS mode — two shorter boxes (RPM + surface speed), tighter spacing.
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: root.viewModel.spindleIsCss
                spacing: root.cssSpacing

                RowLayout {
                    spacing: Theme.spacingSmall

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel.spindleRpmText
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "RPM"
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontBody
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                RowLayout {
                    spacing: Theme.spacingSmall

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel.cssValueText
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "m/min"
                        color: Theme.foregroundSubtle
                        font.pixelSize: Theme.fontBody
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // ---- Movement: Feed / Rapid ---------------------------------------
        Box {
            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: Theme.buttonHeight
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: root.viewModel.movementLetter
                    color: Theme.foreground
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignRight | Qt.AlignBottom
                    text: "(" + (root.viewModel.movementOverridePercent) + "%)"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }
            }

            OutlinedValue {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.inputHeight
                Layout.alignment: Qt.AlignVCenter
                fontSize: 25
                text: root.viewModel.movementValueText
            }

            Text {
                Layout.preferredWidth: root.unitsWidth
                text: root.viewModel.movementUnitsText
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontTitle
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- Tool: Current -> Next, and while the program runs, under the
        // arrow, how long until the machine stops for the next one. With no
        // tool after the current one, the current one alone.
        Box {
            ColumnLayout {
                spacing: 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Current"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.viewModel.currentLoadedToolText
                    color: Theme.foreground
                    font.pixelSize: 26
                }
            }

            ColumnLayout {
                visible: root.viewModel.hasNextTool
                spacing: 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "⟶"
                    color: Theme.foregroundSubtle
                    font.pixelSize: 24
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    visible: text !== ""
                    text: root.viewModel.nextToolTimeText
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody
                    font.family: "monospace"
                }
            }

            ColumnLayout {
                visible: root.viewModel.hasNextTool
                spacing: 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Next"
                    color: Theme.foregroundSubtle
                    font.pixelSize: Theme.fontSmall
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.viewModel.nextToolText
                    color: Theme.foreground
                    font.pixelSize: 26
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
