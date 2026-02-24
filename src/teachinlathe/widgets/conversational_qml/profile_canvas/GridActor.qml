import QtQuick 2.15

QtObject {
    property real width: 0
    property real height: 0
    property real originX: 0
    property real originY: 0
    property real scale: 1
    property var cx
    property var cy
    property var stepsFn
    property color gridColor: "#e0e0e0"
    property real gridLineWidth: 0.5

    function paint(ctx) {
        var s = stepsFn()
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
            var x = cx(z)
            ctx.beginPath()
            ctx.moveTo(x, 0)
            ctx.lineTo(x, height)
            ctx.stroke()
        }
        for (var xw = x0; xw <= x1; xw += s.major) {
            var y = cy(xw)
            ctx.beginPath()
            ctx.moveTo(0, y)
            ctx.lineTo(width, y)
            ctx.stroke()
        }
    }
}
