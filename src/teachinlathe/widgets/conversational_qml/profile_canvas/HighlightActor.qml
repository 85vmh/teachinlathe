import QtQuick 2.15

QtObject {
    property var    primitives: []
    property int    selectedPrimIndex: -1
    property int    selectedBlendIndex: -1
    property string profileType: "od"
    property real   scale: 1
    property var    cx
    property var    cy
    property var    geometry
    property color highlightStrokeColor: "#E53935"
    property color highlightFillColor: "#E53935"
    property color highlightCenterColor: "#888888"
    property color blendColor: "#D97706"
    property real highlightLineWidth: 2
    property real blendLineWidth: 2
    property real startPointRadius: 4
    property real endPointRadius: 3
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
                var sa = Math.atan2(cy(logX) - ccy, cx(logZ) - ccx)
                var cr = Math.sqrt(Math.pow(cx(logZ) - ccx, 2) + Math.pow(cy(logX) - ccy, 2))
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

            if (p.type === "startPoint") {
                var spLogZ = +(p.z_start || 0)
                var spLogX = +(p.x_start || 0)
                var spLX2 = spLogX / 2
                var spNextPH = geometry.halfXPrim(bNextP)
                var isID = String(profileType || "od").toLowerCase() === "id"

                if (p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var spEntryXC = isID ? spLX2 + cw : spLX2 - cw
                    var cg = geometry.chamferGeomLine(spLogZ, spEntryXC, spLogZ, spLX2, spNextPH, cw)
                    if (cg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(cg.csZ), cy(cg.csX * 2))
                        ctx.lineTo(cx(cg.ceZ), cy(cg.ceX * 2))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(cg.csZ), cy(cg.csX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(cg.ceZ), cy(cg.ceX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var spEntryXF = isID ? spLX2 + fr : spLX2 - fr
                    var fg = (bNextP && bNextP.type === "arcTo")
                              ? geometry.filletLineArc(spLogZ, spEntryXF, spLogZ, spLX2, spNextPH, fr)
                              : geometry.filletGeom(spLogZ, spEntryXF, spLogZ, spLX2, spNextPH, fr)
                    if (fg) {
                        var fccx = cx(fg.fcz)
                        var fccy = cy(fg.fcx * 2)
                        var fsa = Math.atan2(cy(fg.t1x * 2) - fccy, cx(fg.t1z) - fccx)
                        var fcr = Math.sqrt(Math.pow(cx(fg.t1z) - fccx, 2) + Math.pow(cy(fg.t1x * 2) - fccy, 2))
                        var fea = Math.atan2(cy(fg.t2x * 2) - fccy, cx(fg.t2z) - fccx)
                        ctx.beginPath()
                        ctx.arc(fccx, fccy, fcr, fsa, fea, fg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(fg.t1z), cy(fg.t1x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(fg.t2z), cy(fg.t2x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }

            } else if (p.type === "lineTo") {
                var ez = +(p.z_end||0)
                var ex = +(p.x_end||0)
                var bNextPH = geometry.halfXPrim(bNextP)

                if (p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var cg = geometry.chamferGeomLine(logZ, logX / 2, ez, ex / 2, bNextPH, cw)
                    if (cg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(cg.csZ), cy(cg.csX * 2))
                        ctx.lineTo(cx(cg.ceZ), cy(cg.ceX * 2))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(cg.csZ), cy(cg.csX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(cg.ceZ), cy(cg.ceX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var fg = (bNextP && bNextP.type === "arcTo")
                              ? geometry.filletLineArc(logZ, logX / 2, ez, ex / 2, bNextPH, fr)
                              : geometry.filletGeom(logZ, logX / 2, ez, ex / 2, bNextPH, fr)
                    if (fg) {
                        var fccx = cx(fg.fcz)
                        var fccy = cy(fg.fcx * 2)
                        var fsa = Math.atan2(cy(fg.t1x * 2) - fccy, cx(fg.t1z) - fccx)
                        var fcr = Math.sqrt(Math.pow(cx(fg.t1z) - fccx, 2) + Math.pow(cy(fg.t1x * 2) - fccy, 2))
                        var fea = Math.atan2(cy(fg.t2x * 2) - fccy, cx(fg.t2z) - fccx)
                        ctx.beginPath()
                        ctx.arc(fccx, fccy, fcr, fsa, fea, fg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(fg.t1z), cy(fg.t1x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(fg.t2z), cy(fg.t2x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "undercut_din509") {
                    var undercutRadius = geometry.undercutBlendValue(p.blend, "undercut_radius", 0.4)
                    var undercutDepth = geometry.undercutBlendValue(p.blend, "undercut_depth", 0.4)
                    var undercutLength = geometry.undercutBlendValue(p.blend, "undercut_length", 2.5)
                    var undercutGeom = geometry.undercutDin509Geom(logZ, logX / 2, ez, ex / 2, bNextPH, undercutRadius, undercutDepth, undercutLength)
                    if (undercutGeom) {
                        ctx.beginPath()
                        ctx.moveTo(cx(undercutGeom.entryZ), cy(undercutGeom.entryX * 2))
                        for (var undercutSegmentIndex = 0; undercutSegmentIndex < undercutGeom.segs.length; undercutSegmentIndex++) {
                            var undercutSegment = undercutGeom.segs[undercutSegmentIndex]
                            if (undercutSegment.type === "line") {
                                ctx.lineTo(cx(undercutSegment.z), cy(undercutSegment.x * 2))
                            } else {
                                var undercutArcCenterCanvasX = cx(undercutSegment.cz)
                                var undercutArcCenterCanvasY = cy(undercutSegment.cx * 2)
                                // recompute radius from actual canvas coords of start point of this arc
                                var prevZ = (undercutSegmentIndex === 0) ? undercutGeom.entryZ : undercutGeom.segs[undercutSegmentIndex - 1].z
                                var prevX = (undercutSegmentIndex === 0) ? undercutGeom.entryX : undercutGeom.segs[undercutSegmentIndex - 1].x
                                var undercutArcCanvasRadius = Math.sqrt(Math.pow(cx(prevZ) - undercutArcCenterCanvasX, 2) + Math.pow(cy(prevX * 2) - undercutArcCenterCanvasY, 2))
                                var undercutArcStartAngle = Math.atan2(cy(prevX * 2) - undercutArcCenterCanvasY, cx(prevZ) - undercutArcCenterCanvasX)
                                var undercutArcEndAngle = Math.atan2(cy(undercutSegment.x * 2) - undercutArcCenterCanvasY, cx(undercutSegment.z) - undercutArcCenterCanvasX)
                                ctx.arc(undercutArcCenterCanvasX, undercutArcCenterCanvasY, undercutArcCanvasRadius, undercutArcStartAngle, undercutArcEndAngle, undercutSegment.anticlockwise)
                            }
                        }
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(undercutGeom.entryZ), cy(undercutGeom.entryX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(undercutGeom.exitZ), cy(undercutGeom.exitX * 2), endPointRadius, 0, Math.PI*2)
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
                var ex2h = ex / 2, acx2h = acx / 2
                var ar2h = Math.sqrt((ex2h - acx2h) * (ex2h - acx2h) + (ez - acz) * (ez - acz))
                var bNextPH = geometry.halfXPrim(bNextP)

                if (p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var cg = geometry.chamferGeomArc(acz, acx2h, ar2h, isCW, ez, ex2h, bNextPH, cw)
                    if (cg) {
                        ctx.beginPath()
                        ctx.moveTo(cx(cg.csZ), cy(cg.csX * 2))
                        ctx.lineTo(cx(cg.ceZ), cy(cg.ceX * 2))
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(cg.csZ), cy(cg.csX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(cg.ceZ), cy(cg.ceX * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var fg = geometry.filletArcLine(acz, acx2h, ar2h, isCW, ez, ex2h, bNextPH, fr)
                    if (fg) {
                        var fccx = cx(fg.fcz)
                        var fccy = cy(fg.fcx * 2)
                        var fsa = Math.atan2(cy(fg.t1x * 2) - fccy, cx(fg.t1z) - fccx)
                        var fcr = Math.sqrt(Math.pow(cx(fg.t1z) - fccx, 2) + Math.pow(cy(fg.t1x * 2) - fccy, 2))
                        var fea = Math.atan2(cy(fg.t2x * 2) - fccy, cx(fg.t2z) - fccx)
                        ctx.beginPath()
                        ctx.arc(fccx, fccy, fcr, fsa, fea, fg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = blendColor
                        ctx.beginPath()
                        ctx.arc(cx(fg.t1z), cy(fg.t1x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                        ctx.beginPath()
                        ctx.arc(cx(fg.t2z), cy(fg.t2x * 2), endPointRadius, 0, Math.PI*2)
                        ctx.fill()
                    }
                }
            }
        }
    }
}
