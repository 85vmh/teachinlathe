import QtQuick 2.15
import theme 1.0
import "../tool_shapes"

// A reamer, small, as DrillThumbnail draws a drill: InsertThumbnail's
// frame and red cross, the cross on the middle of the reamer's end. It
// draws at the scale every insert thumbnail does - the one at which VBMT 16
// fits the square - so a reamer's diameter shows beside the inserts at its
// size. It lies along the middle, pointing left as it does at orientation
// 7, and runs on to the frame.
Item {
    id: root

    property var view: null            // ReamingToolView
    property real size: 50
    //: Whether the frame round it is drawn.
    property bool framed: true
    //: Length of each arm of the tip cross, from the tip, in pixels.
    property real crossArm: 10
    //: Space between the frame and the reference insert, in pixels; the
    //: reamer's end is set in from the left by as much.
    property real padding: 5

    width: size
    height: size
    // The reamer runs on past the frame.
    clip: true

    Rectangle {
        anchors.fill: parent
        z: 2
        visible: root.framed
        color: "transparent"
        radius: Theme.radiusSmall
        border.width: Theme.hairline
        border.color: Theme.outline
    }

    readonly property real pxPerMm: (size - 2 * padding)
                                    / Math.max(2 * (view ? view.catalogReachMm : 16), 0.001)
    readonly property point tip: Qt.point(padding, height / 2)

    Canvas {
        id: cross
        // Bigger than the square: the cross reaches past it. Under the
        // reamer, as the insert thumbnails have it.
        x: -root.crossArm; y: -root.crossArm
        width: root.width + 2 * root.crossArm
        height: root.height + 2 * root.crossArm
        z: 0
        readonly property point at: Qt.point(root.tip.x + root.crossArm, root.tip.y + root.crossArm)
        onAtChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = Theme.redHighlight
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(at.x - root.crossArm, at.y); ctx.lineTo(at.x + root.crossArm, at.y)
            ctx.moveTo(at.x, at.y - root.crossArm); ctx.lineTo(at.x, at.y + root.crossArm)
            ctx.stroke()
        }
    }

    Reamer {
        z: 1
        width: implicitWidth
        height: implicitHeight
        x: root.tip.x - tipPoint.x
        y: root.tip.y - tipPoint.y
        diameter: root.view ? root.view.diameter : 10
        helixAngle: root.view ? root.view.helixAngle : 10
        pxPerMm: root.pxPerMm
        // From the end to the frame.
        length: Math.max(1, (root.width - root.tip.x) / root.pxPerMm)
        bodyColor: root.view ? root.view.bodyColor : "#e5a93b"
        edgeColor: root.view ? root.view.edgeColor : "#674c1b"
    }
}
