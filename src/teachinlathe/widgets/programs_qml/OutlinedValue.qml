import QtQuick 2.15

// Reusable value box shared by ProgramsDro (axis positions) and
// ProgramsToolFeedSpeed (feed / spindle). Keeps the "box" styling in one place.
Rectangle {
    id: box

    property string text: ""
    property int fontSize: 34
    property int horizontalPadding: 12
    property int textAlignment: Text.AlignRight
    property color boxColor: "#f8fafc"
    property color textColor: "#0f172a"

    implicitWidth: 240
    implicitHeight: 60
    radius: 8
    color: boxColor
    border.color: "#cbd5e1"
    border.width: 1

    Text {
        anchors.fill: parent
        anchors.leftMargin: box.horizontalPadding
        anchors.rightMargin: box.horizontalPadding
        text: box.text
        color: box.textColor
        font.pixelSize: box.fontSize
        font.family: "monospace"
        horizontalAlignment: box.textAlignment
        verticalAlignment: Text.AlignVCenter
    }
}
