import QtQuick 2.15

QtObject {
    property real width: 0
    property real height: 0
    property real originX: 0
    property real originY: 0
    property real scale: 1
    property var geometry
    property color gridColor: "#e0e0e0"
    property real gridLineWidth: 0.5

    function paint(ctx) {
        var s = geometry.steps(scale)
        ctx.strokeStyle = gridColor
        ctx.lineWidth = gridLineWidth
        ctx.setLineDash([])

        var zWMin = -originX / scale
        var zWMax = (width - originX) / scale
        var xWMin = -originY / scale
        var xWMax = (height - originY) / scale
        var z0 = Math.floor(zWMin / s.major) * s.major
        var z1 = Math.ceil(zWMax / s.major) * s.major
        var x0 = Math.floor(xWMin / s.major) * s.major
        var x1 = Math.ceil(xWMax / s.major) * s.major

        for (var z = z0; z <= z1; z += s.major) {
            var canvasX = originX + z * scale
            ctx.beginPath()
            ctx.moveTo(canvasX, 0)
            ctx.lineTo(canvasX, height)
            ctx.stroke()
        }
        for (var xw = x0; xw <= x1; xw += s.major) {
            var canvasY = originY + xw * scale
            ctx.beginPath()
            ctx.moveTo(0, canvasY)
            ctx.lineTo(width, canvasY)
            ctx.stroke()
        }
    }
}