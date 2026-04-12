import QtQuick 2.15
import QtQuick.Controls 2.15

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
        color: root.enabled ? "#000000" : "#a0a0a0"
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 40
        color: !root.enabled ? "#f0f0f0" : (root.checked ? "lightblue" : "lightgray")
        border.color: !root.enabled ? "#d3d3d3" : "gray"
        border.width: 1
    }
}
