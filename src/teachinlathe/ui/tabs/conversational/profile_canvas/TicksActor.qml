import QtQuick
import theme
import "axisbreak.js" as AxisBreak

QtObject {
    property real width: 0
    property real height: 0
    property real originX: 0
    property real originY: 0
    property real scale: 1
    property var geometry
    property color zTickColor: Theme.success   // matches AxesActor.zAxisColor
    property color xTickColor: Theme.accentStrong   // matches AxesActor.xAxisColor
    property real tickLineWidth: 1
    property string tickFont: "10px sans-serif"
    // a stretch of Z left out of the drawing: no ticks over it but a break
    // mark, the real Z past it; see axisbreak.js
    property var axisBreak: null
    // the break mark: a zigzag at 60 degrees in the middle of the gap, a
    // straight line out from it each way ending in an arrowhead, to Z- on
    // the left and Z+ on the right - in px
    property real breakZigzagHeight: 6       // peak to peak
    property int  breakZigzagPeaks: 3
    // the mark's line from the edge - on a pixel's middle, so a one px line
    // is one px and not two half-strength ones
    property real breakEdgeInset: 6.5
    property real breakArrowLength: 6
    property real breakArrowHalfWidth: 3

    function paint(ctx) {
        var s = geometry.steps(scale)
        ctx.lineWidth = tickLineWidth
        ctx.setLineDash([])

        // Z — top + bottom edges (green)
        ctx.strokeStyle = zTickColor
        ctx.fillStyle = zTickColor
        ctx.textAlign = "center"
        var zWMin = -originX / scale
        var zWMax = (width - originX) / scale
        var zMarks = AxisBreak.marks(zWMin, zWMax, s.minor, axisBreak)
        for (var i = 0; i < zMarks.length; i++) {
            var z = zMarks[i].real
            var ts = geometry.tickStyle(z, s)
            var canvasX = originX + zMarks[i].drawn * scale
            ctx.beginPath()
            ctx.moveTo(canvasX, 0)
            ctx.lineTo(canvasX, ts.len)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(canvasX, height)
            ctx.lineTo(canvasX, height - ts.len)
            ctx.stroke()
            if (ts.label) {
                ctx.font = tickFont
                ctx.textBaseline = "top"
                ctx.fillText(Math.round(z).toString(), canvasX, ts.len + 2)
                ctx.textBaseline = "bottom"
                ctx.fillText(Math.round(z).toString(), canvasX, height - ts.len - 2)
            }
        }

        // over the stretch left out, a break mark instead of ticks
        if (axisBreak) {
            var gapLeft = originX + axisBreak.far * scale
            var gapRight = originX + axisBreak.near * scale
            _paintBreakMark(ctx, gapLeft, gapRight, breakEdgeInset)
            _paintBreakMark(ctx, gapLeft, gapRight, height - breakEdgeInset)
        }

        // X — left + right edges (blue); data uses diameter, display uses radius.
        // Use scale/2 for tick step selection (effective pixel/mm in diameter space).
        ctx.strokeStyle = xTickColor
        ctx.fillStyle = xTickColor
        var sx = geometry.steps(scale / 2)
        var xDiaMin = -originY * 2 / scale
        var xDiaMax = (height - originY) * 2 / scale
        var xt = Math.floor(xDiaMin / sx.minor) * sx.minor
        for (var x = xt; x <= xDiaMax; x += sx.minor) {
            var tsx = geometry.tickStyle(x, sx)
            var canvasY = originY + (x / 2) * scale
            ctx.beginPath()
            ctx.moveTo(0, canvasY)
            ctx.lineTo(tsx.len, canvasY)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(width, canvasY)
            ctx.lineTo(width - tsx.len, canvasY)
            ctx.stroke()
            if (tsx.label) {
                ctx.font = tickFont
                ctx.textAlign = "left"
                ctx.textBaseline = "middle"
                ctx.fillText(Math.round(x).toString(), tsx.len + 2, canvasY)
                ctx.textAlign = "right"
                ctx.fillText(Math.round(x).toString(), width - tsx.len - 2, canvasY)
            }
        }
    }

    // From canvas x ``left`` to ``right`` along y: the zigzag in the middle,
    // a straight line each side out to an arrowhead at the gap's end.
    function _paintBreakMark(ctx, left, right, y) {
        var span = right - left
        if (span <= 2 * breakArrowLength) return
        var h = breakZigzagHeight / 2
        var run = breakZigzagHeight / Math.tan(60 * Math.PI / 180)  // one stroke at 60 degrees
        var zigWidth = Math.min(span - 2 * breakArrowLength, run * 2 * breakZigzagPeaks)
        var zigLeft = left + (span - zigWidth) / 2
        var strokes = Math.max(2, Math.round(zigWidth / run))
        var step = zigWidth / strokes

        ctx.save()
        ctx.strokeStyle = zTickColor
        ctx.fillStyle = zTickColor
        ctx.lineWidth = tickLineWidth
        ctx.setLineDash([])
        ctx.beginPath()
        // left: from the arrowhead's base to the zigzag
        ctx.moveTo(left + breakArrowLength, y)
        ctx.lineTo(zigLeft, y)
        // the zigzag: up, down, ... about the line, ending on it
        for (var i = 1; i <= strokes; i++) {
            var x = zigLeft + i * step
            var peak = (i === strokes) ? 0 : (i % 2 ? -h : h)
            ctx.lineTo(x, y + peak)
        }
        // right: on to the arrowhead's base
        ctx.lineTo(right - breakArrowLength, y)
        ctx.stroke()
        // the arrowheads, out to Z- and to Z+
        ctx.beginPath()
        ctx.moveTo(left, y)
        ctx.lineTo(left + breakArrowLength, y - breakArrowHalfWidth)
        ctx.lineTo(left + breakArrowLength, y + breakArrowHalfWidth)
        ctx.closePath()
        ctx.moveTo(right, y)
        ctx.lineTo(right - breakArrowLength, y - breakArrowHalfWidth)
        ctx.lineTo(right - breakArrowLength, y + breakArrowHalfWidth)
        ctx.closePath()
        ctx.fill()
        ctx.restore()
    }
}
