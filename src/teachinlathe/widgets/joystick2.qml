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

    // Function to create an arrow path
    function createArrowPath(xDir, yDir) {
        var path = Path {
            startX: centerCircle.x + centerCircle.width / 2
            startY: centerCircle.y + centerCircle.height / 2
            PathLine { x: startX + 70 * xDir; y: startY + 70 * yDir }
        }
        return path;
    }

    // Arrow paths
    PathView {
        width: parent.width
        height: parent.height
        path: createArrowPath(1, 0)  // X+
        delegate: PathDelegate { active: joystick.activeXPlus }
    }
    PathView {
        width: parent.width
        height: parent.height
        path: createArrowPath(-1, 0)  // X-
        delegate: PathDelegate { active: joystick.activeXMinus }
    }
    PathView {
        width: parent.width
        height: parent.height
        path: createArrowPath(0, -1)  // Z+
        delegate: PathDelegate { active: joystick.activeZPlus }
    }
    PathView {
        width: parent.width
        height: parent.height
        path: createArrowPath(0, 1)  // Z-
        delegate: PathDelegate { active: joystick.activeZMinus }
    }

    // Path delegate for drawing arrows
    Component {
        id: arrowDelegate
        Rectangle {
            width: 2
            height: 70
            color: active ? "red" : "lightgrey"
            Rectangle {
                width: 15
                height: 15
                rotation: 45
                color: parent.color
                anchors {
                    bottom: parent.top
                    bottomMargin: -7.5
                    horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }

    // Labels for axis directions
    Label { text: "X+"; anchors.right: centerCircle.left; anchors.verticalCenter: centerCircle.verticalCenter }
    Label { text: "X-"; anchors.left: centerCircle.right; anchors.verticalCenter: centerCircle.verticalCenter }
    Label { text: "Z+"; anchors.bottom: centerCircle.top; anchors.horizontalCenter: centerCircle.horizontalCenter }
    Label { text: "Z-"; anchors.top: centerCircle.bottom; anchors.horizontalCenter: centerCircle.horizontalCenter }
}
