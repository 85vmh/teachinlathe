import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

Rectangle {
    id: root
    color: Theme.surfaceAlt
    border.color: Theme.separator
    border.width: 0

    readonly property var leftActions: AppShellBridge.leftActions
    readonly property var rightActions: AppShellBridge.rightActions
    readonly property string titleText: AppShellBridge.title
    readonly property alias customArea: customArea

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.hairline
        color: Theme.separator
    }

    RowLayout {
        anchors.left: parent.left
        anchors.leftMargin: Theme.titleBarMargin
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - 20
        spacing: 10

        Repeater {
            model: root.leftActions
            delegate: ShellActionButton {
                text: modelData.text || ""
                iconSource: modelData.icon || ""
                enabled: modelData.enabled !== false
                secondary: modelData.id === "back" || modelData.id === "edit_program"
                onClicked: AppShellBridge.triggerHeaderAction(modelData.id || "")
            }
        }
    }

    Text {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.42, 720)
        text: root.titleText
        color: Theme.foreground
        font.pixelSize: 23
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    RowLayout {
        anchors.right: parent.right
        anchors.rightMargin: Theme.titleBarMargin
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - 20
        layoutDirection: Qt.RightToLeft
        spacing: 10

        Repeater {
            model: root.rightActions
            delegate: ShellActionButton {
                text: modelData.text || ""
                iconSource: modelData.icon || ""
                leadingIcon: modelData.leadingIcon || ""
                leadingText: modelData.leadingText || ""
                enabled: modelData.enabled !== false
                checked: !!modelData.checked
                checkable: !!modelData.checked
                active: !!modelData.active
                onClicked: AppShellBridge.triggerHeaderAction(modelData.id || "")
            }
        }
    }

    // What a screen puts in the bar beside the actions - a label over a box
    // of its own, a choice to make there: items parented to this, laid out
    // by the screen (AppShell.titleBarArea).
    Item {
        id: customArea
        anchors.fill: parent
    }
}
