import QtQuick 2.15
import theme 1.0

// The centre line, across the whole canvas: in the Z axis's green, dashed
// long - short like the Z0 line.
QtObject {
    property real width: 0
    property real originY: 0
    property color lineColor: Theme.success          // the Z axis arrow's
    property real lineWidth: 1
    property var dashPattern: [16, 4, 3, 4]          // long dash, gap, dot, gap

    function paint(ctx) {
        ctx.strokeStyle = lineColor
        ctx.lineWidth = lineWidth
        ctx.setLineDash(dashPattern)
        ctx.beginPath()
        ctx.moveTo(0, originY)
        ctx.lineTo(width, originY)
        ctx.stroke()
        ctx.setLineDash([])
    }
}
