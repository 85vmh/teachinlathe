import QtQuick 2.15
import "../../../tooling/ui/shapes/drill.js" as DrillShape
import "../../../tooling/ui/shapes/tap.js" as TapShape

// The drill or tap in the spindle, on the centre line: its point at ``z``,
// its body running on towards +Z, drawn by the Tool Library's own drawing
// (tooling/ui/shapes) - one drawing of each, wherever it shows.
QtObject {
    // {kind: "drill" | "tap", diameter, tip_angle, right_hand, pitch} as the
    // backplot's tool_source describes it, and ``z``, where its point is;
    // null, or any other kind, draws nothing
    property var   tool: null
    property var   cx: null
    property var   cy: null
    property real  scale: 1               // px per mm
    property color bodyColor: "#e5a93b"   // the backplot's insert colours
    property color edgeColor: "#674c1b"
    // where each peck ends, in mm: at each, solid, a drill's point as its V
    // - the tip at that Z, back to its edges - a tap's a straight line across
    // its diameter; and along both edges, dashed, lines from ``peckFrom``
    // (Z Start) to the last one; all in ``peckColor``
    property var   peckZs: []
    property var   peckFrom: null
    property color peckColor: "#2e7d32"
    property var   peckDash: [6, 3]       // px on, px off
    property real  peckLineWidth: 1.5

    function _kind() {
        if (!tool || !(Number(tool.diameter) > 0)) return ""
        if (tool.kind === "drill") return "drill"
        if (tool.kind === "tap" && Number(tool.pitch) > 0) return "tap"
        return ""
    }

    function _drill() {
        return {
            diameter: Number(tool.diameter),
            tipAngle: tool.tip_angle !== undefined ? Number(tool.tip_angle) : 118,
            rightHand: tool.right_hand !== false,
            helixAngle: 30, helixLineWidth: 1, helixGapPx: 3,
            fluteLengthD: 5, shankLengthD: 2, length: 0,
            bodyColor: bodyColor, edgeColor: edgeColor,
            pxPerMm: scale, tipX: cx(Number(tool.z) || 0), tipY: cy(0)
        }
    }

    function _tap() {
        return {
            diameter: Number(tool.diameter), pitch: Number(tool.pitch),
            rightHand: tool.right_hand !== false,
            leadThreads: 3, threadLengthD: 2, minThreads: 8, shankRatio: 0.8,
            shankLengthD: 2, helixLineWidth: 1, length: 0,
            bodyColor: bodyColor, edgeColor: edgeColor,
            pxPerMm: scale, tipX: cx(Number(tool.z) || 0), tipY: cy(0)
        }
    }

    // How far the tool reaches past its point, in mm.
    function length() {
        var kind = _kind()
        if (kind === "drill") return DrillShape.lengths(_drill()).total
        if (kind === "tap") return TapShape.geometry(_tap()).total
        return 0
    }

    // How far back from a peck's Z its mark reaches the tool's edges, in mm:
    // a drill's point; a tap's mark is straight across, 0.
    function peckBack() {
        return _kind() === "drill" ? DrillShape.lengths(_drill()).point : 0
    }

    function paint(ctx) {
        if (!cx || !cy) return
        var kind = _kind()
        if (!kind) return
        _paintPecks(ctx)
        if (kind === "drill") DrillShape.paint(ctx, _drill())
        else TapShape.paint(ctx, _tap())
    }

    function _paintPecks(ctx) {
        if (!peckZs || peckZs.length === 0) return
        var d = Number(tool.diameter)
        var back = peckBack()
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = peckColor
        ctx.lineWidth = peckLineWidth
        ctx.lineJoin = "round"
        ctx.beginPath()
        var zMin = Infinity, zMax = -Infinity
        for (var i = 0; i < peckZs.length; i++) {
            var z = Number(peckZs[i])
            zMin = Math.min(zMin, z)
            zMax = Math.max(zMax, z)
            ctx.moveTo(cx(z + back), cy(-d))
            ctx.lineTo(cx(z), cy(0))
            ctx.lineTo(cx(z + back), cy(d))
        }
        ctx.stroke()
        ctx.setLineDash(peckDash)
        ctx.beginPath()
        var from = peckFrom !== null && peckFrom !== undefined ? Number(peckFrom) : zMax + back
        if (from > zMin + back) {
            ctx.moveTo(cx(from), cy(-d)); ctx.lineTo(cx(zMin + back), cy(-d))
            ctx.moveTo(cx(from), cy(d));  ctx.lineTo(cx(zMin + back), cy(d))
        }
        ctx.stroke()
        ctx.restore()
    }
}
