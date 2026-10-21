// ProfileCanvas.qml
// Draws a lathe profile from a list of primitives (startPoint / lineTo / arcTo).
// Coordinate convention: Z+ → right, X+ → down (lathe radial, outward = positive).
// Scale and origin are computed from fixed viewport margins.
import QtQuick 2.15
import theme 1.0
import "profile_canvas"
import "profile_canvas/brokenstock.js" as Broken
import common.touchable_input 1.0

Canvas {
    id: root

    property var    primitives:        []    // array of primitive objects from JSON
    property int    selectedPrimIndex:  -1  // index into primitives; -1 = none
    property int    selectedBlendIndex: -1  // index of primitive whose blend is selected; -1 = none
    property string profileType:       "od" // "od" or "id" — controls startPoint blend entry direction
    property var    workpiece:         ({})
    property bool   mirrorAcrossCenterline: true  // also draw the profile and its hatched stock above the centre line
    // false makes the canvas a plain viewer: no pan, zoom or selection
    property bool   interactive: true
    // false keeps pan and zoom but leaves taps from selecting anything
    property bool   selectable: true
    // px along the right edge that fitToScreen leaves free, for boxes laid there
    property real   fitInsetRight: 0
    // px fitToScreen leaves on every side as well, for dimensions drawn
    // outside the part
    property real   fitPadding: 0
    // dimensions drawn by DimensionActor; see it for their form
    property var    dimensions: []
    // the finished profile's line
    property color  profileLineColor: "#333333"
    property real   profileLineWidth: 1
    // with the mirror on, each transition of the profile joined to its mirror
    // by a line across the centre line while the profile is defined; else
    // only where it starts and where it ends
    property bool   showTransitions: true
    // a stretch of Z left out of the drawing - the grid and the ticks skip
    // it and mark the real Z past it; see profile_canvas/axisbreak.js
    property var    axisBreak: null
    onAxisBreakChanged: requestPaint()
    // When 0 or more, fitToScreen scales X to the profile alone: its largest
    // diameter plus this many mm (on the diameter) reaches the top and bottom
    // edges - with 10, a Ø50 profile shows up to Ø60. Z still has to fit, so
    // a long part can make it smaller. Below 0, X fits everything drawn with
    // the usual margin.
    property real   fitDiameterMargin: -1
    // where the tool starts, as {x: diameter, z}, drawn by StartPositionActor; null hides it
    property var    startPosition: null
    // where it ends, likewise, in endPositionColor; null hides it
    property var    endPosition: null
    readonly property color endPositionColor: "#8e24aa"
    // more targets, each with its arrow to a box: [{x: diameter, z, color,
    // arrowToRect}], drawn by MarkersActor; fitted as the positions are
    property var    markers: []
    // the drill or tap in the spindle, {kind, diameter, tip_angle,
    // right_hand, pitch, z} (AxialToolActor), its point at z on the centre
    // line; null draws none
    property var    axialTool: null
    // a dot where each arrow to a box starts as well as where it ends -
    // the markers' and the dimensions' leaders
    property bool   arrowStartDots: false
    // the axes - the dashed Z0 line and the Z+ / X+ arrows; the operations
    // leave them out, the origin alone marking Z0
    property bool   showAxes: true
    onShowAxesChanged: requestPaint()
    // how far in from the edges the ticks reach, px
    readonly property real tickBand: 7
    onArrowStartDotsChanged: requestPaint()
    // whether fitToScreen takes in the axial tool's whole length, or only
    // its point: a drill is long, and longer the bigger it is
    property bool   fitAxialToolLength: true
    // more points fitToScreen takes in, as the positions: [{x: diameter, z}]
    property var    fitExtraPositions: []
    // where the axial tool's pecks end, in mm, each drawn as its point, in
    // axialToolPeckColor
    property var    axialToolPecks: []
    // where the edges of what the pecks cut start: Z Start
    property var    axialToolPecksFrom: null
    property color  axialToolPeckColor: feedColor
    onAxialToolPecksChanged: requestPaint()
    // how far back from a peck's Z its mark reaches the axial tool's edges,
    // in mm - see AxialToolActor.peckBack
    function axialToolPeckBack() { return axialToolActor.peckBack() }
    // what roughing will cut, {profile, offset, feeds, rapids}
    // as profileRoughingPreview returns it; null draws none of it
    property var    roughingPreview: null
    // the roughing overlays' colours, for boxes that label their values to match
    readonly property color feedColor:        "#2e7d32"
    readonly property color rapidColor:       "#777777"   // the backplot's rapids
    readonly property color stockToLeaveColor: "#ef6c00"
    // boxes laid over the canvas that the overlays point arrows to, as
    // {x, y, width, height} in canvas px; null draws no arrow
    property var    startPositionArrowRect: null
    property var    endPositionArrowRect: null
    property var    stockToLeaveArrowRect: null

    // A selected cylindrical stretch, fillet or chamfer shows its value in a
    // tag; with this set, tapping the tag opens the numpad and reports the
    // new value through diameterEdited or blendEdited.
    property bool   tagEditable: false

    signal primitiveSelected(int index)
    signal blendSelected(int index)   // the blend carried by primitive ``index``
    signal selectionCleared()
    signal openNumPadRequested(var field)
    // A new diameter for the cylindrical stretch primitive ``index`` is in;
    // primitivesWithDiameter turns it into updated primitives.
    signal diameterEdited(int index, real diameter)
    // A new value for ``field`` ("fillet_radius" / "chamfer_width") of the
    // blend carried by primitive ``index``.
    signal blendEdited(int index, string field, real value)

    // ── Value tag ──────────────────────────────────────────────────────────────
    // What the tag shows for the current selection, or null:
    //   kind         "diameter" | "fillet" | "chamfer"
    //   index        the selected primitive, or the one carrying the blend
    //   value        the number shown and edited
    //   prefix       the symbol before it
    //   field        the blend field it edits (blends only)
    //   description  the numpad's title
    //   anchorX/Y    where the leader touches the profile, in canvas px - on
    //                the upper half when both halves are drawn
    readonly property var _tag: _currentTag()

    function _currentTag() {
        if (selectedPrimIndex >= 0) {
            var cylinder = geom.cylinderAt(_resolvedPrimitives, selectedPrimIndex)
            if (!cylinder) return null
            var lineY = _cy(cylinder.diameter)
            return {
                kind: "diameter", index: selectedPrimIndex, value: cylinder.diameter,
                prefix: "\u00D8", description: "Diameter",
                anchorX: _cx((cylinder.zSelectedStart + cylinder.zSelectedEnd) / 2),
                anchorY: mirrorAcrossCenterline ? 2 * _originY - lineY : lineY
            }
        }
        if (selectedBlendIndex >= 0 && primitives && selectedBlendIndex < primitives.length) {
            var blend = primitives[selectedBlendIndex].blend
            if (!blend || (blend.type !== "fillet" && blend.type !== "chamfer")) return null
            var mid = _blendMidpoint(selectedBlendIndex)
            if (!mid) return null
            var isFillet = blend.type === "fillet"
            return {
                kind: blend.type, index: selectedBlendIndex,
                value: +(isFillet ? blend.fillet_radius : blend.chamfer_width) || 0,
                prefix: isFillet ? "r" : "w",
                field: isFillet ? "fillet_radius" : "chamfer_width",
                description: isFillet ? "Fillet radius" : "Chamfer width",
                anchorX: mid.x,
                anchorY: mirrorAcrossCenterline ? 2 * _originY - mid.y : mid.y
            }
        }
        return null
    }

    // Canvas position halfway along the drawn blend of primitive ``index``
    // (the chamfer's line, the fillet's arc), on the lower half; or null.
    function _blendMidpoint(index) {
        var segs = _renderSegs
        var prevZ = 0
        var prevX = 0
        for (var i = 0; segs && i < segs.length; i++) {
            var s = segs[i]
            if (s.prim === index && s.blend && s.type !== "move") {
                var startX = _cx(prevZ)
                var startY = _cy(prevX)
                if (s.type !== "arc")
                    return { x: (startX + _cx(s.z)) / 2, y: (startY + _cy(s.x)) / 2 }
                var ccx = _cx(s.zc)
                var ccy = _cy(s.xc)
                var radius = Math.sqrt(Math.pow(startX - ccx, 2) + Math.pow(startY - ccy, 2))
                var sa = Math.atan2(startY - ccy, startX - ccx)
                var sweep = Math.atan2(_cy(s.x) - ccy, _cx(s.z) - ccx) - sa
                // the way ctx.arc goes: anticlockwise means decreasing angle
                if (s.anticlockwise) { while (sweep > 0) sweep -= Math.PI * 2 }
                else                 { while (sweep < 0) sweep += Math.PI * 2 }
                return { x: ccx + radius * Math.cos(sa + sweep / 2),
                         y: ccy + radius * Math.sin(sa + sweep / 2) }
            }
            prevZ = s.z
            prevX = s.x
        }
        return null
    }

    // The leader leaves the anchor at 45 degrees, up and to the right (down
    // and to the right on the lower half, away from the part).
    readonly property real _leaderRun: 56   // px along each axis
    readonly property real _leaderEndX: _tag ? _tag.anchorX + _leaderRun : 0
    readonly property real _leaderEndY: _tag ? _tag.anchorY + (mirrorAcrossCenterline ? -_leaderRun : _leaderRun) : 0

    // e.g. "\u00D8 11.000 mm", "r 1.000 mm"
    function _tagText(tag) { return tag.prefix + " " + Number(tag.value).toFixed(3) + " mm" }

    // ``primitives`` with the cylindrical run containing primitive ``index``
    // moved to ``diameter``, or null; for handlers of diameterEdited.
    function primitivesWithDiameter(index, diameter) {
        return geom.withCylinderDiameter(primitives, index, diameter)
    }

    // ── Private state ──────────────────────────────────────────────────────────
    property real _scale:   5.0
    property real _originX: 0     // canvas px → world Z = 0
    property real _originY: 0     // canvas px → world X = 0
    property var  _renderSegs: [] // cached render segments in world coords
    property var  _resolvedPrimitives: []
    property bool _manualView: false  // when true, primitive/size changes don't reset fit
    // false until fitToScreen has placed the drawing: until then only the
    // background is painted, or the first frame of a screen would show it at
    // the starting scale and origin - the profile in a corner, the arrows to
    // the boxes running across the whole canvas
    property bool _fitted: false
    // a fit asked for and not yet made: the next paint makes it first, so no
    // frame is drawn at a view the data has already moved on from
    property bool _fitPending: false

    // Fit once the changes that came together are all in - and in any case
    // before the next paint.
    function _scheduleFit() {
        _fitPending = true
        Qt.callLater(_runPendingFit)
    }
    function _runPendingFit() { if (_fitPending) fitToScreen() }

    readonly property real _circleR: 8   // origin marker radius
    Geometry { id: geom }

    // ── World → canvas ─────────────────────────────────────────────────────────
    // wX is diameter; divide by 2 so 1 mm radius == 1 mm Z on screen.
    function _cx(wZ) { return _originX + wZ * _scale }
    function _cy(wX) { return _originY + (wX / 2) * _scale }

    // ── Recompute + repaint on any relevant change ─────────────────────────────
    onPrimitivesChanged: {
        _rebuildRenderCache()
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onProfileTypeChanged: { _rebuildRenderCache(); requestPaint() }
    onWorkpieceChanged: {
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onWidthChanged:  { if (!_manualView) fitToScreen() }
    onFitInsetRightChanged: { if (!_manualView) _scheduleFit() }
    onFitPaddingChanged:    { if (!_manualView) _scheduleFit() }
    onDimensionsChanged:     requestPaint()
    onHeightChanged: { if (!_manualView) fitToScreen() }
    onStartPositionChanged: {
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onMarkersChanged: {
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onAxialToolChanged: {
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onEndPositionChanged: {
        if (!_manualView) _scheduleFit()
        else              requestPaint()
    }
    onRoughingPreviewChanged:        requestPaint()
    onStartPositionArrowRectChanged: requestPaint()
    onEndPositionArrowRectChanged:   requestPaint()
    onStockToLeaveArrowRectChanged:  requestPaint()
    onSelectedPrimIndexChanged:  requestPaint()
    onSelectedBlendIndexChanged: requestPaint()
    // always fitted anew, zoomed or not: the drawing is a different shape
    onMirrorAcrossCenterlineChanged: _scheduleFit()

    // ── Reset view to fit (public, call when entering the screen) ─────────────
    function resetView() { _manualView = false; _fitted = false; _scheduleFit() }

    // ── Zoom in / out (public, zoom around canvas centre) ─────────────────────
    // how much one zoomIn / zoomOut scales the view
    property real zoomStep: 1.3
    function zoomIn()  { _zoomAround(width / 2, height / 2, zoomStep) }
    function zoomOut() { _zoomAround(width / 2, height / 2, 1.0 / zoomStep) }

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
        _fitPending = false
        if (width <= 0 || height <= 0) return
        var hasProfile = primitives && primitives.length > 0
        var b = hasProfile ? geom.computeBounds(_resolvedPrimitives) : null
        // nothing to fit: drawn as it stands
        if (hasProfile && !b) { _showUnfitted(); return }
        // with no profile, the workpiece and the tool's positions, if any
        if (!b) {
            var hasStock = workpiece && Number(workpiece.stock_length) > 0 && Number(workpiece.external_diameter) > 0
            if (!hasStock && !startPosition && !endPosition) { _showUnfitted(); return }
            b = { fZMin: 0, fZMax: 0, fXMin: 0, fXMax: 0 }
        }
        var profileDiameter = Math.max(Math.abs(b.fXMin), Math.abs(b.fXMax))
        var stockLength = workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
        var stockDiameter = workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
        // the stock broken off after the profile (StockActor): as far as the
        // break reaches past the profile's end, not the stock's whole length:
        // set back three of its bends, reaching out one more
        if (stockLength > 0 && hasProfile && workpiece && workpiece.break_after_profile) {
            b.fZMin = Math.max(-stockLength, b.fZMin - 4 * Broken.reach(1.0) * stockDiameter / 2)
            b.fZMax = Math.max(b.fZMax, 0)
        } else if (stockLength > 0 && workpiece && workpiece.break_after_z !== undefined
                   && workpiece.break_after_z !== null) {
            // Facing's, broken off after Z End: set back five bends - or
            // the workpiece's own setback - reaching out one more
            var bendMm = Broken.reach(1.0) * stockDiameter / 2
            var setback = workpiece.break_after_setback !== undefined && workpiece.break_after_setback !== null
                          ? Math.max(0, Number(workpiece.break_after_setback)) : 5 * bendMm
            b.fZMin = Math.min(b.fZMin, Math.max(-stockLength,
                               Number(workpiece.break_after_z) - setback - bendMm))
            b.fZMax = Math.max(b.fZMax, 0)
        } else if (stockLength > 0) {
            b.fZMin = Math.min(b.fZMin, -stockLength)
            b.fZMax = Math.max(b.fZMax, 0)
        }
        if (stockDiameter > 0) {
            b.fXMin = Math.min(b.fXMin, 0)
            b.fXMax = Math.max(b.fXMax, stockDiameter)
        }
        var positions = [startPosition, endPosition].concat(markers || []).concat(fitExtraPositions || [])
        // the axial tool, from its point to its far end
        if (axialTool && Number(axialTool.diameter) > 0) {
            var toolZ = Number(axialTool.z) || 0
            positions.push({ x: Number(axialTool.diameter), z: toolZ })
            if (fitAxialToolLength)
                positions.push({ x: Number(axialTool.diameter), z: toolZ + axialToolActor.length() })
        }
        for (var p = 0; p < positions.length; p++) {
            if (!positions[p]) continue
            b.fZMax = Math.max(b.fZMax, +positions[p].z || 0)
            b.fZMin = Math.min(b.fZMin, +positions[p].z || 0)
            b.fXMax = Math.max(b.fXMax, Math.abs(+positions[p].x || 0))
        }
        var faceZ = workpiece && workpiece.face_z !== undefined ? Number(workpiece.face_z) : 0
        if (faceZ > 0) b.fZMax = Math.max(b.fZMax, faceZ)
        var MARGIN = 10
        var marginX = MARGIN   // around X, in radius units

        var displayXMin = root.mirrorAcrossCenterline ? -Math.max(Math.abs(b.fXMin), Math.abs(b.fXMax)) / 2 : 0
        var displayXMax = root.mirrorAcrossCenterline ?  Math.max(Math.abs(b.fXMin), Math.abs(b.fXMax)) / 2 : b.fXMax / 2
        if (fitDiameterMargin >= 0) {
            var edge = (profileDiameter + fitDiameterMargin) / 2
            // the extra points - a tool at the start position - in as well,
            // with a little room past them
            for (var e = 0; e < (fitExtraPositions || []).length; e++)
                edge = Math.max(edge, Math.abs(+fitExtraPositions[e].x || 0) / 2 + 2)
            displayXMin = root.mirrorAcrossCenterline ? -edge : 0
            displayXMax = edge
            marginX = 0
        }

        // Z: [zMin-M, zMax+M]
        var spanZ = Math.max(b.fZMax - b.fZMin + 2 * MARGIN, 1)
        // X is diameter in profile primitives; canvas uses radius units for display.
        var spanX = Math.max(displayXMax - displayXMin + 2 * marginX, 1)

        var fitWidth = Math.max(1, width - fitInsetRight - 2 * fitPadding)
        var fitHeight = Math.max(1, height - 2 * fitPadding)
        var scale = Math.min(fitWidth / spanZ, fitHeight / spanX)

        // Centre each axis in whatever canvas space it gets
        var leftOffset = fitPadding + (fitWidth - spanZ * scale) / 2
        var topOffset  = fitPadding + (fitHeight - spanX * scale) / 2

        _scale   = scale
        _originX = leftOffset + (MARGIN - b.fZMin) * scale
        _originY = topOffset  + (marginX - displayXMin) * scale
        _manualView = false
        _fitted = true
        requestPaint()
    }

    function _showUnfitted() {
        if (_fitted) return
        _fitted = true
        requestPaint()
    }

    // ── Paint dispatcher ───────────────────────────────────────────────────────
    onPaint: {
        // a fit still waiting: made now, before anything is drawn
        if (_fitPending) fitToScreen()
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        backgroundActor.paint(ctx)
        // not placed yet, and not zoomed or panned by hand: the background alone
        if (!_fitted && !_manualView) return
        gridActor.paint(ctx)
        ticksActor.paint(ctx)
        stockActor.paint(ctx)
        centerLineActor.paint(ctx)
        if (showAxes) axesActor.paintZeroLine(ctx)
        originActor.paint(ctx)
        pathActor.paint(ctx)
        stockToLeaveActor.paint(ctx)
        toolpathActor.paint(ctx)
        dimensionActor.paint(ctx)
        highlightActor.paint(ctx)
        diameterLeaderActor.paint(ctx)
        axialToolActor.paint(ctx)
        startPositionActor.paint(ctx)
        endPositionActor.paint(ctx)
        markersActor.paint(ctx)
        // the axes' arrows over everything, the arrows to the boxes too;
        // with the stock drawn, X+ past its skin by its usual length
        axesActor.xAxisLength = _stockDrawn() ? _cy(Number(workpiece.external_diameter)) - _cy(0) + axesActor.axisLength
                                              : axesActor.axisLength
        if (showAxes) axesActor.paintArrows(ctx)
    }

    // Whether StockActor draws any stock: not with the mirror off where the
    // stock is broken off after the profile or Z End.
    function _stockDrawn() {
        if (!workpiece || !(Number(workpiece.stock_length) > 0) || !(Number(workpiece.external_diameter) > 0))
            return false
        var brokenAfter = (workpiece.break_after_profile && _renderSegs && _renderSegs.length > 0)
                          || (workpiece.break_after_z !== undefined && workpiece.break_after_z !== null)
        return mirrorAcrossCenterline || !brokenAfter
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
        axisBreak: root.axisBreak
    }

    TicksActor {
        id: ticksActor
        width: root.width
        height: root.height
        originX: root._originX
        originY: root._originY
        scale: root._scale
        geometry: geom
        axisBreak: root.axisBreak
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
        strokeColor: root.profileLineColor
        lineWidth: root.profileLineWidth
        renderSegs: root._renderSegs
        scale: root._scale
        cx: root._cx
        cy: root._cy
        mirrorAcrossCenterline: root.mirrorAcrossCenterline
        showTransitions: root.showTransitions
    }

    DiameterLeaderActor {
        id: diameterLeaderActor
        active: root._tag !== null
        anchorX: root._tag ? root._tag.anchorX : 0
        anchorY: root._tag ? root._tag.anchorY : 0
        endX: root._leaderEndX
        endY: root._leaderEndY
        color: Theme.accentStrong
    }

    StartPositionActor {
        id: startPositionActor
        position: root.startPosition
        arrowToRect: root.startPositionArrowRect
        cx: root._cx
        cy: root._cy
    }

    // the same target, for where the tool ends
    StartPositionActor {
        id: endPositionActor
        position: root.endPosition
        arrowToRect: root.endPositionArrowRect
        color: root.endPositionColor
        cx: root._cx
        cy: root._cy
    }

    MarkersActor {
        id: markersActor
        markers: root.markers
        startDots: root.arrowStartDots
        cx: root._cx
        cy: root._cy
    }

    AxialToolActor {
        id: axialToolActor
        tool: root.axialTool
        peckZs: root.axialToolPecks
        peckFrom: root.axialToolPecksFrom
        peckColor: root.axialToolPeckColor
        scale: root._scale
        cx: root._cx
        cy: root._cy
    }

    StockToLeaveActor {
        id: stockToLeaveActor
        offset: root.roughingPreview ? root.roughingPreview.offset : []
        profile: root.roughingPreview ? root.roughingPreview.profile : []
        color: root.stockToLeaveColor
        lineWidth: pathActor.lineWidth
        cx: root._cx
        cy: root._cy
        mirrorAcrossCenterline: root.mirrorAcrossCenterline
        arrowToRect: root.stockToLeaveArrowRect
    }

    DimensionActor {
        id: dimensionActor
        dimensions: root.dimensions
        startDots: root.arrowStartDots
        cx: root._cx
        cy: root._cy
    }

    ToolpathActor {
        id: toolpathActor
        feeds: root.roughingPreview ? root.roughingPreview.feeds : []
        rapids: root.roughingPreview ? root.roughingPreview.rapids : []
        feedColor: root.feedColor
        rapidColor: root.rapidColor
        cx: root._cx
        cy: root._cy
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
        enabled: root.interactive

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
                if (_wasDrag || !root.selectable) return
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

    // Declared after the PinchArea so it sits above it: a tap here must not
    // also reach the canvas MouseArea and change the selection.
    Rectangle {
        id: valueTag
        visible: root._tag !== null
        width: tagText.implicitWidth + 2 * Theme.spacing
        height: Theme.inputHeight
        // at the end of the leader, kept inside the canvas
        x: Math.max(0, Math.min(root.width - width, root._leaderEndX))
        y: Math.max(0, Math.min(root.height - height,
                                root.mirrorAcrossCenterline ? root._leaderEndY - height : root._leaderEndY))
        radius: Theme.radius
        color: Theme.surface
        border.color: tagField.numpadActive ? Theme.focusBorder : Theme.accentStrong
        border.width: tagField.numpadActive ? 2 : 1

        Text {
            id: tagText
            anchors.centerIn: parent
            text: root._tag ? root._tagText(root._tag) : ""
            color: Theme.foregroundStrong
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontTitle
        }

        // Never shown: the numpad dialog edits a NumpadField, so the tag
        // hands it this one, seeded with the current value on each tap.
        NumpadField {
            id: tagField
            visible: false
            settingName: "profile.tag"
            validatorObject: DoubleValidator { bottom: 0.001; notation: DoubleValidator.StandardNotation }
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            property var editing: null   // the tag being edited, fixed at the tap
            onValueCommitted: function(value) {
                var tag = editing
                if (!tag) return
                if (tag.kind === "diameter")
                    root.diameterEdited(tag.index, Number(value))
                else
                    root.blendEdited(tag.index, tag.field, Number(value))
            }
        }

        MouseArea {
            anchors.fill: parent
            enabled: root.tagEditable
            onClicked: {
                tagField.editing = root._tag
                tagField.description = root._tag.description
                tagField.value = root._tag.value
                tagField.numpadActive = true
                root.openNumPadRequested(tagField)
            }
        }
    }
}
