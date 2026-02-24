import QtQuick 2.15

QtObject {
    property real originX: 0
    property real originY: 0
    property real maxZ: 0
    property real maxX: 0
    property real circleR: 0
    property var cx
    property var cy
    property color zAxisColor: "#2E7D32"
    property color xAxisColor: "#1565C0"
    property real axisLineWidth: 1.5
    property string axisFont: "bold 11px sans-serif"

    function paint(ctx) {
        var aw = 9
        var ah = aw * 0.4
        var cr = circleR

        // Z+ — green
        var zTipX = cx(maxZ + 10)
        var zShaft = zTipX - aw
        var zStart = originX + cr + 1
        ctx.strokeStyle = zAxisColor
        ctx.fillStyle = zAxisColor
        ctx.lineWidth = axisLineWidth
        ctx.setLineDash([])
        if (zShaft > zStart) {
            ctx.beginPath()
            ctx.moveTo(zStart, originY)
            ctx.lineTo(zShaft, originY)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(zTipX,  originY)
        ctx.lineTo(zShaft, originY - ah)
        ctx.lineTo(zShaft, originY + ah)
        ctx.closePath()
        ctx.fill()
        ctx.font = axisFont
        ctx.textAlign = "left"
        ctx.textBaseline = "bottom"
        ctx.fillText("Z+", zTipX + 4, originY - 2)

        // X+ — blue
        var xTipY = cy(maxX + 10)
        var xShaft = xTipY - aw
        var xStart = originY + cr + 1
        ctx.strokeStyle = xAxisColor
        ctx.fillStyle = xAxisColor
        if (xShaft > xStart) {
            ctx.beginPath()
            ctx.moveTo(originX, xStart)
            ctx.lineTo(originX, xShaft)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(originX,      xTipY)
        ctx.lineTo(originX - ah, xShaft)
        ctx.lineTo(originX + ah, xShaft)
        ctx.closePath()
        ctx.fill()
        ctx.font = axisFont
        ctx.textAlign = "left"
        ctx.textBaseline = "top"
        ctx.fillText("X+", originX + 4, xTipY + 2)
    }
}
