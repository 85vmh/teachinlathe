import QtQuick 2.15

QtObject {
    property var renderSegs: []
    property real scale: 1
    property var cx
    property var cy
    property color strokeColor: "#333333"
    property real lineWidth: 1

    function paint(ctx) {
        if (!renderSegs || renderSegs.length === 0) return
        ctx.strokeStyle = strokeColor
        ctx.lineWidth = lineWidth
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        ctx.setLineDash([])

        ctx.beginPath()
        var drawZ = 0
        var drawX = 0
        for (var i = 0; i < renderSegs.length; i++) {
            var s = renderSegs[i]
            if (s.type === "move") {
                drawZ = s.z
                drawX = s.x
                ctx.moveTo(cx(drawZ), cy(drawX))
            } else if (s.type === "line") {
                ctx.lineTo(cx(s.z), cy(s.x))
                drawZ = s.z
                drawX = s.x
            } else if (s.type === "arc") {
                var ccx = cx(s.zc)
                var ccy = cy(s.xc)
                var cr = s.r * scale
                var sa = Math.atan2(cy(drawX) - ccy, cx(drawZ) - ccx)
                var ea = Math.atan2(cy(s.x)   - ccy, cx(s.z)   - ccx)
                ctx.arc(ccx, ccy, cr, sa, ea, s.anticlockwise)
                drawZ = s.z
                drawX = s.x
            }
        }
        ctx.stroke()
    }
}