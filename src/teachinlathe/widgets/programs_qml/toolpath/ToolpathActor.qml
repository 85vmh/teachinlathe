import QtQuick 2.15

QtObject {
    property var batches: []
    property real scale: 1
    property var cx
    property var cy
    function paint(ctx) {
        if (!batches || batches.length === 0) return

        for (var i = 0; i < batches.length; i++) {
            var batch = batches[i]
            ctx.strokeStyle = batch.strokeColor || "#333333"
            ctx.lineWidth = batch.lineWidth || 1.4
            ctx.lineJoin = "round"
            ctx.lineCap = "round"
            ctx.setLineDash(batch.dashPattern || [])
            ctx.beginPath()

            var lines = batch.lines || []
            for (var l = 0; l < lines.length; l++) {
                var s = lines[l]
                ctx.moveTo(cx(s[0]), cy(s[1]))
                ctx.lineTo(cx(s[2]), cy(s[3]))
            }

            var arcs = batch.arcs || []
            for (var a = 0; a < arcs.length; a++) {
                var arc = arcs[a]
                var centerX = cx(arc.cz)
                var centerY = cy(arc.cx)
                var radius = Math.abs(arc.r * scale)
                if (radius <= 0) continue

                var anticlockwise = arc.a1 < arc.a0
                ctx.moveTo(cx(arc.z0), cy(arc.x0))
                ctx.arc(centerX, centerY, radius, arc.a0, arc.a1, anticlockwise)
            }

            ctx.stroke()
            ctx.setLineDash([])
        }
    }
}
