import QtQuick 2.15

QtObject {
    property var primitives: []
    property int selectedPrimIndex: -1
    property int selectedBlendIndex: -1
    property real scale: 1
    property var cx
    property var cy
    property var geometry
    property color highlightStrokeColor: "#E53935"
    property color highlightFillColor: "#E53935"
    property color highlightCenterColor: "#888888"
    property color blendColor: "#D97706"
    property real highlightLineWidth: 2
    property real blendLineWidth: 2.5
    property real startPointRadius: 6
    property real endPointRadius: 5
    property real centerPointRadius: 4

    function paint(ctx) {
        if (selectedPrimIndex < 0 && selectedBlendIndex < 0) return
        if (!primitives) return

        var targetIdx = (selectedPrimIndex >= 0) ? selectedPrimIndex : selectedBlendIndex
        if (targetIdx >= primitives.length) return

        var pos = geometry.walkToIndex(primitives, targetIdx)
        var logZ = pos.logZ
        var logX = pos.logX

        var p = primitives[targetIdx]
        ctx.setLineDash([])

        if (selectedPrimIndex >= 0) {
            // Full theoretical primitive (ignore blend trimming)
            ctx.strokeStyle = highlightStrokeColor
            ctx.lineWidth = highlightLineWidth
            ctx.lineJoin = "round"
            ctx.lineCap = "round"

            if (p.type === "startPoint") {
                ctx.fillStyle = highlightFillColor
                ctx.beginPath()
                ctx.arc(cx(+(p.z_start||0)), cy(+(p.x_start||0)), startPointRadius, 0, Math.PI*2)
                ctx.fill()

            } else if (p.type === "lineTo") {
                var ez = +(p.z_end||0)
                var ex = +(p.x_end||0)
                ctx.beginPath()
                ctx.moveTo(cx(logZ), cy(logX))
                ctx.lineTo(cx(ez), cy(ex))
                ctx.stroke()
                ctx.fillStyle = highlightFillColor
                ctx.beginPath()
                ctx.arc(cx(ez), cy(ex), endPointRadius, 0, Math.PI*2)
                ctx.fill()

            } else if (p.type === "arcTo") {
                var ez = +(p.z_end||0)
                var ex = +(p.x_end||0)
                var acz = +(p.z_center||0)
                var acx = +(p.x_center||0)
                var ar = +(p.arc_radius||0)
                var isCW = (p.direction === "cw")
                var ccx = cx(acz)
                var ccy = cy(acx)
                var cr = ar * scale
                var sa = Math.atan2(cy(logX) - ccy, cx(logZ) - ccx)
                var ea = Math.atan2(cy(ex)   - ccy, cx(ez)   - ccx)
                ctx.beginPath()
                ctx.arc(ccx, ccy, cr, sa, ea, !isCW)
                ctx.stroke()
                ctx.fillStyle = highlightFillColor
                ctx.beginPath()
                ctx.arc(cx(ez), cy(ex), endPointRadius, 0, Math.PI*2)
                ctx.fill()
                ctx.fillStyle = highlightCenterColor
                ctx.beginPath()
                ctx.arc(ccx, ccy, centerPointRadius, 0, Math.PI*2)
                ctx.fill()
            }

        } else {
            // Blend geometry only (amber)
            if (!p.blend || p.blend.type === "none") return
            ctx.strokeStyle = blendColor
            ctx.lineWidth = blendLineWidth
            ctx.lineJoin = "round"
            ctx.lineCap = "round"

            var bNextP = (targetIdx + 1 < primitives.length) ? primitives[targetIdx + 1] : null

            if (p.type === "lineTo") {
                var ez = +(p.z_end||0)
                var ex = +(p.x_end||0)

                if (p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var cg = geometry.chamferGeomLine(logZ, logX, ez, ex, bNextP, cw)
                    if (cg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(cg.csZ), cy(cg.csX))
                        ctx.lineTo(cx(cg.ceZ), cy(cg.ceX))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(cg.csZ), cy(cg.csX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(cg.ceZ), cy(cg.ceX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var fg = (bNextP && bNextP.type === "arcTo")
                              ? geometry.filletLineArc(logZ, logX, ez, ex, bNextP, fr)
                              : geometry.filletGeom(logZ, logX, ez, ex, bNextP, fr)
                    if (fg) {
                        var ccx = cx(fg.fcz)
                        var ccy = cy(fg.fcx)
                        var cr = fr * scale
                        var sa = Math.atan2(cy(fg.t1x) - ccy, cx(fg.t1z) - ccx)
                        var ea = Math.atan2(cy(fg.t2x) - ccy, cx(fg.t2z) - ccx)
                        ctx.beginPath()
                        ctx.arc(ccx, ccy, cr, sa, ea, fg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(fg.t1z), cy(fg.t1x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(fg.t2z), cy(fg.t2x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }

            } else if (p.type === "arcTo") {
                var ez = +(p.z_end||0)
                var ex = +(p.x_end||0)
                var acz = +(p.z_center||0)
                var acx = +(p.x_center||0)
                var ar = +(p.arc_radius||0)
                var isCW = (p.direction === "cw")

                if (p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var cg = geometry.chamferGeomArc(acz, acx, ar, isCW, ez, ex, bNextP, cw)
                    if (cg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(cg.csZ), cy(cg.csX))
                        ctx.lineTo(cx(cg.ceZ), cy(cg.ceX))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(cg.csZ), cy(cg.csX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(cg.ceZ), cy(cg.ceX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var fg = geometry.filletArcLine(acz, acx, ar, isCW, ez, ex, bNextP, fr)
                    if (fg) {
                        var ccx = cx(fg.fcz)
                        var ccy = cy(fg.fcx)
                        var cr = fr * scale
                        var sa = Math.atan2(cy(fg.t1x) - ccy, cx(fg.t1z) - ccx)
                        var ea = Math.atan2(cy(fg.t2x) - ccy, cx(fg.t2z) - ccx)
                        ctx.beginPath()
                        ctx.arc(ccx, ccy, cr, sa, ea, fg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(fg.t1z), cy(fg.t1x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(fg.t2z), cy(fg.t2x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }
            }
        }
    }
}