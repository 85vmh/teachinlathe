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
    property bool _manualView: false  // when true, primitive/size changes don't reset fit

    readonly property real _circleR: 8   // origin marker radius
    Geometry { id: geom }

    // ── World → canvas ─────────────────────────────────────────────────────────
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + wX * _scale }

    // ── Recompute + repaint on any relevant change ─────────────────────────────
    onPrimitivesChanged: {
        _rebuildRenderCache()
        if (!_manualView) _computeScale()
        else              _computeArrows()
        requestPaint()
    }
    onWidthChanged:  { if (!_manualView) { _computeScale(); requestPaint() } }
    onHeightChanged: { if (!_manualView) { _computeScale(); requestPaint() } }
    onSelectedPrimIndexChanged:  requestPaint()
    onSelectedBlendIndexChanged: requestPaint()

    // ── Viewport / scale computation ───────────────────────────────────────────
    function _computeScale() {
        var v = geom.computeViewport(primitives, width, height)
        _scale   = v.scale
        _originX = v.originX
        _originY = v.originY
        _maxZ    = v.maxZ
        _maxX    = v.maxX
    }

    // Updates only the arrow extents when in manual view and primitives change.
    function _computeArrows() {
        var b = geom.computeBounds(primitives)
        if (b) { _maxZ = b.vZMax; _maxX = b.vXMax }
    }

    // ── Zoom in / out (public, zoom around canvas centre) ─────────────────────
    function zoomIn()  { _zoomAround(width / 2, height / 2, 1.3) }
    function zoomOut() { _zoomAround(width / 2, height / 2, 1.0 / 1.3) }

    function _zoomAround(cx, cy, factor) {
        var worldZ = (cx - _originX) / _scale
        var worldX = (cy - _originY) / _scale
        var newScale = Math.max(0.05, Math.min(200.0, _scale * factor))
        _originX = cx - worldZ * newScale
        _originY = cy - worldX * newScale
        _scale   = newScale
        _manualView = true
        requestPaint()
    }

    // ── Fit to screen (public) ─────────────────────────────────────────────────
    // Fits all primitives into the canvas with exactly 10 mm margin on every side.
    function fitToScreen() {
        if (!primitives || primitives.length === 0 || width <= 0 || height <= 0) return
        var b = geom.computeBounds(primitives)
        if (!b) return
        var MARGIN = 10
        var spanZ = Math.max(b.fZMax - b.fZMin + 2 * MARGIN, 1)
        var spanX = Math.max(b.fXMax - b.fXMin + 2 * MARGIN, 1)
        _scale   = Math.min(width / spanZ, height / spanX)
        _originX = -(b.fZMin - MARGIN) * _scale
        _originY = -(b.fXMin - MARGIN) * _scale
        _maxZ    = b.vZMax
        _maxX    = b.vXMax
        _manualView = false
        requestPaint()
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
        geometry: geom
    }

    TicksActor {
        id: ticksActor
        width: root.width
        height: root.height
        originX: root._originX
        originY: root._originY
        scale: root._scale
        geometry: geom
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
                if (geom.distToSegment(px, py, _cx(currentZ), _cy(currentX), _cx(endZ), _cy(endX)) <= HIT) return i
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
                if (geom.distToArc(px, py, centerCanvasX, centerCanvasY, radiusCanvas, startAngle, endAngle, !isClockwise) <= HIT) return i
                currentZ = arcEndZ
                currentX = arcEndX
            }
        }
        return -1
    }

    // ── Mouse: pan + zoom + click + double-click fit ──────────────────────────
    MouseArea {
        anchors.fill: parent

        property bool  _wasDrag:    false
        property real  _dragStartX: 0
        property real  _dragStartY: 0
        property real  _originXAtDragStart: 0
        property real  _originYAtDragStart: 0

        readonly property real _DEAD_ZONE: 4   // px

        onPressed: function(mouse) {
            _wasDrag  = false
            _dragStartX = mouse.x
            _dragStartY = mouse.y
            _originXAtDragStart = root._originX
            _originYAtDragStart = root._originY
        }

        onPositionChanged: function(mouse) {
            var dx = mouse.x - _dragStartX
            var dy = mouse.y - _dragStartY
            if (!_wasDrag && (Math.abs(dx) > _DEAD_ZONE || Math.abs(dy) > _DEAD_ZONE)) {
                _wasDrag = true
                root._manualView = true
            }
            if (_wasDrag) {
                root._originX = _originXAtDragStart + dx
                root._originY = _originYAtDragStart + dy
                root.requestPaint()
            }
        }

        onClicked: function(mouse) {
            if (_wasDrag) return
            var idx = root._hitTest(mouse.x, mouse.y)
            if (idx >= 0) root.primitiveSelected(idx)
        }

        onDoubleClicked: function(mouse) {
            root.fitToScreen()
        }

        onWheel: function(wheel) {
            var ZOOM_FACTOR = 1.15
            var factor = (wheel.angleDelta.y > 0) ? ZOOM_FACTOR : (1.0 / ZOOM_FACTOR)

            // world coord under cursor — compute before changing scale
            var worldZ = (wheel.x - root._originX) / root._scale
            var worldX = (wheel.y - root._originY) / root._scale

            var newScale = Math.max(0.05, Math.min(200.0, root._scale * factor))

            // keep the world point under the cursor fixed
            root._originX = wheel.x - worldZ * newScale
            root._originY = wheel.y - worldX * newScale
            root._scale   = newScale

            root._manualView = true
            root.requestPaint()
        }
    }
}