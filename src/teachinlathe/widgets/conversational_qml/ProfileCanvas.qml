// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// Scale and origin are computed from fixed viewport margins.
import QtQuick 2.15
import "profile_canvas"

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
    property var  _renderSegs: [] // cached render segments in world coords

    readonly property real _circleR: 8   // origin marker radius
    Geometry { id: geom }

    // ── World → canvas ─────────────────────────────────────────────────────────
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + wX * _scale }

    // ── Recompute + repaint on any relevant change ─────────────────────────────
    onPrimitivesChanged:         { _computeScale(); _rebuildRenderCache(); requestPaint() }
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
        var v = geom.computeViewport(primitives, width, height)
        _scale = v.scale
        _originX = v.originX
        _originY = v.originY
        _maxZ = v.maxZ
        _maxX = v.maxX
    }

    // ── Tick helpers ───────────────────────────────────────────────────────────
    function _steps() {
        return geom.steps(_scale)
    }

    // Returns {len, label} for a tick at world value `val`
    function _tickStyle(val, s) {
        return geom.tickStyle(val, s)
    }

    // ── Paint dispatcher ───────────────────────────────────────────────────────
    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        backgroundActor.paint(ctx)
        gridActor.paint(ctx)
        ticksActor.paint(ctx)
        centerLineActor.paint(ctx)
        axesActor.paint(ctx)
        originActor.paint(ctx)
        pathActor.paint(ctx)
        highlightActor.paint(ctx)
    }

    function _rebuildRenderCache() {
        _renderSegs = geom.buildRenderSegments(primitives)
    }

    function _walkToIndex(targetIdx) {
        return geom.walkToIndex(primitives, targetIdx)
    }

    // ── Actor orchestration ───────────────────────────────────────────────────
    BackgroundActor {
        id: backgroundActor
        width: root.width
        height: root.height
    }

    GridActor {
        id: gridActor
        width: root.width
        height: root.height
        originX: root._originX
        originY: root._originY
        scale: root._scale
        cx: root._cx
        cy: root._cy
        stepsFn: root._steps
    }

    TicksActor {
        id: ticksActor
        width: root.width
        height: root.height
        originX: root._originX
        originY: root._originY
        scale: root._scale
        cx: root._cx
        cy: root._cy
        stepsFn: root._steps
        tickStyleFn: root._tickStyle
    }

    CenterLineActor {
        id: centerLineActor
        width: root.width
        originY: root._originY
    }

    AxesActor {
        id: axesActor
        originX: root._originX
        originY: root._originY
        maxZ: root._maxZ
        maxX: root._maxX
        circleR: root._circleR
        cx: root._cx
        cy: root._cy
    }

    OriginActor {
        id: originActor
        originX: root._originX
        originY: root._originY
        circleR: root._circleR
    }

    PathActor {
        id: pathActor
        renderSegs: root._renderSegs
        scale: root._scale
        cx: root._cx
        cy: root._cy
    }

    HighlightActor {
        id: highlightActor
        primitives: root.primitives
        selectedPrimIndex: root.selectedPrimIndex
        selectedBlendIndex: root.selectedBlendIndex
        scale: root._scale
        cx: root._cx
        cy: root._cy
        geometry: geom
    }

    // ── Hit testing ────────────────────────────────────────────────────────────
    function _distToSegment(px, py, x1, y1, x2, y2) {
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
        var end = _normAngle(endAng)
        var angle = _normAngle(testAngle)
        if (!anticlockwise) {          // CW: angles increase from s to e
            return (start <= end) ? (angle >= start && angle <= end) : (angle >= start || angle <= end)
        } else {                       // CCW: angles decrease from s to e
            return (start >= end) ? (angle >= end && angle <= start) : (angle <= end || angle >= start)
        }
    }

    function _distToArc(px, py, ccx, ccy, cr, sa, ea, anticlockwise) {
        var deltaX = px - ccx
        var deltaY = py - ccy
        var distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
        if (distance < 1) return cr
        var distanceToCircle = Math.abs(distance - cr)
        if (distanceToCircle > 20) return 1e9
        if (_angleInArc(Math.atan2(deltaY, deltaX), sa, ea, anticlockwise)) return distanceToCircle
        // nearest arc endpoint
        var startX = ccx + cr * Math.cos(sa)
        var startY = ccy + cr * Math.sin(sa)
        var endX = ccx + cr * Math.cos(ea)
        var endY = ccy + cr * Math.sin(ea)
        var distStart = Math.sqrt((px - startX) * (px - startX) + (py - startY) * (py - startY))
        var distEnd = Math.sqrt((px - endX) * (px - endX) + (py - endY) * (py - endY))
        return Math.min(distStart, distEnd)
    }

    function _hitTest(px, py) {
        if (!primitives || primitives.length === 0) return -1
        var HIT = 10    // pixel tolerance
        var currentZ = 0
        var currentX = 0
        for (var i = 0; i < primitives.length; i++) {
            var p = primitives[i]
            if (p.type === "startPoint") {
                var startZ = +(p.z_start || 0)
                var startX = +(p.x_start || 0)
                var deltaX = px - _cx(startZ)
                var deltaY = py - _cy(startX)
                if (deltaX * deltaX + deltaY * deltaY <= HIT * HIT) return i
                currentZ = startZ
                currentX = startX
            } else if (p.type === "lineTo") {
                var endZ = +(p.z_end || 0)
                var endX = +(p.x_end || 0)
                if (_distToSegment(px, py, _cx(currentZ), _cy(currentX), _cx(endZ), _cy(endX)) <= HIT) return i
                currentZ = endZ
                currentX = endX
            } else if (p.type === "arcTo") {
                var arcEndZ = +(p.z_end || 0)
                var arcEndX = +(p.x_end || 0)
                var centerZ = +(p.z_center || 0)
                var centerX = +(p.x_center || 0)
                var arcRadius = +(p.arc_radius || 0)
                var isClockwise = (p.direction === "cw")
                var centerCanvasX = _cx(centerZ)
                var centerCanvasY = _cy(centerX)
                var radiusCanvas = arcRadius * _scale
                var startAngle = Math.atan2(_cy(currentX) - centerCanvasY, _cx(currentZ) - centerCanvasX)
                var endAngle = Math.atan2(_cy(arcEndX) - centerCanvasY, _cx(arcEndZ) - centerCanvasX)
                if (_distToArc(px, py, centerCanvasX, centerCanvasY, radiusCanvas, startAngle, endAngle, !isClockwise) <= HIT) return i
                currentZ = arcEndZ
                currentX = arcEndX
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
