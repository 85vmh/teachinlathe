import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Sits to the right of ProgramsDro, above the gremlin. Shows the current /
// upcoming tool, the feed (with override) and the spindle (RPM, plus constant
// surface speed when in CSS mode). Values are dummy for now — a single source
// of truth will be wired in later.
Rectangle {
    id: root

    // --- Dummy data (to be replaced by a view model) -----------------------
    property int currentTool: 1
    property int nextTool: 5

    property real feedValue: 0.01
    property int feedOverride: 100
    property string feedUnits: "mm/rev"

    property int spindleOverride: 100
    property real spindleRpm: 1000
    property real cssValue: 200
    property bool cssMode: false

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
    radius: 4

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
                text: "T" + root.currentTool
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
                text: "T" + root.nextTool
                color: "#172033"
                font.pixelSize: 26
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ---- Feed row (aligns with the X axis row) ------------------------
        RowLayout {
            Layout.preferredHeight: root.rowHeight
            spacing: 8

            RowLayout {
                Layout.preferredWidth: root.labelWidth
                Layout.preferredHeight: 40
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: "F"
                    color: "#172033"
                    font.pixelSize: 40
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    Layout.alignment: Qt.AlignRight | Qt.AlignBottom
                    text: "(" + root.feedOverride + "%)"
                    color: "#475569"
                    font.pixelSize: 15
                }
            }

            DroValueBox {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.inputHeight
                Layout.alignment: Qt.AlignVCenter
                fontSize: 25
                text: Number(root.feedValue).toFixed(2)
            }

            Text {
                Layout.preferredWidth: root.unitsWidth
                text: root.feedUnits
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
                    text: "(" + root.spindleOverride + "%)"
                    color: "#475569"
                    font.pixelSize: 15
                }
            }

            // RPM mode — single box, same height as the feed box.
            RowLayout {
                Layout.alignment: Qt.AlignVCenter
                visible: !root.cssMode
                spacing: 8

                DroValueBox {
                    Layout.preferredWidth: root.valueBoxWidth
                    Layout.preferredHeight: root.inputHeight
                    fontSize: 25
                    text: Number(root.spindleRpm).toFixed(0)
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
                visible: root.cssMode
                spacing: root.cssSpacing

                RowLayout {
                    spacing: 8

                    DroValueBox {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: Number(root.spindleRpm).toFixed(0)
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

                    DroValueBox {
                        Layout.preferredWidth: root.valueBoxWidth
                        Layout.preferredHeight: root.cssInputHeight
                        fontSize: 18
                        text: Number(root.cssValue).toFixed(0)
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
