import QtQuick
import theme
import tabs.tool_library.shapes

// The insert as it sits in the holder.
//
// The Z and X axes are fixed through the middle of the view, and the insert
// is placed with its cutting tip where they cross: changing the orientation
// or the angles turns the insert about that point, the axes stay put. Each
// angle is dimensioned as a drawing would: an extension line out of the
// insert's side, and an arrowed arc from its half of the Z axis to it. The
// insert is drawn over all of it.
//
// The scale is fixed by the view's size, not by the insert, so changing the
// insert size visibly changes the drawing.
Rectangle {
    id: root

    property var editor: null

    //: The furthest any catalogue insert reaches from its cutting tip (a
    //: VBMT 16 is about 32 mm tip to tip); the scale is chosen so it fits
    //: whichever way it points.
    readonly property real maxReachMm: 33
    readonly property real pxPerMm: Math.max(1, (Math.min(width, height) / 2 - Theme.margin) / maxReachMm)

    readonly property point centre: Qt.point(width / 2, height / 2)

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    // ── Axes and angle arcs, under the insert ───────────────────────────────
    Canvas {
        id: guides
        anchors.fill: parent
        antialiasing: true
        z: 0

        readonly property var directions: root.editor ? root.editor.edgeDirections : []
        onDirectionsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        //: Arrowhead length and half-width, in pixels.
        readonly property real arrowLength: 11
        readonly property real arrowHalfWidth: 4
        //: How far past the insert's side the arcs are drawn, and how far
        //: past the arcs the extension lines run, in pixels.
        readonly property real arcClearance: 24
        readonly property real extensionOvershoot: 14
        //: The arcs sit just outside the insert's sides, so a bigger insert
        //: has bigger arcs and longer extension lines.
        readonly property real arcRadius: (root.editor ? root.editor.edgeLengthMm : 0)
                                          * root.pxPerMm + arcClearance
        onArcRadiusChanged: requestPaint()

        function along(p, deg, len) {
            var r = deg * Math.PI / 180
            return { x: p.x + len * Math.cos(r), y: p.y - len * Math.sin(r) }
        }

        // A filled arrowhead with its point at `tip`, pointing at `deg`.
        function arrowHead(ctx, tip, deg) {
            var r = deg * Math.PI / 180
            var dx = Math.cos(r), dy = -Math.sin(r)
            var bx = tip.x - arrowLength * dx, by = tip.y - arrowLength * dy
            ctx.beginPath()
            ctx.moveTo(tip.x, tip.y)
            ctx.lineTo(bx - arrowHalfWidth * dy, by + arrowHalfWidth * dx)
            ctx.lineTo(bx + arrowHalfWidth * dy, by - arrowHalfWidth * dx)
            ctx.closePath()
            ctx.fill()
        }

        function arcPath(ctx, p, radius, fromDeg, toDeg) {
            ctx.beginPath()
            // Canvas angles run clockwise with y down: negate.
            ctx.arc(p.x, p.y, radius, -fromDeg * Math.PI / 180, -toDeg * Math.PI / 180, toDeg > fromDeg)
            ctx.stroke()
        }

        // An angle dimension from the ray at `from` to the ray at `to`,
        // the short way round: a thin extension line carrying the insert's
        // side on past its end for the arc to stop on, the arc, an
        // arrowhead at each end and the figure. When the arc is too short to hold both arrowheads they
        // go outside, pointing in, as a drawing would have them.
        function angleDimension(ctx, p, from, to, radius, label, color) {
            var sweep = ((to - from) % 360 + 540) % 360 - 180
            var sign = sweep >= 0 ? 1 : -1
            var end = from + sweep

            ctx.strokeStyle = Theme.foregroundMuted
            ctx.lineWidth = 1
            var reach = along(p, to, radius + extensionOvershoot)
            ctx.beginPath()
            ctx.moveTo(p.x, p.y); ctx.lineTo(reach.x, reach.y)
            ctx.stroke()

            ctx.strokeStyle = color
            ctx.fillStyle = color
            ctx.lineWidth = 2
            var start = along(p, from, radius), stop = along(p, end, radius)
            var arcLength = Math.abs(sweep) * Math.PI / 180 * radius
            if (arcLength >= 2.5 * arrowLength) {
                arcPath(ctx, p, radius, from, end)
                arrowHead(ctx, start, from - 90 * sign)
                arrowHead(ctx, stop, end + 90 * sign)
            } else {
                var tail = (2 * arrowLength) / radius * 180 / Math.PI
                arcPath(ctx, p, radius, Math.min(from, end) - tail, Math.max(from, end) + tail)
                arrowHead(ctx, start, from + 90 * sign)
                arrowHead(ctx, stop, end - 90 * sign)
            }

            var mid = along(p, from + sweep / 2, radius + 30)
            ctx.font = Theme.fontSmall + "px sans-serif"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillText(label, mid.x, mid.y)
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var p = root.centre

            ctx.strokeStyle = Theme.foregroundFaint
            ctx.lineWidth = 1
            ctx.setLineDash([6, 4])
            ctx.beginPath()
            ctx.moveTo(0, p.y); ctx.lineTo(width, p.y)
            ctx.moveTo(p.x, 0); ctx.lineTo(p.x, height)
            ctx.stroke()
            ctx.setLineDash([])

            if (!root.editor || directions.length !== 4)
                return
            var front = root.editor.frontAngle, back = root.editor.backAngle
            // Front and back lie either side of the corner and never
            // overlap, so they share a radius.
            angleDimension(ctx, p, directions[0], directions[1], arcRadius,
                           "F " + Number(front.toFixed(2)) + "°", Theme.accentStrong)
            angleDimension(ctx, p, directions[2], directions[3], arcRadius,
                           "B " + Number(back.toFixed(2)) + "°", Theme.warning)
        }
    }

    // ── The insert, its tip on the centre ───────────────────────────────────
    TurningInsertBase {
        id: insert
        z: 1
        width: root.width
        height: root.height

        // Where the tip lands with the insert centred, from the centre, in
        // pixels - TurningInsertBase's own arithmetic for its tip marker.
        // The insert is moved back by that much.
        readonly property point tipOffset: {
            var t = activeTip()
            var a = orientation * Math.PI / 180
            var k = pxPerMm
            return Qt.point(k * (t.x * Math.cos(a) - t.y * Math.sin(a)),
                            -k * (t.x * Math.sin(a) + t.y * Math.cos(a)))
        }
        x: -tipOffset.x
        y: -tipOffset.y

        shape: root.editor ? root.editor.shapeLetter : "C"
        insertType: root.editor ? root.editor.insertType : "T"
        ic: root.editor ? root.editor.ic : 6.35
        noseRadius: root.editor ? root.editor.noseRadiusMm : 0.4
        orientation: root.editor ? root.editor.insertRotation : 0
        pxPerMm: root.pxPerMm
        showToolTip: true
        openHole: true
        bodyColor: root.editor ? root.editor.insertBodyColor : "#e5a93b"
        edgeColor: root.editor ? root.editor.insertEdgeColor : "#674c1b"
    }

    Column {
        z: 2
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: Theme.spacingLarge
        spacing: 4

        Text {
            text: root.editor ? root.editor.isoCode : ""
            color: Theme.foreground
            font.pixelSize: Theme.fontTitle
            font.bold: true
        }
        Text {
            text: !root.editor ? ""
                  : root.editor.isRound ? "Round insert  ·  Q" + root.editor.orientation
                  : "Corner " + root.editor.cornerAngle + "°  ·  Q" + root.editor.orientation
            color: Theme.foregroundSubtle
            font.pixelSize: Theme.fontSmall
        }
    }
}
