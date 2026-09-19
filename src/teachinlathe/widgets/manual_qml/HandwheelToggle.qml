import QtQuick 2.15
import QtQuick.Controls 2.15
import theme 1.0

Button {
    id: root
    property string axisLabel: "X"
    checkable: true
    text: axisLabel

    width: 80
    height: 80
    font.pixelSize: 32
    font.bold: true

    contentItem: Text {
        text: root.text
        color: root.enabled ? "#000000" : Theme.outlineEmphasis
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 40
        color: !root.enabled ? Theme.surfaceSunken : (root.checked ? "lightblue" : "lightgray")
        border.color: !root.enabled ? Theme.outline : "gray"
        border.width: Theme.hairline
    }
}
