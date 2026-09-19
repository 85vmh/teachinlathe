import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

/*
 * One of the controls floating over the backplot. These were QPushButtons
 * created and positioned from Python, with their colours in a stylesheet
 * string; they are ordinary QML buttons now, laid out by anchors like
 * everything else on the screen.
 */
Button {
    id: control

    property color baseColor: Theme.primary
    property color hoverColor: Theme.primaryPressed
    property color borderColor: Theme.primaryBorder

    implicitHeight: Theme.buttonHeight
    implicitWidth: label.implicitWidth + 32
    focusPolicy: Qt.NoFocus

    contentItem: Text {
        id: label
        text: control.text
        color: control.enabled ? "white" : Theme.outlineDisabled
        font.pixelSize: Theme.fontBody
        font.family: "Noto Sans"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: Theme.radius
        color: !control.enabled ? Theme.primaryDisabled
             : control.down || control.hovered ? control.hoverColor
             : control.baseColor
        border.width: Theme.hairline
        border.color: control.enabled ? control.borderColor : Theme.primaryDisabled
    }
}
