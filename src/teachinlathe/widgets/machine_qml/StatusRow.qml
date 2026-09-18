import QtQuick 2.15

// One machine-state line: a lamp that lights when something is wrong, and the
// text that says what. The .ui lit its LEDs on the fault, not on the good
// state, and that reads better on a splash you only see when blocked.
Row {
    id: root

    property bool ok: false
    property string text: ""

    spacing: 12

    Rectangle {
        width: 22
        height: 22
        radius: 11
        anchors.verticalCenter: parent.verticalCenter
        color: root.ok ? "#2d7d46" : "#c0392b"
        border.width: 2
        border.color: root.ok ? "#3fb950" : "#e06c5a"

        SequentialAnimation on opacity {
            running: !root.ok
            loops: Animation.Infinite
            NumberAnimation { to: 0.45; duration: 700; easing.type: Easing.InOutQuad }
            NumberAnimation { to: 1.0;  duration: 700; easing.type: Easing.InOutQuad }
        }
        onColorChanged: if (root.ok) opacity = 1.0
    }

    Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        color: root.ok ? "#2d7d46" : "#c0392b"
        font.pixelSize: 20
        font.bold: true
    }
}
