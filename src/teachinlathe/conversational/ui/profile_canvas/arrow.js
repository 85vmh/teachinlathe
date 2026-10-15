// Leader arrows from something drawn on the canvas to a box laid over it.
// Every one ends the same way: at a dot in front of the middle of the box's
// left side, its arrowhead's tip on the dot's edge (paintToBox).
.pragma library

// how thick the arrows are drawn, and the borders of the boxes they point to
var lineWidth = 1.5
// the arrowhead, in px
var headLength = 16
var headHalfWidth = 6
// px, the dot in front of the box an arrow points to
var dotRadius = 3

// The centre of the dot an arrow to box ``rect`` {x, y, width, height} ends
// at: touching the middle of its left side.
function anchorOf(rect) {
    return { x: rect.x - dotRadius, y: rect.y + rect.height / 2 }
}

// An arrow from (sx, sy), starting ``gap`` px out, to box ``rect``: the dot
// in front of the box, and the arrow's tip on the dot's edge.
function paintToBox(ctx, sx, sy, rect, color, gap) {
    var dot = anchorOf(rect)
    ctx.save()
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(dot.x, dot.y, dotRadius, 0, 2 * Math.PI)
    ctx.fill()
    ctx.restore()

    var dx = dot.x - sx, dy = dot.y - sy
    var length = Math.sqrt(dx * dx + dy * dy)
    if (length <= dotRadius) return
    paint(ctx, sx, sy, dot.x - dx / length * dotRadius, dot.y - dy / length * dotRadius, color, gap)
}

// A line from (sx, sy), starting ``gap`` px out, to (ex, ey), with the
// arrowhead at (ex, ey).
function paint(ctx, sx, sy, ex, ey, color, gap) {
    var arrowLength = headLength
    var arrowHalfWidth = headHalfWidth
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
