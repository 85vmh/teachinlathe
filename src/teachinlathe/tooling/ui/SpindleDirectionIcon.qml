import QtQuick 2.15
import common 1.0

// The spindle direction a cutting tool is used with, as its M code's icon:
// M3 or M4, no button round it. `clockwise` is M3; null draws nothing.
Image {
    id: root

    property var clockwise: null
    //: Its side, in pixels; the SVG is square.
    property real size: 36

    width: size
    height: size
    visible: clockwise !== null && clockwise !== undefined
    source: Images.url(clockwise === false ? "spindle_m4.svg" : "spindle_m3.svg")
    sourceSize.width: size
    sourceSize.height: size
    fillMode: Image.PreserveAspectFit
    smooth: true
}
