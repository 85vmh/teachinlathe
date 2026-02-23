// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// The canvas origin (Z=0, X=0) is always at the visual centre.
// Scale is computed automatically so the profile + 20 mm margin fits the canvas.
import QtQuick 2.15

Canvas {
    id: root

    property var primitives: []   // array of primitive objects from JSON

    // ── Private state ──────────────────────────────────────────────────────────
    property real _scale:   5.0          // px / mm
    property real _originX: width  / 2  // canvas px that maps to world Z = 0
    property real _originY: height / 2  // canvas px that maps to world X = 0

    // Max positive vertex coords — used to set arrow tip positions
    property real _maxZ: 0
    property real _maxX: 0

    // Origin circle radius — shared by _paintOriginMarker and _paintAxes
    readonly property real _circleR: 8

    // ── World → canvas helpers ─────────────────────────────────────────────────
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + wX * _scale }

    // ── Trigger recompute whenever input or size changes ───────────────────────
    onPrimitivesChanged: { _computeScale(); requestPaint() }
    onWidthChanged:      { _computeScale(); requestPaint() }
    onHeightChanged:     { _computeScale(); requestPaint() }

    // ── Scale + arrow-length computation ──────────────────────────────────────
    function _computeScale() {
        if (!primitives || primitives.length === 0 || width <= 0 || height <= 0) {
            _scale = 5; _maxZ = 0; _maxX = 0
            return
        }

        var zMin = 1e9, zMax = -1e9
        var xMin = 1e9, xMax = -1e9
        var vZMax = 0, vXMax = 0   // vertex-only max positive (for arrows)

        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            var vz, vx

            if (p.type === "startPoint") {
                vz = +(p.z_start || 0);  vx = +(p.x_start || 0)
            } else if (p.type === "lineTo") {
                vz = +(p.z_end || 0);    vx = +(p.x_end || 0)
            } else if (p.type === "arcTo") {
                vz = +(p.z_end || 0);    vx = +(p.x_end || 0)
            } else { continue }

            // Expand vertex bounds (no arc bbox here — used only for arrows)
            if (vz < zMin) zMin = vz;  if (vz > zMax) zMax = vz
            if (vx < xMin) xMin = vx;  if (vx > xMax) xMax = vx
            if (vz > vZMax) vZMax = vz
            if (vx > vXMax) vXMax = vx

            // Also expand with arc conservative bounding box (for scale only)
            if (p.type === "arcTo") {
                var r  = +(p.arc_radius || 0)
                var zc = +(p.z_center   || 0)
                var xc = +(p.x_center   || 0)
                var bzMin = zc - r, bzMax = zc + r
                var bxMin = xc - r, bxMax = xc + r
                if (bzMin < zMin) zMin = bzMin;  if (bzMax > zMax) zMax = bzMax
                if (bxMin < xMin) xMin = bxMin;  if (bxMax > xMax) xMax = bxMax
            }
        }

        _maxZ = vZMax
        _maxX = vXMax

        // Add 20 mm margin on every side for scale computation
        zMin -= 20;  zMax += 20
        xMin -= 20;  xMax += 20

        var scaleZ = (width  / 2) / Math.max(Math.abs(zMin), Math.abs(zMax), 1)
        var scaleX = (height / 2) / Math.max(Math.abs(xMin), Math.abs(xMax), 1)
        _scale = Math.min(scaleZ, scaleX)
    }

    // ── Minor / major tick step selection based on current scale ───────────────
    function _steps() {
        if (_scale >= 8)   return { minor: 1,  major: 10 }
        if (_scale >= 3)   return { minor: 2,  major: 10 }
        if (_scale >= 1)   return { minor: 5,  major: 10 }
        if (_scale >= 0.4) return { minor: 10, major: 50 }
        return                    { minor: 50, major: 100 }
    }

    function _isMajor(val, majorStep) {
        return Math.round(Math.abs(val) * 1000) % Math.round(majorStep * 1000) < 1
    }

    // ── Paint dispatcher ───────────────────────────────────────────────────────
    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        _paintBackground(ctx)
        _paintGrid(ctx)
        _paintTicks(ctx)
        _paintCenterLine(ctx)    // dashed spindle axis line — drawn first
        _paintAxes(ctx)          // arrows over the dashed line
        _paintOriginMarker(ctx)  // circle over line and arrows
        _paintProfile(ctx)
    }

    // ── Background ─────────────────────────────────────────────────────────────
    function _paintBackground(ctx) {
        ctx.fillStyle = "#f5f5f5"
        ctx.fillRect(0, 0, width, height)
    }

    // ── Light grid (major step only) ───────────────────────────────────────────
    function _paintGrid(ctx) {
        var s = _steps()
        ctx.strokeStyle = "#e0e0e0"
        ctx.lineWidth   = 0.5
        ctx.setLineDash([])

        var zWMin = -_originX / _scale
        var zWMax = (width - _originX) / _scale
        var xWMin = -_originY / _scale
        var xWMax = (height - _originY) / _scale

        var z0 = Math.floor(zWMin / s.major) * s.major
        var z1 = Math.ceil(zWMax  / s.major) * s.major
        for (var z = z0; z <= z1; z += s.major) {
            var canX = _cx(z)
            ctx.beginPath(); ctx.moveTo(canX, 0); ctx.lineTo(canX, height); ctx.stroke()
        }

        var x0 = Math.floor(xWMin / s.major) * s.major
        var x1 = Math.ceil(xWMax  / s.major) * s.major
        for (var x = x0; x <= x1; x += s.major) {
            var canY = _cy(x)
            ctx.beginPath(); ctx.moveTo(0, canY); ctx.lineTo(width, canY); ctx.stroke()
        }
    }

    // ── Tick marks + labels on all four edges ──────────────────────────────────
    function _paintTicks(ctx) {
        var s = _steps()
        ctx.strokeStyle = "#666666"
        ctx.fillStyle   = "#333333"
        ctx.lineWidth   = 1
        ctx.setLineDash([])

        // ── Z axis (top + bottom edges) ───────────────────────────────────────
        ctx.textAlign    = "center"
        var zWMin = -_originX / _scale
        var zWMax = (width - _originX) / _scale
        var zt = Math.floor(zWMin / s.minor) * s.minor
        for (var z = zt; z <= zWMax; z += s.minor) {
            var maj  = _isMajor(z, s.major)
            var tLen = maj ? 7 : 3
            var canX = _cx(z)

            ctx.beginPath(); ctx.moveTo(canX, 0);      ctx.lineTo(canX, tLen);          ctx.stroke()
            ctx.beginPath(); ctx.moveTo(canX, height);  ctx.lineTo(canX, height - tLen); ctx.stroke()

            if (maj) {
                var label = Math.round(z).toString()
                ctx.font = "10px sans-serif"
                ctx.textBaseline = "top"
                ctx.fillText(label, canX, tLen + 2)
                ctx.textBaseline = "bottom"
                ctx.fillText(label, canX, height - tLen - 2)
            }
        }

        // ── X axis (left + right edges) ───────────────────────────────────────
        var xWMin = -_originY / _scale
        var xWMax = (height - _originY) / _scale
        var xt = Math.floor(xWMin / s.minor) * s.minor
        for (var x = xt; x <= xWMax; x += s.minor) {
            var majX  = _isMajor(x, s.major)
            var tLenX = majX ? 7 : 3
            var canY  = _cy(x)

            ctx.beginPath(); ctx.moveTo(0,     canY); ctx.lineTo(tLenX,         canY); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(width, canY); ctx.lineTo(width - tLenX, canY); ctx.stroke()

            if (majX) {
                var labelX = Math.round(x).toString()
                ctx.font = "10px sans-serif"
                ctx.textAlign    = "left"
                ctx.textBaseline = "middle"
                ctx.fillText(labelX, tLenX + 2, canY)
                ctx.textAlign = "right"
                ctx.fillText(labelX, width - tLenX - 2, canY)
            }
        }
    }

    // ── Dashed spindle centre line (horizontal, through Z=0, X=0) ─────────────
    // Pattern: -- - -- - --  (long dash, gap, short dash, gap, repeat)
    function _paintCenterLine(ctx) {
        ctx.strokeStyle = "#bbbbbb"
        ctx.lineWidth   = 1
        ctx.setLineDash([10, 4, 3, 4])
        ctx.beginPath()
        ctx.moveTo(0,     _originY)
        ctx.lineTo(width, _originY)
        ctx.stroke()
        ctx.setLineDash([])   // reset for subsequent draws
    }

    // ── Axis arrows (Z+ right, X+ down) starting from circle edge ─────────────
    function _paintAxes(ctx) {
        var aw  = 9           // arrowhead length
        var ah  = aw * 0.4    // arrowhead half-width
        var cr  = _circleR    // start offset = circle radius

        // ── Z+ arrow — green, → right ─────────────────────────────────────────
        var zTipX  = _cx(_maxZ + 10)          // tip of arrow in canvas px
        var zShaft = zTipX - aw               // shaft end (before arrowhead)
        var zStart = _originX + cr + 1        // begin just outside circle

        ctx.strokeStyle = "#2E7D32"
        ctx.fillStyle   = "#2E7D32"
        ctx.lineWidth   = 1.5
        ctx.setLineDash([])

        if (zShaft > zStart) {
            ctx.beginPath()
            ctx.moveTo(zStart, _originY)
            ctx.lineTo(zShaft, _originY)
            ctx.stroke()
        }
        // Arrowhead
        ctx.beginPath()
        ctx.moveTo(zTipX,  _originY)
        ctx.lineTo(zShaft, _originY - ah)
        ctx.lineTo(zShaft, _originY + ah)
        ctx.closePath(); ctx.fill()
        // Label
        ctx.font = "bold 11px sans-serif"
        ctx.textAlign = "left"; ctx.textBaseline = "bottom"
        ctx.fillText("Z+", zTipX + 4, _originY - 2)

        // ── X+ arrow — blue, ↓ down ────────────────────────────────────────────
        var xTipY  = _cy(_maxX + 10)          // tip of arrow in canvas px
        var xShaft = xTipY - aw               // shaft end (before arrowhead)
        var xStart = _originY + cr + 1        // begin just outside circle

        ctx.strokeStyle = "#1565C0"
        ctx.fillStyle   = "#1565C0"

        if (xShaft > xStart) {
            ctx.beginPath()
            ctx.moveTo(_originX, xStart)
            ctx.lineTo(_originX, xShaft)
            ctx.stroke()
        }
        // Arrowhead
        ctx.beginPath()
        ctx.moveTo(_originX,      xTipY)
        ctx.lineTo(_originX - ah, xShaft)
        ctx.lineTo(_originX + ah, xShaft)
        ctx.closePath(); ctx.fill()
        // Label
        ctx.font = "bold 11px sans-serif"
        ctx.textAlign = "left"; ctx.textBaseline = "top"
        ctx.fillText("X+", _originX + 4, xTipY + 2)
    }

    // ── Origin marker: circle split into 4 quadrants, alternating fill ─────────
    function _paintOriginMarker(ctx) {
        var r   = _circleR
        var ocx = _originX
        var ocy = _originY

        ctx.lineWidth   = 1.5
        ctx.fillStyle   = "#222222"
        ctx.strokeStyle = "#222222"
        ctx.setLineDash([])

        // angles: -π/2 = top, 0 = right, π/2 = bottom, π = left
        // Filled: top-right (Q1) and bottom-left (Q3)
        var quads = [
            { start: -Math.PI / 2, end: 0,              fill: true  },   // top-right
            { start: 0,            end: Math.PI / 2,    fill: false },   // bottom-right
            { start: Math.PI / 2,  end: Math.PI,        fill: true  },   // bottom-left
            { start: Math.PI,      end: 3 * Math.PI / 2, fill: false },  // top-left
        ]
        for (var i = 0; i < quads.length; i++) {
            var q = quads[i]
            ctx.beginPath()
            ctx.moveTo(ocx, ocy)
            ctx.arc(ocx, ocy, r, q.start, q.end, false)
            ctx.closePath()
            if (q.fill) ctx.fill()
            else        ctx.stroke()
        }
    }

    // ── Profile line + vertex dots ─────────────────────────────────────────────
    function _paintProfile(ctx) {
        if (!primitives || primitives.length === 0) return

        var curZ = 0, curX = 0

        ctx.strokeStyle = "#1565C0"
        ctx.lineWidth   = 2
        ctx.lineJoin    = "round"
        ctx.lineCap     = "round"
        ctx.setLineDash([])
        ctx.beginPath()

        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]

            if (p.type === "startPoint") {
                curZ = +(p.z_start || 0)
                curX = +(p.x_start || 0)
                ctx.moveTo(_cx(curZ), _cy(curX))

            } else if (p.type === "lineTo") {
                var ez = +(p.z_end || 0), ex = +(p.x_end || 0)
                ctx.lineTo(_cx(ez), _cy(ex))
                curZ = ez; curX = ex

            } else if (p.type === "arcTo") {
                var aez = +(p.z_end    || 0), aex = +(p.x_end    || 0)
                var acz = +(p.z_center || 0), acx = +(p.x_center || 0)
                var ar  = +(p.arc_radius || 0)
                var isCW = (p.direction === "cw")

                var ccx = _cx(acz), ccy = _cy(acx)
                var cr  = ar * _scale

                // Canvas Y is down → CW in world = CW in canvas
                var startAng = Math.atan2(_cy(curX) - ccy, _cx(curZ) - ccx)
                var endAng   = Math.atan2(_cy(aex)  - ccy, _cx(aez)  - ccx)
                ctx.arc(ccx, ccy, cr, startAng, endAng, !isCW)
                curZ = aez; curX = aex
            }
        }
        ctx.stroke()

        // Vertex dots
        ctx.fillStyle = "#E53935"
        for (var j = 0; j < primitives.length; j++) {
            var pt = primitives[j]
            var pz, px
            if      (pt.type === "startPoint") { pz = +(pt.z_start||0); px = +(pt.x_start||0) }
            else if (pt.type === "lineTo")     { pz = +(pt.z_end  ||0); px = +(pt.x_end  ||0) }
            else if (pt.type === "arcTo")      { pz = +(pt.z_end  ||0); px = +(pt.x_end  ||0) }
            else continue

            ctx.beginPath()
            ctx.arc(_cx(pz), _cy(px), 4, 0, Math.PI * 2)
            ctx.fill()
        }
    }
}