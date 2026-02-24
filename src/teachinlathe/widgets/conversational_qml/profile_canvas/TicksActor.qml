import QtQuick 2.15

QtObject {
    property real width: 0
    property real height: 0
    property real originX: 0
    property real originY: 0
    property real scale: 1
    property var geometry
    property color tickStrokeColor: "#666666"
    property color tickFillColor: "#333333"
    property real tickLineWidth: 1
    property string tickFont: "10px sans-serif"

    function paint(ctx) {
        var s = geometry.steps(scale)
        ctx.strokeStyle = tickStrokeColor
        ctx.fillStyle = tickFillColor
        ctx.lineWidth = tickLineWidth
        ctx.setLineDash([])

        // Z — top + bottom edges
        ctx.textAlign = "center"
        var zWMin = -originX / scale
        var zWMax = (width - originX) / scale
        var zt = Math.floor(zWMin / s.minor) * s.minor
        for (var z = zt; z <= zWMax; z += s.minor) {
            var ts = geometry.tickStyle(z, s)
            var canvasX = originX + z * scale
            ctx.beginPath()
            ctx.moveTo(canvasX, 0)
            ctx.lineTo(canvasX, ts.len)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(canvasX, height)
            ctx.lineTo(canvasX, height - ts.len)
            ctx.stroke()
            if (ts.label) {
                ctx.font = tickFont
                ctx.textBaseline = "top"
                ctx.fillText(Math.round(z).toString(), canvasX, ts.len + 2)
                ctx.textBaseline = "bottom"
                ctx.fillText(Math.round(z).toString(), canvasX, height - ts.len - 2)
            }
        }

        // X — left + right edges
        var xWMin = -originY / scale
        var xWMax = (height - originY) / scale
        var xt = Math.floor(xWMin / s.minor) * s.minor
        for (var x = xt; x <= xWMax; x += s.minor) {
            var tsx = geometry.tickStyle(x, s)
            var canvasY = originY + x * scale
            ctx.beginPath()
            ctx.moveTo(0, canvasY)
            ctx.lineTo(tsx.len, canvasY)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(width, canvasY)
            ctx.lineTo(width - tsx.len, canvasY)
            ctx.stroke()
            if (tsx.label) {
                ctx.font = tickFont
                ctx.textAlign = "left"
                ctx.textBaseline = "middle"
                ctx.fillText(Math.round(x).toString(), tsx.len + 2, canvasY)
                ctx.textAlign = "right"
                ctx.fillText(Math.round(x).toString(), width - tsx.len - 2, canvasY)
            }
        }
    }
}