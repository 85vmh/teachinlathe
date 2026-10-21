import QtQuick 2.15
import theme 1.0

// A holder's offsets, as a column: "Offsets" centred over X and Z, each
// value to the right. A missing value reads "Not set"; while either is
// missing it and the title are orange.
Column {
    id: root

    property string xOffset: ""         // as shown, or empty until touched off
    property string zOffset: ""

    readonly property bool offsetsSet: xOffset !== "" && zOffset !== ""

    spacing: 4

    Text {
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: "Offsets"
        color: root.offsetsSet ? Theme.foregroundMuted : Theme.warning
        font.pixelSize: Theme.fontLarge
        font.bold: true
    }

    Repeater {
        model: [{ axis: "X:", value: root.xOffset },
                { axis: "Z:", value: root.zOffset }]
        delegate: Item {
            width: root.width
            height: axisLabel.implicitHeight

            Text {
                id: axisLabel
                text: modelData.axis
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
                font.family: "monospace"
            }
            Text {
                anchors.right: parent.right
                text: modelData.value !== "" ? modelData.value : "Not set"
                color: modelData.value !== "" ? Theme.foreground : Theme.warning
                font.pixelSize: Theme.fontBody
                font.family: "monospace"
            }
        }
    }
}
