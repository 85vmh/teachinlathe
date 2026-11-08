import QtQuick
import theme

// An option that stays on or off, as a card: its name at the left, a switch
// (ToggleSwitch) at the right, and all of the card taps it - clicked(); what
// it is for sets checked. The program screens' Break on M1 and Skip / Blocks.
Rectangle {
    id: root

    property alias text: label.text
    property bool checked: false
    property int fontPixelSize: Theme.fontBody

    signal clicked()

    implicitWidth: label.implicitWidth + toggle.implicitWidth + 3 * Theme.spacing
    implicitHeight: Theme.buttonHeight
    radius: Theme.radius
    color: area.pressed ? Theme.hover : Theme.surfaceAlt
    border.color: Theme.outline
    border.width: Theme.hairline
    opacity: enabled ? 1.0 : Theme.disabledOpacity

    Text {
        id: label
        anchors.left: parent.left
        anchors.leftMargin: Theme.spacing
        anchors.right: toggle.left
        anchors.rightMargin: Theme.spacingSmall
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.foreground
        font.pixelSize: root.fontPixelSize
        font.bold: true
        elide: Text.ElideRight
    }

    ToggleSwitch {
        id: toggle
        anchors.right: parent.right
        anchors.rightMargin: Theme.spacing
        anchors.verticalCenter: parent.verticalCenter
        checked: root.checked
    }

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
