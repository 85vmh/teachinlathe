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
                var aez = +(p.z_end||0)
                var aex = +(p.x_end||0)
                var acz = +(p.z_center||0)
                var acx = +(p.x_center||0)
                var ar = +(p.arc_radius||0)
                var isCW2 = (p.direction === "cw")
                var ccx = cx(acz)
                var ccy = cy(acx)
                var cr2 = ar * scale
                var sa2 = Math.atan2(cy(logX) - ccy, cx(logZ) - ccx)
                var ea2 = Math.atan2(cy(aex)  - ccy, cx(aez)  - ccx)
                ctx.beginPath()
                ctx.arc(ccx, ccy, cr2, sa2, ea2, !isCW2)
                ctx.stroke()
                ctx.fillStyle = highlightFillColor
                ctx.beginPath()
                ctx.arc(cx(aez), cy(aex), endPointRadius, 0, Math.PI*2)
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
                var lez = +(p.z_end||0)
                var lex = +(p.x_end||0)

                if (p.blend.type === "chamfer") {
                    var lcw  = +(p.blend.chamfer_width || 0)
                    var lcg = geometry.chamferGeomLine(logZ, logX, lez, lex, bNextP, lcw)
                    if (lcg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(lcg.csZ), cy(lcg.csX))
                        ctx.lineTo(cx(lcg.ceZ), cy(lcg.ceX))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(lcg.csZ), cy(lcg.csX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(lcg.ceZ), cy(lcg.ceX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var lfr = +(p.blend.fillet_radius || 0)
                    var lfg = (bNextP && bNextP.type === "arcTo")
                              ? geometry.filletLineArc(logZ, logX, lez, lex, bNextP, lfr)
                              : geometry.filletGeom(logZ, logX, lez, lex, bNextP, lfr)
                    if (lfg) {
                        var lfccx = cx(lfg.fcz)
                        var lfccy = cy(lfg.fcx)
                        var lfcr = lfr * scale
                        var lfsa = Math.atan2(cy(lfg.t1x) - lfccy, cx(lfg.t1z) - lfccx)
                        var lfea = Math.atan2(cy(lfg.t2x) - lfccy, cx(lfg.t2z) - lfccx)
                        ctx.beginPath()
                        ctx.arc(lfccx, lfccy, lfcr, lfsa, lfea, lfg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(lfg.t1z), cy(lfg.t1x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(lfg.t2z), cy(lfg.t2x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }

            } else if (p.type === "arcTo") {
                var aaez = +(p.z_end||0)
                var aaex = +(p.x_end||0)
                var aacz = +(p.z_center||0)
                var aacx = +(p.x_center||0)
                var aar = +(p.arc_radius||0)
                var aisCW = (p.direction === "cw")

                if (p.blend.type === "chamfer") {
                    var aacw  = +(p.blend.chamfer_width || 0)
                    var acg2 = geometry.chamferGeomArc(aacz, aacx, aar, aisCW, aaez, aaex, bNextP, aacw)
                    if (acg2) {
                        ctx.beginPath()
                        ctx.moveTo(cx(acg2.csZ), cy(acg2.csX))
                        ctx.lineTo(cx(acg2.ceZ), cy(acg2.ceX))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(acg2.csZ), cy(acg2.csX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(acg2.ceZ), cy(acg2.ceX), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var aafr = +(p.blend.fillet_radius || 0)
                    var aafg = geometry.filletArcLine(aacz, aacx, aar, aisCW, aaez, aaex, bNextP, aafr)
                    if (aafg) {
                        var aafccx = cx(aafg.fcz)
                        var aafccy = cy(aafg.fcx)
                        var aafcr = aafr * scale
                        var aafsa = Math.atan2(cy(aafg.t1x) - aafccy, cx(aafg.t1z) - aafccx)
                        var aafea = Math.atan2(cy(aafg.t2x) - aafccy, cx(aafg.t2z) - aafccx)
                        ctx.beginPath()
                        ctx.arc(aafccx, aafccy, aafcr, aafsa, aafea, aafg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(aafg.t1z), cy(aafg.t1x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(aafg.t2z), cy(aafg.t2x), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }
            }
        }
    }
}
