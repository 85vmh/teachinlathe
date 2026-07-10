import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Modal overlay shown over the full-screen run view when a program finishes.
// Implemented as a plain Item overlay (not a Popup) to avoid Popup/overlay
// crashes inside a QQuickWidget.
Item {
    id: root
    anchors.fill: parent
    visible: false
    z: 1000

    property string programName: ""
    property string movement: ""
    property string toolchange: ""
    property string total: ""
    property Item dialogTarget: null

    readonly property point _targetTopLeft: dialogTarget
        ? dialogTarget.mapToItem(root, 0, 0)
        : Qt.point(0, 0)
    readonly property real _targetWidth: dialogTarget ? dialogTarget.width : root.width
    readonly property real _targetHeight: dialogTarget ? dialogTarget.height : root.height

    function open() { root.visible = true }
    function close() { root.visible = false }

    // Dim backdrop that also swallows clicks behind the card.
    Rectangle {
        anchors.fill: parent
        color: "#80000000"
        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        x: root._targetTopLeft.x + (root._targetWidth - width) / 2
        y: root._targetTopLeft.y + (root._targetHeight - height) / 2
        width: 460
        height: card.implicitHeight + 48
        radius: 10
        color: "#ffffff"
        border.color: "#cbd5e1"
        border.width: 1

        ColumnLayout {
            id: card
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 24 }
            spacing: 18

            Text {
                Layout.fillWidth: true
                text: "Program complete: " + root.programName
                font.pixelSize: 20
                font.bold: true
                color: "#0f172a"
                elide: Text.ElideRight
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 24
                rowSpacing: 10

                Text { text: "Movement Time:"; font.pixelSize: 16; color: "#475569" }
                Text { text: root.movement; font.pixelSize: 16; font.bold: true; color: "#0f172a"
                       Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }

                Text { text: "Toolchange Time:"; font.pixelSize: 16; color: "#475569" }
                Text { text: root.toolchange; font.pixelSize: 16; font.bold: true; color: "#0f172a"
                       Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }

                Text { text: "Total Run Time:"; font.pixelSize: 16; color: "#475569" }
                Text { text: root.total; font.pixelSize: 16; font.bold: true; color: "#0f172a"
                       Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 12

                Button {
                    text: "Done"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    font.pixelSize: 16
                    onClicked: { programsViewModel.runDone(); root.close() }
                }
                Button {
                    text: "Run Again"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    font.pixelSize: 16
                    onClicked: { programsViewModel.runAgain(); root.close() }
                }
            }
        }
    }
}
