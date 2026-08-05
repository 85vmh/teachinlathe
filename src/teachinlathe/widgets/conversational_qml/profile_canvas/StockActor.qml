import QtQuick 2.15

QtObject {
    property var workpiece: ({})
    property var renderSegs: []
    property string profileType: "od"
    property var cx
    property var cy

    readonly property real stockLength: workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
    readonly property real externalDiameter: workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
    readonly property real internalDiameter: workpiece && workpiece.internal_diameter !== undefined ? Number(workpiece.internal_diameter) : 0

    function _pathProfileToStock(ctx, stockX) {
        var started = false
        var stockStartZ = 0
        var stockEndZ = -Math.max(0, stockLength)
        var drawZ = 0
        var drawX = 0
        for (var i = 0; i < (renderSegs || []).length; i++) {
            var s = renderSegs[i]
            if (s.type === "move") {
                if (!started) {
                    ctx.moveTo(cx(stockStartZ), cy(stockX))
                    ctx.lineTo(cx(stockStartZ), cy(s.x))
                    ctx.lineTo(cx(s.z), cy(s.x))
                    started = true
                } else {
                    ctx.lineTo(cx(drawZ), cy(stockX))
                    ctx.lineTo(cx(s.z), cy(stockX))
                    ctx.lineTo(cx(s.z), cy(s.x))
                }
                drawZ = s.z
                drawX = s.x
            } else if (s.type === "line") {
                ctx.lineTo(cx(s.z), cy(s.x))
                drawZ = s.z
                drawX = s.x
            } else if (s.type === "arc") {
                var ccx = cx(s.zc)
                var ccy = cy(s.xc)
                var sa = Math.atan2(cy(drawX) - ccy, cx(drawZ) - ccx)
                var cr = Math.sqrt(Math.pow(cx(drawZ) - ccx, 2) + Math.pow(cy(drawX) - ccy, 2))
                var ea = Math.atan2(cy(s.x) - ccy, cx(s.z) - ccx)
                ctx.arc(ccx, ccy, cr, sa, ea, s.anticlockwise)
                drawZ = s.z
                drawX = s.x
            }
        }
        if (!started) return false
        ctx.lineTo(cx(stockEndZ), cy(drawX))
        ctx.lineTo(cx(stockEndZ), cy(stockX))
        ctx.lineTo(cx(stockStartZ), cy(stockX))
        ctx.closePath()
        return true
    }

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
        var stockZ = -Math.max(0, stockLength)
        var stockX = Math.max(0, externalDiameter)
        if (stockLength <= 0 || stockX <= 0 || !cx || !cy) return

        var left = cx(0)
        var right = cx(stockZ)
        var top = cy(0)
        var bottom = cy(stockX)
        var hasInternalDiameter = internalDiameter > 0
        var innerX = hasInternalDiameter ? Math.max(0, Math.min(internalDiameter, stockX)) : 0

        ctx.save()
        ctx.beginPath()
        ctx.rect(Math.min(left, right), Math.min(top, bottom), Math.abs(right - left), Math.abs(bottom - top))
        ctx.clip()

        var profileMode = String(profileType || "od").toLowerCase()
        var hatchBoundaryX = profileMode === "id" ? stockX : innerX
        if (profileMode === "od" || profileMode === "id") {
            ctx.save()
            ctx.beginPath()
            if (_pathProfileToStock(ctx, hatchBoundaryX)) {
                ctx.clip()
                _hatchCurrentClip(ctx, Math.min(left, right), Math.min(top, bottom), Math.max(left, right), Math.max(top, bottom))
            }
            ctx.restore()
        }
        ctx.restore()

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

        if (hasInternalDiameter && innerX > 0) {
            ctx.strokeStyle = "#aeb4bd"
            ctx.beginPath()
            ctx.moveTo(left, cy(innerX))
            ctx.lineTo(right, cy(innerX))
            ctx.stroke()
        }
    }
}
