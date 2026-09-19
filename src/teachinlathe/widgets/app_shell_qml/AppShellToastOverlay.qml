import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Item {
    id: root

    Rectangle {
        id: toast
        visible: appShellBridge ? appShellBridge.toastVisible : false
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
            text: appShellBridge ? appShellBridge.toastText : ""
            color: Theme.surface
            font.pixelSize: Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
