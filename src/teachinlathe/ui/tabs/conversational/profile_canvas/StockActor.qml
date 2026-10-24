import QtQuick
import theme
import "brokenstock.js" as Broken

QtObject {
    property var workpiece: ({})
    property var renderSegs: []
    property string profileType: "od"
    property var cx
    property var cy
    property bool mirrorAcrossCenterline: false
    // while the view moves: the finished part inside a broken stock not
    // hatched - its clips cost the most of anything the canvas draws
    property bool simplified: false

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
    // Profile Roughing's and Contour's: with a profile, broken off after it -
    // where the profile ends, set back by as far as the break bends in and
    // then by the break's whole width again, a stretch of plain stock before
    // it - instead of drawn on to its full length; the finished part hatched
    // as before. Only while mirrored: with the mirror off no stock is drawn,
    // the profile alone
    readonly property bool breakAfterProfile: !!(workpiece && workpiece.break_after_profile)
                                              && !!renderSegs && renderSegs.length > 0
    // Facing's and Drilling's: broken off after Z End, in mm - set back by
    // as far as the break bends in and then by twice the break's width - or
    // null. The same rules as after a profile; only while mirrored
    readonly property var breakAfterZ: workpiece && workpiece.break_after_z !== undefined
                                       && workpiece.break_after_z !== null ? Number(workpiece.break_after_z) : null
    // Facing's: where the face ends up, in mm - the stock in front of it,
    // faced off, not drawn - or null: the face where it is
    readonly property var facedTo: workpiece && workpiece.faced_to !== undefined
                                   && workpiece.faced_to !== null ? Number(workpiece.faced_to) : null

    // Where the profile ends, its smallest Z, in mm.
    function profileEndZ() {
        var zMin = 0
        for (var i = 0; i < renderSegs.length; i++)
            if (renderSegs[i].z !== undefined) zMin = Math.min(zMin, Number(renderSegs[i].z))
        return zMin
    }

    // The Z the stock is broken off at after the profile, in mm, or null.
    function profileBreakZ() {
        if (!breakAfterProfile) return null
        var bend = Broken.reach(1.0) * Math.max(0, externalDiameter) / 2
        return Math.max(-Math.max(0, stockLength), profileEndZ() - 3 * bend)
    }

    // The Z the stock is broken off at after Z End, in mm, or null.
    // How far past Z End the break is, mm: ``break_after_setback`` when the
    // workpiece gives it (Parting's, to keep a broken stock one diameter
    // long), else five of the break's bends.
    function zEndSetback() {
        if (workpiece && workpiece.break_after_setback !== undefined && workpiece.break_after_setback !== null)
            return Math.max(0, Number(workpiece.break_after_setback))
        return 5 * Broken.reach(1.0) * Math.max(0, externalDiameter) / 2
    }

    function zEndBreakZ() {
        if (breakAfterZ === null) return null
        return Math.max(-Math.max(0, stockLength), breakAfterZ - zEndSetback())
    }

    // the colours and pitch the stock is drawn in, whole or broken
    readonly property color hatchColor:   "#d5d9df"
    readonly property color outlineColor: "#6b7280"
    readonly property color boreColor:    "#aeb4bd"
    // the cut face of a broken end: its ground a shade darker than the
    // stock's, its hatch darker again so it still stands out on it
    readonly property color lensFillColor:  "#e5e7eb"
    readonly property color lensHatchColor: "#a3aab4"
    // Profile Roughing's and Contour's tube: the stock past the profile's end
    // hatched lighter than the finished part (a bar is left plain)
    readonly property color pastProfileHatchColor: "#e6e9ed"
    readonly property real  hatchPitch:   12
    // the outline and the bore lines; the hatch stays at one px
    readonly property real  outlineWidth: 1.5

    // Canvas y of diameter x, on the mirrored half (above the centre line)
    // when asked.
    function _cy(x, mirrored) { return cy(mirrored ? -x : x) }

    function _pathProfileToStock(ctx, stockX, mirrored, endZ) {
        var started = false
        var stockStartZ = 0
        var stockEndZ = endZ !== undefined ? endZ : -Math.max(0, stockLength)
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

    function _hatchCurrentClip(ctx, left, top, right, bottom, colour) {
        var spacing = hatchPitch
        var overshoot = bottom - top
        ctx.strokeStyle = colour !== undefined ? colour : hatchColor
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

        var breakZ = profileBreakZ()
        var zEndBreak = zEndBreakZ()
        if (breakFarEnd || breakZ !== null || zEndBreak !== null) {
            var innerX = Math.max(0, Math.min(internalDiameter, stockX))
            var R = cy(stockX) - cy(0), r = innerX > 0 ? cy(innerX) - cy(0) : 0
            var style = { fill: Theme.surface, hatch: hatchColor, hatchPitch: hatchPitch,
                          outline: outlineColor, bore: boreColor, lineWidth: outlineWidth,
                          lensFill: lensFillColor, lensHatch: lensHatchColor }
            if (zEndBreak !== null) {
                // as after a profile: with the mirror off no stock; the
                // stock from its face back to the break - a tube's walls
                // hatched light, a bar plain - and Facing's faced-off stock
                // in front of Z End, under the toolpath, not drawn: the
                // background
                if (!mirrorAcrossCenterline) return
                style.hatch = pastProfileHatchColor
                var face = facedTo !== null ? Math.min(facedTo, faceZ) : faceZ
                // G33's thread: from Z Start to Z End only what is inside its
                // profile is stock - the grooves cut out, the profile its
                // outline there
                var thread = workpiece && workpiece.thread ? workpiece.thread : null
                if (thread && thread.lower && thread.upper && thread.lower.length > 0
                        && thread.lower.length === thread.upper.length) {
                    var tFrom = Math.max(Number(thread.from), Number(thread.to))
                    var tTo = Math.min(Number(thread.from), Number(thread.to))
                    var span = 2 * R + 4
                    style.material = function(c) {
                        var farX = cx(-Math.max(0, stockLength)) - span
                        // past the thread, and in front of it up to the face
                        c.rect(farX, cy(0) - span, cx(tTo) - farX, 2 * span)
                        if (tFrom < face) c.rect(cx(tFrom), cy(0) - span, cx(face) - cx(tFrom), 2 * span)
                        // the middle left out: whole across the gap, as far
                        // as the breaks reach either side of it
                        if (breakMiddle) {
                            var reachPx = Broken.reach(R)
                            c.rect(cx(breakMiddle.far) - reachPx, cy(0) - span,
                                   cx(breakMiddle.near) - cx(breakMiddle.far) + 2 * reachPx, 2 * span)
                        }
                        // within it, inside its profile, both halves
                        // the near half's profile below, the far half's over
                        for (var l = 0; l < thread.lower.length; l++) {
                            var lo = thread.lower[l], up = thread.upper[l]
                            c.moveTo(cx(+lo[0].z), cy(+lo[0].x))
                            for (var p = 1; p < lo.length; p++) c.lineTo(cx(+lo[p].z), cy(+lo[p].x))
                            for (p = up.length - 1; p >= 0; p--) c.lineTo(cx(+up[p].z), cy(+up[p].x))
                            c.closePath()
                        }
                    }
                    style.skinTo = cx(tTo)
                }
                if (breakMiddle) {
                    // a stretch of its middle left out as well (Parting's,
                    // far down the stock): the piece at the face broken off
                    // at the gap; the far piece, broken at both its ends
                    Broken.piece(ctx, cx(breakMiddle.near), cx(face), cy(0), R, r, true, false, style)
                    Broken.piece(ctx, cx(zEndBreak), cx(breakMiddle.far), cy(0), R, r, true, true, style)
                } else {
                    Broken.paint(ctx, cx(face), cx(zEndBreak), cy(0), R, r, style)
                }
                return
            }
            if (breakZ !== null) {
                // Mirror off: no stock at all - the profile alone, with the
                // toolpath over it; the broken stock is a whole-bar drawing
                if (!mirrorAcrossCenterline) return
                // the finished part hatched as before, within the piece
                var self = this
                style.noWallHatch = true
                // Below the centre line, where the break's S bulges out past
                // its line: hatched past it by as far as the S reaches - the
                // piece's own outline, the clip this is drawn in, stops it at
                // the S - and past the profile's end the bar whole, from the
                // bore out to its skin. Above the line, as it was: to the
                // break line.
                var hatchEndZ = breakZ - 2 * Broken.reach(1.0) * stockX / 2
                var wholeFrom = cx(profileEndZ()), wholeTo = cx(hatchEndZ)
                // a tube's stock past the profile lighter than the part; a
                // bar not hatched at all, neither the part nor the stock
                var pastColor = innerX > 0 ? pastProfileHatchColor : null
                var top = cy(-stockX), bottom = cy(stockX)
                // what is drawn on the part's side of the profile's end, or past it
                function side(c, past, draw) {
                    if (past && pastColor === null) return
                    c.save()
                    c.beginPath()
                    if (past) c.rect(wholeTo - 1, top, wholeFrom - wholeTo + 1, bottom - top)
                    else c.rect(wholeFrom, top, cx(faceZ) - wholeFrom, bottom - top)
                    c.clip()
                    draw(past ? pastColor : hatchColor)
                    c.restore()
                }
                style.inside = function(c) {
                    if (pastColor === null || self.simplified) return
                    for (var k = 0; k < 2; k++) {
                        side(c, k === 1, function(colour) {
                            self._hatchHalf(c, hatchEndZ, stockX, false, colour)
                            self._hatchHalf(c, breakZ, stockX, true, colour)
                        })
                    }
                    var lower = [cy(innerX), cy(stockX)]
                    c.save()
                    c.beginPath()
                    c.rect(wholeTo, lower[0], wholeFrom - wholeTo, lower[1] - lower[0])
                    c.clip()
                    self._hatchCurrentClip(c, wholeTo, lower[0], wholeFrom, lower[1], pastColor)
                    c.restore()
                }
                // What the toolpath takes off - between the profile and the
                // skin, up to the profile's end, on both halves - not filled:
                // the background behind the toolpath. The rest of the piece
                // as before. Nor the skin's lines over it: they stop at the
                // profile's end.
                if (String(profileType || "od").toLowerCase() === "od") {
                    style.skinTo = wholeFrom
                    var farX = cx(-Math.max(0, stockLength)) - 2 * R
                    style.fillInside = function(c) {
                        for (var m = 0; m < 2; m++) {
                            c.beginPath()
                            if (self._pathProfileToStock(c, 0, m === 1, -Math.max(0, stockLength))) c.fill()
                        }
                        c.beginPath(); c.rect(farX, top, wholeFrom - farX, bottom - top); c.fill()
                    }
                }
                Broken.paint(ctx, cx(faceZ), cx(breakZ), cy(0), R, r, style)
                return
            }
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

    // The hatch of one half: the material, or with a profile the finished
    // part - from the face back to ``stockZ``; in ``colour``, or the hatch's.
    function _hatchHalf(ctx, stockZ, stockX, mirrored, colour) {
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
            _hatchCurrentClip(ctx, Math.min(left, right), Math.min(top, bottom), Math.max(left, right), Math.max(top, bottom), colour)
            ctx.restore()
        } else if (profileMode === "od" || profileMode === "id") {
            ctx.save()
            ctx.beginPath()
            if (_pathProfileToStock(ctx, hatchBoundaryX, mirrored, stockZ)) {
                ctx.clip()
                _hatchCurrentClip(ctx, Math.min(left, right), Math.min(top, bottom), Math.max(left, right), Math.max(top, bottom), colour)
            }
            ctx.restore()
        }
        ctx.restore()
    }

    // One half of an OD profile's stock drawn whole (Define Profile) as
    // Profile Roughing draws it: the finished part and the stock past the
    // profile's end on the surface colour, what is turned off between the
    // profile and the skin left on the background; a tube's part hatched, the
    // stock past it lighter, a bar not hatched at all.
    function _paintProfileHalf(ctx, stockZ, stockX, mirrored, innerX) {
        var endX = cx(profileEndZ())
        var far = cx(stockZ)
        var skin = _cy(stockX, mirrored), axis = cy(0)
        var top = Math.min(skin, axis), bottom = Math.max(skin, axis)
        ctx.save()
        ctx.fillStyle = Theme.surface
        ctx.beginPath()
        if (_pathProfileToStock(ctx, 0, mirrored, stockZ)) ctx.fill()
        if (endX > far) { ctx.beginPath(); ctx.rect(far, top, endX - far, bottom - top); ctx.fill() }
        ctx.restore()
        if (innerX <= 0) return
        // the part, to the profile's end
        ctx.save()
        ctx.beginPath(); ctx.rect(endX, top, cx(faceZ) - endX, bottom - top); ctx.clip()
        _hatchHalf(ctx, stockZ, stockX, mirrored)
        ctx.restore()
        // past it, the walls, lighter
        if (endX > far) {
            var wall = _cy(innerX, mirrored)
            var wTop = Math.min(skin, wall), wBottom = Math.max(skin, wall)
            ctx.save()
            ctx.beginPath(); ctx.rect(far, wTop, endX - far, wBottom - wTop); ctx.clip()
            _hatchCurrentClip(ctx, far, wTop, endX, wBottom, pastProfileHatchColor)
            ctx.restore()
        }
    }

    // One half of an ID profile's stock drawn whole (Define Profile), as the
    // Program Header draws a tube: all of it on the surface colour, the
    // hatch's diagonal throughout - in front of the profile's end the
    // finished part, between the profile and the skin; past it the walls,
    // out from the bore: the profile's end diameter, or the stock's when
    // that is wider. The bore, and what the profile bores out, plain.
    function _paintIdProfileHalf(ctx, stockZ, stockX, mirrored, innerX) {
        var endX = cx(profileEndZ())
        var face = cx(faceZ), far = cx(stockZ)
        var skin = _cy(stockX, mirrored), axis = cy(0)
        var top = Math.min(skin, axis), bottom = Math.max(skin, axis)
        ctx.save()
        ctx.fillStyle = Theme.surface
        ctx.fillRect(far, top, face - far, bottom - top)
        ctx.restore()
        if (endX > far) {
            var lastSeg = renderSegs[renderSegs.length - 1]
            var bore = _cy(Math.min(stockX, Math.max(innerX, Number(lastSeg.x) || 0)), mirrored)
            var wTop = Math.min(skin, bore), wBottom = Math.max(skin, bore)
            ctx.save()
            // into the part by a px, its lines from the same origin: one hatch
            ctx.beginPath(); ctx.rect(far, wTop, endX + 1 - far, wBottom - wTop); ctx.clip()
            _hatchCurrentClip(ctx, far, top, face, bottom)
            ctx.restore()
            if (bore !== axis) {
                ctx.strokeStyle = boreColor
                ctx.lineWidth = outlineWidth
                ctx.setLineDash([])
                ctx.beginPath()
                ctx.moveTo(endX, bore)
                ctx.lineTo(far, bore)
                ctx.stroke()
            }
        }
        ctx.save()
        ctx.beginPath(); ctx.rect(endX, top, face - endX, bottom - top); ctx.clip()
        ctx.beginPath()
        if (_pathProfileToStock(ctx, stockX, mirrored, stockZ)) {
            ctx.clip()
            _hatchCurrentClip(ctx, far, top, face, bottom)
        }
        ctx.restore()
    }

    // One half of the stock: below the centre line, or its mirror above it.
    function _paintHalf(ctx, stockZ, stockX, mirrored) {
        var left = cx(faceZ)
        var right = cx(stockZ)
        var top = cy(0)
        var bottom = _cy(stockX, mirrored)
        var hasInternalDiameter = internalDiameter > 0
        var innerX = hasInternalDiameter ? Math.max(0, Math.min(internalDiameter, stockX)) : 0

        var hasProfile = renderSegs && renderSegs.length > 0
        var isId = String(profileType || "od").toLowerCase() === "id"
        if (hasProfile && !isId)
            _paintProfileHalf(ctx, stockZ, stockX, mirrored, innerX)
        else if (hasProfile)
            _paintIdProfileHalf(ctx, stockZ, stockX, mirrored, innerX)
        else
            _hatchHalf(ctx, stockZ, stockX, mirrored)

        // its outside and its far end; its face only when it stands proud of
        // Z0 - at Z0 the dashed Z0 line goes, and only the finished profile
        // is drawn over that. With an OD profile (Define Profile), its outside
        // only past the profile's end, not along it; with an ID one, the
        // whole of it, and at the profile's start the part's face, out from
        // the profile to the skin
        ctx.strokeStyle = outlineColor
        ctx.lineWidth = outlineWidth
        ctx.setLineDash([])
        ctx.beginPath()
        ctx.moveTo(hasProfile && !isId ? Math.max(right, cx(profileEndZ())) : left, bottom)
        ctx.lineTo(right, bottom)
        ctx.lineTo(right, top)
        if (faceZ > 0) {
            ctx.moveTo(left, bottom)
            ctx.lineTo(left, top)
        }
        if (hasProfile && isId) {
            ctx.moveTo(cx(renderSegs[0].z), _cy(renderSegs[0].x, mirrored))
            ctx.lineTo(cx(renderSegs[0].z), bottom)
        }
        ctx.stroke()

        // the bore; an ID profile's draws its own
        if (hasInternalDiameter && innerX > 0 && !(hasProfile && isId)) {
            ctx.strokeStyle = boreColor
            ctx.beginPath()
            ctx.moveTo(left, _cy(innerX, mirrored))
            ctx.lineTo(right, _cy(innerX, mirrored))
            ctx.stroke()
        }
    }
}
