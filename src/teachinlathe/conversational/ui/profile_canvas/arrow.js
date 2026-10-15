// Leader arrows from something drawn on the canvas to a box laid over it.
.pragma library

// how thick the arrows are drawn, and the borders of the boxes they point to
var lineWidth = 1.5

// The point of rect {x, y, width, height} nearest (px, py).
function nearestOnRect(rect, px, py) {
    return {
        x: Math.max(rect.x, Math.min(rect.x + rect.width,  px)),
        y: Math.max(rect.y, Math.min(rect.y + rect.height, py))
    }
}

// A line from (sx, sy), starting ``gap`` px out, to (ex, ey), with the
// arrowhead at (ex, ey).
function paint(ctx, sx, sy, ex, ey, color, gap) {
    var arrowLength = 12
    var arrowHalfWidth = 4
    var dx = ex - sx
    var dy = ey - sy
    var length = Math.sqrt(dx * dx + dy * dy)
    if (length <= (gap || 0) + arrowLength) return
    var ux = dx / length
    var uy = dy / length
    var baseX = ex - ux * arrowLength
    var baseY = ey - uy * arrowLength

    ctx.save()
    ctx.setLineDash([])
    ctx.globalAlpha = 1.0
    ctx.strokeStyle = color
    ctx.fillStyle = color
    ctx.lineWidth = lineWidth
    ctx.beginPath()
    ctx.moveTo(sx + ux * (gap || 0), sy + uy * (gap || 0))
    ctx.lineTo(baseX, baseY)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(ex, ey)
    ctx.lineTo(baseX - uy * arrowHalfWidth, baseY + ux * arrowHalfWidth)
    ctx.lineTo(baseX + uy * arrowHalfWidth, baseY - ux * arrowHalfWidth)
    ctx.closePath()
    ctx.fill()
    ctx.restore()
}
