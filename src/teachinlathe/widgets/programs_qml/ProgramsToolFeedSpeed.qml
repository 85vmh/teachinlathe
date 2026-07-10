import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Sits to the right of ProgramsDro, above the gremlin. Shows the current /
// upcoming tool, movement speed and spindle state. Calculations live in the
// view model; this component only displays formatted values.
Rectangle {
    id: root

    property var viewModel

    // --- Metrics (kept in sync with ProgramsDro so rows line up) -----------
    property int headerHeight: 30
    property int rowHeight: 60
    property int inputHeight: 40
    property int cssInputHeight: 30
    property int cssSpacing: 6
    property int columnSpacing: 18
    property int labelWidth: 80
    property int valueBoxWidth: 100
    property int unitsWidth: 72

    color: "#eef2f7"
    border.color: "#cfd7e3"
    border.width: 1
    radius: 6

    ColumnLayout {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 20
        anchors.topMargin: 16
        spacing: root.columnSpacing

        // ---- Header: T[current]  --upcoming tool-->  T[next] --------------
        RowLayout {
            Layout.preferredHeight: root.headerHeight
            spacing: 8

            Text {
                text: root.viewModel ? root.viewModel.currentToolText : "T0"
                color: "#172033"
                font.pixelSize: 26
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                    Layout.fillWidth: true
                    text: "⟶"
                    color: "#475569"
                    font.pixelSize: 24
                    horizontalAlignment: Text.AlignHCenter
            }

            Text {
                text: root.viewModel ? root.viewModel.nextToolText : "T-"
                color: "#172033"
                font.pixelSize: 26
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- Movement row: Feed / Rapid (aligns with the X axis row) ------
        RowLayout {
            Layout.preferredHeight: root.rowHeight
            spacing: 8

            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: 40
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: root.viewModel ? root.viewModel.movementLetter : "-"
                    color: "#172033"
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignRight | Qt.AlignBottom
                    text: "(" + (root.viewModel ? root.viewModel.movementOverridePercent : 0) + "%)"
                    color: "#475569"
                    font.pixelSize: 15
                }
            }

            OutlinedValue {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.inputHeight
                Layout.alignment: Qt.AlignVCenter
                fontSize: 25
                text: root.viewModel ? root.viewModel.movementValueText : "0.00"
            }

            Text {
                Layout.preferredWidth: root.unitsWidth
                text: root.viewModel ? root.viewModel.movementUnitsText : "mm/rev"
                color: "#475569"
                font.pixelSize: 20
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- Spindle row (aligns with the Z axis row) ---------------------
        RowLayout {
            Layout.preferredHeight: root.rowHeight
            spacing: 8

            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: 40
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: "S"
                    color: "#172033"
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
                    text: "(" + (root.viewModel ? root.viewModel.spindleOverridePercent : 0) + "%)"
                    color: "#475569"
                    font.pixelSize: 15
                }
            }

            // RPM mode — single box, same height as the feed box.
            RowLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: !(root.viewModel && root.viewModel.spindleIsCss)
                spacing: 8

                OutlinedValue {
                    Layout.preferredWidth: root.valueBoxWidth
                    Layout.preferredHeight: root.inputHeight
                    fontSize: 25
                    text: root.viewModel ? root.viewModel.spindleRpmText : "0"
                }

                Text {
                    Layout.preferredWidth: root.unitsWidth
                    text: "RPM"
                    color: "#475569"
                    font.pixelSize: 20
                    verticalAlignment: Text.AlignVCenter
                }
            }

            // CSS mode — two shorter boxes (RPM + surface speed), tighter spacing.
            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: root.viewModel && root.viewModel.spindleIsCss
                spacing: root.cssSpacing

                RowLayout {
                    spacing: 8

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel ? root.viewModel.spindleRpmText : "0"
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "RPM"
                        color: "#475569"
                        font.pixelSize: 16
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                RowLayout {
                    spacing: 8

                    OutlinedValue {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: root.viewModel ? root.viewModel.cssValueText : "0"
                    }

                    Text {
                        Layout.preferredWidth: root.unitsWidth
                        text: "m/min"
                        color: "#475569"
                        font.pixelSize: 16
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}
