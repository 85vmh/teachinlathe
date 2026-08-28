import QtQuick 2.15

QtObject {
    property var workpiece: ({})
    property var stockProfile: []
    property var cx
    property var cy

    readonly property real stockLength: workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
    readonly property real externalDiameter: workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
    readonly property real internalDiameter: workpiece && workpiece.internal_diameter !== undefined ? Number(workpiece.internal_diameter) : 0

    function _hatchCurrentClip(ctx, left, top, right, bottom) {
        var spacing = 12
        var overshoot = bottom - top
        ctx.strokeStyle = "#d5d9df"
        ctx.lineWidth = 1
        ctx.setLineDash([])
        for (var x = left - overshoot; x < right + overshoot; x += spacing) {
            ctx.beginPath()
            ctx.moveTo(x, bottom)
            ctx.lineTo(x + overshoot, top)
            ctx.stroke()
        }
    }

    function paint(ctx) {
        paintStock(ctx)
        paintHatch(ctx)
    }

    function paintStock(ctx) {
        var stockZ = -Math.max(0, stockLength)
        var stockX = Math.max(0, externalDiameter)
        if (stockLength <= 0 || stockX <= 0 || !cx || !cy) return

        var left = cx(0)
        var right = cx(stockZ)
        var innerX = Math.max(0, Math.min(internalDiameter, stockX))
        var top = cy(innerX)
        var bottom = cy(stockX)

        ctx.strokeStyle = "#9ca3af"
        ctx.lineWidth = 1
        ctx.setLineDash([])
        ctx.beginPath()
        ctx.moveTo(left, bottom)
        ctx.lineTo(right, bottom)
        ctx.lineTo(right, top)
        ctx.moveTo(left, bottom)
        ctx.lineTo(left, top)
        ctx.stroke()

        if (internalDiameter > 0) {
            ctx.strokeStyle = "#aeb4bd"
            ctx.beginPath()
            ctx.moveTo(left, cy(innerX))
            ctx.lineTo(right, cy(innerX))
            ctx.stroke()
        }
    }

    function paintHatch(ctx) {
        var stockZ = -Math.max(0, stockLength)
        var stockX = Math.max(0, externalDiameter)
        if (stockLength <= 0 || stockX <= 0 || !cx || !cy) return

        var left = cx(0)
        var right = cx(stockZ)
        var innerX = Math.max(0, Math.min(internalDiameter, stockX))
        var top = cy(innerX)
        var bottom = cy(stockX)
        var rectLeft = Math.min(left, right)
        var rectRight = Math.max(left, right)
        var rectTop = Math.min(top, bottom)
        var rectBottom = Math.max(top, bottom)
        var points = _profileCanvasPoints(stockZ, stockX, innerX)

        ctx.save()
        ctx.beginPath()
        ctx.rect(rectLeft, rectTop, rectRight - rectLeft, rectBottom - rectTop)
        ctx.clip()
        if (points.length < 2) {
            _hatchCurrentClip(ctx, rectLeft, rectTop, rectRight, rectBottom)
        } else {
            _hatchToProfile(ctx, rectLeft, rectTop, rectRight, rectBottom, points)
        }
        ctx.restore()
    }

    function _profileCanvasPoints(stockZ, stockX, innerX) {
        if (!stockProfile || stockProfile.length < 2) return []

        var points = []
        for (var i = 0; i < stockProfile.length; i++) {
            var p = stockProfile[i]
            if (!p || p.length < 2) continue
            var z = Number(p[0])
            var x = Number(p[1])
            if (!isFinite(z) || !isFinite(x)) continue
            if (z < stockZ || z > 0) continue
            points.push({ z: z, x: Math.max(innerX, Math.min(x, stockX)) })
        }
        if (points.length < 2) return []

        points.sort(function(a, b) { return a.z - b.z })
        _extendProfileEndToExternalDiameter(points, stockX)

        var out = []
        for (var j = 0; j < points.length; j++) {
            out.push({ px: cx(points[j].z), py: cy(points[j].x) })
        }
        return out
    }

    function _extendProfileEndToExternalDiameter(points, stockX) {
        var last = points[points.length - 1]
        if (Math.abs(last.z) > 0.000001 || last.x >= stockX - 0.000001) return
        points.push({ z: 0, x: stockX })
    }

    function _hatchToProfile(ctx, rectLeft, rectTop, rectRight, rectBottom, profilePoints) {
        var spacing = 12
        var kMin = rectLeft + rectTop
        var kMax = rectRight + rectBottom

        ctx.strokeStyle = "#d5d9df"
        ctx.lineWidth = 1
        ctx.setLineDash([])

        for (var k = kMin - spacing; k <= kMax + spacing; k += spacing) {
            var rectHits = _diagonalRectIntersections(k, rectLeft, rectTop, rectRight, rectBottom)
            if (rectHits.length < 2) continue

            rectHits.sort(function(a, b) { return a.t - b.t })
            var lower = rectHits[0]
            var upper = rectHits[rectHits.length - 1]
            var profileHit = _diagonalProfileHit(k, lower, upper, profilePoints)

            var hatchEnd = profileHit ? _pointBeforeHit(upper, profileHit) : lower
            ctx.beginPath()
            ctx.moveTo(upper.x, upper.y)
            ctx.lineTo(hatchEnd.x, hatchEnd.y)
            ctx.stroke()
        }
    }

    function _diagonalRectIntersections(k, left, top, right, bottom) {
        var hits = []
        _addRectHit(hits, k - top, top, left, top, right, bottom)
        _addRectHit(hits, k - bottom, bottom, left, top, right, bottom)
        _addRectHit(hits, left, k - left, left, top, right, bottom)
        _addRectHit(hits, right, k - right, left, top, right, bottom)
        return hits
    }

    function _addRectHit(hits, x, y, left, top, right, bottom) {
        if (x < left - 0.001 || x > right + 0.001 || y < top - 0.001 || y > bottom + 0.001) return
        for (var i = 0; i < hits.length; i++) {
            if (Math.abs(hits[i].x - x) < 0.001 && Math.abs(hits[i].y - y) < 0.001) return
        }
        hits.push({ x: x, y: y, t: x - y })
    }

    function _diagonalProfileHit(k, lower, upper, profilePoints) {
        var best = null
        var bestT = -1e100
        for (var i = 0; i < profilePoints.length - 1; i++) {
            var a = profilePoints[i]
            var b = profilePoints[i + 1]
            var denom = (b.px - a.px) + (b.py - a.py)
            if (Math.abs(denom) < 0.000001) continue

            var u = (k - a.px - a.py) / denom
            if (u < -0.000001 || u > 1.000001) continue

            var x = a.px + (b.px - a.px) * u
            var y = a.py + (b.py - a.py) * u
            if (!_pointOnSegment(x, y, lower, upper)) continue

            var t = x - y
            if (t > bestT) {
                bestT = t
                best = { x: x, y: y }
            }
        }
        return best
    }

    function _pointOnSegment(x, y, a, b) {
        return x >= Math.min(a.x, b.x) - 0.001
            && x <= Math.max(a.x, b.x) + 0.001
            && y >= Math.min(a.y, b.y) - 0.001
            && y <= Math.max(a.y, b.y) + 0.001
    }

    function _pointBeforeHit(start, hit) {
        var dx = start.x - hit.x
        var dy = start.y - hit.y
        var length = Math.sqrt(dx * dx + dy * dy)
        if (length < 1.5) return start
        var gap = 1.5
        return {
            x: hit.x + dx * gap / length,
            y: hit.y + dy * gap / length
        }
    }

}
