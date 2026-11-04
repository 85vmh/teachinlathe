import QtQuick

QtObject {
    property var renderSegs: []
    property real scale: 1
    property var cx
    property var cy
    // Geometry: the solid's outline, which the lines across are kept within
    required property var geometry
    property color strokeColor: "#333333"
    property real lineWidth: 1
    property bool mirrorAcrossCenterline: false
    property bool showTransitions: true
    // without them, the lines at the profile's start and end too: none at all
    property bool showEnds: true
    // the part the profile bounds filled, from it to the centre line - on
    // both halves when they are drawn - in ``fillColor`` (paintFill)
    property bool fill: false
    property color fillColor: "#ffffff"
    property string profileType: "od"
    // An ID profile's last diameter, from where it ends back to Z0: both its
    // edges dashed, as Drilling draws the hole it drills, in the grey of the
    // bore past the profile (StockActor's boreColor)
    property color holeColor: "#aeb4bd"
    property var   holeDash: [6, 3]       // px on, px off
    property real  holeLineWidth: 1.5

    function paint(ctx) {
        if (!renderSegs || renderSegs.length === 0) return
        ctx.strokeStyle = strokeColor
        ctx.lineWidth = lineWidth
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        ctx.setLineDash([])

        _paintPath(ctx, false)
        if (mirrorAcrossCenterline) {
            _paintPath(ctx, true)
            _paintTransitions(ctx)
        }
        if (String(profileType || "od").toLowerCase() === "id")
            _paintHole(ctx)
    }

    function _paintHole(ctx) {
        var end = renderSegs[renderSegs.length - 1]
        var x = Math.abs(Number(end.x) || 0), z = Number(end.z) || 0
        if (x <= 0 || z >= 0) return
        ctx.save()
        ctx.strokeStyle = holeColor
        ctx.lineWidth = holeLineWidth
        ctx.setLineDash(holeDash)
        ctx.beginPath()
        ctx.moveTo(cx(z), cy(x)); ctx.lineTo(cx(0), cy(x))
        if (mirrorAcrossCenterline) {
            ctx.moveTo(cx(z), cy(-x)); ctx.lineTo(cx(0), cy(-x))
        }
        ctx.stroke()
        ctx.restore()
    }

    // With both halves drawn, every transition of the profile - where one
    // primitive or blend gives way to the next - is joined to its mirror
    // image by a line across the centre line. The first one is wherever the
    // path starts, which is where a start-point blend begins rather than the
    // start diameter itself. Without ``showTransitions``, only the first and
    // the last: where the profile starts and where it ends.
    function _paintTransitions(ctx) {
        var joins = []
        for (var i = 0; i < renderSegs.length; i++) {
            var s = renderSegs[i]
            if (s.interior || Math.abs(s.x) < 1e-9) continue
            joins.push(s)
        }
        if (!showTransitions && !showEnds) return
        if (!showTransitions && joins.length > 2) joins = [joins[0], joins[joins.length - 1]]
        // an ID profile's start is the bore's mouth, not across the part - the
        // stock draws the face out from it to the skin - and its end goes on
        // into the stock as the new bore: nothing across it there
        if (String(profileType || "od").toLowerCase() === "id" && joins.length > 0) {
            var endZ = renderSegs[renderSegs.length - 1].z
            joins = joins.slice(1).filter(function(j) { return Math.abs(j.z - endZ) > 1e-6 })
        }
        // each only as far as it crosses the part from its point on the
        // profile: not over the groove an undercut leaves, nor on past it
        // through the core under the groove
        var outline = geometry.solidOutline(renderSegs, cx, cy)
        ctx.beginPath()
        for (var k = 0; k < joins.length; k++) {
            var x = cx(joins[k].z)
            var spans = geometry.solidSpansFromEnds(outline, x, cy(joins[k].x), cy(-joins[k].x))
            for (var n = 0; n < spans.length; n++) {
                ctx.moveTo(x, spans[n][0])
                ctx.lineTo(x, spans[n][1])
            }
        }
        ctx.stroke()
    }

    // Under everything else of the profile: the part it bounds, filled down
    // to the centre line, as the stock's fill is under it.
    function paintFill(ctx) {
        if (!fill || !renderSegs || renderSegs.length === 0) return
        ctx.save()
        ctx.fillStyle = fillColor
        var halves = mirrorAcrossCenterline ? [false, true] : [false]
        for (var h = 0; h < halves.length; h++) {
            ctx.beginPath()
            var ends = _tracePath(ctx, halves[h])
            ctx.lineTo(cx(ends.endZ), cy(0))
            ctx.lineTo(cx(ends.startZ), cy(0))
            ctx.closePath()
            ctx.fill()
        }
        ctx.restore()
    }

    function _paintPath(ctx, mirrored) {
        ctx.beginPath()
        _tracePath(ctx, mirrored)
        ctx.stroke()
    }

    // The profile on the current path, mirrored over the centre line when
    // ``mirrored``: {startZ, endZ}, where it starts and ends.
    function _tracePath(ctx, mirrored) {
        var startZ = renderSegs.length > 0 ? renderSegs[0].z : 0
        var drawZ = 0
        var drawX = 0
        for (var i = 0; i < renderSegs.length; i++) {
            var s = renderSegs[i]
            if (s.type === "move") {
                drawZ = s.z
                drawX = mirrored ? -s.x : s.x
                ctx.moveTo(cx(drawZ), cy(drawX))
            } else if (s.type === "line") {
                ctx.lineTo(cx(s.z), cy(mirrored ? -s.x : s.x))
                drawZ = s.z
                drawX = mirrored ? -s.x : s.x
            } else if (s.type === "arc") {
                var ccx = cx(s.zc)
                var ccy = cy(mirrored ? -s.xc : s.xc)
                var sa = Math.atan2(cy(drawX) - ccy, cx(drawZ) - ccx)
                var cr = Math.sqrt(Math.pow(cx(drawZ) - ccx, 2) + Math.pow(cy(drawX) - ccy, 2))
                var endX = mirrored ? -s.x : s.x
                var ea = Math.atan2(cy(endX) - ccy, cx(s.z) - ccx)
                ctx.arc(ccx, ccy, cr, sa, ea, mirrored ? !s.anticlockwise : s.anticlockwise)
                drawZ = s.z
                drawX = endX
            }
        }
        return { startZ: startZ, endZ: drawZ }
    }
}
