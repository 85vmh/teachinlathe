import QtQuick 2.0
import QtQuick.Window 2.0

Window {
    visible: true
    width: 400
    height: 400
    title: "Joystick Demo"

    Joystick {
        anchors.centerIn: parent
        width: 200
        height: 200
        // Set these properties to true to see the active state
        // activeXPlus: true
        // activeXMinus: true
        // activeZPlus: true
        // activeZMinus: true
    }
}
