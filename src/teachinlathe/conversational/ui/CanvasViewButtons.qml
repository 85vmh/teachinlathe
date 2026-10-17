// CanvasViewButtons.qml — the buttons laid over a ProfileCanvas's top-left
// corner: zoom in and out (the backplot's: held down, they repeat), fit to
// screen, and mirror, which draws the upper half above the centre line too
// or leaves only the lower one.
import QtQuick 2.15
import common 1.0
import theme 1.0
import "../../programs/ui" as Programs

Row {
    id: root

    property var  canvas: null           // the ProfileCanvas they act on
    property bool showMirror: true       // false where there is no profile to mirror

    anchors { top: parent.top; left: parent.left; topMargin: 24; leftMargin: 24 }
    spacing: Theme.spacing

    Programs.BackplotIconButton {
        iconSource: Images.url("zoom-in.svg")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 100
        onClicked: root.canvas.zoomIn()
    }
    Programs.BackplotIconButton {
        iconSource: Images.url("zoom-out.svg")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 100
        onClicked: root.canvas.zoomOut()
    }
    Programs.BackplotIconButton {
        iconSource: Images.url("zoom-fit.svg")
        onClicked: root.canvas.fitToScreen()
    }
    Programs.BackplotIconButton {
        visible: root.showMirror
        iconSource: Images.url("mirror.svg")
        active: root.canvas ? root.canvas.mirrorAcrossCenterline : false
        onClicked: root.canvas.mirrorAcrossCenterline = !root.canvas.mirrorAcrossCenterline
    }
}
