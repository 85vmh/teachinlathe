import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#f5f7fb"
    border.color: "#d6dce7"
    border.width: 0

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: "#d6dce7"
    }

    RowLayout {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - 20
        spacing: 10

        Repeater {
            model: appShellBridge.leftActions
            delegate: ShellActionButton {
                text: modelData.text || ""
                enabled: modelData.enabled !== false
                secondary: modelData.id === "back" || modelData.id === "edit_program"
                onClicked: appShellBridge.triggerHeaderAction(modelData.id || "")
            }
        }
    }

    Text {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.42, 720)
        text: appShellBridge.title
        color: "#1e2430"
        font.pixelSize: 23
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    RowLayout {
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - 20
        layoutDirection: Qt.RightToLeft
        spacing: 10

        Repeater {
            model: appShellBridge.rightActions
            delegate: ShellActionButton {
                text: modelData.text || ""
                enabled: modelData.enabled !== false
                checked: !!modelData.checked
                checkable: !!modelData.checked
                onClicked: appShellBridge.triggerHeaderAction(modelData.id || "")
            }
        }
    }
}
