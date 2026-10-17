import QtQuick 2.15
import "../../../tooling/ui/shapes/drill.js" as DrillShape

// The drill in the spindle, on the centre line: its point at ``z``, its body
// running on towards +Z, as the Tool Library draws it (tooling/ui/shapes).
QtObject {
    // {diameter, tip_angle, right_hand} as the backplot's tool_source
    // describes a drill, and ``z``, where its point is; null draws nothing
    property var   drill: null
    property var   cx: null
    property var   cy: null
    property real  scale: 1               // px per mm
    property color bodyColor: "#e5a93b"   // the backplot's insert colours
    property color edgeColor: "#674c1b"
    // where each peck ends, in mm: at each, the drill's point drawn as its
    // V - the tip at that Z, its arms back to the drill's edges at its point
    // angle - and along both edges, lines from ``peckFrom`` (Z Start) to the
    // last V's arms, all dotted in ``peckColor``
    property var   peckZs: []
    property var   peckFrom: null
    property color peckColor: "#2e7d32"
    property var   peckDash: [2, 3]       // px on, px off
    property real  peckLineWidth: 1.5

    function _shape() {
        return {
            diameter: Number(drill.diameter) || 0,
            tipAngle: drill.tip_angle !== undefined ? Number(drill.tip_angle) : 118,
            rightHand: drill.right_hand !== false,
            helixAngle: 30, helixLineWidth: 1, helixGapPx: 3,
            fluteLengthD: 5, shankLengthD: 2, length: 0,
            bodyColor: bodyColor, edgeColor: edgeColor,
            pxPerMm: scale, tipX: cx(Number(drill.z) || 0), tipY: cy(0)
        }
    }

    // How far the drill reaches past its point, in mm.
    function length() {
        if (!drill || !(Number(drill.diameter) > 0)) return 0
        return DrillShape.lengths({ diameter: Number(drill.diameter),
                                    tipAngle: drill.tip_angle !== undefined ? Number(drill.tip_angle) : 118,
                                    fluteLengthD: 5, shankLengthD: 2, length: 0 }).total
    }

    function paint(ctx) {
        if (!drill || !cx || !cy || !(Number(drill.diameter) > 0)) return
        _paintPecks(ctx)
        DrillShape.paint(ctx, _shape())
    }

    function _paintPecks(ctx) {
        if (!peckZs || peckZs.length === 0) return
        var d = Number(drill.diameter)
        var point = DrillShape.lengths({ diameter: d,
                                         tipAngle: drill.tip_angle !== undefined ? Number(drill.tip_angle) : 118,
                                         fluteLengthD: 5, shankLengthD: 2, length: 0 }).point
        ctx.save()
        ctx.setLineDash(peckDash)
        ctx.strokeStyle = peckColor
        ctx.lineWidth = peckLineWidth
        ctx.lineJoin = "round"
        ctx.beginPath()
        var zMin = Infinity, zMax = -Infinity
        for (var i = 0; i < peckZs.length; i++) {
            var z = Number(peckZs[i])
            zMin = Math.min(zMin, z)
            zMax = Math.max(zMax, z)
            ctx.moveTo(cx(z + point), cy(-d))
            ctx.lineTo(cx(z), cy(0))
            ctx.lineTo(cx(z + point), cy(d))
        }
        var from = peckFrom !== null && peckFrom !== undefined ? Number(peckFrom) : zMax + point
        if (from > zMin + point) {
            ctx.moveTo(cx(from), cy(-d)); ctx.lineTo(cx(zMin + point), cy(-d))
            ctx.moveTo(cx(from), cy(d));  ctx.lineTo(cx(zMin + point), cy(d))
        }
        ctx.stroke()
        ctx.restore()
    }
}
