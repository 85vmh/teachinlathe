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
    property bool   mirrorAcrossCenterline: false
    property color highlightStrokeColor: "#E53935"
    property color highlightFillColor: "#E53935"
    property color highlightCenterColor: "#888888"
    property color blendColor: "#D97706"
    property real highlightLineWidth: 2
    property real blendLineWidth: 2
    property real startPointRadius: 4
    property real endPointRadius: 3
    property real centerPointRadius: 4
    // Mirrored, the selection's colour also fills the band between it and
    // its mirror image, at this opacity (70% transparent).
    property real overlayOpacity: 0.3

    function paint(ctx) {
        var sel = _selection()
        if (!sel) return
        ctx.setLineDash([])
        ctx.lineJoin = "round"
        ctx.lineCap = "round"

        if (mirrorAcrossCenterline) {
            if (sel.trace) {
                _paintOverlay(ctx, sel, false)
                _paintOverlay(ctx, sel, true)
            } else if (sel.startPoint) {
                // A start point has no extent; join it to its mirror instead.
                ctx.strokeStyle = sel.color
                ctx.lineWidth = sel.lineWidth
                ctx.beginPath()
                ctx.moveTo(cx(sel.startPoint.z), cy(sel.startPoint.x))
                ctx.lineTo(cx(sel.startPoint.z), cy(-sel.startPoint.x))
                ctx.stroke()
            }
        }

        _paintSelection(ctx, sel, false)
        if (mirrorAcrossCenterline)
            _paintSelection(ctx, sel, true)
    }

    // ── Drawing ──────────────────────────────────────────────────────────────

    // Reflect everything drawn until the matching restore() across the centre
    // line. Done on the context rather than the coordinates, so arcs turn the
    // right way round without each one being worked out again.
    function _beginHalf(ctx, mirrored) {
        ctx.save()
        if (mirrored) {
            ctx.translate(0, 2 * cy(0))
            ctx.scale(1, -1)
        }
    }

    function _paintSelection(ctx, sel, mirrored) {
        _beginHalf(ctx, mirrored)
        if (sel.trace) {
            ctx.strokeStyle = sel.color
            ctx.lineWidth = sel.lineWidth
            ctx.beginPath()
            sel.trace(ctx)
            ctx.stroke()
        }
        for (var i = 0; i < sel.points.length; i++) {
            var pt = sel.points[i]
            ctx.fillStyle = pt.color
            ctx.beginPath()
            ctx.arc(cx(pt.z), cy(pt.x), pt.r, 0, Math.PI * 2)
            ctx.fill()
        }
        ctx.restore()
    }

    // The area between the selection and the centre line, from where it
    // starts along Z to where it ends; drawn once per half, the two together
    // fill the band between the selection and its mirror image.
    function _paintOverlay(ctx, sel, mirrored) {
        _beginHalf(ctx, mirrored)
        ctx.globalAlpha = overlayOpacity
        ctx.fillStyle = sel.color
        ctx.beginPath()
        sel.trace(ctx)
        ctx.lineTo(cx(sel.endZ), cy(0))
        ctx.lineTo(cx(sel.startZ), cy(0))
        ctx.closePath()
        ctx.fill()
        ctx.restore()
    }

    // ── What is selected ─────────────────────────────────────────────────────
    //
    // Returns null, or:
    //   color, lineWidth
    //   trace(ctx)      adds the selected curve to the current path, starting
    //                   with a moveTo; absent for a start point
    //   startZ, endZ    where the curve starts and ends along Z
    //   points          dots to draw: {z, x, r, color}, x as a diameter
    //   startPoint      {z, x} when the selection is the start point itself

    function _point(z, x, r, color) { return { z: z, x: x, r: r, color: color } }

    function _arcTrace(centerZ, centerX, startZ, startX, endZ, endX, anticlockwise) {
        return function(ctx) {
            var ccx = cx(centerZ)
            var ccy = cy(centerX)
            var sa = Math.atan2(cy(startX) - ccy, cx(startZ) - ccx)
            var cr = Math.sqrt(Math.pow(cx(startZ) - ccx, 2) + Math.pow(cy(startX) - ccy, 2))
            var ea = Math.atan2(cy(endX) - ccy, cx(endZ) - ccx)
            ctx.moveTo(cx(startZ), cy(startX))
            ctx.arc(ccx, ccy, cr, sa, ea, anticlockwise)
        }
    }

    function _lineTrace(startZ, startX, endZ, endX) {
        return function(ctx) {
            ctx.moveTo(cx(startZ), cy(startX))
            ctx.lineTo(cx(endZ), cy(endX))
        }
    }

    // A chamfer from the geometry helpers, in radius units.
    function _chamfer(cg) {
        if (!cg) return null
        return {
            color: blendColor, lineWidth: blendLineWidth,
            trace: _lineTrace(cg.csZ, cg.csX * 2, cg.ceZ, cg.ceX * 2),
            startZ: cg.csZ, endZ: cg.ceZ,
            points: [_point(cg.csZ, cg.csX * 2, endPointRadius, blendColor),
                     _point(cg.ceZ, cg.ceX * 2, endPointRadius, blendColor)]
        }
    }

    // A fillet from the geometry helpers, in radius units.
    function _fillet(fg) {
        if (!fg) return null
        return {
            color: blendColor, lineWidth: blendLineWidth,
            trace: _arcTrace(fg.fcz, fg.fcx * 2, fg.t1z, fg.t1x * 2, fg.t2z, fg.t2x * 2, fg.anticlockwise),
            startZ: fg.t1z, endZ: fg.t2z,
            points: [_point(fg.t1z, fg.t1x * 2, endPointRadius, blendColor),
                     _point(fg.t2z, fg.t2x * 2, endPointRadius, blendColor)]
        }
    }

    function _undercut(ug) {
        if (!ug) return null
        return {
            color: blendColor, lineWidth: blendLineWidth,
            trace: function(ctx) {
                ctx.moveTo(cx(ug.entryZ), cy(ug.entryX * 2))
                for (var i = 0; i < ug.segs.length; i++) {
                    var seg = ug.segs[i]
                    if (seg.type === "line") {
                        ctx.lineTo(cx(seg.z), cy(seg.x * 2))
                    } else {
                        var ccx = cx(seg.cz)
                        var ccy = cy(seg.cx * 2)
                        // radius from the canvas position of this arc's start point
                        var prevZ = (i === 0) ? ug.entryZ : ug.segs[i - 1].z
                        var prevX = (i === 0) ? ug.entryX : ug.segs[i - 1].x
                        var cr = Math.sqrt(Math.pow(cx(prevZ) - ccx, 2) + Math.pow(cy(prevX * 2) - ccy, 2))
                        var sa = Math.atan2(cy(prevX * 2) - ccy, cx(prevZ) - ccx)
                        var ea = Math.atan2(cy(seg.x * 2) - ccy, cx(seg.z) - ccx)
                        ctx.arc(ccx, ccy, cr, sa, ea, seg.anticlockwise)
                    }
                }
            },
            startZ: ug.entryZ, endZ: ug.exitZ,
            points: [_point(ug.entryZ, ug.entryX * 2, endPointRadius, blendColor),
                     _point(ug.exitZ, ug.exitX * 2, endPointRadius, blendColor)]
        }
    }

    function _selection() {
        if (selectedPrimIndex < 0 && selectedBlendIndex < 0) return null
        if (!primitives) return null

        var targetIdx = (selectedPrimIndex >= 0) ? selectedPrimIndex : selectedBlendIndex
        if (targetIdx >= primitives.length) return null

        var pos = geometry.walkToIndex(primitives, targetIdx)
        var logZ = pos.logZ
        var logX = pos.logX
        var p = primitives[targetIdx]

        if (selectedPrimIndex >= 0) {
            // Full theoretical primitive (ignore blend trimming)
            if (p.type === "startPoint") {
                var sz = +(p.z_start || 0)
                var sx = +(p.x_start || 0)
                return {
                    color: highlightStrokeColor, lineWidth: highlightLineWidth,
                    startPoint: { z: sz, x: sx },
                    points: [_point(sz, sx, startPointRadius, highlightFillColor)]
                }
            }
            if (p.type === "lineTo") {
                var lz = +(p.z_end || 0)
                var lx = +(p.x_end || 0)
                return {
                    color: highlightStrokeColor, lineWidth: highlightLineWidth,
                    trace: _lineTrace(logZ, logX, lz, lx),
                    startZ: logZ, endZ: lz,
                    points: [_point(lz, lx, endPointRadius, highlightFillColor)]
                }
            }
            if (p.type === "arcTo") {
                var az = +(p.z_end || 0)
                var ax = +(p.x_end || 0)
                var acz = +(p.z_center || 0)
                var acx = +(p.x_center || 0)
                return {
                    color: highlightStrokeColor, lineWidth: highlightLineWidth,
                    trace: _arcTrace(acz, acx, logZ, logX, az, ax, p.direction !== "cw"),
                    startZ: logZ, endZ: az,
                    points: [_point(az, ax, endPointRadius, highlightFillColor),
                             _point(acz, acx, centerPointRadius, highlightCenterColor)]
                }
            }
            return null
        }

        // Blend geometry only (amber)
        if (!p.blend || p.blend.type === "none") return null
        var bNextP = (targetIdx + 1 < primitives.length) ? primitives[targetIdx + 1] : null
        var bNextPH = geometry.halfXPrim(bNextP)

        if (p.type === "startPoint") {
            var spLogZ = +(p.z_start || 0)
            var spLX2 = +(p.x_start || 0) / 2
            var isID = String(profileType || "od").toLowerCase() === "id"

            if (p.blend.type === "chamfer") {
                var scw = +(p.blend.chamfer_width || 0)
                var spEntryXC = isID ? spLX2 + scw : spLX2 - scw
                return _chamfer(geometry.chamferGeomLine(spLogZ, spEntryXC, spLogZ, spLX2, bNextPH, scw))
            }
            if (p.blend.type === "fillet") {
                var sfr = +(p.blend.fillet_radius || 0)
                var spEntryXF = isID ? spLX2 + sfr : spLX2 - sfr
                return _fillet((bNextP && bNextP.type === "arcTo")
                               ? geometry.filletLineArc(spLogZ, spEntryXF, spLogZ, spLX2, bNextPH, sfr)
                               : geometry.filletGeom(spLogZ, spEntryXF, spLogZ, spLX2, bNextPH, sfr))
            }
            return null
        }

        if (p.type === "lineTo") {
            var ez = +(p.z_end || 0)
            var ex = +(p.x_end || 0)

            if (p.blend.type === "chamfer") {
                var cw = +(p.blend.chamfer_width || 0)
                return _chamfer(geometry.chamferGeomLine(logZ, logX / 2, ez, ex / 2, bNextPH, cw))
            }
            if (p.blend.type === "fillet") {
                var fr = +(p.blend.fillet_radius || 0)
                return _fillet((bNextP && bNextP.type === "arcTo")
                               ? geometry.filletLineArc(logZ, logX / 2, ez, ex / 2, bNextPH, fr)
                               : geometry.filletGeom(logZ, logX / 2, ez, ex / 2, bNextPH, fr))
            }
            if (p.blend.type === "undercut_din509") {
                var undercutRadius = geometry.undercutBlendValue(p.blend, "undercut_radius", 0.4)
                var undercutDepth = geometry.undercutBlendValue(p.blend, "undercut_depth", 0.4)
                var undercutLength = geometry.undercutBlendValue(p.blend, "undercut_length", 2.5)
                return _undercut(geometry.undercutDin509Geom(logZ, logX / 2, ez, ex / 2, bNextPH,
                                                             undercutRadius, undercutDepth, undercutLength))
            }
            return null
        }

        if (p.type === "arcTo") {
            var arcEz = +(p.z_end || 0)
            var arcEx2h = +(p.x_end || 0) / 2
            var arcCz = +(p.z_center || 0)
            var arcCx2h = +(p.x_center || 0) / 2
            var isCW = (p.direction === "cw")
            var ar2h = Math.sqrt((arcEx2h - arcCx2h) * (arcEx2h - arcCx2h) + (arcEz - arcCz) * (arcEz - arcCz))

            if (p.blend.type === "chamfer") {
                var acw = +(p.blend.chamfer_width || 0)
                return _chamfer(geometry.chamferGeomArc(arcCz, arcCx2h, ar2h, isCW, arcEz, arcEx2h, bNextPH, acw))
            }
            if (p.blend.type === "fillet") {
                var afr = +(p.blend.fillet_radius || 0)
                return _fillet(geometry.filletArcLine(arcCz, arcCx2h, ar2h, isCW, arcEz, arcEx2h, bNextPH, afr))
            }
        }
        return null
    }
}
