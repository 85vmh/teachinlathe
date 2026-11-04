import QtQuick
import QtQuick.Controls
import theme
import TeachInLathe

Item {
    id: root

    Rectangle {
        id: toast
        visible: AppShellBridge.toastVisible
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 200
        width: toastText.implicitWidth + 100
        height: toastText.implicitHeight + 50
        radius: Theme.radiusLarge
        color: "#cc303030"

        Text {
            id: toastText
            anchors.centerIn: parent
            text: AppShellBridge.toastText
            color: Theme.surface
            font.pixelSize: Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
