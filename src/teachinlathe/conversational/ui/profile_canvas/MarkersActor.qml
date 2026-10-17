import QtQuick 2.15
import "arrow.js" as Arrow

// Any number of marks, each with its arrow to its box. A mark is a target,
// as StartPositionActor draws the start position's, or with ``line`` a Z
// line: vertical, across the centre line, ``x`` its length as a diameter,
// the arrow from whichever of its ends is nearer the box.
QtObject {
    // [{x: diameter, z, color, arrowToRect, line}]
    property var markers: []
    property var cx: null
    property var cy: null
    property real lineWidth: 1.5

    property StartPositionActor _one: StartPositionActor {}

    function paint(ctx) {
        if (!markers || !cx || !cy) return
        _one.cx = cx
        _one.cy = cy
        for (var i = 0; i < markers.length; i++) {
            var m = markers[i]
            if (!m) continue
            if (m.line) {
                _paintLine(ctx, m)
                continue
            }
            _one.position = { x: m.x || 0, z: m.z || 0 }
            _one.color = m.color || "#1565c0"
            _one.arrowToRect = m.arrowToRect || null
            _one.paint(ctx)
        }
        _one.position = null
    }

    function _paintLine(ctx, m) {
        var color = m.color || "#1565c0"
        var px = cx(+m.z || 0)
        var top = cy(-Math.abs(+m.x || 0)), bottom = cy(Math.abs(+m.x || 0))
        ctx.save()
        ctx.setLineDash([])
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.moveTo(px, top)
        ctx.lineTo(px, bottom)
        ctx.stroke()
        if (m.arrowToRect) {
            var r = m.arrowToRect
            var above = r.y + r.height / 2 < cy(0)
            Arrow.paintToBox(ctx, px, above ? top : bottom, r, color, 0)
        }
        ctx.restore()
    }
}
