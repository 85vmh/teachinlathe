import QtQuick 2.15

QtObject {
    property real originX: 0
    property real originY: 0
    property real circleR: 0
    property color strokeColor: "#222222"
    property color fillColor: "#222222"
    property real lineWidth: 1.5

    function paint(ctx) {
        var r = circleR
        var ocx = originX
        var ocy = originY
        ctx.lineWidth = lineWidth
        ctx.fillStyle = fillColor
        ctx.strokeStyle = strokeColor
        ctx.setLineDash([])
        var quads = [
            { start: -Math.PI/2,     end: 0,              fill: true  },
            { start: 0,              end: Math.PI/2,       fill: false },
            { start: Math.PI/2,      end: Math.PI,         fill: true  },
            { start: Math.PI,        end: 3*Math.PI/2,     fill: false }
        ]
        for (var i = 0; i < quads.length; i++) {
            var q = quads[i]
            ctx.beginPath()
            ctx.moveTo(ocx, ocy)
            ctx.arc(ocx, ocy, r, q.start, q.end, false)
            ctx.closePath()
            if (q.fill) {
                ctx.fill()
            }
            ctx.stroke()
        }
    }
}
