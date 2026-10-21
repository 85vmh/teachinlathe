import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

Rectangle {
    id: root
    color: Theme.foregroundStrong
    border.color: Theme.outlineInverse
    border.width: Theme.hairline

    readonly property string statusSummary: AppShellBridge.statusSummary
    readonly property var events: AppShellBridge.events

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.buttonHeight

            Text {
                text: "Application Events"
                color: "white"
                font.pixelSize: Theme.fontTitle
                font.bold: true
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
            }

            Button {
                text: "Clear"
                onClicked: AppShellBridge.clearEvents()
            }
        }

        Text {
            text: root.statusSummary
            color: "#9fb0c7"
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.events

            delegate: Text {
                width: ListView.view ? ListView.view.width : 400
                text: "[" + modelData.timestamp + "] " + modelData.level + " " + modelData.source + ": " + modelData.message
                color: modelData.level === "ERROR" ? "#ff8a80"
                     : modelData.level === "WARNING" ? "#ffd180"
                     : modelData.level === "COMMAND" ? "#80cbc4"
                     : Theme.separator
                font.pixelSize: Theme.fontSmall
                elide: Text.ElideRight
            }
        }
    }
}
