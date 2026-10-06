// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// Scale and origin are computed from fixed viewport margins.
import QtQuick 2.15
import "profile_canvas"

Canvas {
    id: root

    property var    primitives:        []    // array of primitive objects from JSON
    property int    selectedPrimIndex:  -1  // index into primitives; -1 = none
    property int    selectedBlendIndex: -1  // index of primitive whose blend is selected; -1 = none
    property string profileType:       "od" // "od" or "id" — controls startPoint blend entry direction
    property var    workpiece:         ({})
    property bool   mirrorAcrossCenterline: true  // also draw the profile and its hatched stock above the centre line

    signal primitiveSelected(int index)
    signal blendSelected(int index)   // the blend carried by primitive ``index``
    signal selectionCleared()

    // ── Private state ──────────────────────────────────────────────────────────
    property real _scale:   5.0
    property real _originX: 0     // canvas px → world Z = 0
    property real _originY: 0     // canvas px → world X = 0
    property var  _renderSegs: [] // cached render segments in world coords
    property var  _resolvedPrimitives: []
    property bool _manualView: false  // when true, primitive/size changes don't reset fit

    readonly property real _circleR: 8   // origin marker radius
    Geometry { id: geom }

    // ── World → canvas ─────────────────────────────────────────────────────────
    // wX is diameter; divide by 2 so 1 mm radius == 1 mm Z on screen.
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + (wX / 2) * _scale }

    // ── Recompute + repaint on any relevant change ─────────────────────────────
    onPrimitivesChanged: {
        _rebuildRenderCache()
        if (!_manualView) Qt.callLater(fitToScreen)
        else              requestPaint()
    }
    onProfileTypeChanged: { _rebuildRenderCache(); requestPaint() }
    onWorkpieceChanged: {
        if (!_manualView) Qt.callLater(fitToScreen)
        else              requestPaint()
    }
    onWidthChanged:  { if (!_manualView) fitToScreen() }
    onHeightChanged: { if (!_manualView) fitToScreen() }
    onSelectedPrimIndexChanged:  requestPaint()
    onSelectedBlendIndexChanged: requestPaint()
    onMirrorAcrossCenterlineChanged: {
        if (!_manualView) Qt.callLater(fitToScreen)
        else              requestPaint()
    }

    // ── Reset view to fit (public, call when entering the screen) ─────────────
    function resetView() { _manualView = false; Qt.callLater(fitToScreen) }

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
    // Z axis: symmetric 10 mm margins left and right of the profile.
    // X axis: equal margin above the center line (X=0) and below fXMax.
    //         The non-constraining axis is centred in the remaining canvas space.
    function fitToScreen() {
        if (!primitives || primitives.length === 0 || width <= 0 || height <= 0) return
        var b = geom.computeBounds(_resolvedPrimitives)
        if (!b) return
        var stockLength = workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
        var stockDiameter = workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
        if (stockLength > 0) {
            b.fZMin = Math.min(b.fZMin, -stockLength)
            b.fZMax = Math.max(b.fZMax, 0)
        }
        if (stockDiameter > 0) {
            b.fXMin = Math.min(b.fXMin, 0)
            b.fXMax = Math.max(b.fXMax, stockDiameter)
        }
        var MARGIN = 10

        var displayXMin = root.mirrorAcrossCenterline ? -Math.max(Math.abs(b.fXMin), Math.abs(b.fXMax)) / 2 : 0
        var displayXMax = root.mirrorAcrossCenterline ?  Math.max(Math.abs(b.fXMin), Math.abs(b.fXMax)) / 2 : b.fXMax / 2

        // Z: [zMin-M, zMax+M]
        var spanZ = Math.max(b.fZMax - b.fZMin + 2 * MARGIN, 1)
        // X is diameter in profile primitives; canvas uses radius units for display.
        var spanX = Math.max(displayXMax - displayXMin + 2 * MARGIN, 1)

        var scale = Math.min(width / spanZ, height / spanX)

        // Centre each axis in whatever canvas space it gets
        var leftOffset = (width  - spanZ * scale) / 2
        var topOffset  = (height - spanX * scale) / 2

        _scale   = scale
        _originX = leftOffset + (MARGIN - b.fZMin) * scale
        _originY = topOffset  + (MARGIN - displayXMin) * scale
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
        stockActor.paint(ctx)
        centerLineActor.paint(ctx)
        axesActor.paint(ctx)
        originActor.paint(ctx)
        pathActor.paint(ctx)
        highlightActor.paint(ctx)
    }

    function _rebuildRenderCache() {
        _resolvedPrimitives = geom.resolvePrimitives(primitives)
        _renderSegs = geom.buildRenderSegments(_resolvedPrimitives, root.profileType)
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
        height:  root.height
        circleR: root._circleR
    }

    OriginActor {
        id: originActor
        originX: root._originX
        originY: root._originY
        circleR: root._circleR
    }

    StockActor {
        id: stockActor
        workpiece: root.workpiece
        renderSegs: root._renderSegs
        profileType: root.profileType
        cx: root._cx
        cy: root._cy
        mirrorAcrossCenterline: root.mirrorAcrossCenterline
    }

    PathActor {
        id: pathActor
        renderSegs: root._renderSegs
        scale: root._scale
        cx: root._cx
        cy: root._cy
        mirrorAcrossCenterline: root.mirrorAcrossCenterline
    }

    HighlightActor {
        id: highlightActor
        primitives: root._resolvedPrimitives
        selectedPrimIndex: root.selectedPrimIndex
        selectedBlendIndex: root.selectedBlendIndex
        profileType: root.profileType
        scale: root._scale
        cx: root._cx
        cy: root._cy
        geometry: geom
        mirrorAcrossCenterline: root.mirrorAcrossCenterline
    }

    // ── Hit testing ────────────────────────────────────────────────────────────
    function _hitTest(px, py) {
        var hitPrimitives = root._resolvedPrimitives
        if (!hitPrimitives || hitPrimitives.length === 0) return -1
        var HIT = 10    // pixel tolerance
        var currentZ = 0
        var currentX = 0
        for (var i = 0; i < hitPrimitives.length; i++) {
            var p = hitPrimitives[i]
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
                var radiusCanvas = Math.sqrt(Math.pow(_cx(currentZ) - centerCanvasX, 2) + Math.pow(_cy(currentX) - centerCanvasY, 2))
                var startAngle = Math.atan2(_cy(currentX) - centerCanvasY, _cx(currentZ) - centerCanvasX)
                var endAngle = Math.atan2(_cy(arcEndX) - centerCanvasY, _cx(arcEndZ) - centerCanvasX)
                if (geom.distToArc(px, py, centerCanvasX, centerCanvasY, radiusCanvas, startAngle, endAngle, !isClockwise) <= HIT) return i
                currentZ = arcEndZ
                currentX = arcEndX
            }
        }
        return -1
    }

    // ── Hit testing the drawn blends ──────────────────────────────────────────
    // Canvas distance from (px, py) to render segment ``s``, which starts at
    // world (prevZ, prevX).
    function _distToRenderSeg(px, py, s, prevZ, prevX) {
        var startX = _cx(prevZ)
        var startY = _cy(prevX)
        if (s.type !== "arc")
            return geom.distToSegment(px, py, startX, startY, _cx(s.z), _cy(s.x))
        var ccx = _cx(s.zc)
        var ccy = _cy(s.xc)
        var radius = Math.sqrt(Math.pow(startX - ccx, 2) + Math.pow(startY - ccy, 2))
        return geom.distToArc(px, py, ccx, ccy, radius,
                              Math.atan2(startY - ccy, startX - ccx),
                              Math.atan2(_cy(s.x) - ccy, _cx(s.z) - ccx),
                              s.anticlockwise)
    }

    // The drawn line nearest (px, py), within the hit tolerance: a render
    // segment, whose ``prim`` and ``blend`` say what it is, or the start
    // point's marker as {prim, blend: false}. null when nothing is that close.
    function _strokeHitTest(px, py) {
        var segs = root._renderSegs
        if (!segs) return null
        var HIT = 10    // pixel tolerance, as _hitTest
        var best = null
        var bestDistance = HIT
        var prevZ = 0
        var prevX = 0
        for (var i = 0; i < segs.length; i++) {
            var s = segs[i]
            if (s.type !== "move") {
                var distance = _distToRenderSeg(px, py, s, prevZ, prevX)
                if (distance <= bestDistance) {
                    best = s
                    bestDistance = distance
                }
            }
            prevZ = s.z
            prevX = s.x
        }
        // The start point is a marker, not a segment: it wins when it is the
        // nearer of the two, as it did in _hitTest.
        var prims = root._resolvedPrimitives
        for (var k = 0; prims && k < prims.length; k++) {
            if (prims[k].type !== "startPoint") continue
            var dx = px - _cx(+(prims[k].z_start || 0))
            var dy = py - _cy(+(prims[k].x_start || 0))
            if (Math.sqrt(dx * dx + dy * dy) <= bestDistance)
                best = { prim: k, blend: false }
            break
        }
        return best
    }

    // ── Hit testing the solid between the profile and its mirror ──────────────
    // A click inside the outline the two halves close off picks the stretch
    // of the profile it falls in - the stretch the transition lines bound -
    // as if the profile line itself had been clicked. Returns that stretch's
    // render segment, whose ``prim`` and ``blend`` say what it is, or null
    // outside the outline. Only meaningful with both halves drawn.
    function _solidHitTest(px, py) {
        var segs = root._renderSegs
        if (!segs || segs.length < 2) return null

        var lower = geom.flattenRenderSegments(segs, _cx, _cy)
        var outline = lower.slice()
        for (var m = lower.length - 1; m >= 0; m--)
            outline.push({ x: lower[m].x, y: 2 * _originY - lower[m].y })
        if (!geom.pointInPolygon(px, py, outline)) return null

        // Fold the click onto the lower half, then take the nearest segment
        // among those spanning its Z; vertical ones span none, so they only
        // win when nothing else does.
        var foldedY = _originY + Math.abs(py - _originY)
        var best = null
        var bestDistance = Infinity
        var bestSpans = false
        var prevZ = 0
        var prevX = 0
        for (var i = 0; i < segs.length; i++) {
            var s = segs[i]
            if (s.type !== "move") {
                var startX = _cx(prevZ)
                var spans = px >= Math.min(startX, _cx(s.z)) && px <= Math.max(startX, _cx(s.z))
                var distance = _distToRenderSeg(px, foldedY, s, prevZ, prevX)
                if ((spans && !bestSpans) || (spans === bestSpans && distance < bestDistance)) {
                    best = s
                    bestDistance = distance
                    bestSpans = spans
                }
            }
            prevZ = s.z
            prevX = s.x
        }
        return best
    }

    // ── Touch: two-finger pinch zooms, and pans with the fingers ──────────────
    // One finger still reaches the MouseArea inside (pan, tap, double-tap);
    // a second finger hands the gesture over here, which cancels that drag.
    PinchArea {
        anchors.fill: parent

        property real _scaleAtStart:  1
        property real _worldZAtStart: 0
        property real _worldXAtStart: 0

        onPinchStarted: function(pinch) {
            _scaleAtStart  = root._scale
            _worldZAtStart = (pinch.startCenter.x - root._originX) / root._scale
            _worldXAtStart = (pinch.startCenter.y - root._originY) / root._scale
            root._manualView = true
        }

        onPinchUpdated: function(pinch) {
            var newScale = Math.max(0.05, Math.min(200.0, _scaleAtStart * pinch.scale))

            // the world point that started between the fingers stays between them
            root._originX = pinch.center.x - _worldZAtStart * newScale
            root._originY = pinch.center.y - _worldXAtStart * newScale
            root._scale   = newScale
            root.requestPaint()
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
                var mirrored = root.mirrorAcrossCenterline
                var mirrorY = 2 * root._originY - mouse.y   // the click reflected across the centre line

                // 1. a drawn line, on either half: a blend's line selects the
                //    blend, any other the primitive it was drawn for
                var hit = root._strokeHitTest(mouse.x, mouse.y)
                if (!hit && mirrored)
                    hit = root._strokeHitTest(mouse.x, mirrorY)
                // 2. the primitives as entered, before any blend trims them
                if (!hit) {
                    var idx = root._hitTest(mouse.x, mouse.y)
                    if (idx < 0 && mirrored)
                        idx = root._hitTest(mouse.x, mirrorY)
                    if (idx >= 0)
                        hit = { prim: idx, blend: false }
                }
                // 3. anywhere inside the solid the two halves enclose
                if (!hit && mirrored)
                    hit = root._solidHitTest(mouse.x, mouse.y)

                if (!hit) root.selectionCleared()
                else if (hit.blend) root.blendSelected(hit.prim)
                else root.primitiveSelected(hit.prim)
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
}
