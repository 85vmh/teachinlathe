import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

Rectangle {
    id: root
    color: Theme.surfaceAlt
    readonly property string currentTab: AppShellBridge.currentTab
    readonly property bool logsExpanded: AppShellBridge.logsExpanded

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
                { id: "tools", label: "Tool Library" },
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
                    onClicked: AppShellBridge.activateTab(modelData.id)
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
                onClicked: AppShellBridge.toggleLogs()
            }
        }
    }
}
