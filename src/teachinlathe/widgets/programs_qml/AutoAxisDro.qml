import QtQuick 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root

    property string axisLabel: "X"
    property real position: -123.345
    property real dtg: -123.345
    property int axisLabelWidth: 44
    property int valueBoxWidth: 220
    property int valueBoxHeight: 60
    property int axisLabelFontSize: 40
    property int valueFontSize: 34
    property int valueHorizontalPadding: 12
    property int valueBoxRadius: 8
    property int rowSpacing: 18

    spacing: root.rowSpacing

    Text {
        Layout.preferredWidth: root.axisLabelWidth
        text: root.axisLabel
        color: "#172033"
        font.pixelSize: root.axisLabelFontSize
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    Rectangle {
        Layout.preferredWidth: root.valueBoxWidth
        Layout.preferredHeight: root.valueBoxHeight
        radius: root.valueBoxRadius
        color: "#f8fafc"
        border.color: "#cbd5e1"
        border.width: 1

        Text {
            anchors.fill: parent
            anchors.leftMargin: root.valueHorizontalPadding
            anchors.rightMargin: root.valueHorizontalPadding
            text: Number(root.position).toFixed(3)
            color: "#0f172a"
            font.pixelSize: root.valueFontSize
            font.family: "monospace"
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    Rectangle {
        Layout.preferredWidth: root.valueBoxWidth
        Layout.preferredHeight: root.valueBoxHeight
        radius: root.valueBoxRadius
        color: "#f8fafc"
        border.color: "#cbd5e1"
        border.width: 1

        Text {
            anchors.fill: parent
            anchors.leftMargin: root.valueHorizontalPadding
            anchors.rightMargin: root.valueHorizontalPadding
            text: Number(root.dtg).toFixed(3)
            color: "#0f172a"
            font.pixelSize: root.valueFontSize
            font.family: "monospace"
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }
}
