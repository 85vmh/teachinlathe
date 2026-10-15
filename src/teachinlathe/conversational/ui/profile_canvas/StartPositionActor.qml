import QtQuick 2.15
import "arrow.js" as Arrow

// Where roughing starts (X Start / Z Start): a transparent rectangle from
// Z Start to the profile's smallest Z, out to X Start on both sides of the
// centre line, with a small target on its lower corner at the start point and
// an arrow from that target to the box holding the values.
QtObject {
    property var   position: null        // {x: diameter, z}; null draws nothing
    property real  zEnd: 0               // the profile's smallest Z
    property var   cx: null              // world Z -> canvas x
    property var   cy: null              // world X (diameter) -> canvas y
    property bool  mirrorAcrossCenterline: true
    property var   arrowToRect: null     // the box the arrow points to, in canvas px; null draws no arrow
    property color color: "#1565c0"
    property real  fillAlpha: 0.12
    property real  targetRadius: 7       // px
    property real  lineWidth: 1.5

    function paint(ctx) {
        if (!position || !cx || !cy) return
        var x = Math.abs(+position.x || 0)
        var left   = cx(Math.min(zEnd, +position.z || 0))
        var right  = cx(Math.max(zEnd, +position.z || 0))
        var top    = mirrorAcrossCenterline ? cy(-x) : cy(0)
        var bottom = cy(x)
        var tx = cx(+position.z || 0)
        var ty = bottom

        ctx.save()
        ctx.globalAlpha = fillAlpha
        ctx.fillStyle = color
        ctx.fillRect(left, top, right - left, bottom - top)
        ctx.globalAlpha = 1.0
        ctx.strokeStyle = color
        ctx.lineWidth = 1
        ctx.setLineDash([6, 4])
        ctx.strokeRect(left, top, right - left, bottom - top)
        ctx.setLineDash([])

        _paintTarget(ctx, tx, ty)
        if (arrowToRect) {
            var to = Arrow.nearestOnRect(arrowToRect, tx, ty)
            Arrow.paint(ctx, tx, ty, to.x, to.y, color, targetRadius * 1.6)
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
