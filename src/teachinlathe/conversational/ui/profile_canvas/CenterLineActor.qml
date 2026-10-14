import QtQuick 2.15

QtObject {
    property real width: 0
    property real originY: 0
    property color lineColor: "#bbbbbb"
    property real lineWidth: 1
    property var dashPattern: [10, 4, 3, 4]

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
