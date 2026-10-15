import QtQuick 2.15
import "arrow.js" as Arrow

// Dimensions, as on a drawing: a short extension line at each end and a
// double-headed arrow between them, each in its own colour, with a leader to
// the box that holds its value. The leader leaves the arrow a quarter of the
// way from its ``from`` end - on a diameter from -D, 3/4 of the way up (from
// +D, 3/4 of the way down); on a length from Z0, 3/4 of the way from its Z-
// end - as a short line (right for a diameter; away from the part for a
// length), then an arrow to the box as every canvas arrow ends: see
// Arrow.paintToBox.
//
// Each dimension is one of
//   {axis: "x", from, to, z, offset, color, arrowToRect}
//       a diameter: from X ``from`` to X ``to`` (diameters, -D to D spans
//       both halves), drawn ``offset`` px to the right of Z ``z``; with
//       ``offset`` 0, at Z ``z`` itself, between the lines it measures,
//       with no extension lines
//   {axis: "z", from, to, x, offset, color, arrowToRect}
//       a length: from Z ``from`` to Z ``to``, drawn ``offset`` px below
//       diameter ``x`` - above it when ``offset`` is negative, as for the
//       upper half's -D
// arrowToRect is the box, in canvas px, or null for no leader.
QtObject {
    property var  dimensions: []
    property var  cx: null
    property var  cy: null
    property real lineWidth: 1
    property real gap: 4             // px between the part and an extension line
    property real overshoot: 6       // px an extension line runs past the arrow
    property real headLength: 10     // px
    property real headHalfWidth: 3.5 // px
    property real leaderStub: 16     // px of the short line the leader starts with

    function paint(ctx) {
        if (!cx || !cy || !dimensions) return
        for (var i = 0; i < dimensions.length; i++)
            _paintDimension(ctx, dimensions[i])
    }

    function _paintDimension(ctx, d) {
        var a, b
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = d.color
        ctx.fillStyle = d.color
        ctx.lineWidth = lineWidth
        ctx.beginPath()
        if (d.axis === "x") {
            var edge = cx(d.z)
            var lineX = edge + d.offset
            var y0 = cy(d.from), y1 = cy(d.to)
            if (d.offset > 0) {
                ctx.moveTo(edge + gap, y0); ctx.lineTo(lineX + overshoot, y0)
                ctx.moveTo(edge + gap, y1); ctx.lineTo(lineX + overshoot, y1)
            }
            a = { x: lineX, y: y0 }; b = { x: lineX, y: y1 }
        } else {
            var base = cy(d.x)
            var lineY = base + d.offset
            var away = d.offset < 0 ? -1 : 1   // up, above the part
            var x0 = cx(d.from), x1 = cx(d.to)
            // none at Z0: the dashed Z0 line is the extension line there
            if (d.from !== 0) { ctx.moveTo(x0, base + away * gap); ctx.lineTo(x0, lineY + away * overshoot) }
            if (d.to !== 0)   { ctx.moveTo(x1, base + away * gap); ctx.lineTo(x1, lineY + away * overshoot) }
            a = { x: x0, y: lineY }; b = { x: x1, y: lineY }
        }
        ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
        ctx.stroke()
        _paintHead(ctx, b, a)
        _paintHead(ctx, a, b)
        ctx.restore()

        if (d.arrowToRect)
            _paintLeader(ctx, d, a, b)
    }

    function _paintLeader(ctx, d, a, b) {
        // a quarter of the way from the ``from`` end, and the short line from it
        var start = { x: a.x + (b.x - a.x) / 4, y: a.y + (b.y - a.y) / 4 }
        var stubEnd = d.axis === "x" ? { x: start.x + leaderStub, y: start.y }
                                     : { x: start.x, y: start.y + (d.offset < 0 ? -leaderStub : leaderStub) }
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = d.color
        ctx.lineWidth = Arrow.lineWidth
        ctx.beginPath()
        ctx.moveTo(start.x, start.y)
        ctx.lineTo(stubEnd.x, stubEnd.y)
        ctx.stroke()
        ctx.restore()

        Arrow.paintToBox(ctx, stubEnd.x, stubEnd.y, d.arrowToRect, d.color, 0)
    }

    // An arrowhead with its tip at ``tip``, pointing away from ``from``.
    function _paintHead(ctx, from, tip) {
        var dx = tip.x - from.x, dy = tip.y - from.y
        var length = Math.sqrt(dx * dx + dy * dy)
        if (length < 2 * headLength) return
        var ux = dx / length, uy = dy / length
        var baseX = tip.x - ux * headLength, baseY = tip.y - uy * headLength
        ctx.beginPath()
        ctx.moveTo(tip.x, tip.y)
        ctx.lineTo(baseX - uy * headHalfWidth, baseY + ux * headHalfWidth)
        ctx.lineTo(baseX + uy * headHalfWidth, baseY - ux * headHalfWidth)
        ctx.closePath()
        ctx.fill()
    }
}
