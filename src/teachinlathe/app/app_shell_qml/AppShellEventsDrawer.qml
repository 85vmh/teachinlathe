import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

Rectangle {
    id: root
    color: Theme.surfaceSunken
    border.color: Theme.outline
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
                color: Theme.foregroundStrong
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
            color: Theme.foregroundMuted
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
                text: "[" + modelData.timestamp + "] " + modelData.level + ": " + modelData.message
                color: modelData.level === "ERROR" ? Theme.danger
                     : modelData.level === "WARNING" ? Theme.warning
                     : modelData.level === "COMMAND" ? Theme.accentStrong
                     : Theme.foregroundMuted
                font.pixelSize: Theme.fontSmall
                elide: Text.ElideRight
            }
        }
    }
}
