import QtQuick
import common

// The spindle direction a cutting tool is used with, as its M code's icon:
// M3 or M4, no button round it. `clockwise` is M3; null draws nothing.
// `on`: drawn green - the spindle turning that way (the manual spindle panel).
Image {
    id: root

    property var clockwise: null
    property bool on: false
    //: Its side, in pixels; the SVG is square.
    property real size: 36

    width: size
    height: size
    visible: clockwise !== null && clockwise !== undefined
    source: Images.url((clockwise === false ? "spindle_m4" : "spindle_m3") + (on ? "_on.svg" : ".svg"))
    sourceSize.width: size
    sourceSize.height: size
    fillMode: Image.PreserveAspectFit
    smooth: true
}
