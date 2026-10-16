import QtQuick 2.15
import theme 1.0
import "brokenstock.js" as Broken

QtObject {
    property var workpiece: ({})
    property var renderSegs: []
    property string profileType: "od"
    property var cx
    property var cy
    property bool mirrorAcrossCenterline: false

    readonly property real stockLength: workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
    readonly property real externalDiameter: workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
    readonly property real internalDiameter: workpiece && workpiece.internal_diameter !== undefined ? Number(workpiece.internal_diameter) : 0
    // where the raw face is: Z0 unless the stock still stands proud of it,
    // as before facing
    readonly property real faceZ: workpiece && workpiece.face_z !== undefined ? Math.max(0, Number(workpiece.face_z)) : 0
    // drawn with its far end broken off - stock_length is then how much of
    // it is drawn, not how long it is - opaque over the grid, as the Program
    // Header shows it; see brokenstock.js
    readonly property bool breakFarEnd: !!(workpiece && workpiece.break_far_end)
    // and a stretch of its middle left out too: {near, far} in drawn Z, where
    // the piece at the face and the far piece are broken off, or null
    readonly property var breakMiddle: workpiece && workpiece.break_middle ? workpiece.break_middle : null

    // the colours and pitch the stock is drawn in, whole or broken
    readonly property color hatchColor:   "#d5d9df"
    readonly property color outlineColor: "#6b7280"
    readonly property color boreColor:    "#aeb4bd"
    // the cut face of a broken end: its ground a shade darker than the
    // stock's, its hatch darker again so it still stands out on it
    readonly property color lensFillColor:  "#e5e7eb"
    readonly property color lensHatchColor: "#a3aab4"
    readonly property real  hatchPitch:   12
    // the outline and the bore lines; the hatch stays at one px
    readonly property real  outlineWidth: 1.5

    // Canvas y of diameter x, on the mirrored half (above the centre line)
    // when asked.
    function _cy(x, mirrored) { return cy(mirrored ? -x : x) }

    function _pathProfileToStock(ctx, stockX, mirrored) {
        var started = false
        var stockStartZ = 0
        var stockEndZ = -Math.max(0, stockLength)
        var drawZ = 0
        var drawX = 0
        for (var i = 0; i < (renderSegs || []).length; i++) {
            var s = renderSegs[i]
            if (s.type === "move") {
                if (!started) {
                    ctx.moveTo(cx(stockStartZ), _cy(stockX, mirrored))
                    ctx.lineTo(cx(stockStartZ), _cy(s.x, mirrored))
                    ctx.lineTo(cx(s.z), _cy(s.x, mirrored))
                    started = true
                } else {
                    ctx.lineTo(cx(drawZ), _cy(stockX, mirrored))
                    ctx.lineTo(cx(s.z), _cy(stockX, mirrored))
                    ctx.lineTo(cx(s.z), _cy(s.x, mirrored))
                }
                drawZ = s.z
                drawX = s.x
            } else if (s.type === "line") {
                ctx.lineTo(cx(s.z), _cy(s.x, mirrored))
                drawZ = s.z
                drawX = s.x
            } else if (s.type === "arc") {
                var ccx = cx(s.zc)
                var ccy = _cy(s.xc, mirrored)
                var sa = Math.atan2(_cy(drawX, mirrored) - ccy, cx(drawZ) - ccx)
                var cr = Math.sqrt(Math.pow(cx(drawZ) - ccx, 2) + Math.pow(_cy(drawX, mirrored) - ccy, 2))
                var ea = Math.atan2(_cy(s.x, mirrored) - ccy, cx(s.z) - ccx)
                // reflected across the centre line, the arc turns the other way
                ctx.arc(ccx, ccy, cr, sa, ea, mirrored ? !s.anticlockwise : s.anticlockwise)
                drawZ = s.z
                drawX = s.x
            }
        }
        if (!started) return false
        ctx.lineTo(cx(stockEndZ), _cy(drawX, mirrored))
        ctx.lineTo(cx(stockEndZ), _cy(stockX, mirrored))
        ctx.lineTo(cx(stockStartZ), _cy(stockX, mirrored))
        ctx.closePath()
        return true
    }

    function _hatchCurrentClip(ctx, left, top, right, bottom) {
        var spacing = hatchPitch
        var overshoot = bottom - top
        ctx.strokeStyle = hatchColor
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
        var stockZ = -Math.max(0, stockLength)
        var stockX = Math.max(0, externalDiameter)
        if (stockLength <= 0 || stockX <= 0 || !cx || !cy) return

        if (breakFarEnd) {
            var innerX = Math.max(0, Math.min(internalDiameter, stockX))
            var R = cy(stockX) - cy(0), r = innerX > 0 ? cy(innerX) - cy(0) : 0
            var style = { fill: Theme.surface, hatch: hatchColor, hatchPitch: hatchPitch,
                          outline: outlineColor, bore: boreColor, lineWidth: outlineWidth,
                          lensFill: lensFillColor, lensHatch: lensHatchColor }
            if (breakMiddle) {
                // the piece at the face, broken off at the gap; the far piece,
                // broken at both its ends
                Broken.piece(ctx, cx(breakMiddle.near), cx(faceZ), cy(0), R, r, true, false, style)
                Broken.piece(ctx, cx(stockZ), cx(breakMiddle.far), cy(0), R, r, true, true, style)
            } else {
                Broken.paint(ctx, cx(faceZ), cx(stockZ), cy(0), R, r, style)
            }
            return
        }

        _paintHalf(ctx, stockZ, stockX, false)
        if (mirrorAcrossCenterline)
            _paintHalf(ctx, stockZ, stockX, true)
    }

    // One half of the stock: below the centre line, or its mirror above it.
    function _paintHalf(ctx, stockZ, stockX, mirrored) {
        var left = cx(faceZ)
        var right = cx(stockZ)
        var top = cy(0)
        var bottom = _cy(stockX, mirrored)
        var hasInternalDiameter = internalDiameter > 0
        var innerX = hasInternalDiameter ? Math.max(0, Math.min(internalDiameter, stockX)) : 0

        ctx.save()
        ctx.beginPath()
        ctx.rect(Math.min(left, right), Math.min(top, bottom), Math.abs(right - left), Math.abs(bottom - top))
        ctx.clip()

        var profileMode = String(profileType || "od").toLowerCase()
        var hatchBoundaryX = profileMode === "id" ? stockX : innerX
        if (!renderSegs || renderSegs.length === 0) {
            // no profile yet: the whole stock, outside the bore, is material
            var innerY = _cy(innerX, mirrored)
            ctx.save()
            ctx.beginPath()
            ctx.rect(Math.min(left, right), Math.min(innerY, bottom), Math.abs(right - left), Math.abs(bottom - innerY))
            ctx.clip()
            _hatchCurrentClip(ctx, Math.min(left, right), Math.min(top, bottom), Math.max(left, right), Math.max(top, bottom))
            ctx.restore()
        } else if (profileMode === "od" || profileMode === "id") {
            ctx.save()
            ctx.beginPath()
            if (_pathProfileToStock(ctx, hatchBoundaryX, mirrored)) {
                ctx.clip()
                _hatchCurrentClip(ctx, Math.min(left, right), Math.min(top, bottom), Math.max(left, right), Math.max(top, bottom))
            }
            ctx.restore()
        }
        ctx.restore()

        // its outside and its far end; its face only when it stands proud of
        // Z0 - at Z0 the dashed Z0 line goes, and only the finished profile
        // is drawn over that
        ctx.strokeStyle = outlineColor
        ctx.lineWidth = outlineWidth
        ctx.setLineDash([])
        ctx.beginPath()
        ctx.moveTo(left, bottom)
        ctx.lineTo(right, bottom)
        ctx.lineTo(right, top)
        if (faceZ > 0) {
            ctx.moveTo(left, bottom)
            ctx.lineTo(left, top)
        }
        ctx.stroke()

        if (hasInternalDiameter && innerX > 0) {
            ctx.strokeStyle = boreColor
            ctx.beginPath()
            ctx.moveTo(left, _cy(innerX, mirrored))
            ctx.lineTo(right, _cy(innerX, mirrored))
            ctx.stroke()
        }
    }
}
