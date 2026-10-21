import QtQuick 2.15
import theme 1.0
import "shapes"

// A turning tool's insert, small: drawn as the editor draws it - same
// shape, colours, open hole and turn - centred in a framed square. Every
// thumbnail draws at one scale, the one at which VBMT 16 fits the square at
// any turn, so a small insert looks small (and the few bigger ones are
// clipped by the frame). A short red cross marks the cutting tip, the tool's control point;
// the insert is drawn over it, and the cross stops at the frame.
Item {
    id: root

    property var view: null            // TurningToolView
    property real size: 50
    //: Whether the frame round it is drawn.
    property bool framed: true
    //: Length of each arm of the tip cross, from the tip, in pixels.
    property real crossArm: 10
    //: Space between the frame and the insert, in pixels.
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

    // A point of the insert's own frame, in mm, turned as it is drawn and
    // flipped to screen y - still in mm, about the insert's centre.
    function turned(p) {
        var a = insert.orientation * Math.PI / 180
        return Qt.point(p.x * Math.cos(a) - p.y * Math.sin(a),
                        -(p.x * Math.sin(a) + p.y * Math.cos(a)))
    }

    // The turned insert's extent, in mm, about its centre:
    // {left, right, top, bottom}. From the sharp outline - the nose radius
    // only ever takes a little off a corner.
    readonly property var bounds: {
        var o = insert.outline()
        if (o.round) {
            var r = insert.ic / 2
            return { left: -r, right: r, top: -r, bottom: r }
        }
        var b = { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }
        for (var i = 0; i < o.verts.length; i++) {
            var p = turned(o.verts[i])
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

    // The cutting tip, in pixels.
    readonly property point tip: {
        var t = turned(insert.activeTip())
        return Qt.point(centre.x + pxPerMm * t.x, centre.y + pxPerMm * t.y)
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

    TurningInsertBase {
        id: insert
        z: 1
        // TurningInsertBase draws about its own middle: move it so that is
        // where the centre was worked out to be.
        width: root.width
        height: root.height
        x: root.centre.x - width / 2
        y: root.centre.y - height / 2
        shape: root.view ? root.view.shapeLetter : "C"
        insertType: root.view ? root.view.insertType : "T"
        ic: root.view ? root.view.ic : 6.35
        noseRadius: root.view ? root.view.noseRadiusMm : 0.4
        orientation: root.view ? root.view.insertRotation : 0
        pxPerMm: root.pxPerMm
        openHole: true
        bodyColor: root.view ? root.view.insertBodyColor : "#e5a93b"
        edgeColor: root.view ? root.view.insertEdgeColor : "#674c1b"
    }
}
