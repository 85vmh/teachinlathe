// Stock drawn with breaks, as on a drawing (ASME Y14.2, ISO 128): a piece of
// the bar whose ends are broken off - an S from edge to edge, and on one half
// a lens between that S and its mirror, the cut face, on a darker ground and
// hatched across the walls' hatch. A tube's walls are hatched and its bore
// drawn; a bar's body is plain, only its cut faces hatched.
//
// A piece can be broken at either end or both. Its left end's break is the
// one worked out and accepted in the break-symbol demo ("Varianta folosibila",
// ~/Work/prompts/break-symbol) - the lens above the centre line; its right
// end's is that turned 180 degrees, the lens below, as the two sides of a gap
// are drawn. Keep the shape in step with the demo.
//
// Lengths are canvas px. An end's shape is worked in (u, v): u out from the
// end line into the gap, v down from the centre line.
.pragma library

// how far the S reaches out, as a fraction of the first accepted version's
var BEND = 2 / 3

// Every break's S is shaped as a tube's with this bore, a fraction of the
// radius - the shape that was accepted - whatever the stock's bore really is:
// a bar's and every tube's break look the same. A tube's bore lines meet it
// where its bore really is.
var SHAPE_BORE = 0.4

// The lower half of the end: across the bore from the centre line, then the
// far wall's end back to the corner. Each segment is [p0, c1, c2, p1].
function segments(R, r) {
    var b = 0.22 * R * BEND
    return {
        bore: [[0, 0], [0.13 * R * BEND, r / 3], [0.2 * R * BEND, 2 * r / 3], [b, r]],
        wall: [[b, r], [0.28 * R * BEND, r + 0.4 * (R - r)], [0.2 * R * BEND, R], [0, R]]
    }
}

function reversed(s) { return [s[3], s[2], s[1], s[0]] }

// The upper half: the lower half turned 180 degrees about its point on the
// centre line (wall, bore), and that flipped about the vertical through it -
// its mirror out in the gap (wall2, bore2). Top to bottom.
function upperHalf(t) {
    function turn(seg) { return seg.map(function(p) { return [-p[0], -p[1]] }) }
    function flip(seg) { return seg.map(function(p) { return [-p[0], p[1]] }) }
    var wall = reversed(turn(t.wall)), bore = reversed(turn(t.bore))
    return { wall: wall, bore: bore, wall2: flip(wall), bore2: flip(bore) }
}

// How far a break reaches out into its gap, at its furthest, in px.
function reach(R) {
    var wall = segments(R, SHAPE_BORE * R).wall, most = 0
    for (var i = 0; i <= 100; i++) most = Math.max(most, bezierAt(wall, i / 100)[0])
    return most
}

function bezierAt(s, t) {
    var u = 1 - t
    return [u*u*u*s[0][0] + 3*u*u*t*s[1][0] + 3*u*t*t*s[2][0] + t*t*t*s[3][0],
            u*u*u*s[0][1] + 3*u*u*t*s[1][1] + 3*u*t*t*s[2][1] + t*t*t*s[3][1]]
}

// The point of the segments at height y, by halving the one that spans it.
function pointAtY(segs, y) {
    for (var i = 0; i < segs.length; i++) {
        var s = segs[i]
        var y0 = s[0][1], y1 = s[3][1]
        if ((y - y0) * (y - y1) > 0) continue
        var lo = 0, hi = 1, rising = y1 > y0
        for (var k = 0; k < 40; k++) {
            var mid = (lo + hi) / 2
            if ((bezierAt(s, mid)[1] < y) === rising) lo = mid; else hi = mid
        }
        return bezierAt(s, (lo + hi) / 2)
    }
    return null
}

function curve(ctx, s) { ctx.bezierCurveTo(s[1][0], s[1][1], s[2][0], s[2][1], s[3][0], s[3][1]) }

// Diagonals ``pitch`` px apart over the rect, clipped to whatever the caller
// set; ``across``, the other diagonal.
function hatch(ctx, left, top, right, bottom, pitch, across) {
    var span = bottom - top
    for (var x = left - span; x < right + span; x += pitch) {
        ctx.beginPath()
        if (across) { ctx.moveTo(x, top); ctx.lineTo(x + span, bottom) }
        else        { ctx.moveTo(x, bottom); ctx.lineTo(x + span, top) }
        ctx.stroke()
    }
}

// A broken end at canvas x, the gap on its ``side`` (-1 left, +1 right):
// {segs: its four segments top to bottom, lens: [arcs, mirrored arcs], top,
// bottom: the corners}, in canvas px.
function brokenEnd(x, cy, R, shapeR, side) {
    var t = segments(R, shapeR), up = upperHalf(t)
    var place = side < 0
        ? function(seg) { return seg.map(function(p) { return [x - p[0], cy + p[1]] }) }
        // the left end's shape turned 180 degrees
        : function(seg) { return seg.map(function(p) { return [x + p[0], cy - p[1]] }) }
    var segs = [place(up.wall), place(up.bore), place(t.bore), place(t.wall)]
    if (side > 0) segs = segs.reverse().map(reversed)        // still top to bottom
    var lens = [[place(up.wall), place(up.bore)], [place(up.wall2), place(up.bore2)]]
    return { segs: segs, lens: lens, top: segs[0][0], bottom: segs[3][3] }
}

// A plain end - the bar's face - at canvas x: no break, no outline.
function faceEnd(x, cy, R) {
    return { segs: [], lens: null, top: [x, cy - R], bottom: [x, cy + R] }
}

// One piece of the stock from canvas x ``leftX`` to ``rightX``, about the
// centre line at canvas y ``cy``, outer radius ``R`` and bore radius ``r``
// (0: a bar) in px, each end broken or the bar's face. ``style``: fill,
// hatch, hatchPitch, outline, bore, lineWidth, lensFill, lensHatch - as the
// canvas draws its stock - and, for a caller with hatching of its own (the
// finished part, say), ``noWallHatch`` to leave a tube's walls plain and
// ``inside(ctx)``, called after the fill, clipped to the piece's body; and
// ``fillInside(ctx)`` to fill only some of the body, in the fill colour set,
// and ``skinTo``, the canvas x the skin's lines stop at short of the right end.
function piece(ctx, leftX, rightX, cy, R, r, leftBroken, rightBroken, style) {
    if (R <= 0 || rightX <= leftX) return
    var solid = r <= 0
    var shapeR = SHAPE_BORE * R
    var left = leftBroken ? brokenEnd(leftX, cy, R, shapeR, -1) : faceEnd(leftX, cy, R)
    var right = rightBroken ? brokenEnd(rightX, cy, R, shapeR, 1) : faceEnd(rightX, cy, R)
    var top = cy - R, bottom = cy + R
    var i, k

    function body() {
        ctx.beginPath()
        ctx.moveTo(left.top[0], left.top[1])
        for (i = 0; i < left.segs.length; i++) curve(ctx, left.segs[i])
        ctx.lineTo(left.bottom[0], left.bottom[1])
        ctx.lineTo(right.bottom[0], right.bottom[1])
        for (i = right.segs.length - 1; i >= 0; i--) curve(ctx, reversed(right.segs[i]))
        ctx.lineTo(right.top[0], right.top[1])
        ctx.closePath()
    }
    function lensPath(end) {
        var a = end.lens[0], b = end.lens[1]
        ctx.beginPath()
        ctx.moveTo(a[0][0][0], a[0][0][1]); curve(ctx, a[0]); curve(ctx, a[1])
        curve(ctx, reversed(b[1])); curve(ctx, reversed(b[0]))
        ctx.closePath()
    }
    var broken = []
    if (leftBroken) broken.push(left)
    if (rightBroken) broken.push(right)

    ctx.save()
    ctx.setLineDash([])

    // opaque, over the grid behind it - or only where ``fillInside(ctx)``
    // fills, clipped to the body; the cut faces on a darker ground
    ctx.fillStyle = style.fill
    if (style.fillInside) {
        ctx.save()
        body(); ctx.clip()
        style.fillInside(ctx)
        ctx.restore()
    } else {
        body(); ctx.fill()
    }
    ctx.fillStyle = style.lensFill || style.fill
    for (k = 0; k < broken.length; k++) { lensPath(broken[k]); ctx.fill() }

    ctx.lineWidth = 1
    if (style.inside) {
        ctx.save()
        body(); ctx.clip()
        style.inside(ctx)
        ctx.restore()
    }
    // a tube's walls, hatched as the canvas hatches its stock
    if (!solid && !style.noWallHatch) {
        ctx.strokeStyle = style.hatch
        var bands = [[top, cy - r], [cy + r, bottom]]
        for (k = 0; k < bands.length; k++) {
            ctx.save()
            body(); ctx.clip()
            ctx.beginPath(); ctx.rect(leftX - R, bands[k][0], rightX - leftX + 2 * R, bands[k][1] - bands[k][0]); ctx.clip()
            hatch(ctx, leftX - R, bands[k][0], rightX + R, bands[k][1], style.hatchPitch, false)
            ctx.restore()
        }
    }
    // the cut faces, hatched across
    ctx.strokeStyle = style.lensHatch || style.hatch
    for (k = 0; k < broken.length; k++) {
        ctx.save()
        lensPath(broken[k]); ctx.clip()
        hatch(ctx, broken[k].top[0] - 2 * R, top, broken[k].top[0] + 2 * R, bottom, style.hatchPitch, true)
        ctx.restore()
    }

    // the outline: the skin from end to end, and the breaks - not a face,
    // which is on Z0, where the dashed Z0 line goes
    ctx.strokeStyle = style.outline
    ctx.lineWidth = style.lineWidth || 1
    ctx.beginPath()
    var skinTo = style.skinTo !== undefined ? Math.min(style.skinTo, right.top[0]) : right.top[0]
    ctx.moveTo(left.top[0], left.top[1]); ctx.lineTo(skinTo, right.top[1])
    ctx.moveTo(left.bottom[0], left.bottom[1]); ctx.lineTo(skinTo, right.bottom[1])
    for (k = 0; k < broken.length; k++) {
        var arcs = broken[k].segs.concat(broken[k].lens[1])
        for (i = 0; i < arcs.length; i++) {
            ctx.moveTo(arcs[i][0][0], arcs[i][0][1]); curve(ctx, arcs[i])
        }
    }
    ctx.stroke()

    // a tube's bore, each line from break to break, or to the face
    if (!solid) {
        ctx.strokeStyle = style.bore
        ctx.beginPath()
        var levels = [cy - r, cy + r]
        for (k = 0; k < levels.length; k++) {
            var from = leftBroken ? pointAtY(left.segs, levels[k]) : [leftX, levels[k]]
            var to = rightBroken ? pointAtY(right.segs, levels[k]) : [rightX, levels[k]]
            if (from && to) { ctx.moveTo(from[0], levels[k]); ctx.lineTo(to[0], levels[k]) }
        }
        ctx.stroke()
    }
    ctx.restore()
}

// The stock from its face at canvas x ``faceX`` back to ``breakX``, where it
// is broken off: one piece, its far end broken.
function paint(ctx, faceX, breakX, cy, R, r, style) {
    piece(ctx, breakX, faceX, cy, R, r, true, false, style)
}
