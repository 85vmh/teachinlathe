import QtQuick 2.15

QtObject {
    // Returns the geometric bounding box of all primitives:
    //   { fZMin, fZMax, fXMin, fXMax, vZMax, vXMax }
    // where vZMax/vXMax are the maximum positive vertex coords (used for arrow tips).
    // Returns null if primitives is empty.
    function computeBounds(primitives) {
        if (!primitives || primitives.length === 0) return null
        var fZMin = 1e9, fZMax = -1e9, fXMin = 1e9, fXMax = -1e9
        var vZMax = 0, vXMax = 0
        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            var vz, vx
            if (p.type === "startPoint") {
                vz = +(p.z_start || 0); vx = +(p.x_start || 0)
            } else if (p.type === "lineTo") {
                vz = +(p.z_end || 0); vx = +(p.x_end || 0)
            } else if (p.type === "arcTo") {
                vz = +(p.z_end || 0); vx = +(p.x_end || 0)
                var r = +(p.arc_radius || 0)
                var zc = +(p.z_center || 0)
                var xc = +(p.x_center || 0)
                fZMin = Math.min(fZMin, zc - r); fZMax = Math.max(fZMax, zc + r)
                fXMin = Math.min(fXMin, xc - r); fXMax = Math.max(fXMax, xc + r)
            } else { continue }
            fZMin = Math.min(fZMin, vz); fZMax = Math.max(fZMax, vz)
            fXMin = Math.min(fXMin, vx); fXMax = Math.max(fXMax, vx)
            if (vz > vZMax) vZMax = vz
            if (vx > vXMax) vXMax = vx
        }
        if (fZMin === 1e9) return null
        return { fZMin: fZMin, fZMax: fZMax, fXMin: fXMin, fXMax: fXMax,
                 vZMax: vZMax, vXMax: vXMax }
    }

    // Auto-fit viewport margins:
    //   top    = 20 mm above X=0 (spindle axis)
    //   right  = 20 mm past Z+ arrow tip  (= vZMax + 10 + 20 = vZMax + 30)
    //   bottom = 10 mm past X+ arrow tip  (= vXMax + 10 + 10 = vXMax + 20)
    //   left   = all data + 20 mm margin
    function computeViewport(primitives, width, height) {
        var empty = { scale: 5, originX: width / 2, originY: height / 2, maxZ: 0, maxX: 0 }
        if (!primitives || primitives.length === 0 || width <= 0 || height <= 0) return empty
        var b = computeBounds(primitives)
        if (!b) return empty

        var leftBound   = b.fZMin - 20
        var rightBound  = Math.max(b.fZMax, b.vZMax + 30)
        var topBound    = -20
        var bottomBound = Math.max(b.fXMax, b.vXMax + 20)

        var scale = Math.min(
            width  / Math.max(rightBound - leftBound,  1),
            height / Math.max(bottomBound - topBound, 1)
        )
        return {
            scale:   scale,
            originX: (-leftBound) * scale,
            originY: (-topBound)  * scale,
            maxZ:    b.vZMax,
            maxX:    b.vXMax
        }
    }

    function steps(scale) {
        if (scale >= 2)   return { minor: 1,  major: 10  }
        if (scale >= 0.4) return { minor: 10, major: 50  }
        return                   { minor: 50, major: 100 }
    }

    function _isMajor(val, step) {
        return Math.round(Math.abs(val) * 1000) % Math.round(step * 1000) < 1
    }

    function tickStyle(val, s) {
        if (_isMajor(val, s.major)) return { len: 7, label: true  }
        if (_isMajor(val, 5))       return { len: 7, label: false }
        return                             { len: 3, label: false }
    }

    function filletGeom(startZ, startX, cornerZ, cornerX, nextP, fr) {
        var sdz = cornerZ - startZ
        var sdx = cornerX - startX
        var slen = Math.sqrt(sdz * sdz + sdx * sdx)
        if (slen < 0.001 || fr < 0.001) {
            return null
        }
        if (!nextP || nextP.type !== "lineTo") {
            return null
        }
        var ndz = +(nextP.z_end || 0) - cornerZ
        var ndx = +(nextP.x_end || 0) - cornerX
        var nlen = Math.sqrt(ndz * ndz + ndx * ndx)
        if (nlen < 0.001) {
            return null
        }

        var d1z = sdz / slen
        var d1x = sdx / slen
        var d2z = ndz / nlen
        var d2x = ndx / nlen

        var cross = d1z * d2x - d1x * d2z
        var dot = d1z * d2z + d1x * d2x
        var absCross = Math.abs(cross)
        if (absCross < 0.001) {
            return null
        }

        var t = fr * (1.0 - dot) / absCross
        var t1z = cornerZ - t * d1z
        var t1x = cornerX - t * d1x
        var t2z = cornerZ + t * d2z
        var t2x = cornerX + t * d2x

        var perpZ = (cross > 0) ? -d1x : d1x
        var perpX = (cross > 0) ? d1z : -d1z

        return {
            t1z: t1z,
            t1x: t1x,
            t2z: t2z,
            t2x: t2x,
            fcz: t1z + fr * perpZ,
            fcx: t1x + fr * perpX,
            anticlockwise: (cross < 0)
        }
    }

    function filletArcLine(acz, acx, ar, isCW, jZ, jX, nextP, fr) {
        if (!nextP || nextP.type !== "lineTo") {
            return null
        }
        var d2zr = +(nextP.z_end || 0) - jZ
        var d2xr = +(nextP.x_end || 0) - jX
        var d2len = Math.sqrt(d2zr * d2zr + d2xr * d2xr)
        if (d2len < 0.001 || fr < 0.001 || ar < 0.001) {
            return null
        }
        var d2z = d2zr / d2len
        var d2x = d2xr / d2len

        var rez = jZ - acz
        var rex = jX - acx
        var rlen = Math.sqrt(rez * rez + rex * rex)
        if (rlen < 0.001) {
            return null
        }
        var d1z = (isCW ? -rex : rex) / rlen
        var d1x = (isCW ? rez : -rez) / rlen

        var cross = d1z * d2x - d1x * d2z
        if (Math.abs(cross) < 0.001) {
            return null
        }

        var n2z = (cross > 0) ? -d2x : d2x
        var n2x = (cross > 0) ? d2z : -d2z

        var dz = jZ + fr * n2z - acz
        var dx = jX + fr * n2x - acx

        var dotD2 = dz * d2z + dx * d2x
        var discrim = dotD2 * dotD2 - (dz * dz + dx * dx) + (ar + fr) * (ar + fr)
        if (discrim < 0) {
            return null
        }

        var t = -dotD2 + Math.sqrt(discrim)

        var fcz = jZ + fr * n2z + t * d2z
        var fcx = jX + fr * n2x + t * d2x
        var t2z = jZ + t * d2z
        var t2x = jX + t * d2x
        var vcz = fcz - acz
        var vcx = fcx - acx
        var vclen = Math.sqrt(vcz * vcz + vcx * vcx)
        if (vclen < 0.001) {
            return null
        }
        return {
            t1z: acz + ar * vcz / vclen,
            t1x: acx + ar * vcx / vclen,
            t2z: t2z,
            t2x: t2x,
            fcz: fcz,
            fcx: fcx,
            anticlockwise: (cross < 0)
        }
    }

    function filletLineArc(startZ, startX, cornerZ, cornerX, nextArc, fr) {
        if (!nextArc || nextArc.type !== "arcTo") {
            return null
        }
        var isCW = (nextArc.direction === "cw")
        var acz = +(nextArc.z_center || 0)
        var acx = +(nextArc.x_center || 0)
        var ar = +(nextArc.arc_radius || 0)
        if (fr < 0.001 || ar < 0.001) {
            return null
        }

        var sdz = cornerZ - startZ
        var sdx = cornerX - startX
        var slen = Math.sqrt(sdz * sdz + sdx * sdx)
        if (slen < 0.001) {
            return null
        }
        var d1z = sdz / slen
        var d1x = sdx / slen

        var rsz = cornerZ - acz
        var rsx = cornerX - acx
        var rlen = Math.sqrt(rsz * rsz + rsx * rsx)
        if (rlen < 0.001) {
            return null
        }
        var d2z = (isCW ? -rsx : rsx) / rlen
        var d2x = (isCW ? rsz : -rsz) / rlen

        var cross = d1z * d2x - d1x * d2z
        if (Math.abs(cross) < 0.001) {
            return null
        }

        var n1z = (cross > 0) ? -d1x : d1x
        var n1x = (cross > 0) ? d1z : -d1z

        var dz = cornerZ + fr * n1z - acz
        var dx = cornerX + fr * n1x - acx

        var dotD1 = dz * d1z + dx * d1x
        var discrim = dotD1 * dotD1 - (dz * dz + dx * dx) + (ar + fr) * (ar + fr)
        if (discrim < 0) {
            return null
        }

        var t = dotD1 + Math.sqrt(discrim)

        var fcz = cornerZ - t * d1z + fr * n1z
        var fcx = cornerX - t * d1x + fr * n1x
        var t1z = cornerZ - t * d1z
        var t1x = cornerX - t * d1x
        var vcz = fcz - acz
        var vcx = fcx - acx
        var vclen = Math.sqrt(vcz * vcz + vcx * vcx)
        if (vclen < 0.001) {
            return null
        }

        return {
            t1z: t1z,
            t1x: t1x,
            t2z: acz + ar * vcz / vclen,
            t2x: acx + ar * vcx / vclen,
            fcz: fcz,
            fcx: fcx,
            anticlockwise: (cross < 0)
        }
    }

    function chamferGeomLine(logZ, logX, ez, ex, nextP, cw) {
        var sdz = ez - logZ
        var sdx = ex - logX
        var slen = Math.sqrt(sdz * sdz + sdx * sdx)
        if (slen < 0.001 || cw < 0.001) {
            return null
        }
        var csZ = ez - cw * sdz / slen
        var csX = ex - cw * sdx / slen
        var ceZ = ez
        var ceX = ex
        if (nextP && nextP.type === "lineTo") {
            var ndz = +(nextP.z_end || 0) - ez
            var ndx = +(nextP.x_end || 0) - ex
            var nlen = Math.sqrt(ndz * ndz + ndx * ndx)
            if (nlen > 0.001) {
                ceZ = ez + cw * ndz / nlen
                ceX = ex + cw * ndx / nlen
            }
        } else if (nextP && nextP.type === "arcTo") {
            var nacz = +(nextP.z_center || 0)
            var nacx = +(nextP.x_center || 0)
            var nrz = ez - nacz
            var nrx = ex - nacx
            var nndz = (nextP.direction === "cw") ? -nrx : nrx
            var nndx = (nextP.direction === "cw") ? nrz : -nrz
            var nlen2 = Math.sqrt(nndz * nndz + nndx * nndx)
            if (nlen2 > 0.001) {
                ceZ = ez + cw * nndz / nlen2
                ceX = ex + cw * nndx / nlen2
            }
        }
        return { csZ: csZ, csX: csX, ceZ: ceZ, ceX: ceX }
    }

    function chamferGeomArc(acz, acx, ar, isCW, aez, aex, nextP, acw) {
        var arez = aez - acz
        var arex = aex - acx
        var arlen = Math.sqrt(arez * arez + arex * arex)
        if (arlen < 0.001 || acw < 0.001) {
            return null
        }
        var atdz = isCW ? -arex : arex
        var atdx = isCW ? arez : -arez
        var csZ = aez - acw * atdz / arlen
        var csX = aex - acw * atdx / arlen
        var ceZ = aez
        var ceX = aex
        if (nextP && nextP.type === "lineTo") {
            var andz = +(nextP.z_end || 0) - aez
            var andx = +(nextP.x_end || 0) - aex
            var anlen = Math.sqrt(andz * andz + andx * andx)
            if (anlen > 0.001) {
                ceZ = aez + acw * andz / anlen
                ceX = aex + acw * andx / anlen
            }
        }
        return { csZ: csZ, csX: csX, ceZ: ceZ, ceX: ceX }
    }

    function buildRenderSegments(primitives, profileType) {
        var segs = []
        if (!primitives || primitives.length === 0) {
            return segs
        }
        var isID = (String(profileType || "od").toLowerCase() === "id")

        var logZ = 0
        var logX = 0

        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            if (p.type === "startPoint") {
                logZ = +(p.z_start || 0)
                logX = +(p.x_start || 0)
                var spNextPrim = _nextPrim(primitives, i)
                if (p.blend && p.blend.type !== "none" && spNextPrim) {
                    var spLX2 = logX / 2
                    var spNextH = halfXPrim(spNextPrim)
                    if (p.blend.type === "chamfer") {
                        var spcw = +(p.blend.chamfer_width || 0)
                        var spEntryX = isID ? spLX2 + spcw : spLX2 - spcw
                        var spcg = chamferGeomLine(logZ, spEntryX, logZ, spLX2, spNextH, spcw)
                        if (spcg) {
                            segs.push({ type: "move", z: spcg.csZ, x: spcg.csX * 2 })
                            segs.push({ type: "line", z: spcg.ceZ, x: spcg.ceX * 2 })
                        } else {
                            segs.push({ type: "move", z: logZ, x: logX })
                        }
                    } else if (p.blend.type === "fillet") {
                        var spfr = +(p.blend.fillet_radius || 0)
                        var spEntryXF = isID ? spLX2 + spfr : spLX2 - spfr
                        var spfg = (spNextPrim.type === "arcTo")
                            ? filletLineArc(logZ, spEntryXF, logZ, spLX2, spNextH, spfr)
                            : filletGeom(logZ, spEntryXF, logZ, spLX2, spNextH, spfr)
                        if (spfg) {
                            segs.push({ type: "move", z: spfg.t1z, x: spfg.t1x * 2 })
                            segs.push({
                                type: "arc",
                                z: spfg.t2z, x: spfg.t2x * 2,
                                zc: spfg.fcz, xc: spfg.fcx * 2,
                                r: spfr,
                                anticlockwise: spfg.anticlockwise
                            })
                        } else {
                            segs.push({ type: "move", z: logZ, x: logX })
                        }
                    } else {
                        segs.push({ type: "move", z: logZ, x: logX })
                    }
                } else {
                    segs.push({ type: "move", z: logZ, x: logX })
                }
            } else if (p.type === "lineTo") {
                var ez = +(p.z_end || 0)
                var ex = +(p.x_end || 0)
                if (p.blend && p.blend.type === "chamfer") {
                    var cw = +(p.blend.chamfer_width || 0)
                    var cg = chamferGeomLine(logZ, logX / 2, ez, ex / 2, halfXPrim(_nextPrim(primitives, i)), cw)
                    if (cg) {
                        segs.push({ type: "line", z: cg.csZ, x: cg.csX * 2 })
                        segs.push({ type: "line", z: cg.ceZ, x: cg.ceX * 2 })
                    } else {
                        segs.push({ type: "line", z: ez, x: ex })
                    }
                } else if (p.blend && p.blend.type === "fillet") {
                    var fr = +(p.blend.fillet_radius || 0)
                    var nextPrim = _nextPrim(primitives, i)
                    var nextPrimH = halfXPrim(nextPrim)
                    var fg = (nextPrim && nextPrim.type === "arcTo")
                        ? filletLineArc(logZ, logX / 2, ez, ex / 2, nextPrimH, fr)
                        : filletGeom(logZ, logX / 2, ez, ex / 2, nextPrimH, fr)
                    if (fg) {
                        segs.push({ type: "line", z: fg.t1z, x: fg.t1x * 2 })
                        segs.push({
                            type: "arc",
                            z: fg.t2z, x: fg.t2x * 2,
                            zc: fg.fcz, xc: fg.fcx * 2,
                            r: fr,
                            anticlockwise: fg.anticlockwise
                        })
                    } else {
                        segs.push({ type: "line", z: ez, x: ex })
                    }
                } else {
                    segs.push({ type: "line", z: ez, x: ex })
                }
                logZ = ez
                logX = ex
            } else if (p.type === "arcTo") {
                var aez = +(p.z_end || 0)
                var aex = +(p.x_end || 0)
                var acz = +(p.z_center || 0)
                var acx = +(p.x_center || 0)
                var ar = +(p.arc_radius || 0)
                var isCW = (p.direction === "cw")

                if (p.blend && p.blend.type === "chamfer") {
                    var acw  = +(p.blend.chamfer_width || 0)
                    var acx2c = acx / 2, aex2c = aex / 2
                    var ar2c  = Math.sqrt((aex2c - acx2c) * (aex2c - acx2c) + (aez - acz) * (aez - acz))
                    var acg = chamferGeomArc(acz, acx2c, ar2c, isCW, aez, aex2c, halfXPrim(_nextPrim(primitives, i)), acw)
                    if (acg) {
                        segs.push({
                            type: "arc",
                            z: acg.csZ, x: acg.csX * 2,
                            zc: acz, xc: acx, r: ar,
                            anticlockwise: !isCW
                        })
                        segs.push({ type: "line", z: acg.ceZ, x: acg.ceX * 2 })
                    } else {
                        segs.push({
                            type: "arc",
                            z: aez, x: aex,
                            zc: acz, xc: acx, r: ar,
                            anticlockwise: !isCW
                        })
                    }
                } else if (p.blend && p.blend.type === "fillet") {
                    var afr  = +(p.blend.fillet_radius || 0)
                    var acx2f = acx / 2, aex2f = aex / 2
                    var ar2f  = Math.sqrt((aex2f - acx2f) * (aex2f - acx2f) + (aez - acz) * (aez - acz))
                    var afg = filletArcLine(acz, acx2f, ar2f, isCW, aez, aex2f, halfXPrim(_nextPrim(primitives, i)), afr)
                    if (afg) {
                        segs.push({
                            type: "arc",
                            z: afg.t1z, x: afg.t1x * 2,
                            zc: acz, xc: acx, r: ar,
                            anticlockwise: !isCW
                        })
                        segs.push({
                            type: "arc",
                            z: afg.t2z, x: afg.t2x * 2,
                            zc: afg.fcz, xc: afg.fcx * 2,
                            r: afr,
                            anticlockwise: afg.anticlockwise
                        })
                    } else {
                        segs.push({
                            type: "arc",
                            z: aez, x: aex,
                            zc: acz, xc: acx, r: ar,
                            anticlockwise: !isCW
                        })
                    }
                } else {
                    segs.push({
                        type: "arc",
                        z: aez,
                        x: aex,
                        zc: acz,
                        xc: acx,
                        r: ar,
                        anticlockwise: !isCW
                    })
                }
                logZ = aez
                logX = aex
            }
        }
        return segs
    }

    function walkToIndex(primitives, targetIdx) {
        var logZ = 0
        var logX = 0
        for (var j = 0; j < targetIdx; j++) {
            var p = primitives[j]
            if (p.type === "startPoint") {
                logZ = +(p.z_start || 0)
                logX = +(p.x_start || 0)
            } else if (p.type === "lineTo") {
                logZ = +(p.z_end || 0)
                logX = +(p.x_end || 0)
            } else if (p.type === "arcTo") {
                logZ = +(p.z_end || 0)
                logX = +(p.x_end || 0)
            }
        }
        return { logZ: logZ, logX: logX }
    }

    function _nextPrim(primitives, i) {
        if (i + 1 < primitives.length) {
            return primitives[i + 1]
        }
        return null
    }

    // Returns a copy of primitive p with all X coordinates halved (diameter → radius).
    // Used so blend geometry functions compute in isometric radius-Z space.
    function halfXPrim(p) {
        if (!p) return null
        if (p.type === "lineTo") {
            return { type: "lineTo", z_end: p.z_end, x_end: (+(p.x_end || 0)) / 2, blend: p.blend }
        }
        if (p.type === "arcTo") {
            var xe2 = (+(p.x_end    || 0)) / 2
            var xc2 = (+(p.x_center || 0)) / 2
            var ze  = +(p.z_end     || 0)
            var zc  = +(p.z_center  || 0)
            return { type: "arcTo",
                     z_end: ze, x_end: xe2,
                     z_center: zc, x_center: xc2,
                     arc_radius: Math.sqrt((xe2 - xc2) * (xe2 - xc2) + (ze - zc) * (ze - zc)),
                     direction: p.direction, blend: p.blend }
        }
        return p
    }

    // ── Hit-test helpers (operate on canvas pixel coords) ─────────────────────
    function distToSegment(px, py, x1, y1, x2, y2) {
        var deltaX = x2 - x1
        var deltaY = y2 - y1
        var lengthSquared = deltaX * deltaX + deltaY * deltaY
        if (lengthSquared < 1) {
            return Math.sqrt((px - x1) * (px - x1) + (py - y1) * (py - y1))
        }
        var t = Math.max(0, Math.min(1, ((px - x1) * deltaX + (py - y1) * deltaY) / lengthSquared))
        var closestX = x1 + t * deltaX - px
        var closestY = y1 + t * deltaY - py
        return Math.sqrt(closestX * closestX + closestY * closestY)
    }

    function _normAngle(a) {
        var TWO_PI = Math.PI * 2
        return ((a % TWO_PI) + TWO_PI) % TWO_PI
    }

    function _angleInArc(testAngle, startAng, endAng, anticlockwise) {
        var start = _normAngle(startAng)
        var end   = _normAngle(endAng)
        var angle = _normAngle(testAngle)
        if (!anticlockwise) {          // CW: angles increase from s to e
            return (start <= end) ? (angle >= start && angle <= end) : (angle >= start || angle <= end)
        } else {                       // CCW: angles decrease from s to e
            return (start >= end) ? (angle >= end && angle <= start) : (angle <= end || angle >= start)
        }
    }

    function distToArc(px, py, ccx, ccy, cr, sa, ea, anticlockwise) {
        var deltaX = px - ccx
        var deltaY = py - ccy
        var distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
        if (distance < 1) return cr
        var distanceToCircle = Math.abs(distance - cr)
        if (_angleInArc(Math.atan2(deltaY, deltaX), sa, ea, anticlockwise)) return distanceToCircle
        // nearest arc endpoint
        var startX = ccx + cr * Math.cos(sa)
        var startY = ccy + cr * Math.sin(sa)
        var endX   = ccx + cr * Math.cos(ea)
        var endY   = ccy + cr * Math.sin(ea)
        var distStart = Math.sqrt((px - startX) * (px - startX) + (py - startY) * (py - startY))
        var distEnd   = Math.sqrt((px - endX)   * (px - endX)   + (py - endY)   * (py - endY))
        return Math.min(distStart, distEnd)
    }
}
