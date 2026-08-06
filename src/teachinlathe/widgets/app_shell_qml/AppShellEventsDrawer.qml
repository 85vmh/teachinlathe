import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#11161d"
    border.color: "#2b3440"
    border.width: 1

    readonly property string statusSummary: appShellBridge ? appShellBridge.statusSummary : ""
    readonly property var events: appShellBridge ? appShellBridge.events : []

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 40

            Text {
                text: "Application Events"
                color: "white"
                font.pixelSize: 20
                font.bold: true
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
            }

            Button {
                text: "Clear"
                onClicked: if (appShellBridge) appShellBridge.clearEvents()
            }
        }

        Text {
            text: root.statusSummary
            color: "#9fb0c7"
            font.pixelSize: 13
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
                     : "#d8e0ef"
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }
    }
}
