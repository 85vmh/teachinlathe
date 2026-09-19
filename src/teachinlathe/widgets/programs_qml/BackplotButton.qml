import QtQuick 2.15
import QtQuick.Controls 2.15

/*
 * One of the controls floating over the backplot. These were QPushButtons
 * created and positioned from Python, with their colours in a stylesheet
 * string; they are ordinary QML buttons now, laid out by anchors like
 * everything else on the screen.
 */
Button {
    id: control

    property color baseColor: "#2d7d46"
    property color hoverColor: "#25673a"
    property color borderColor: "#3fb950"

    implicitHeight: 44
    implicitWidth: label.implicitWidth + 32
    focusPolicy: Qt.NoFocus

    contentItem: Text {
        id: label
        text: control.text
        color: control.enabled ? "white" : "#d9e7de"
        font.pixelSize: 16
        font.family: "Noto Sans"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 6
        color: !control.enabled ? "#8ea99a"
             : control.down || control.hovered ? control.hoverColor
             : control.baseColor
        border.width: 1
        border.color: control.enabled ? control.borderColor : "#8ea99a"
    }
}
