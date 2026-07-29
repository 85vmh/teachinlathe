import QtQuick 2.15
import QtQuick.Controls 2.15

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
        radius: 8
        color: "#cc303030"

        Text {
            id: toastText
            anchors.centerIn: parent
            text: appShellBridge ? appShellBridge.toastText : ""
            color: "#ffffff"
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
