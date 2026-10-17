// blade.js — a parting / grooving blade, drawn on a given 2D context: the
// same blade wherever it shows - the Tool Library's preview and thumbnail,
// an operation's canvas.
//
// In the blade's own frame, in mm: its cutting end on y = 0, from x = -w/2
// to w/2, its body running on to y = -length; the corners rounded by
// leftRadius and rightRadius. Then mirrored top to bottom when ``mirrored``,
// turned ``rotation`` degrees counter-clockwise, and drawn with its control
// point - the middle of the cutting end - on (tipX, tipY) px, y down the
// screen.
//
// `d`: width, length, leftRadius, rightRadius, rotation, mirrored, pxPerMm,
// tipX, tipY, bodyColor, edgeColor, lineWidth (px).
//
// The far end - the holder's side - is not drawn as an end but broken off,
// as a drawing breaks a long part: a straight line across, as wide as the
// blade, with one zigzag in its middle.
.pragma library

// The break line across the far end, in the blade's frame: from ``x0`` to
// ``x1`` (either way round) at y = -len, its zigzag in the middle third of
// the width - points [[x, y]].
function _breakLine(w, len, x0, x1) {
    var h = 0.3 * w                  // how far the zigzag reaches either way
    var dir = x1 > x0 ? 1 : -1
    return [[x0, -len],
            [-dir * 0.18 * w, -len],
            [-dir * 0.06 * w, -len + h],
            [dir * 0.06 * w, -len - h],
            [dir * 0.18 * w, -len],
            [x1, -len]]
}

// A point of the blade's frame, in mm, mirrored and turned as it is drawn,
// flipped to screen y - still in mm, about the control point.
function turned(d, x, y) {
    if (d.mirrored) y = -y
    var a = d.rotation * Math.PI / 180
    return { x: x * Math.cos(a) - y * Math.sin(a),
             y: -(x * Math.sin(a) + y * Math.cos(a)) }
}

// Its four corners as drawn, about the control point, in mm.
function corners(d) {
    var w = d.width / 2, l = d.length
    return [turned(d, -w, 0), turned(d, w, 0), turned(d, w, -l), turned(d, -w, -l)]
}

function paint(ctx, d) {
    var w = d.width, len = d.length, k = d.pxPerMm
    if (!(w > 0) || !(len > 0) || !(k > 0)) return
    ctx.save()
    ctx.translate(d.tipX, d.tipY)
    ctx.rotate(-d.rotation * Math.PI / 180)
    ctx.scale(k, d.mirrored ? k : -k)
    var i, pts
    // the body, its far end along the break line
    ctx.beginPath()
    ctx.moveTo(-w / 2, -len)
    ctx.arcTo(-w / 2, 0, w / 2, 0, d.leftRadius)
    ctx.arcTo(w / 2, 0, w / 2, -len, d.rightRadius)
    pts = _breakLine(w, len, w / 2, -w / 2)
    for (i = 0; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1])
    ctx.closePath()
    ctx.fillStyle = d.bodyColor
    ctx.fill()
    ctx.lineJoin = "round"
    ctx.lineWidth = (d.lineWidth || 1) / k
    ctx.strokeStyle = d.edgeColor
    // the sides and the cutting end - not the far end, which is the break
    ctx.beginPath()
    ctx.moveTo(-w / 2, -len)
    ctx.arcTo(-w / 2, 0, w / 2, 0, d.leftRadius)
    ctx.arcTo(w / 2, 0, w / 2, -len, d.rightRadius)
    ctx.lineTo(w / 2, -len)
    ctx.stroke()
    // the break line, side to side
    pts = _breakLine(w, len, w / 2, -w / 2)
    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for (i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1])
    ctx.lineJoin = "miter"
    ctx.stroke()
    ctx.restore()
}
