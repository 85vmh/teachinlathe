import QtQuick 2.0

Item {
    id: joystick
    width: 200
    height: 200

    property bool activeXPlus: false
    property bool activeXMinus: false
    property bool activeZPlus: false
    property bool activeZMinus: false

    // Central circle
    Rectangle {
        id: centerCircle
        width: 50
        height: 50
        radius: 25
        color: "grey"
        anchors.centerIn: parent
    }

    // Function to create a line for arrow
    function createArrow(x1, y1, x2, y2, color) {
        return Line {
            x1: x1; y1: y1
            x2: x2; y2: y2
            strokeColor: color
            strokeWidth: 2
        }
    }

    // Arrows
    Loader {
        sourceComponent: createArrow(centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2,
                                     centerCircle.x + centerCircle.width / 2 + 70, centerCircle.y + centerCircle.height / 2,
                                     activeXPlus ? "red" : "lightgrey")
    }
    Loader {
        sourceComponent: createArrow(centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2,
                                     centerCircle.x + centerCircle.width / 2 - 70, centerCircle.y + centerCircle.height / 2,
                                     activeXMinus ? "red" : "lightgrey")
    }
    Loader {
        sourceComponent: createArrow(centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2,
                                     centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2 - 70,
                                     activeZPlus ? "red" : "lightgrey")
    }
    Loader {
        sourceComponent: createArrow(centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2,
                                     centerCircle.x + centerCircle.width / 2, centerCircle.y + centerCircle.height / 2 + 70,
                                     activeZMinus ? "red" : "lightgrey")
    }

    // Labels for axis directions
    Text { text: "X+"; anchors.right: centerCircle.left; anchors.verticalCenter: centerCircle.verticalCenter }
    Text { text: "X-"; anchors.left: centerCircle.right; anchors.verticalCenter: centerCircle.verticalCenter }
    Text { text: "Z+"; anchors.bottom: centerCircle.top; anchors.horizontalCenter: centerCircle.horizontalCenter }
    Text { text: "Z-"; anchors.top: centerCircle.bottom; anchors.horizontalCenter: centerCircle.horizontalCenter }
}
