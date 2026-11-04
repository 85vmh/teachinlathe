import QtQuick

// The roughing toolpath, on the lower half only: the cuts solid - the final
// contour pass among them - every other pass with small arrowheads every
// 10 mm showing which way it cuts, and the rapids
// between them (retracts included) dashed in the backplot's rapid grey.
QtObject {
    property var   feeds: []             // [{x0, z0, x1, z1, pass}], X as diameter
    property var   rapids: []            // [{x0, z0, x1, z1}]
    property var   cx: null
    property var   cy: null
    property color feedColor: "#2e7d32"
    property color rapidColor: "#777777"
    property real  lineWidth: 2           // the cuts
    property real  contourLineWidth: 3    // the final contour pass
    property real  rapidLineWidth: 1
    property var   rapidDash: [6, 3]      // px on, px off
    property real  arrowLength: 12        // px
    property real  arrowHalfWidth: 4.5    // px
    property real  arrowEvery: 10         // mm along the cut, X counted on the diameter
    // while the view moves: square line ends - round ones take the
    // rasterizer off its fast way, and are what the toolpath costs to draw
    property bool  simplified: false

    function paint(ctx) {
        if (!cx || !cy) return
        _paintMoves(ctx, rapids, rapidColor, rapidDash, rapidLineWidth)
        _paintMoves(ctx, feeds.filter(function(m) { return !m.contour }), feedColor, [], lineWidth)
        _paintMoves(ctx, feeds.filter(function(m) { return m.contour }), feedColor, [], contourLineWidth)
        _paintDirections(ctx)
    }

    function _paintMoves(ctx, moves, color, dash, width) {
        if (!moves || moves.length === 0) return
        ctx.save()
        ctx.setLineDash(dash)
        ctx.lineCap = simplified ? "butt" : "round"
        ctx.strokeStyle = color
        ctx.lineWidth = width
        ctx.beginPath()
        for (var i = 0; i < moves.length; i++) {
            var m = moves[i]
            ctx.moveTo(cx(m.z0), cy(m.x0))
            ctx.lineTo(cx(m.z1), cy(m.x1))
        }
        ctx.stroke()
        ctx.restore()
    }

    // Along each even pass, pointing the way the tool moves, an arrowhead
    // starting arrowEvery / 2 mm into the pass and a new one every arrowEvery
    // mm after, as long as it still fits; a pass shorter than arrowEvery gets
    // a single one, centred halfway along. Distances run along the whole
    // pass, across its cuts and around its arcs. A pass whose feeds say
    // ``arrows``: "along", so on every pass, not only the even ones; "end",
    // one arrowhead on each of its feeds instead, its tip where the feed ends
    // (a peck, at the depth it goes to).
    function _paintDirections(ctx) {
        if (!feeds || feeds.length === 0) return
        ctx.save()
        ctx.setLineDash([])
        ctx.fillStyle = feedColor
        var first = 0
        for (var i = 1; i <= feeds.length; i++) {
            if (i < feeds.length && feeds[i].pass === feeds[first].pass) continue
            var arrows = feeds[first].arrows
            if (arrows === "end") _paintEndHeads(ctx, feeds.slice(first, i))
            else if (arrows === "along" || feeds[first].pass % 2 === 0) _paintPassDirections(ctx, feeds.slice(first, i))
            first = i
        }
        ctx.restore()
    }

    // in mm, X on the diameter as the machine moves it: a radial cut gets an
    // arrowhead every arrowEvery / 2 mm of the half that is drawn
    function _mm(m) {
        return Math.sqrt(Math.pow(m.z1 - m.z0, 2) + Math.pow(m.x1 - m.x0, 2))
    }

    function _paintPassDirections(ctx, moves) {
        var total = 0
        for (var i = 0; i < moves.length; i++) total += _mm(moves[i])
        if (total <= 0) return
        var centred = total < arrowEvery
        var at = centred ? total / 2 : arrowEvery / 2
        var walked = 0
        for (var j = 0; j < moves.length && at < total; j++) {
            var m = moves[j]
            var mm = _mm(m)
            var sx = cx(m.z0), sy = cy(m.x0)
            var dx = cx(m.z1) - sx, dy = cy(m.x1) - sy
            var length = Math.sqrt(dx * dx + dy * dy)
            while (at < walked + mm) {
                if (length > 0) {
                    var ux = dx / length, uy = dy / length
                    var t = (at - walked) / mm
                    var px = sx + dx * t, py = sy + dy * t
                    if (centred) {
                        _paintHead(ctx, px - ux * arrowLength / 2, py - uy * arrowLength / 2, ux, uy)
                    } else if ((total - at) / total * _passLength(moves) >= arrowLength) {
                        _paintHead(ctx, px, py, ux, uy)
                    }
                }
                if (centred) return
                at += arrowEvery
            }
            walked += mm
        }
    }

    // an arrowhead on each move, its tip on the move's end - and, with
    // ``endTick`` (mm), a thin line across there that wide either way, at
    // most as long as the arrowhead's base
    function _paintEndHeads(ctx, moves) {
        for (var i = 0; i < moves.length; i++) {
            var m = moves[i]
            var sx = cx(m.z0), sy = cy(m.x0), ex = cx(m.z1), ey = cy(m.x1)
            if (m.endTick > 0) {
                ctx.save()
                ctx.strokeStyle = feedColor
                ctx.lineWidth = 1
                var half = Math.min(Math.abs(cx(m.z1 + m.endTick) - ex), arrowHalfWidth)
                ctx.beginPath()
                ctx.moveTo(ex - half, ey)
                ctx.lineTo(ex + half, ey)
                ctx.stroke()
                ctx.restore()
            }
            var length = Math.sqrt(Math.pow(ex - sx, 2) + Math.pow(ey - sy, 2))
            if (length < arrowLength) continue
            var ux = (ex - sx) / length, uy = (ey - sy) / length
            _paintHead(ctx, ex - ux * arrowLength, ey - uy * arrowLength, ux, uy)
        }
    }

    // on screen, in px
    function _passLength(moves) {
        var length = 0
        for (var i = 0; i < moves.length; i++) {
            var m = moves[i]
            length += Math.sqrt(Math.pow(cx(m.z1) - cx(m.z0), 2) + Math.pow(cy(m.x1) - cy(m.x0), 2))
        }
        return length
    }

    // An arrowhead whose base is at (px, py), pointing along (ux, uy).
    function _paintHead(ctx, px, py, ux, uy) {
        var baseX = px, baseY = py
        var tipX = px + ux * arrowLength
        var tipY = py + uy * arrowLength
        ctx.beginPath()
        ctx.moveTo(tipX, tipY)
        ctx.lineTo(baseX - uy * arrowHalfWidth, baseY + ux * arrowHalfWidth)
        ctx.lineTo(baseX + uy * arrowHalfWidth, baseY - ux * arrowHalfWidth)
        ctx.closePath()
        ctx.fill()
    }
}
