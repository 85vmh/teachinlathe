import QtQuick

// What roughing leaves for another tool - pockets and corners the insert
// cannot reach - filled translucent red over the profile, on the lower half
// with the toolpath.
QtObject {
    property var   regions: []           // [[{x, z}]], X as diameter
    property var   cx: null
    property var   cy: null
    property color color: "#d32f2f"

    function paint(ctx) {
        if (!cx || !cy || !regions || regions.length === 0) return
        ctx.save()
        ctx.setLineDash([])
        ctx.lineWidth = 1
        ctx.strokeStyle = color
        ctx.fillStyle = Qt.rgba(color.r, color.g, color.b, 0.35)
        for (var i = 0; i < regions.length; i++) {
            var points = regions[i]
            if (!points || points.length < 3) continue
            ctx.beginPath()
            ctx.moveTo(cx(points[0].z), cy(points[0].x))
            for (var j = 1; j < points.length; j++)
                ctx.lineTo(cx(points[j].z), cy(points[j].x))
            ctx.closePath()
            ctx.fill()
            ctx.stroke()
        }
        ctx.restore()
    }
}
