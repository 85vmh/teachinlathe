import QtQuick

QtObject {
    property var renderSegs: []
    property real scale: 1
    property var cx
    property var cy
    property color strokeColor: "#333333"
    property real lineWidth: 1
    property bool mirrorAcrossCenterline: false
    property bool showTransitions: true
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
        if (!showTransitions && joins.length > 2) joins = [joins[0], joins[joins.length - 1]]
        // an ID profile's start is the bore's mouth, not across the part - the
        // stock draws the face out from it to the skin - and its end goes on
        // into the stock as the new bore: nothing across it there
        if (String(profileType || "od").toLowerCase() === "id" && joins.length > 0) {
            var endZ = renderSegs[renderSegs.length - 1].z
            joins = joins.slice(1).filter(function(j) { return Math.abs(j.z - endZ) > 1e-6 })
        }
        ctx.beginPath()
        for (var k = 0; k < joins.length; k++) {
            ctx.moveTo(cx(joins[k].z), cy(joins[k].x))
            ctx.lineTo(cx(joins[k].z), cy(-joins[k].x))
        }
        ctx.stroke()
    }

    function _paintPath(ctx, mirrored) {
        ctx.beginPath()
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
        ctx.stroke()
    }
}
