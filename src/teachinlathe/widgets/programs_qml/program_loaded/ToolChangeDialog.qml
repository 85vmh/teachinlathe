import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent
    visible: viewModel ? viewModel.requested : false
    enabled: visible
    z: 1200

    property var viewModel
    readonly property color textColor: "#1e2430"
    readonly property color confirmColor: "#2e7d32"
    readonly property color cancelColor: "#c62828"
    property real dialogCenterX: root.width * 0.75
    property real dialogCenterY: root.height / 2

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
    }

    Rectangle {
        anchors.fill: parent
        color: "#80000000"
        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        width: 620
        height: card.implicitHeight + 48
        x: Math.max(0, Math.min(root.width - width, root.dialogCenterX - width / 2))
        y: Math.max(0, Math.min(root.height - height, root.dialogCenterY - height / 2))
        radius: 10
        color: "#ffffff"
        border.color: "#cbd5e1"
        border.width: 1

        ColumnLayout {
            id: card
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 24
            }
            spacing: 18

            Text {
                Layout.fillWidth: true
                text: "Tool Change"
                font.pixelSize: 20
                font.bold: true
                color: root.textColor
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                textFormat: Text.RichText
                text: "Please load <b>" + root.escapeHtml(root.viewModel ? root.viewModel.toolNoText : "T?") + "</b>"
                    + ((root.viewModel && root.viewModel.toolDescription.length > 0)
                        ? " [" + root.escapeHtml(root.viewModel.toolDescription) + "]"
                        : "")
                font.pixelSize: 18
                color: root.textColor
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            Item { Layout.preferredHeight: 16 }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 0

                Text {
                    text: "Press "
                    font.pixelSize: 18
                    color: root.textColor
                }

                Text {
                    id: cycleStartText
                    text: "CycleStart"
                    font.pixelSize: 18
                    font.bold: true
                    color: root.confirmColor
                    opacity: cycleStartMouse.pressed ? 0.65 : 1.0

                    MouseArea {
                        id: cycleStartMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: if (root.viewModel) root.viewModel.confirmPressed()
                        onReleased: if (root.viewModel) root.viewModel.confirmReleased()
                        onCanceled: if (root.viewModel) root.viewModel.confirmReleased()
                    }
                }

                Text {
                    text: " to confirm the tool change"
                    font.pixelSize: 18
                    color: root.textColor
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 0

                Text {
                    text: "Press "
                    font.pixelSize: 18
                    color: root.textColor
                }

                Text {
                    id: cycleAbortText
                    text: "CycleAbort"
                    font.pixelSize: 18
                    font.bold: true
                    color: root.cancelColor
                    opacity: cycleAbortMouse.pressed ? 0.65 : 1.0

                    MouseArea {
                        id: cycleAbortMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: if (root.viewModel) root.viewModel.cancelPressed()
                        onReleased: if (root.viewModel) root.viewModel.cancelReleased()
                        onCanceled: if (root.viewModel) root.viewModel.cancelReleased()
                    }
                }

                Text {
                    text: " to stop the program."
                    font.pixelSize: 18
                    color: root.textColor
                }
            }
        }
    }
}
