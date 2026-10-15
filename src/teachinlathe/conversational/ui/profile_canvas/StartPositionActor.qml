import QtQuick 2.15
import "arrow.js" as Arrow

// Where roughing starts (X Start / Z Start): a small target at the start
// point, on the lower half, and an arrow from it to the box holding the
// values.
QtObject {
    property var   position: null        // {x: diameter, z}; null draws nothing
    property var   cx: null              // world Z -> canvas x
    property var   cy: null              // world X (diameter) -> canvas y
    property var   arrowToRect: null     // the box the arrow points to, in canvas px; null draws no arrow
    property color color: "#1565c0"
    property real  targetRadius: 7       // px
    property real  lineWidth: 1.5

    function paint(ctx) {
        if (!position || !cx || !cy) return
        var tx = cx(+position.z || 0)
        var ty = cy(Math.abs(+position.x || 0))

        ctx.save()
        ctx.setLineDash([])
        _paintTarget(ctx, tx, ty)
        if (arrowToRect) {
            Arrow.paintToBox(ctx, tx, ty, arrowToRect, color, targetRadius * 1.6)
        }
        ctx.restore()
    }

    function _paintTarget(ctx, px, py) {
        var r = targetRadius
        ctx.globalAlpha = 0.3
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(px, py, r, 0, 2 * Math.PI, false)
        ctx.fill()
        ctx.globalAlpha = 1.0
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(px - r * 1.6, py)
        ctx.lineTo(px + r * 1.6, py)
        ctx.moveTo(px, py - r * 1.6)
        ctx.lineTo(px, py + r * 1.6)
        ctx.stroke()
    }
}
