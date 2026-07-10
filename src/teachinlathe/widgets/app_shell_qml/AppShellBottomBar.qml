import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#f5f7fb"
    readonly property string currentTab: appShellBridge ? appShellBridge.currentTab : ""
    readonly property bool logsExpanded: appShellBridge ? appShellBridge.logsExpanded : false

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: "#d6dce7"
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
                { id: "programs", label: "Programs" }
            ]

            delegate: Rectangle {
                Layout.preferredWidth: 200
                Layout.fillHeight: true
                color: root.currentTab === modelData.id ? "#e6edf7" : "transparent"

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 3
                    visible: root.currentTab === modelData.id
                    color: "#2d7d46"
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: root.currentTab === modelData.id ? "#1e2430" : "#4a5568"
                    font.pixelSize: 16
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
            color: eventsArea.pressed || root.logsExpanded ? "#eef3fb" : "transparent"

            Text {
                anchors.centerIn: parent
                text: root.logsExpanded ? "Close Events" : "Events"
                color: "#4a5568"
                font.pixelSize: 16
            }

            MouseArea {
                id: eventsArea
                anchors.fill: parent
                onClicked: if (appShellBridge) appShellBridge.toggleLogs()
            }
        }
    }
}
