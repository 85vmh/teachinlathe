// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// Scale and origin are computed from fixed viewport margins.
import QtQuick 2.15

Canvas {
    id: root

    property var primitives:        []   // array of primitive objects from JSON
    property int selectedPrimIndex:  -1  // index into primitives; -1 = none
    property int selectedBlendIndex: -1  // index of primitive whose blend is selected; -1 = none

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
    onPrimitivesChanged:         { _computeScale(); requestPaint() }
    onWidthChanged:              { _computeScale(); requestPaint() }
    onHeightChanged:             { _computeScale(); requestPaint() }
    onSelectedPrimIndexChanged:  requestPaint()
    onSelectedBlendIndexChanged: requestPaint()

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
            ctx.beginPath();  ctx.moveTo(ocx, ocy)
            ctx.arc(ocx, ocy, r, q.start, q.end, false)
            ctx.closePath()
            if (q.fill)
                ctx.fill();
            ctx.stroke()
        }
    }

    // ── Fillet geometry: tangent points + arc centre for a line-line fillet ──────
    // startZ/X: logical start of line 1, cornerZ/X: the corner (end of lineTo),
    // nextP: the next primitive (must be a lineTo), fr: fillet radius.
    // Returns {t1z,t1x, t2z,t2x, fcz,fcx, anticlockwise} or null when invalid.
    function _filletGeom(startZ, startX, cornerZ, cornerX, nextP, fr) {
        var sdz = cornerZ - startZ, sdx = cornerX - startX
        var slen = Math.sqrt(sdz*sdz + sdx*sdx)
        if (slen < 0.001 || fr < 0.001) return null
        if (!nextP || nextP.type !== "lineTo") return null
        var ndz = +(nextP.z_end||0) - cornerZ, ndx = +(nextP.x_end||0) - cornerX
        var nlen = Math.sqrt(ndz*ndz + ndx*ndx)
        if (nlen < 0.001) return null

        var d1z = sdz / slen, d1x = sdx / slen   // unit dir of line 1 (into corner)
        var d2z = ndz / nlen, d2x = ndx / nlen   // unit dir of line 2 (out of corner)

        // 2D cross and dot products
        var cross = d1z * d2x - d1x * d2z        // sin(θ), sign → turn direction
        var dot   = d1z * d2z + d1x * d2x        // cos(θ)
        var absCross = Math.abs(cross)
        if (absCross < 0.001) return null         // lines (nearly) parallel

        // Tangent length: t = r / tan(α/2) where α = deflection angle between -d1 and d2
        // cos(α) = -dot, sin(α) = absCross → t = r·(1-dot)/absCross
        var t   = fr * (1.0 - dot) / absCross
        var t1z = cornerZ - t * d1z,  t1x = cornerX - t * d1x  // tangent pt on line 1
        var t2z = cornerZ + t * d2z,  t2x = cornerX + t * d2x  // tangent pt on line 2

        // Perpendicular to d1 pointing towards the arc centre (inside of the turn)
        // cross > 0 → CW turn → centre is to the LEFT of d1 = (-d1x, d1z)
        // cross < 0 → CCW turn → centre is to the RIGHT of d1 = (d1x, -d1z)
        var perpZ = (cross > 0) ? -d1x :  d1x
        var perpX = (cross > 0) ?  d1z : -d1z

        return {
            t1z: t1z, t1x: t1x, t2z: t2z, t2x: t2x,
            fcz: t1z + fr * perpZ, fcx: t1x + fr * perpX,
            anticlockwise: (cross < 0)   // CW turn → arc drawn CW → anticlockwise=false
        }
    }

    // ── Fillet geometry: arcTo end → lineTo (exact circle-line tangency) ──────
    // The fillet circle (radius fr) must be externally tangent to the original arc
    // (|C2-C1| = R+fr) and tangent to line 2 (dist = fr).
    // Solves the resulting quadratic for the fillet centre C2 on the offset of line 2.
    // Returns {t1z,t1x, t2z,t2x, fcz,fcx, anticlockwise} or null.
    // T1 is the tangent point on the original arc, T2 on the line.
    function _filletArcLine(acz, acx, ar, isCW, jZ, jX, nextP, fr) {
        if (!nextP || nextP.type !== "lineTo") return null
        var d2zr = +(nextP.z_end||0) - jZ,  d2xr = +(nextP.x_end||0) - jX
        var d2len = Math.sqrt(d2zr*d2zr + d2xr*d2xr)
        if (d2len < 0.001 || fr < 0.001 || ar < 0.001) return null
        var d2z = d2zr / d2len,  d2x = d2xr / d2len

        // Arc tangent at end:  CW → (-rex, rez)/rlen,  CCW → (rex, -rez)/rlen
        var rez = jZ - acz,  rex = jX - acx
        var rlen = Math.sqrt(rez*rez + rex*rex)
        if (rlen < 0.001) return null
        var d1z = (isCW ? -rex : rex) / rlen
        var d1x = (isCW ?  rez : -rez) / rlen

        var cross = d1z * d2x - d1x * d2z
        if (Math.abs(cross) < 0.001) return null  // arc tangent ~ parallel to line

        // Normal to line 2 pointing toward the fillet centre (same convention as _filletGeom)
        var n2z = (cross > 0) ? -d2x :  d2x
        var n2x = (cross > 0) ?  d2z : -d2z

        // Δ = J + fr·n2 − C1  (vector from arc centre to offset-line base)
        var dz = jZ + fr*n2z - acz
        var dx = jX + fr*n2x - acx

        // Quadratic: t² + 2(Δ·d2)t + (|Δ|² − (R+fr)²) = 0
        var dotD2 = dz*d2z + dx*d2x
        var discrim = dotD2*dotD2 - (dz*dz + dx*dx) + (ar+fr)*(ar+fr)
        if (discrim < 0) return null

        var t = -dotD2 + Math.sqrt(discrim)   // root nearest to junction

        // Fillet centre C2, tangent point on line T2, tangent point on arc T1
        var fcz = jZ + fr*n2z + t*d2z
        var fcx = jX + fr*n2x + t*d2x
        var t2z = jZ + t*d2z
        var t2x = jX + t*d2x
        var vcz = fcz - acz,  vcx = fcx - acx
        var vclen = Math.sqrt(vcz*vcz + vcx*vcx)
        if (vclen < 0.001) return null
        return {
            t1z: acz + ar * vcz / vclen,
            t1x: acx + ar * vcx / vclen,
            t2z: t2z, t2x: t2x,
            fcz: fcz, fcx: fcx,
            anticlockwise: (cross < 0)
        }
    }

    // ── Fillet geometry: lineTo end → arcTo (exact circle-arc tangency) ─────────
    // The fillet circle (radius fr) must be tangent to line 1 (incoming) and
    // externally tangent to arc 2 (|C_f - C_arc| = ar + fr).
    // Parameterises the fillet centre along the offset of line 1 going backward.
    // Returns {t1z,t1x, t2z,t2x, fcz,fcx, anticlockwise} or null.
    // T1 is the tangent point on line 1, T2 on arc 2.
    function _filletLineArc(startZ, startX, cornerZ, cornerX, nextArc, fr) {
        if (!nextArc || nextArc.type !== "arcTo") return null
        var isCW = (nextArc.direction === "cw")
        var acz = +(nextArc.z_center||0), acx = +(nextArc.x_center||0)
        var ar  = +(nextArc.arc_radius||0)
        if (fr < 0.001 || ar < 0.001) return null

        // Line 1 direction (into corner)
        var sdz = cornerZ - startZ, sdx = cornerX - startX
        var slen = Math.sqrt(sdz*sdz + sdx*sdx)
        if (slen < 0.001) return null
        var d1z = sdz / slen, d1x = sdx / slen

        // Arc 2 tangent direction at start (= corner), same formula as arc-end tangent
        var rsz = cornerZ - acz, rsx = cornerX - acx
        var rlen = Math.sqrt(rsz*rsz + rsx*rsx)
        if (rlen < 0.001) return null
        var d2z = (isCW ? -rsx : rsx) / rlen
        var d2x = (isCW ?  rsz : -rsz) / rlen

        var cross = d1z * d2x - d1x * d2z
        if (Math.abs(cross) < 0.001) return null  // line tangent to arc

        // Normal to line 1 pointing toward fillet centre (same convention as _filletGeom)
        var n1z = (cross > 0) ? -d1x :  d1x
        var n1x = (cross > 0) ?  d1z : -d1z

        // Δ = J + fr·n1 − C_arc  (vector from arc centre to offset-line base)
        var dz = cornerZ + fr*n1z - acz
        var dx = cornerX + fr*n1x - acx

        // Parameterise along −d1 (going backward from corner along line 1):
        // t² + 2(Δ·(−d1))t + (|Δ|² − (ar+fr)²) = 0
        // t = (Δ·d1) ± sqrt((Δ·d1)² − |Δ|² + (ar+fr)²)
        // Take the root nearest to the junction (mirrors _filletArcLine convention)
        var dotD1 = dz*d1z + dx*d1x
        var discrim = dotD1*dotD1 - (dz*dz + dx*dx) + (ar+fr)*(ar+fr)
        if (discrim < 0) return null

        var t = dotD1 + Math.sqrt(discrim)  // T1 is t units back from corner along line 1

        // Fillet centre C_f, tangent point on line T1, tangent point on arc T2
        var fcz = cornerZ - t*d1z + fr*n1z
        var fcx = cornerX - t*d1x + fr*n1x
        var t1z = cornerZ - t*d1z
        var t1x = cornerX - t*d1x
        var vcz = fcz - acz, vcx = fcx - acx
        var vclen = Math.sqrt(vcz*vcz + vcx*vcx)
        if (vclen < 0.001) return null

        return {
            t1z: t1z, t1x: t1x,
            t2z: acz + ar * vcz / vclen,
            t2x: acx + ar * vcx / vclen,
            fcz: fcz, fcx: fcx,
            anticlockwise: (cross < 0)
        }
    }

    // ── Chamfer geometry helpers ────────────────────────────────────────────────
    // Both return {csZ, csX, ceZ, ceX} (chamfer start / end) or null if degenerate.

    // For a lineTo ending at (ez,ex): csZ/X steps back along the incoming segment,
    // ceZ/X steps forward along the next segment's tangent direction.
    function _chamferGeomLine(logZ, logX, ez, ex, nextP, cw) {
        var sdz = ez - logZ, sdx = ex - logX
        var slen = Math.sqrt(sdz*sdz + sdx*sdx)
        if (slen < 0.001 || cw < 0.001) return null
        var csZ = ez - cw * sdz / slen,  csX = ex - cw * sdx / slen
        var ceZ = ez, ceX = ex
        if (nextP && nextP.type === "lineTo") {
            var ndz = +(nextP.z_end||0) - ez,  ndx = +(nextP.x_end||0) - ex
            var nlen = Math.sqrt(ndz*ndz + ndx*ndx)
            if (nlen > 0.001) { ceZ = ez + cw*ndz/nlen; ceX = ex + cw*ndx/nlen }
        } else if (nextP && nextP.type === "arcTo") {
            var nacz = +(nextP.z_center||0), nacx = +(nextP.x_center||0)
            var nrz = ez - nacz, nrx = ex - nacx
            var nndz = (nextP.direction === "cw") ? -nrx :  nrx
            var nndx = (nextP.direction === "cw") ?  nrz : -nrz
            var nlen2 = Math.sqrt(nndz*nndz + nndx*nndx)
            if (nlen2 > 0.001) { ceZ = ez + cw*nndz/nlen2; ceX = ex + cw*nndx/nlen2 }
        }
        return { csZ: csZ, csX: csX, ceZ: ceZ, ceX: ceX }
    }

    // For an arcTo ending at (aez,aex): csZ/X steps back along the arc end tangent,
    // ceZ/X steps forward along the next segment's tangent direction.
    function _chamferGeomArc(acz, acx, ar, isCW, aez, aex, nextP, acw) {
        var arez = aez - acz, arex = aex - acx
        var arlen = Math.sqrt(arez*arez + arex*arex)
        if (arlen < 0.001 || acw < 0.001) return null
        var atdz = isCW ? -arex :  arex    // tangent at arc end: CW → (-arex, arez)
        var atdx = isCW ?  arez : -arez
        var csZ = aez - acw * atdz / arlen,  csX = aex - acw * atdx / arlen
        var ceZ = aez, ceX = aex
        if (nextP && nextP.type === "lineTo") {
            var andz = +(nextP.z_end||0) - aez,  andx = +(nextP.x_end||0) - aex
            var anlen = Math.sqrt(andz*andz + andx*andx)
            if (anlen > 0.001) { ceZ = aez + acw*andz/anlen; ceX = aex + acw*andx/anlen }
        }
        return { csZ: csZ, csX: csX, ceZ: ceZ, ceX: ceX }
    }

    // ── Profile (dark gray, no vertex dots) ────────────────────────────────────
    function _paintProfile(ctx) {
        if (!primitives || primitives.length === 0) return
        var logZ = 0, logX = 0
        var drawZ = 0, drawX = 0
        ctx.strokeStyle = "#333333"; ctx.lineWidth = 1
        ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.setLineDash([])

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
                            var nndz = (nextP.direction === "cw") ? -nrx :  nrx
                            var nndx = (nextP.direction === "cw") ?  nrz : -nrz
                            var nlen2 = Math.sqrt(nndz*nndz + nndx*nndx)
                            if (nlen2 > 0.001) { ceZ = ez + cw*nndz/nlen2; ceX = ex + cw*nndx/nlen2 }
                        }

                        // Solid profile up to chamfer start, then chamfer to chamfer end
                        ctx.lineTo(_cx(csZ), _cy(csX))
                        ctx.lineTo(_cx(ceZ), _cy(ceX))
                        drawZ = ceZ; drawX = ceX
                    } else {
                        ctx.lineTo(_cx(ez), _cy(ex))
                        drawZ = ez; drawX = ex
                    }
                } else if (p.blend && p.blend.type === "fillet") {
                    var fr  = +(p.blend.fillet_radius || 0)
                    var nextPrim = i+1 < primitives.length ? primitives[i+1] : null
                    var fg = (nextPrim && nextPrim.type === "arcTo")
                             ? _filletLineArc(logZ, logX, ez, ex, nextPrim, fr)
                             : _filletGeom(logZ, logX, ez, ex, nextPrim, fr)
                    if (fg) {
                        ctx.lineTo(_cx(fg.t1z), _cy(fg.t1x))
                        var fccx = _cx(fg.fcz), fccy = _cy(fg.fcx), fcr = fr * _scale
                        var fsa = Math.atan2(_cy(fg.t1x) - fccy, _cx(fg.t1z) - fccx)
                        var fea = Math.atan2(_cy(fg.t2x) - fccy, _cx(fg.t2z) - fccx)
                        ctx.arc(fccx, fccy, fcr, fsa, fea, fg.anticlockwise)
                        drawZ = fg.t2z; drawX = fg.t2x
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

                if (p.blend && p.blend.type === "chamfer") {
                    var acw = +(p.blend.chamfer_width || 0)
                    // Tangent direction at arc end (rotate radius vector at end):
                    //   CW:  (-rex,  rez)    CCW: ( rex, -rez)
                    var arez = aez - acz, arex = aex - acx
                    var arlen = Math.sqrt(arez*arez + arex*arex)
                    if (arlen > 0.001 && acw > 0.001) {
                        var atdz = isCW ? -arex :  arex
                        var atdx = isCW ?  arez : -arez
                        // Chamfer start: step back from arc end along arc tangent
                        var acsZ = aez - acw * atdz / arlen
                        var acsX = aex - acw * atdx / arlen
                        // Chamfer end: step forward along next line from corner
                        var aceZ = aez, aceX = aex
                        var anextP = (i+1 < primitives.length) ? primitives[i+1] : null
                        if (anextP && anextP.type === "lineTo") {
                            var andz = +(anextP.z_end||0) - aez
                            var andx = +(anextP.x_end||0) - aex
                            var anlen = Math.sqrt(andz*andz + andx*andx)
                            if (anlen > 0.001) { aceZ = aez + acw*andz/anlen; aceX = aex + acw*andx/anlen }
                        }
                        // Trim arc to cs angle, then draw chamfer line to ce
                        var ea_cs = Math.atan2(_cy(acsX) - ccy, _cx(acsZ) - ccx)
                        ctx.arc(ccx, ccy, cr, sa, ea_cs, !isCW)
                        ctx.lineTo(_cx(aceZ), _cy(aceX))
                        drawZ = aceZ; drawX = aceX
                    } else {
                        var ea_fb = Math.atan2(_cy(aex) - ccy, _cx(aez) - ccx)
                        ctx.arc(ccx, ccy, cr, sa, ea_fb, !isCW)
                        drawZ = aez; drawX = aex
                    }
                } else if (p.blend && p.blend.type === "fillet") {
                    var afr = +(p.blend.fillet_radius || 0)
                    var afg = _filletArcLine(acz, acx, ar, isCW, aez, aex,
                                             i+1 < primitives.length ? primitives[i+1] : null, afr)
                    if (afg) {
                        // Original arc trimmed to T1, then fillet arc to T2
                        var ea_t1 = Math.atan2(_cy(afg.t1x) - ccy, _cx(afg.t1z) - ccx)
                        ctx.arc(ccx, ccy, cr, sa, ea_t1, !isCW)
                        var afccx = _cx(afg.fcz), afccy = _cy(afg.fcx), afcr = afr * _scale
                        var afsa = Math.atan2(_cy(afg.t1x) - afccy, _cx(afg.t1z) - afccx)
                        var afea = Math.atan2(_cy(afg.t2x) - afccy, _cx(afg.t2z) - afccx)
                        ctx.arc(afccx, afccy, afcr, afsa, afea, afg.anticlockwise)
                        drawZ = afg.t2z; drawX = afg.t2x
                    } else {
                        var ea_fb3 = Math.atan2(_cy(aex) - ccy, _cx(aez) - ccx)
                        ctx.arc(ccx, ccy, cr, sa, ea_fb3, !isCW)
                        drawZ = aez; drawX = aex
                    }
                } else {
                    var ea = Math.atan2(_cy(aex) - ccy, _cx(aez) - ccx)
                    ctx.arc(ccx, ccy, cr, sa, ea, !isCW)
                    drawZ = aez; drawX = aex
                }
                logZ = aez; logX = aex
            }
        }
        ctx.stroke()
    }

    // ── Walk primitives up to (not including) targetIdx ─────────────────────────
    // Returns {logZ, logX}: the logical endpoint of the primitive just before targetIdx.
    // Blend trimming only affects the draw position, not the logical endpoint —
    // _paintHighlight renders the full theoretical primitive so only logZ/logX is needed.
    function _walkToIndex(targetIdx) {
        var logZ = 0, logX = 0
        for (var j = 0; j < targetIdx; j++) {
            var p = primitives[j]
            if      (p.type === "startPoint") { logZ = +(p.z_start||0); logX = +(p.x_start||0) }
            else if (p.type === "lineTo")     { logZ = +(p.z_end  ||0); logX = +(p.x_end  ||0) }
            else if (p.type === "arcTo")      { logZ = +(p.z_end  ||0); logX = +(p.x_end  ||0) }
        }
        return { logZ: logZ, logX: logX }
    }

    function _paintHighlight(ctx) {
        if (selectedPrimIndex < 0 && selectedBlendIndex < 0) return
        if (!primitives) return

        var targetIdx = (selectedPrimIndex >= 0) ? selectedPrimIndex : selectedBlendIndex
        if (targetIdx >= primitives.length) return

        var pos  = _walkToIndex(targetIdx)
        var logZ = pos.logZ, logX = pos.logX

        var p = primitives[targetIdx]
        ctx.setLineDash([])

        if (selectedPrimIndex >= 0) {
            // ── Full theoretical primitive (ignore blend trimming) ────────────────
            ctx.strokeStyle = "#E53935"; ctx.lineWidth = 2
            ctx.lineJoin = "round"; ctx.lineCap = "round"

            if (p.type === "startPoint") {
                ctx.fillStyle = "#E53935"
                ctx.beginPath()
                ctx.arc(_cx(+(p.z_start||0)), _cy(+(p.x_start||0)), 6, 0, Math.PI*2)
                ctx.fill()

            } else if (p.type === "lineTo") {
                var ez = +(p.z_end||0), ex = +(p.x_end||0)
                ctx.beginPath()
                ctx.moveTo(_cx(logZ), _cy(logX))
                ctx.lineTo(_cx(ez), _cy(ex))
                ctx.stroke()
                ctx.fillStyle = "#E53935"
                ctx.beginPath(); ctx.arc(_cx(ez), _cy(ex), 5, 0, Math.PI*2); ctx.fill()

            } else if (p.type === "arcTo") {
                var aez = +(p.z_end||0),    aex = +(p.x_end||0)
                var acz = +(p.z_center||0), acx = +(p.x_center||0)
                var ar  = +(p.arc_radius||0), isCW2 = (p.direction === "cw")
                var ccx = _cx(acz), ccy = _cy(acx), cr2 = ar * _scale
                var sa2 = Math.atan2(_cy(logX) - ccy, _cx(logZ) - ccx)
                var ea2 = Math.atan2(_cy(aex)  - ccy, _cx(aez)  - ccx)
                ctx.beginPath()
                ctx.arc(ccx, ccy, cr2, sa2, ea2, !isCW2)
                ctx.stroke()
                ctx.fillStyle = "#E53935"
                ctx.beginPath(); ctx.arc(_cx(aez), _cy(aex), 5, 0, Math.PI*2); ctx.fill()
                ctx.fillStyle = "#888888"
                ctx.beginPath(); ctx.arc(ccx, ccy, 4, 0, Math.PI*2); ctx.fill()
            }

        } else {
            // ── Blend geometry only (amber) ──────────────────────────────────────
            if (!p.blend || p.blend.type === "none") return
            ctx.strokeStyle = "#D97706"; ctx.lineWidth = 2.5
            ctx.lineJoin = "round"; ctx.lineCap = "round"

            var bNextP = (targetIdx + 1 < primitives.length) ? primitives[targetIdx + 1] : null

            if (p.type === "lineTo") {
                var lez = +(p.z_end||0), lex = +(p.x_end||0)

                if (p.blend.type === "chamfer") {
                    var lcw  = +(p.blend.chamfer_width || 0)
                    var lsdz = lez - logZ, lsdx = lex - logX
                    var lslen = Math.sqrt(lsdz*lsdz + lsdx*lsdx)
                    if (lslen > 0.001 && lcw > 0.001) {
                        var lcsZ = lez - lcw * lsdz / lslen
                        var lcsX = lex - lcw * lsdx / lslen
                        var lceZ = lez, lceX = lex
                        if (bNextP && bNextP.type === "lineTo") {
                            var lndz = +(bNextP.z_end||0) - lez
                            var lndx = +(bNextP.x_end||0) - lex
                            var lnlen = Math.sqrt(lndz*lndz + lndx*lndx)
                            if (lnlen > 0.001) { lceZ = lez + lcw*lndz/lnlen; lceX = lex + lcw*lndx/lnlen }
                        } else if (bNextP && bNextP.type === "arcTo") {
                            var lnacz = +(bNextP.z_center||0), lnacx = +(bNextP.x_center||0)
                            var lnrz = lez - lnacz, lnrx = lex - lnacx
                            var lnndz = (bNextP.direction === "cw") ? -lnrx :  lnrx
                            var lnndx = (bNextP.direction === "cw") ?  lnrz : -lnrz
                            var lnlen2 = Math.sqrt(lnndz*lnndz + lnndx*lnndx)
                            if (lnlen2 > 0.001) { lceZ = lez + lcw*lnndz/lnlen2; lceX = lex + lcw*lnndx/lnlen2 }
                        }
                        ctx.beginPath()
                        ctx.moveTo(_cx(lcsZ), _cy(lcsX))
                        ctx.lineTo(_cx(lceZ), _cy(lceX))
                        ctx.stroke()
                        ctx.fillStyle = "#D97706"
                        ctx.beginPath(); ctx.arc(_cx(lcsZ), _cy(lcsX), 5, 0, Math.PI*2); ctx.fill()
                        ctx.beginPath(); ctx.arc(_cx(lceZ), _cy(lceX), 5, 0, Math.PI*2); ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var lfr = +(p.blend.fillet_radius || 0)
                    var lfg = (bNextP && bNextP.type === "arcTo")
                              ? _filletLineArc(logZ, logX, lez, lex, bNextP, lfr)
                              : _filletGeom(logZ, logX, lez, lex, bNextP, lfr)
                    if (lfg) {
                        var lfccx = _cx(lfg.fcz), lfccy = _cy(lfg.fcx), lfcr = lfr * _scale
                        var lfsa  = Math.atan2(_cy(lfg.t1x) - lfccy, _cx(lfg.t1z) - lfccx)
                        var lfea  = Math.atan2(_cy(lfg.t2x) - lfccy, _cx(lfg.t2z) - lfccx)
                        ctx.beginPath()
                        ctx.arc(lfccx, lfccy, lfcr, lfsa, lfea, lfg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = "#D97706"
                        ctx.beginPath(); ctx.arc(_cx(lfg.t1z), _cy(lfg.t1x), 5, 0, Math.PI*2); ctx.fill()
                        ctx.beginPath(); ctx.arc(_cx(lfg.t2z), _cy(lfg.t2x), 5, 0, Math.PI*2); ctx.fill()
                    }
                }

            } else if (p.type === "arcTo") {
                var aaez = +(p.z_end||0),    aaex = +(p.x_end||0)
                var aacz = +(p.z_center||0), aacx = +(p.x_center||0)
                var aar  = +(p.arc_radius||0), aisCW = (p.direction === "cw")

                if (p.blend.type === "chamfer") {
                    var aacw  = +(p.blend.chamfer_width || 0)
                    var aarez = aaez - aacz, aarex = aaex - aacx
                    var aarlen = Math.sqrt(aarez*aarez + aarex*aarex)
                    if (aarlen > 0.001 && aacw > 0.001) {
                        var aatdz = aisCW ? -aarex :  aarex
                        var aatdx = aisCW ?  aarez : -aarez
                        var aacsZ = aaez - aacw * aatdz / aarlen
                        var aacsX = aaex - aacw * aatdx / aarlen
                        var aaceZ = aaez, aaceX = aaex
                        if (bNextP && bNextP.type === "lineTo") {
                            var aandz = +(bNextP.z_end||0) - aaez
                            var aandx = +(bNextP.x_end||0) - aaex
                            var aanlen = Math.sqrt(aandz*aandz + aandx*aandx)
                            if (aanlen > 0.001) { aaceZ = aaez + aacw*aandz/aanlen; aaceX = aaex + aacw*aandx/aanlen }
                        }
                        ctx.beginPath()
                        ctx.moveTo(_cx(aacsZ), _cy(aacsX))
                        ctx.lineTo(_cx(aaceZ), _cy(aaceX))
                        ctx.stroke()
                        ctx.fillStyle = "#D97706"
                        ctx.beginPath(); ctx.arc(_cx(aacsZ), _cy(aacsX), 5, 0, Math.PI*2); ctx.fill()
                        ctx.beginPath(); ctx.arc(_cx(aaceZ), _cy(aaceX), 5, 0, Math.PI*2); ctx.fill()
                    }

                } else if (p.blend.type === "fillet") {
                    var aafr = +(p.blend.fillet_radius || 0)
                    var aafg = _filletArcLine(aacz, aacx, aar, aisCW, aaez, aaex, bNextP, aafr)
                    if (aafg) {
                        var aafccx = _cx(aafg.fcz), aafccy = _cy(aafg.fcx), aafcr = aafr * _scale
                        var aafsa  = Math.atan2(_cy(aafg.t1x) - aafccy, _cx(aafg.t1z) - aafccx)
                        var aafea  = Math.atan2(_cy(aafg.t2x) - aafccy, _cx(aafg.t2z) - aafccx)
                        ctx.beginPath()
                        ctx.arc(aafccx, aafccy, aafcr, aafsa, aafea, aafg.anticlockwise)
                        ctx.stroke()
                        ctx.fillStyle = "#D97706"
                        ctx.beginPath(); ctx.arc(_cx(aafg.t1z), _cy(aafg.t1x), 5, 0, Math.PI*2); ctx.fill()
                        ctx.beginPath(); ctx.arc(_cx(aafg.t2z), _cy(aafg.t2x), 5, 0, Math.PI*2); ctx.fill()
                    }
                }
            }
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