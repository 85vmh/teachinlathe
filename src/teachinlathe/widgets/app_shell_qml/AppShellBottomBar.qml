import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

Rectangle {
    id: root
    color: Theme.surfaceAlt
    readonly property string currentTab: appShellBridge ? appShellBridge.currentTab : ""
    readonly property bool logsExpanded: appShellBridge ? appShellBridge.logsExpanded : false

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Theme.hairline
        color: Theme.separator
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 6

        Repeater {
            model: [
                { id: "manual", label: "Manual Turning" },
                { id: "conversational", label: "Conversational" },
                { id: "programs", label: "Programs" },
                { id: "settings", label: "Machine Settings" }
            ]

            delegate: Rectangle {
                Layout.preferredWidth: 200
                Layout.fillHeight: true
                color: root.currentTab === modelData.id ? Theme.accentSoft : "transparent"

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 3
                    visible: root.currentTab === modelData.id
                    color: Theme.primary
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: root.currentTab === modelData.id ? Theme.foreground : Theme.foregroundSubtle
                    font.pixelSize: Theme.fontBody
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: if (appShellBridge) appShellBridge.activateTab(modelData.id)
                }
            }
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            Layout.preferredWidth: 150
            Layout.fillHeight: true
            color: eventsArea.pressed || root.logsExpanded ? Theme.hover : "transparent"

            Text {
                anchors.centerIn: parent
                text: root.logsExpanded ? "Close Events" : "Events"
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontBody
            }

            MouseArea {
                id: eventsArea
                anchors.fill: parent
                onClicked: if (appShellBridge) appShellBridge.toggleLogs()
            }
        }
    }
}
