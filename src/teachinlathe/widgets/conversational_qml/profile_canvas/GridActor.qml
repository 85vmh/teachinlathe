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
        var sz = geometry.steps(scale)
        var sx = geometry.steps(scale / 2)
        ctx.strokeStyle = gridColor
        ctx.lineWidth = gridLineWidth
        ctx.setLineDash([])

        var zWMin = -originX / scale
        var zWMax = (width - originX) / scale
        var z0 = Math.floor(zWMin / sz.major) * sz.major
        var z1 = Math.ceil(zWMax / sz.major) * sz.major

        for (var z = z0; z <= z1; z += sz.major) {
            var canvasX = originX + z * scale
            ctx.beginPath()
            ctx.moveTo(canvasX, 0)
            ctx.lineTo(canvasX, height)
            ctx.stroke()
        }

        // X gridlines: data is diameter, display is radius (divide by 2)
        var xDiaMin = -originY * 2 / scale
        var xDiaMax = (height - originY) * 2 / scale
        var x0 = Math.floor(xDiaMin / sx.major) * sx.major
        var x1 = Math.ceil(xDiaMax / sx.major) * sx.major
        for (var xw = x0; xw <= x1; xw += sx.major) {
            var canvasY = originY + (xw / 2) * scale
            ctx.beginPath()
            ctx.moveTo(0, canvasY)
            ctx.lineTo(width, canvasY)
            ctx.stroke()
        }
    }
}