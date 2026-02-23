// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// Scale and origin are computed from fixed viewport margins.
import QtQuick 2.15

Canvas {
    id: root

    property var primitives:       []   // array of primitive objects from JSON
    property int selectedPrimIndex: -1  // index into primitives; -1 = none

    signal primitiveSelected(int index)

    // ── Private state ──────────────────────────────────────────────────────────
    property real _scale:   5.0
    property real _originX: 0     // canvas px → world Z = 0
    property real _originY: 0     // canvas px → world X = 0
    property real _maxZ:    0     // max positive vertex Z  (for Z+ arrow length)
    property real _maxX:    0     // max positive vertex X  (for X+ arrow length)

    readonly property real _circleR: 8   // origin marker radius

    // ── World → canvas ─────────────────────────────────────────────────────────
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + wX * _scale }

    // ── Recompute + repaint on any relevant change ─────────────────────────────
    onPrimitivesChanged:        { _computeScale(); requestPaint() }
    onWidthChanged:             { _computeScale(); requestPaint() }
    onHeightChanged:            { _computeScale(); requestPaint() }
    onSelectedPrimIndexChanged: requestPaint()

    // ── Viewport / scale computation ───────────────────────────────────────────
    // Viewport margins:
    //   top    = 20 mm above X=0 (spindle axis)
    //   right  = 20 mm past Z+ arrow tip  (= vZMax + 10 + 20 = vZMax + 30)
    //   bottom = 10 mm past X+ arrow tip  (= vXMax + 10 + 10 = vXMax + 20)
    //   left   = all data + 20 mm margin
    function _computeScale() {
        if (!primitives || primitives.length === 0 || width <= 0 || height <= 0) {
            _scale = 5;  _maxZ = 0;  _maxX = 0
            _originX = width / 2;  _originY = height / 2
            return
        }

        var fZMin = 1e9, fZMax = -1e9
        var fXMin = 1e9, fXMax = -1e9
        var vZMax = 0,   vXMax = 0

        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            var vz, vx

            if      (p.type === "startPoint") { vz = +(p.z_start||0);  vx = +(p.x_start||0) }
            else if (p.type === "lineTo")     { vz = +(p.z_end  ||0);  vx = +(p.x_end  ||0) }
            else if (p.type === "arcTo") {
                vz = +(p.z_end||0);  vx = +(p.x_end||0)
                var r  = +(p.arc_radius||0)
                var zc = +(p.z_center  ||0),  xc = +(p.x_center||0)
                if (zc-r < fZMin) fZMin = zc-r;  if (zc+r > fZMax) fZMax = zc+r
                if (xc-r < fXMin) fXMin = xc-r;  if (xc+r > fXMax) fXMax = xc+r
            } else { continue }

            if (vz < fZMin) fZMin = vz;  if (vz > fZMax) fZMax = vz
            if (vx < fXMin) fXMin = vx;  if (vx > fXMax) fXMax = vx
            if (vz > vZMax) vZMax = vz
            if (vx > vXMax) vXMax = vx
        }

        _maxZ = vZMax
        _maxX = vXMax

        var leftBound   = fZMin - 20
        var rightBound  = Math.max(fZMax, vZMax + 30)
        var topBound    = -20
        var bottomBound = Math.max(fXMax, vXMax + 20)

        _scale   = Math.min(width  / Math.max(rightBound - leftBound, 1),
                            height / Math.max(bottomBound - topBound,  1))
        _originX = (-leftBound) * _scale
        _originY = (-topBound)  * _scale   // = 20 * _scale
    }

    // ── Tick helpers ───────────────────────────────────────────────────────────
    function _steps() {
        if (_scale >= 8)   return { minor: 1,  major: 10 }
        if (_scale >= 3)   return { minor: 2,  major: 10 }
        if (_scale >= 1)   return { minor: 5,  major: 10 }
        if (_scale >= 0.4) return { minor: 10, major: 50 }
        return                    { minor: 50, major: 100 }
    }

    function _isMajor(val, step) {
        return Math.round(Math.abs(val) * 1000) % Math.round(step * 1000) < 1
    }

    // Returns {len, label} for a tick at world value `val`
    function _tickStyle(val, s) {
        if (_isMajor(val, s.major))                      return { len: 7, label: true  }
        if (s.minor <= 5 && _isMajor(val, 5))            return { len: 7, label: false }
        return                                                  { len: 3, label: false }
    }

    // ── Paint dispatcher ───────────────────────────────────────────────────────
    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        _paintBackground(ctx)
        _paintGrid(ctx)
        _paintTicks(ctx)
        _paintCenterLine(ctx)
        _paintAxes(ctx)
        _paintOriginMarker(ctx)
        _paintProfile(ctx)
        _paintHighlight(ctx)
    }

    // ── Background ─────────────────────────────────────────────────────────────
    function _paintBackground(ctx) {
        ctx.fillStyle = "#f5f5f5"
        ctx.fillRect(0, 0, width, height)
    }

    // ── Grid (major step) ──────────────────────────────────────────────────────
    function _paintGrid(ctx) {
        var s = _steps()
        ctx.strokeStyle = "#e0e0e0"
        ctx.lineWidth   = 0.5
        ctx.setLineDash([])

        var zWMin = -_originX / _scale,          zWMax = (width  - _originX) / _scale
        var xWMin = -_originY / _scale,          xWMax = (height - _originY) / _scale
        var z0 = Math.floor(zWMin/s.major)*s.major,  z1 = Math.ceil(zWMax/s.major)*s.major
        var x0 = Math.floor(xWMin/s.major)*s.major,  x1 = Math.ceil(xWMax/s.major)*s.major

        for (var z = z0; z <= z1; z += s.major) {
            var cx = _cx(z)
            ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, height); ctx.stroke()
        }
        for (var x = x0; x <= x1; x += s.major) {
            var cy = _cy(x)
            ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(width, cy); ctx.stroke()
        }
    }

    // ── Tick marks on all four edges ───────────────────────────────────────────
    function _paintTicks(ctx) {
        var s = _steps()
        ctx.strokeStyle = "#666666"
        ctx.fillStyle   = "#333333"
        ctx.lineWidth   = 1
        ctx.setLineDash([])

        // Z — top + bottom edges
        ctx.textAlign = "center"
        var zWMin = -_originX / _scale,  zWMax = (width  - _originX) / _scale
        var zt = Math.floor(zWMin / s.minor) * s.minor
        for (var z = zt; z <= zWMax; z += s.minor) {
            var ts   = _tickStyle(z, s)
            var canX = _cx(z)
            ctx.beginPath(); ctx.moveTo(canX, 0);      ctx.lineTo(canX, ts.len);           ctx.stroke()
            ctx.beginPath(); ctx.moveTo(canX, height);  ctx.lineTo(canX, height - ts.len);  ctx.stroke()
            if (ts.label) {
                ctx.font = "10px sans-serif"
                ctx.textBaseline = "top";    ctx.fillText(Math.round(z).toString(), canX, ts.len + 2)
                ctx.textBaseline = "bottom"; ctx.fillText(Math.round(z).toString(), canX, height - ts.len - 2)
            }
        }

        // X — left + right edges
        var xWMin = -_originY / _scale,  xWMax = (height - _originY) / _scale
        var xt = Math.floor(xWMin / s.minor) * s.minor
        for (var x = xt; x <= xWMax; x += s.minor) {
            var tsx  = _tickStyle(x, s)
            var canY = _cy(x)
            ctx.beginPath(); ctx.moveTo(0,     canY); ctx.lineTo(tsx.len,         canY); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(width, canY); ctx.lineTo(width - tsx.len, canY); ctx.stroke()
            if (tsx.label) {
                ctx.font = "10px sans-serif"
                ctx.textAlign = "left";  ctx.textBaseline = "middle"
                ctx.fillText(Math.round(x).toString(), tsx.len + 2, canY)
                ctx.textAlign = "right"
                ctx.fillText(Math.round(x).toString(), width - tsx.len - 2, canY)
            }
        }
    }

    // ── Spindle axis centre line — dashed, behind arrows ──────────────────────
    function _paintCenterLine(ctx) {
        ctx.strokeStyle = "#bbbbbb"
        ctx.lineWidth   = 1
        ctx.setLineDash([10, 4, 3, 4])
        ctx.beginPath()
        ctx.moveTo(0, _originY); ctx.lineTo(width, _originY)
        ctx.stroke()
        ctx.setLineDash([])
    }

    // ── Axis arrows (Z+ right, X+ down) starting from circle edge ─────────────
    function _paintAxes(ctx) {
        var aw = 9, ah = aw * 0.4, cr = _circleR

        // Z+ — green
        var zTipX  = _cx(_maxZ + 10)
        var zShaft = zTipX - aw
        var zStart = _originX + cr + 1
        ctx.strokeStyle = "#2E7D32"; ctx.fillStyle = "#2E7D32"; ctx.lineWidth = 1.5
        ctx.setLineDash([])
        if (zShaft > zStart) {
            ctx.beginPath(); ctx.moveTo(zStart, _originY); ctx.lineTo(zShaft, _originY); ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(zTipX,  _originY)
        ctx.lineTo(zShaft, _originY - ah)
        ctx.lineTo(zShaft, _originY + ah)
        ctx.closePath(); ctx.fill()
        ctx.font = "bold 11px sans-serif"
        ctx.textAlign = "left"; ctx.textBaseline = "bottom"
        ctx.fillText("Z+", zTipX + 4, _originY - 2)

        // X+ — blue
        var xTipY  = _cy(_maxX + 10)
        var xShaft = xTipY - aw
        var xStart = _originY + cr + 1
        ctx.strokeStyle = "#1565C0"; ctx.fillStyle = "#1565C0"
        if (xShaft > xStart) {
            ctx.beginPath(); ctx.moveTo(_originX, xStart); ctx.lineTo(_originX, xShaft); ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(_originX,      xTipY)
        ctx.lineTo(_originX - ah, xShaft)
        ctx.lineTo(_originX + ah, xShaft)
        ctx.closePath(); ctx.fill()
        ctx.font = "bold 11px sans-serif"
        ctx.textAlign = "left"; ctx.textBaseline = "top"
        ctx.fillText("X+", _originX + 4, xTipY + 2)
    }

    // ── Origin marker: circle with alternating filled/outlined quadrants ────────
    function _paintOriginMarker(ctx) {
        var r = _circleR, ocx = _originX, ocy = _originY
        ctx.lineWidth = 1.5; ctx.fillStyle = "#222222"; ctx.strokeStyle = "#222222"
        ctx.setLineDash([])
        var quads = [
            { start: -Math.PI/2,     end: 0,              fill: true  },
            { start: 0,              end: Math.PI/2,       fill: false },
            { start: Math.PI/2,      end: Math.PI,         fill: true  },
            { start: Math.PI,        end: 3*Math.PI/2,     fill: false },
        ]
        for (var i = 0; i < quads.length; i++) {
            var q = quads[i]
            ctx.beginPath(); ctx.moveTo(ocx, ocy)
            ctx.arc(ocx, ocy, r, q.start, q.end, false)
            ctx.closePath()
            if (q.fill) ctx.fill(); else ctx.stroke()
        }
    }

        // ── Profile (dark gray, no vertex dots) ────────────────────────────────────
    function _paintProfile(ctx) {
        if (!primitives || primitives.length === 0) return
        var logZ = 0, logX = 0
        var drawZ = 0, drawX = 0
        ctx.strokeStyle = "#333333"; ctx.lineWidth = 2
        ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.setLineDash([])

        // Collect dotted "extensions" for chamfers so the original corner is still visible
        // after the chamfer cuts it off.
        var chamferDashes = []   // each item: { z1, x1, z2, x2 }

        ctx.beginPath()
        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            if (p.type === "startPoint") {
                logZ = +(p.z_start||0); logX = +(p.x_start||0)
                drawZ = logZ; drawX = logX
                ctx.moveTo(_cx(logZ), _cy(logX))
            } else if (p.type === "lineTo") {
                var ez = +(p.z_end||0), ex = +(p.x_end||0)
                if (p.blend && p.blend.type === "chamfer") {
                    var cw  = +(p.blend.chamfer_width || 0)
                    var sdz = ez - logZ, sdx = ex - logX
                    var slen = Math.sqrt(sdz*sdz + sdx*sdx)
                    if (slen > 0.001 && cw > 0.001) {
                        // chamfer start: back off from end along current segment
                        var csZ = ez - cw * sdz / slen
                        var csX = ex - cw * sdx / slen
                        // chamfer end: advance from corner along next segment
                        var ceZ = ez, ceX = ex
                        var nextP = (i+1 < primitives.length) ? primitives[i+1] : null
                        if (nextP && nextP.type === "lineTo") {
                            var ndz = +(nextP.z_end||0) - ez
                            var ndx = +(nextP.x_end||0) - ex
                            var nlen = Math.sqrt(ndz*ndz + ndx*ndx)
                            if (nlen > 0.001) { ceZ = ez + cw*ndz/nlen; ceX = ex + cw*ndx/nlen }
                        } else if (nextP && nextP.type === "arcTo") {
                            var nacz = +(nextP.z_center||0), nacx = +(nextP.x_center||0)
                            var nrz = ez - nacz, nrx = ex - nacx
                            var nndz = (nextP.direction === "cw") ? nrx : -nrx
                            var nndx = (nextP.direction === "cw") ? -nrz : nrz
                            var nlen2 = Math.sqrt(nndz*nndz + nndx*nndx)
                            if (nlen2 > 0.001) { ceZ = ez + cw*nndz/nlen2; ceX = ex + cw*nndx/nlen2 }
                        }

                        // Solid profile up to chamfer start, then chamfer to chamfer end
                        ctx.lineTo(_cx(csZ), _cy(csX))
                        ctx.lineTo(_cx(ceZ), _cy(ceX))
                        drawZ = ceZ; drawX = ceX

                        // Dotted "would-have-been" lines to the original corner
                        chamferDashes.push({ z1: csZ, x1: csX, z2: ez,  x2: ex })
                        chamferDashes.push({ z1: ez,  x1: ex,  z2: ceZ, x2: ceX })
                    } else {
                        ctx.lineTo(_cx(ez), _cy(ex))
                        drawZ = ez; drawX = ex
                    }
                } else {
                    ctx.lineTo(_cx(ez), _cy(ex))
                    drawZ = ez; drawX = ex
                }
                logZ = ez; logX = ex
            } else if (p.type === "arcTo") {
                var aez = +(p.z_end||0),   aex = +(p.x_end||0)
                var acz = +(p.z_center||0), acx = +(p.x_center||0)
                var ar  = +(p.arc_radius||0), isCW = (p.direction === "cw")
                var ccx = _cx(acz), ccy = _cy(acx), cr = ar * _scale
                var sa = Math.atan2(_cy(drawX)-ccy, _cx(drawZ)-ccx)
                var ea = Math.atan2(_cy(aex)  -ccy, _cx(aez)  -ccx)
                ctx.arc(ccx, ccy, cr, sa, ea, !isCW)
                logZ = aez; logX = aex
                drawZ = aez; drawX = aex
            }
        }
        ctx.stroke()

        // Draw dotted extensions *after* the solid profile, so we don't mess up the main path.
        if (chamferDashes.length > 0) {
            ctx.save()
            ctx.setLineDash([2, 3])
            ctx.strokeStyle = "#7a7a7a"
            ctx.lineWidth = 1.2
            ctx.lineJoin = "round"
            ctx.lineCap = "round"
            ctx.beginPath()
            for (var d = 0; d < chamferDashes.length; d++) {
                var s = chamferDashes[d]
                ctx.moveTo(_cx(s.z1), _cy(s.x1))
                ctx.lineTo(_cx(s.z2), _cy(s.x2))
            }
            ctx.stroke()
            ctx.restore()
        }
    }

    function _paintHighlight(ctx) {
        var idx = selectedPrimIndex
        if (idx < 0 || !primitives || idx >= primitives.length) return

        // Track logical and actual drawn position before the selected primitive
        var logZ = 0, logX = 0
        var drawZ = 0, drawX = 0
        for (var j = 0; j < idx; j++) {
            var prev = primitives[j]
            if (prev.type === "startPoint") {
                logZ = +(prev.z_start||0); logX = +(prev.x_start||0)
                drawZ = logZ; drawX = logX
            } else if (prev.type === "lineTo") {
                var pez = +(prev.z_end||0), pex = +(prev.x_end||0)
                if (prev.blend && prev.blend.type === "chamfer") {
                    var pcw = +(prev.blend.chamfer_width || 0)
                    var pNextP = (j+1 < primitives.length) ? primitives[j+1] : null
                    var pceZ = pez, pceX = pex
                    if (pNextP && pNextP.type === "lineTo" && pcw > 0.001) {
                        var pndz = +(pNextP.z_end||0) - pez
                        var pndx = +(pNextP.x_end||0) - pex
                        var pnlen = Math.sqrt(pndz*pndz + pndx*pndx)
                        if (pnlen > 0.001) { pceZ = pez + pcw*pndz/pnlen; pceX = pex + pcw*pndx/pnlen }
                    } else if (pNextP && pNextP.type === "arcTo" && pcw > 0.001) {
                        var pnacz = +(pNextP.z_center||0), pnacx = +(pNextP.x_center||0)
                        var pnrz = pez - pnacz, pnrx = pex - pnacx
                        var pnndz = (pNextP.direction === "cw") ? pnrx : -pnrx
                        var pnndx = (pNextP.direction === "cw") ? -pnrz : pnrz
                        var pnlen2 = Math.sqrt(pnndz*pnndz + pnndx*pnndx)
                        if (pnlen2 > 0.001) { pceZ = pez + pcw*pnndz/pnlen2; pceX = pex + pcw*pnndx/pnlen2 }
                    }
                    drawZ = pceZ; drawX = pceX
                } else {
                    drawZ = pez; drawX = pex
                }
                logZ = pez; logX = pex
            } else if (prev.type === "arcTo") {
                logZ = +(prev.z_end||0); logX = +(prev.x_end||0)
                drawZ = logZ; drawX = logX
            }
        }

        var p = primitives[idx]
        ctx.setLineDash([])

        if (p.type === "startPoint") {
            ctx.fillStyle = "#E53935"
            ctx.beginPath()
            ctx.arc(_cx(+(p.z_start||0)), _cy(+(p.x_start||0)), 6, 0, Math.PI*2)
            ctx.fill()

        } else if (p.type === "lineTo") {
            var ez = +(p.z_end||0), ex = +(p.x_end||0)
            ctx.strokeStyle = "#E53935"; ctx.lineWidth = 2
            ctx.lineJoin = "round"; ctx.lineCap = "round"
            ctx.beginPath()
            ctx.moveTo(_cx(drawZ), _cy(drawX))
            if (p.blend && p.blend.type === "chamfer") {
                var hcw  = +(p.blend.chamfer_width || 0)
                var hsdz = ez - logZ, hsdx = ex - logX
                var hslen = Math.sqrt(hsdz*hsdz + hsdx*hsdx)
                if (hslen > 0.001 && hcw > 0.001) {
                    var hcsZ = ez - hcw * hsdz / hslen
                    var hcsX = ex - hcw * hsdx / hslen
                    var hceZ = ez, hceX = ex
                    var hnextP = (idx+1 < primitives.length) ? primitives[idx+1] : null
                    if (hnextP && hnextP.type === "lineTo") {
                        var hndz = +(hnextP.z_end||0) - ez
                        var hndx = +(hnextP.x_end||0) - ex
                        var hnlen = Math.sqrt(hndz*hndz + hndx*hndx)
                        if (hnlen > 0.001) { hceZ = ez + hcw*hndz/hnlen; hceX = ex + hcw*hndx/hnlen }
                    } else if (hnextP && hnextP.type === "arcTo") {
                        var hnacz = +(hnextP.z_center||0), hnacx = +(hnextP.x_center||0)
                        var hnrz = ez - hnacz, hnrx = ex - hnacx
                        var hnndz = (hnextP.direction === "cw") ? hnrx : -hnrx
                        var hnndx = (hnextP.direction === "cw") ? -hnrz : hnrz
                        var hnlen2 = Math.sqrt(hnndz*hnndz + hnndx*hnndx)
                        if (hnlen2 > 0.001) { hceZ = ez + hcw*hnndz/hnlen2; hceX = ex + hcw*hnndx/hnlen2 }
                    }
                    ctx.lineTo(_cx(hcsZ), _cy(hcsX))
                    ctx.lineTo(_cx(hceZ), _cy(hceX))
                    ctx.stroke()
                    ctx.fillStyle = "#E53935"
                    ctx.beginPath(); ctx.arc(_cx(hceZ), _cy(hceX), 5, 0, Math.PI*2); ctx.fill()
                } else {
                    ctx.lineTo(_cx(ez), _cy(ex)); ctx.stroke()
                    ctx.fillStyle = "#E53935"
                    ctx.beginPath(); ctx.arc(_cx(ez), _cy(ex), 5, 0, Math.PI*2); ctx.fill()
                }
            } else {
                ctx.lineTo(_cx(ez), _cy(ex)); ctx.stroke()
                ctx.fillStyle = "#E53935"
                ctx.beginPath(); ctx.arc(_cx(ez), _cy(ex), 5, 0, Math.PI*2); ctx.fill()
            }

        } else if (p.type === "arcTo") {
            var aez = +(p.z_end||0),    aex = +(p.x_end||0)
            var acz = +(p.z_center||0), acx = +(p.x_center||0)
            var ar  = +(p.arc_radius||0), isCW2 = (p.direction === "cw")
            var ccx = _cx(acz), ccy = _cy(acx), cr2 = ar * _scale
            var sa2 = Math.atan2(_cy(drawX)-ccy, _cx(drawZ)-ccx)
            var ea2 = Math.atan2(_cy(aex)  -ccy, _cx(aez)  -ccx)
            ctx.strokeStyle = "#E53935"; ctx.lineWidth = 2
            ctx.lineJoin = "round"; ctx.lineCap = "round"
            ctx.beginPath()
            ctx.arc(ccx, ccy, cr2, sa2, ea2, !isCW2)
            ctx.stroke()
            ctx.fillStyle = "#E53935"
            ctx.beginPath(); ctx.arc(_cx(aez), _cy(aex), 5, 0, Math.PI*2); ctx.fill()
            ctx.fillStyle = "#888888"
            ctx.beginPath(); ctx.arc(ccx, ccy, 4, 0, Math.PI*2); ctx.fill()
        }
    }

    // ── Hit testing ────────────────────────────────────────────────────────────
    function _distToSegment(px, py, x1, y1, x2, y2) {
        var dx = x2-x1, dy = y2-y1
        var lenSq = dx*dx + dy*dy
        if (lenSq < 1) return Math.sqrt((px-x1)*(px-x1) + (py-y1)*(py-y1))
        var t  = Math.max(0, Math.min(1, ((px-x1)*dx + (py-y1)*dy) / lenSq))
        var rx = x1 + t*dx - px, ry = y1 + t*dy - py
        return Math.sqrt(rx*rx + ry*ry)
    }

    function _normAngle(a) {
        var TWO_PI = Math.PI * 2
        return ((a % TWO_PI) + TWO_PI) % TWO_PI
    }

    function _angleInArc(testAngle, startAng, endAng, anticlockwise) {
        var s = _normAngle(startAng), e = _normAngle(endAng), a = _normAngle(testAngle)
        if (!anticlockwise) {          // CW: angles increase from s to e
            return (s <= e) ? (a >= s && a <= e) : (a >= s || a <= e)
        } else {                       // CCW: angles decrease from s to e
            return (s >= e) ? (a >= e && a <= s) : (a <= s || a >= e)
        }
    }

    function _distToArc(px, py, ccx, ccy, cr, sa, ea, anticlockwise) {
        var dx = px-ccx, dy = py-ccy
        var dist = Math.sqrt(dx*dx + dy*dy)
        if (dist < 1) return cr
        var distToCircle = Math.abs(dist - cr)
        if (distToCircle > 20) return 1e9
        if (_angleInArc(Math.atan2(dy, dx), sa, ea, anticlockwise)) return distToCircle
        // nearest arc endpoint
        var sx = ccx + cr*Math.cos(sa), sy = ccy + cr*Math.sin(sa)
        var ex = ccx + cr*Math.cos(ea), ey = ccy + cr*Math.sin(ea)
        var d1 = Math.sqrt((px-sx)*(px-sx) + (py-sy)*(py-sy))
        var d2 = Math.sqrt((px-ex)*(px-ex) + (py-ey)*(py-ey))
        return Math.min(d1, d2)
    }

    function _hitTest(px, py) {
        if (!primitives || primitives.length === 0) return -1
        var HIT = 10    // pixel tolerance
        var curZ = 0, curX = 0
        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            if (p.type === "startPoint") {
                var sz = +(p.z_start||0), sx = +(p.x_start||0)
                var dx = px - _cx(sz), dy = py - _cy(sx)
                if (dx*dx + dy*dy <= HIT*HIT) return i
                curZ = sz; curX = sx
            } else if (p.type === "lineTo") {
                var ez = +(p.z_end||0), ex = +(p.x_end||0)
                if (_distToSegment(px, py, _cx(curZ), _cy(curX), _cx(ez), _cy(ex)) <= HIT) return i
                curZ = ez; curX = ex
            } else if (p.type === "arcTo") {
                var aez = +(p.z_end||0),    aex = +(p.x_end||0)
                var acz = +(p.z_center||0), acx = +(p.x_center||0)
                var ar  = +(p.arc_radius||0), isCW = (p.direction === "cw")
                var ccx = _cx(acz), ccy = _cy(acx), cr = ar * _scale
                var sa  = Math.atan2(_cy(curX)-ccy, _cx(curZ)-ccx)
                var ea  = Math.atan2(_cy(aex) -ccy, _cx(aez) -ccx)
                if (_distToArc(px, py, ccx, ccy, cr, sa, ea, !isCW) <= HIT) return i
                curZ = aez; curX = aex
            }
        }
        return -1
    }

    // ── Click handler ──────────────────────────────────────────────────────────
    MouseArea {
        anchors.fill: parent
        onClicked: function(mouse) {
            var idx = root._hitTest(mouse.x, mouse.y)
            if (idx >= 0) root.primitiveSelected(idx)
        }
    }
}