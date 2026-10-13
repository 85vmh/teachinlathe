import QtQuick 2.15
import theme 1.0
import "../tool_shapes"

// A threading tool's insert, small: InsertThumbnail's frame and red tip
// cross around a ThreadingInsert. It draws at the scale every turning
// thumbnail does - the one at which VBMT 16 fits the square - so a 16ER
// sits beside a CCMT 06 at their true sizes; it is centred on its outline.
Item {
    id: root

    property var view: null            // ThreadingToolView
    property real size: 50
    //: Whether the frame round it is drawn.
    property bool framed: true
    //: Length of each arm of the tip cross, from the tip, in pixels.
    property real crossArm: 10
    //: Space between the frame and the reference insert, in pixels.
    property real padding: 5

    width: size
    height: size
    // The tip is on the insert's edge, so its cross reaches past the frame.
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

    // A point of the insert's own frame, in mm, mirrored and turned as it
    // is drawn and flipped to screen y - still in mm, about its centre.
    function turned(p) {
        var x = insert.hand === "L" ? -p.x : p.x
        var a = insert.orientation * Math.PI / 180
        return Qt.point(x * Math.cos(a) - p.y * Math.sin(a),
                        -(x * Math.sin(a) + p.y * Math.cos(a)))
    }

    // The turned insert's extent, in mm, about its centre: the triangle it
    // is cut from, corners at the inscribed circle's diameter. Its
    // reference side is the vertical one, at x = -IC/2.
    readonly property var bounds: {
        var ic = insert.ic, h = ic * Math.sqrt(3) / 2
        var verts = [Qt.point(ic, 0), Qt.point(-ic / 2, h), Qt.point(-ic / 2, -h)]
        var b = { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }
        for (var i = 0; i < verts.length; i++) {
            var p = turned(verts[i])
            b.left = Math.min(b.left, p.x); b.right = Math.max(b.right, p.x)
            b.top = Math.min(b.top, p.y); b.bottom = Math.max(b.bottom, p.y)
        }
        return b
    }
    readonly property real pxPerMm: (size - 2 * padding)
                                    / Math.max(2 * (view ? view.catalogReachMm : insert.ic), 0.001)
    // Where the insert's centre goes so the turned outline is centred.
    readonly property point centre: Qt.point(
        width / 2 - pxPerMm * (bounds.left + bounds.right) / 2,
        height / 2 - pxPerMm * (bounds.top + bounds.bottom) / 2)

    // The tooth's tip, in pixels. activeTip() is already mirrored.
    readonly property point tip: {
        var t = insert.activeTip()
        var a = insert.orientation * Math.PI / 180
        return Qt.point(centre.x + pxPerMm * (t.x * Math.cos(a) - t.y * Math.sin(a)),
                        centre.y - pxPerMm * (t.x * Math.sin(a) + t.y * Math.cos(a)))
    }

    Canvas {
        id: cross
        // Bigger than the square: the tip is on its edge, and its cross
        // reaches past it.
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

    ThreadingInsert {
        id: insert
        z: 1
        // ThreadingInsert draws about its own middle: move it so that is
        // where the centre was worked out to be.
        width: root.width
        height: root.height
        x: root.centre.x - width / 2
        y: root.centre.y - height / 2
        insertSize: root.view ? root.view.sizeCode : "16"
        pitch: root.view ? root.view.pitch : 1.5
        hand: root.view ? root.view.drawnHand : "R"
        orientation: root.view ? root.view.insertRotation : 0
        pxPerMm: root.pxPerMm
        bodyColor: root.view ? root.view.insertBodyColor : "#e5a93b"
        edgeColor: root.view ? root.view.insertEdgeColor : "#674c1b"
        // ThreadingInsert fills its hole; the turning thumbnails cut theirs
        // open. The card's colour reads the same.
        holeColor: Theme.surface
    }
}
