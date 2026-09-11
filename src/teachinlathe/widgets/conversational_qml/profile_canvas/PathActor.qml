import QtQuick 2.15

QtObject {
    property var renderSegs: []
    property real scale: 1
    property var cx
    property var cy
    property color strokeColor: "#333333"
    property real lineWidth: 1
    property bool mirrorAcrossCenterline: false

    function paint(ctx) {
        if (!renderSegs || renderSegs.length === 0) return
        ctx.strokeStyle = strokeColor
        ctx.lineWidth = lineWidth
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        ctx.setLineDash([])

        _paintPath(ctx, false)
        if (mirrorAcrossCenterline)
            _paintPath(ctx, true)
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
