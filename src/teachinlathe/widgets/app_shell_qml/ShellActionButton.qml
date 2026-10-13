import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Rectangle {
    id: root

    property alias text: label.text
    property bool secondary: false
    property bool checkable: false
    property bool checked: false
    // Lit, as when the action is waiting to be taken - the Programs tab ties
    // Cycle Start's to the machine's cycle-start LED, so it blinks with it.
    property bool active: false
    //: An icon in place of the text: a square toggle, light, blue while
    //: checked - as the toggles in the screens are.
    property url iconSource: ""
    readonly property bool isIcon: iconSource.toString() !== ""

    signal clicked()

    implicitWidth: isIcon ? Theme.buttonHeight : Math.max(96, label.implicitWidth + 36)
    implicitHeight: Theme.buttonHeight
    radius: Theme.radius
    color: {
        if (isIcon) return checked ? Theme.selection : (actionArea.pressed ? Theme.accentSoft : Theme.surface)
        if (!enabled) return secondary ? Theme.surfaceSunken : Theme.primaryDisabled
        if (checkable && checked) return actionArea.pressed ? "#684b0f" : "#7a5a12"
        if (secondary) return actionArea.pressed ? Theme.accentSoft : Theme.hover
        if (active) return actionArea.pressed ? Theme.primaryPressed : Theme.primaryBorder
        return actionArea.pressed ? Theme.primaryPressed : Theme.primary
    }
    border.width: isIcon && checked ? 2 : Theme.hairline
    border.color: {
        if (isIcon) return checked ? Theme.accent : Theme.outlineStrong
        if (!enabled) return secondary ? Theme.separator : Theme.primaryDisabled
        if (checkable && checked) return "#d7ba7d"
        return secondary ? "#c5d0df" : Theme.primaryBorder
    }
    opacity: enabled ? 1.0 : 0.75

    Image {
        visible: root.isIcon
        anchors.centerIn: parent
        width: parent.height - 8
        height: width
        source: root.iconSource
        sourceSize.width: width
        sourceSize.height: height
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    Text {
        id: label
        visible: !root.isIcon
        anchors.centerIn: parent
        color: root.secondary ? (root.enabled ? Theme.foreground : "#8c97a8") : "white"
        font.pixelSize: root.secondary ? 15 : 16
        font.bold: true
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    MouseArea {
        id: actionArea
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
