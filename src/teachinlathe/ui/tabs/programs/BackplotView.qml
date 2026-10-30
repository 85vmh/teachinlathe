// BackplotView.qml — the backplot as every screen shows it: the plot on its
// panel, its gestures - pan, pinch, wheel, double tap to fit, three fingers
// to clear - and the buttons over it: zoom, fit, mirror, clear. What it
// shows is the machine, or a simulation (``simulation``): drawn the same.
import QtQuick
import TeachInLathe.Backplot
import theme
import common

Rectangle {
    id: root

    // A simulation to show instead of the machine (SimulateViewModel), set where
    // this is made; null, the machine.
    property var simulation: null
    // How far three fingers have to travel together, in px, for the swipe
    // that clears the plot.
    property int clearSwipeDistance: 80
    // the plot itself, for what it is told to show and do
    readonly property alias plot: backplot

    // The same panel an operation detail sits on: white with
    // a light border. The preview's own palette is tuned to
    // match - see _configure_for_lathe.
    color: Theme.surface
    border.color: Theme.outline
    border.width: Theme.hairline

    // Was an empty Item that Python mapped a QOpenGLWidget
    // onto, resyncing its geometry on every move and resize.
    // The preview renders into the scene graph now, so it is
    // just an item, and the controls over it are ordinary
    // buttons rather than QPushButtons positioned by hand.
    LatheBackplot {
        id: backplot
        simulation: root.simulation

        // three fingers swiped this far clear the plot
        clearSwipeDistance: root.clearSwipeDistance
        anchors.fill: parent
        anchors.margins: 1

        // Two fingers pinch-zoom, and pan as they move. One
        // finger still reaches the MouseArea inside; a second
        // one hands the gesture over here, cancelling that pan.
        PinchArea {
            anchors.fill: parent
            onPinchStarted: function (pinch) {
                backplot.pinchStarted(pinch.startCenter.x, pinch.startCenter.y)
            }
            onPinchUpdated: function (pinch) {
                backplot.pinchUpdated(pinch.scale, pinch.center.x, pinch.center.y)
            }
            onPinchFinished: backplot.pinchFinished()

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                onPressed: function (mouse) {
                    backplot.pressed(mouse.x, mouse.y)
                }
                onPositionChanged: function (mouse) {
                    if (mouse.buttons & Qt.MiddleButton)
                        backplot.zoomDragged(mouse.y)
                    else if (mouse.buttons & Qt.LeftButton)
                        backplot.panned(mouse.x, mouse.y)
                }
                onDoubleClicked: backplot.fitToWindow()
                onWheel: function (wheel) {
                    backplot.wheelZoom(wheel.angleDelta.y)
                }
            }
        }

        // As the profile canvases have them (Theme), over the
        // scale the plot draws round its own edge.
        Row {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: Theme.zoomInOutFitMirrorButtonMarginLeft
            anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
            spacing: Theme.zoomInOutFitMirrorButtonSpacing

            BackplotIconButton {
                implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                iconSource: Images.url("zoom-in.svg")
                autoRepeat: true
                autoRepeatDelay: 300
                autoRepeatInterval: 100
                onClicked: backplot.zoomIn()
            }
            BackplotIconButton {
                implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                iconSource: Images.url("zoom-out.svg")
                autoRepeat: true
                autoRepeatDelay: 300
                autoRepeatInterval: 100
                onClicked: backplot.zoomOut()
            }
            BackplotIconButton {
                implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                iconSource: Images.url("zoom-fit.svg")
                onClicked: backplot.fitToWindow()
            }
            // the material left so far, drawn above the centre
            // line; off when the app starts, then as left
            BackplotIconButton {
                implicitWidth: Theme.zoomInOutFitMirrorButtonSize
                implicitHeight: Theme.zoomInOutFitMirrorButtonSize
                iconSource: Images.url("mirror.svg")
                active: backplot.mirror
                onClicked: backplot.mirror = !backplot.mirror
            }
        }

        // Same button as the zoom row, so the two line up
        // across the top of the plot - as far in from the right
        // as the row is from the left; the tint is what says
        // it throws something away.
        BackplotIconButton {
            implicitWidth: Theme.zoomInOutFitMirrorButtonSize
            implicitHeight: Theme.zoomInOutFitMirrorButtonSize
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: Theme.zoomInOutFitMirrorButtonMarginLeft
            anchors.topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
            iconSource: Images.url("brush_out.svg")
            tint: Theme.danger
            borderTint: Theme.danger
            onClicked: backplot.clearPlot()
        }
    }
}
