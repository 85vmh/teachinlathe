import QtQuick 2.15
import "arrow.js" as Arrow

// Any number of marks, each with its arrow to its box. A mark is a target,
// as StartPositionActor draws the start position's; with ``line`` a Z line:
// vertical, across the centre line, ``x`` its length as a diameter, the
// arrow from whichever of its ends is nearer the box - or, given ``top``
// and ``bottom`` (diameters, negative above the centre line), from ``top``
// to ``bottom``, the arrow from diameter ``arrowAt``; ``dash`` [on, off]
// px draws it dashed, and with no ``arrowToRect`` it has no arrow; with
// ``hline`` an X
// line: horizontal, at diameter ``x`` (negative: above the centre line),
// from Z ``z - half`` to ``z + half`` (mm) - or to ``z + halfRight`` - the
// arrow from its right end; with ``blend`` "chamfer" or "fillet" an edge
// break at the corner at Z ``z``, diameter ``x``, ``size`` mm along each
// way - into the part, on its Z+ side - what it takes off filled in
// ``fill``, and its mirror when ``mirror``; the arrow, if any, from its
// middle; with ``polyline`` open lines through points {z, x} (x a diameter,
// as drawn: negative over the centre line), one list per line - with
// ``mirror``, each drawn below and over the centre line both.
QtObject {
    // [{x: diameter, z, color, arrowToRect, line, top, bottom, arrowAt, dash, hline, half}]
    property var markers: []
    property var cx: null
    property var cy: null
    property real lineWidth: 1             // as a dimension's extension lines
    // a dot where each arrow to a box starts, too
    property bool startDots: false

    property StartPositionActor _one: StartPositionActor {}

    function paint(ctx) {
        if (!markers || !cx || !cy) return
        _one.cx = cx
        _one.cy = cy
        for (var i = 0; i < markers.length; i++) {
            var m = markers[i]
            if (!m || m.visible === false) continue
            if (m.line) {
                _paintLine(ctx, m)
                continue
            }
            if (m.hline) {
                _paintHLine(ctx, m)
                continue
            }
            if (m.blend) {
                _paintBlend(ctx, m)
                continue
            }
            if (m.polyline) {
                _paintPolyline(ctx, m)
                continue
            }
            _one.position = { x: m.x || 0, z: m.z || 0 }
            _one.color = m.color || "#1565c0"
            _one.arrowToRect = m.arrowToRect || null
            _one.paint(ctx)
        }
        _one.position = null
    }

    function _paintPolyline(ctx, m) {
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = m.color || "#455a64"
        ctx.lineWidth = m.lineWidth || 1.5
        ctx.lineJoin = "miter"
        var signs = m.mirror ? [1, -1] : [0]
        ctx.beginPath()
        for (var s = 0; s < signs.length; s++) {
            for (var l = 0; l < m.polyline.length; l++) {
                var pts = m.polyline[l]
                for (var i = 0; i < pts.length; i++) {
                    var x = signs[s] === 0 ? +pts[i].x : signs[s] * Math.abs(+pts[i].x)
                    var px = cx(+pts[i].z), py = cy(x)
                    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
                }
            }
        }
        ctx.stroke()
        ctx.restore()
    }

    function _paintBlend(ctx, m) {
        var size = Math.abs(+m.size || 0)
        if (!(size > 0) || (m.blend !== "chamfer" && m.blend !== "fillet")) return
        var color = m.color || "#1565c0"
        var z = +m.z || 0, d = Math.abs(+m.x || 0)
        // one corner: the radius ``r`` positive below the centre line,
        // negative above; its middle, in px
        function corner(sign) {
            var r = sign * d / 2, inward = -sign * size
            function edge() {
                if (m.blend === "chamfer") {
                    ctx.moveTo(cx(z + size), cy(2 * r))
                    ctx.lineTo(cx(z), cy(2 * (r + inward)))
                } else {
                    // a quarter circle about (z + size, r + inward)
                    var steps = 16
                    for (var i = 0; i <= steps; i++) {
                        var a = (Math.PI / 2) * i / steps
                        var pz = z + size - size * Math.sin(a)
                        var pr = r + inward - inward * Math.cos(a)
                        if (i === 0) ctx.moveTo(cx(pz), cy(2 * pr)); else ctx.lineTo(cx(pz), cy(2 * pr))
                    }
                }
            }
            // what it takes off: between the outside, Z, and the edge break
            if (m.fill) {
                ctx.beginPath()
                edge()
                ctx.lineTo(cx(z), cy(2 * r))
                ctx.closePath()
                ctx.fillStyle = m.fill
                ctx.fill()
            }
            ctx.beginPath()
            edge()
            ctx.stroke()
            var mz = m.blend === "chamfer" ? z + size / 2 : z + size - size * Math.SQRT1_2
            var mr = m.blend === "chamfer" ? r + inward / 2 : r + inward - inward * Math.SQRT1_2
            return { x: cx(mz), y: cy(2 * mr) }
        }
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        var below = corner(1)
        if (m.mirror) corner(-1)
        if (m.arrowToRect)
            Arrow.paintToBox(ctx, below.x, below.y, m.arrowToRect, color, 0, startDots)
        ctx.restore()
    }

    function _paintHLine(ctx, m) {
        var color = m.color || "#1565c0"
        var py = cy(+m.x || 0)
        var half = Math.abs(+m.half || 0)
        var halfRight = m.halfRight !== undefined ? Math.abs(+m.halfRight) : half
        var left = cx((+m.z || 0) - half), right = cx((+m.z || 0) + halfRight)
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.moveTo(left, py)
        ctx.lineTo(right, py)
        ctx.stroke()
        if (m.arrowToRect)
            Arrow.paintToBox(ctx, right, py, m.arrowToRect, color, 0, startDots)
        ctx.restore()
    }

    function _paintLine(ctx, m) {
        var color = m.color || "#1565c0"
        var px = cx(+m.z || 0)
        var top = m.top !== undefined ? cy(+m.top) : cy(-Math.abs(+m.x || 0))
        var bottom = m.bottom !== undefined ? cy(+m.bottom) : cy(Math.abs(+m.x || 0))
        ctx.save()
        ctx.setLineDash(m.dash || [])
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.moveTo(px, top)
        ctx.lineTo(px, bottom)
        ctx.stroke()
        ctx.setLineDash([])
        if (m.arrowToRect) {
            var r = m.arrowToRect
            var above = r.y + r.height / 2 < cy(0)
            var from = m.arrowAt !== undefined ? cy(+m.arrowAt) : (above ? top : bottom)
            Arrow.paintToBox(ctx, px, from, r, color, 0, startDots)
        }
        ctx.restore()
    }
}
