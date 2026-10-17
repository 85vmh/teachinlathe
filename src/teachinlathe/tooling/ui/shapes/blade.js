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
.pragma library

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
    ctx.beginPath()
    ctx.moveTo(-w / 2, -len)
    ctx.arcTo(-w / 2, 0, w / 2, 0, d.leftRadius)
    ctx.arcTo(w / 2, 0, w / 2, -len, d.rightRadius)
    ctx.lineTo(w / 2, -len)
    ctx.closePath()
    ctx.fillStyle = d.bodyColor
    ctx.fill()
    ctx.lineJoin = "round"
    ctx.lineWidth = (d.lineWidth || 1) / k
    ctx.strokeStyle = d.edgeColor
    ctx.stroke()
    ctx.restore()
}
