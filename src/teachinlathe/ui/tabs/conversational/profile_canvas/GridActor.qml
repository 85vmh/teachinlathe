import QtQuick
import "axisbreak.js" as AxisBreak

QtObject {
    property real width: 0
    property real height: 0
    property real originX: 0
    property real originY: 0
    property real scale: 1
    property var geometry
    property color gridColor: "#e0e0e0"
    property real gridLineWidth: 0.5
    // a stretch of Z left out of the drawing; see axisbreak.js
    property var axisBreak: null

    function paint(ctx) {
        var sz = geometry.steps(scale)
        var sx = geometry.steps(scale / 2)
        ctx.strokeStyle = gridColor
        ctx.lineWidth = gridLineWidth
        ctx.setLineDash([])

        var zWMin = -originX / scale
        var zWMax = (width - originX) / scale
        // at the ticks' Z: none in a left-out stretch, the real Z past it
        var zMarks = AxisBreak.marks(zWMin, zWMax, sz.major, axisBreak)
        for (var i = 0; i < zMarks.length; i++) {
            var canvasX = originX + zMarks[i].drawn * scale
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