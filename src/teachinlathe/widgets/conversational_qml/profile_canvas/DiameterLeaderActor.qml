import QtQuick 2.15

// The leader from a selected cylindrical stretch to its diameter tag: a line
// from the profile (anchor) out to the tag (end), with the arrowhead on the
// profile.
QtObject {
    property bool  active: false
    property real  anchorX: 0
    property real  anchorY: 0
    property real  endX: 0
    property real  endY: 0
    property color color: "#1565c0"
    property real  lineWidth: 1.5
    property real  arrowLength: 12
    property real  arrowHalfWidth: 4

    function paint(ctx) {
        if (!active) return
        var dx = anchorX - endX
        var dy = anchorY - endY
        var length = Math.sqrt(dx * dx + dy * dy)
        if (length < 1) return
        var ux = dx / length
        var uy = dy / length

        ctx.setLineDash([])
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.beginPath()
        ctx.moveTo(endX, endY)
        ctx.lineTo(anchorX - ux * arrowLength, anchorY - uy * arrowLength)
        ctx.stroke()

        // arrowhead, its tip on the profile
        var baseX = anchorX - ux * arrowLength
        var baseY = anchorY - uy * arrowLength
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.moveTo(anchorX, anchorY)
        ctx.lineTo(baseX - uy * arrowHalfWidth, baseY + ux * arrowHalfWidth)
        ctx.lineTo(baseX + uy * arrowHalfWidth, baseY - ux * arrowHalfWidth)
        ctx.closePath()
        ctx.fill()
    }
}
