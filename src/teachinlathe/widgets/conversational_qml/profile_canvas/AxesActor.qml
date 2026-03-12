import QtQuick 2.15

QtObject {
    property real originX: 0
    property real originY: 0
    property real height:  0

    // ── Configurable sizes (pixels, zoom-independent) ─────────────────────
    property real axisLength:    60    // shaft + head, origin to tip
    property real arrowHeadLen:  14    // arrowhead depth (along axis)
    property real arrowHeadWidth: 7    // arrowhead half-width (perpendicular)

    property color zAxisColor:    "#2E7D32"
    property color xAxisColor:    "#1565C0"
    property color zeroLineColor: "#999999"
    property real axisLineWidth:  1.5
    property real zeroLineWidth:  0.8
    property string axisFont:     "bold 11px sans-serif"
    property var zeroDashPattern: [8, 5, 2, 5]   // long dash · dot · long dash …
    property real circleR: 0

    function paint(ctx) {
        var ahl = arrowHeadLen
        var ahw = arrowHeadWidth

        // ── Z=0 dashed vertical line (full canvas height) ─────────────────
        ctx.strokeStyle = zeroLineColor
        ctx.lineWidth   = zeroLineWidth
        ctx.setLineDash(zeroDashPattern)
        ctx.beginPath()
        ctx.moveTo(originX, 0)
        ctx.lineTo(originX, height)
        ctx.stroke()
        ctx.setLineDash([])

        // ── Z+ arrow — green, fixed pixel length, rightward from origin ───
        var zTipX  = originX + axisLength
        var zShaft = zTipX - ahl
        var zStart = originX + circleR + 1

        ctx.strokeStyle = zAxisColor
        ctx.fillStyle   = zAxisColor
        ctx.lineWidth   = axisLineWidth
        if (zShaft > zStart) {
            ctx.beginPath()
            ctx.moveTo(zStart, originY)
            ctx.lineTo(zShaft, originY)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(zTipX,  originY)
        ctx.lineTo(zShaft, originY - ahw)
        ctx.lineTo(zShaft, originY + ahw)
        ctx.closePath()
        ctx.fill()

        ctx.font         = axisFont
        ctx.textAlign    = "center"
        ctx.textBaseline = "bottom"
        ctx.fillText("Z+", zTipX - ahl / 2, originY - ahw - 2)

        // ── X+ arrow — blue, fixed pixel length, downward from origin ─────
        var xTipY  = originY + axisLength
        var xShaft = xTipY - ahl
        var xStart = originY + circleR + 1

        ctx.strokeStyle = xAxisColor
        ctx.fillStyle   = xAxisColor
        if (xShaft > xStart) {
            ctx.beginPath()
            ctx.moveTo(originX, xStart)
            ctx.lineTo(originX, xShaft)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(originX,      xTipY)
        ctx.lineTo(originX - ahw, xShaft)
        ctx.lineTo(originX + ahw, xShaft)
        ctx.closePath()
        ctx.fill()

        ctx.font         = axisFont
        ctx.textAlign    = "right"
        ctx.textBaseline = "middle"
        ctx.fillText("X+", originX - ahw - 4, xTipY - ahl / 2)
    }
}