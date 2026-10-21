import QtQuick
import "arrow.js" as Arrow

// The profile offset by stock to leave - what roughing stops at - on both
// halves, the stock it leaves on the finished profile filled half
// transparent, and an arrow from the upper half to the box that holds the
// values.
QtObject {
    property var   offset: []            // [{x, z}], X as diameter
    property var   profile: []           // the finished profile, likewise
    property real  fillAlpha: 0.5
    property var   cx: null
    property var   cy: null
    property bool  mirrorAcrossCenterline: true
    property var   arrowToRect: null     // the stock to leave box, in canvas px
    property color color: "#ef6c00"
    property real  lineWidth: 1

    function paint(ctx) {
        if (!cx || !cy || !offset || offset.length < 2) return
        _fillHalf(ctx, 1)
        if (mirrorAcrossCenterline) _fillHalf(ctx, -1)

        ctx.save()
        ctx.setLineDash([])
        ctx.lineJoin = "round"
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        _paintHalf(ctx, 1)
        if (mirrorAcrossCenterline) _paintHalf(ctx, -1)
        ctx.restore()

        if (!arrowToRect) return
        // from the offset point nearest where the arrow ends, on the upper
        // half when drawn
        var sign = mirrorAcrossCenterline ? -1 : 1
        var to = Arrow.anchorOf(arrowToRect)
        var best = null, bestDistance = Infinity
        for (var i = 0; i < offset.length; i++) {
            var px = cx(offset[i].z), py = cy(sign * offset[i].x)
            var d = Math.pow(to.x - px, 2) + Math.pow(to.y - py, 2)
            if (d < bestDistance) { bestDistance = d; best = { x: px, y: py } }
        }
        if (best) Arrow.paintToBox(ctx, best.x, best.y, arrowToRect, color, 0)
    }

    // Between the offset and the profile: along the offset, then back along
    // the profile, so their ends join each other directly.
    function _fillHalf(ctx, sign) {
        if (!profile || profile.length < 2) return
        ctx.save()
        ctx.globalAlpha = fillAlpha
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.moveTo(cx(offset[0].z), cy(sign * offset[0].x))
        for (var i = 1; i < offset.length; i++)
            ctx.lineTo(cx(offset[i].z), cy(sign * offset[i].x))
        for (var j = profile.length - 1; j >= 0; j--)
            ctx.lineTo(cx(profile[j].z), cy(sign * profile[j].x))
        ctx.closePath()
        ctx.fill()
        ctx.restore()
    }

    function _paintHalf(ctx, sign) {
        ctx.beginPath()
        ctx.moveTo(cx(offset[0].z), cy(sign * offset[0].x))
        for (var i = 1; i < offset.length; i++)
            ctx.lineTo(cx(offset[i].z), cy(sign * offset[i].x))
        ctx.stroke()
    }
}
