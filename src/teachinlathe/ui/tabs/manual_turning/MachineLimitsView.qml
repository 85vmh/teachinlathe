// MachineLimitsView.qml — the back of the area under the DRO: the machine
// drawn, in machine coordinates (G53, X a radius), all of it one canvas.
//
// The grid is the machine's travel (the INI's axis limits), fitted to the
// width; pinch or the wheel zooms - out past the edges if need be - a drag
// pans, a double tap fits it again. Round the grid's edges the ticks the
// profile canvases have: Z along the top and bottom, X down the sides. On the
// grid: a target for each of Home, M6 (the tool change position), G28 and G30
// in its colour - its name at its top right, or at its bottom right where
// another is at the same point - the chuck and tailstock limits as lines past
// it with an arrow from each up to the bottom of its card, an origin sign -
// its 12 to 3 o'clock quadrant alone filled - where the machine is now, as it
// jogs - the Machine Coordinates DRO's position (G53), where a tool without
// offsets has its tip - and the current loaded tool, to
// scale, its tip that far from it its tool offset says. The work offset in use
// (G54...) has the profile canvases' origin sign at its zero, its name beside
// it: it stays put when the tool changes, the tool moves. All as AXIS draws
// them. Between that sign and the tool's tip, its tool offsets: the rectangle
// they make, solid from the sign's edge - an arrow at both ends, its length beside
// it - and dashed from the tip. What the limits keep the tool from - up to
// the chuck's once it is set, past the tailstock's while it is on - is greyed
// out: the grid there and its Z ticks. The ticks are drawn over the limits'
// lines.
//
// Laid over the canvas: the chuck's and the tailstock's cards at the top, the
// zoom buttons between them as the profile canvases' (CanvasViewButtons), and
// in a row in the bottom right corner M6's, G28's and G30's, each with its
// TeachIn (TeachInLatheDroViewModel). A tap on one of those shows its
// position's X and Z in a bubble over its target; a tap on the canvas hides it.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common
import common.touchable_input
import tabs.conversational
import theme
import tabs.conversational.profile_canvas
import "../conversational/profile_canvas/arrow.js" as Arrow

Rectangle {
    id: root

    required property var viewModel
    signal openNumPadRequested(Item field)

    color: Theme.surfaceSunken
    border.color: Theme.outline
    border.width: Theme.hairline
    radius: Theme.radius
    clip: true

    readonly property var map: viewModel.machineLimitsMap

    // each position's colour: its card, its target and its name on the grid
    readonly property color toolChangeColor: "#e65100"
    readonly property color g28Color: "#6a1b9a"
    readonly property color g30Color: "#00838f"
    readonly property color chuckColor: Theme.foregroundSubtle
    readonly property color tailstockColor: Theme.accentStrong
    readonly property color homeColor: Theme.accentStrong
    // the tool offsets drawn between the machine position and the tool's tip
    readonly property color toolOffsetColor: "#455a64"
    // the tool, in the backplot's insert colours
    readonly property color toolBodyColor: "#e5a93b"
    readonly property color toolEdgeColor: "#674c1b"
    // as the profile canvases' (GridActor, TicksActor)
    readonly property color gridColor: "#e0e0e0"
    readonly property color travelFill: Theme.surface
    readonly property color zTickColor: Theme.success
    readonly property color xTickColor: Theme.accentStrong
    // what is out of the limits' reach: its Z ticks, and laid over the grid
    readonly property color disabledTickColor: "#e0e0e0"
    readonly property color disabledGridVeil: Qt.rgba(0.93, 0.93, 0.93, 0.75)
    readonly property string tickFont: "10px sans-serif"
    // px at least between two labelled ticks
    readonly property int labelSpacing: 60

    // round the grid when it is fitted: in from the sides, and clear of the
    // cards over the canvas
    readonly property int fitMargin: 40
    // how far the limits' lines run past the grid, under it and over it
    readonly property int lineUnder: 14
    readonly property int lineOver: 44
    // px between the top cards and the top of the limits' lines, fitted
    readonly property int arrowRoom: 36
    readonly property real targetRadius: 7
    // the work offset's origin sign
    readonly property real workOriginRadius: 8
    // the machine position's sign
    readonly property real machineMarkRadius: 8
    // px between a target's cross and the tip of its bubble's tail
    readonly property int bubbleGap: 2

    function positionColor(name) {
        return name === "M6" ? toolChangeColor : name === "G28" ? g28Color
             : name === "G30" ? g30Color : Theme.foreground
    }

    // The view: px per mm, and the canvas point of machine Z0 X0. Fitted to
    // the width until the operator moves it.
    property real viewScale: 1
    property real originX: 0
    property real originY: 0
    property bool userMoved: false

    // the position whose X and Z the bubble shows: "M6", "G28", "G30" or none
    property string bubbleName: ""
    readonly property var bubblePosition: {
        var list = map && map.positions ? map.positions : []
        for (var i = 0; i < list.length; i++)
            if (list[i].name === bubbleName)
                return list[i]
        return null
    }
    function toggleBubble(name) { bubbleName = (bubbleName === name) ? "" : name }

    function px(z) { return originX + z * viewScale }
    function py(x) { return originY + x * viewScale }

    function fitToWidth() {
        var t = map ? map.travel : null
        if (!t || width <= 0 || height <= 0)
            return
        var spanZ = Math.max(t.zMax - t.zMin, 1)
        viewScale = (width - 2 * fitMargin) / spanZ
        originX = fitMargin - t.zMin * viewScale
        // between the cards at the top - room left for the limits' arrows up
        // to them - and those at the bottom; right under the top ones where
        // it is taller than that
        var top = topCards.y + topCards.height + arrowRoom + lineOver
        var bottom = bottomCards.y - lineUnder
        var spanX = (t.xMax - t.xMin) * viewScale
        originY = Math.max(top, (top + bottom - spanX) / 2) - t.xMin * viewScale
        userMoved = false
        canvas.requestPaint()
    }

    // zoomed by ``factor`` about the canvas point (cx, cy)
    function zoomAt(factor, cx, cy) {
        var next = Math.max(0.05, Math.min(viewScale * factor, 200))
        factor = next / viewScale
        originX = cx - (cx - originX) * factor
        originY = cy - (cy - originY) * factor
        viewScale = next
        userMoved = true
        canvas.requestPaint()
    }

    // what CanvasViewButtons calls, as on a ProfileCanvas: about the middle
    readonly property real zoomStep: 1.3
    function zoomIn() { zoomAt(zoomStep, width / 2, height / 2) }
    function zoomOut() { zoomAt(1 / zoomStep, width / 2, height / 2) }
    function fitToScreen() { fitToWidth() }

    onWidthChanged: if (!userMoved) Qt.callLater(fitToWidth)
    onHeightChanged: if (!userMoved) Qt.callLater(fitToWidth)
    onMapChanged: canvas.requestPaint()
    Component.onCompleted: Qt.callLater(fitToWidth)

    Connections {
        target: root.viewModel
        // the machine position's sign and the tool follow the machine
        function onDroChanged() { canvas.requestPaint() }
        function onToolDrawingChanged() { canvas.requestPaint() }
        function onWorkOffsetChanged() { canvas.requestPaint() }
    }

    Canvas {
        id: canvas
        anchors.fill: parent

        OriginActor {
            id: workOrigin
            circleR: root.workOriginRadius
        }
        OriginActor {
            id: machineMark
            circleR: root.machineMarkRadius
            quads: [
                { start: -Math.PI / 2, end: 0,               fill: true  },
                { start: 0,            end: Math.PI / 2,     fill: false },
                { start: Math.PI / 2,  end: Math.PI,         fill: false },
                { start: Math.PI,      end: 3 * Math.PI / 2, fill: false }
            ]
        }

        // the step of the ticks and the grid at this zoom: the labelled
        // ticks a round number of mm (1, 2 or 5 times a power of ten) at
        // least labelSpacing px apart, the grid and the small ticks a fifth
        // of that
        function steps(scale) {
            var wanted = root.labelSpacing / Math.max(scale, 1e-6)
            var power = Math.pow(10, Math.floor(Math.log(wanted) / Math.LN10))
            var major = 10 * power
            var candidates = [1, 2, 5, 10]
            for (var i = 0; i < candidates.length; i++)
                if (candidates[i] * power >= wanted) { major = candidates[i] * power; break }
            return { minor: major / 5, major: major }
        }
        function isMultiple(v, step) {
            return Math.round(Math.abs(v) * 1000) % Math.round(step * 1000) < 1
        }
        function tickLength(v, s) {
            return isMultiple(v, s.major) ? 7 : 3
        }

        function grid(ctx, t, s) {
            var left = root.px(t.zMin), right = root.px(t.zMax)
            var top = root.py(t.xMin), bottom = root.py(t.xMax)
            ctx.fillStyle = root.travelFill
            ctx.fillRect(left, top, right - left, bottom - top)
            ctx.strokeStyle = root.gridColor
            ctx.lineWidth = 0.5
            ctx.beginPath()
            for (var z = Math.ceil(t.zMin / s.minor) * s.minor; z <= t.zMax + 1e-9; z += s.minor) {
                ctx.moveTo(root.px(z), top)
                ctx.lineTo(root.px(z), bottom)
            }
            for (var x = Math.ceil(t.xMin / s.minor) * s.minor; x <= t.xMax + 1e-9; x += s.minor) {
                ctx.moveTo(left, root.py(x))
                ctx.lineTo(right, root.py(x))
            }
            ctx.stroke()
            ctx.strokeStyle = Theme.outlineStrong
            ctx.lineWidth = 1
            ctx.strokeRect(left, top, right - left, bottom - top)
        }

        // the ticks round the grid's edges, pointing out, their labels
        // outside: Z along the top and bottom, X - a radius - down the sides
        // whether ``z`` is out of the limits' reach
        function outOfReach(z, m) {
            return (m.chuckSet && z < m.chuck - 1e-9)
                    || (m.tailstockOn && m.tailstock !== null && m.tailstock !== undefined
                        && z > m.tailstock + 1e-9)
        }

        // the grid up to the chuck's limit and past the tailstock's, veiled
        function veilOutOfReach(ctx, t, m) {
            var top = root.py(t.xMin), bottom = root.py(t.xMax)
            ctx.fillStyle = root.disabledGridVeil
            if (m.chuckSet && m.chuck > t.zMin)
                ctx.fillRect(root.px(t.zMin), top, root.px(Math.min(m.chuck, t.zMax)) - root.px(t.zMin), bottom - top)
            if (m.tailstockOn && m.tailstock !== null && m.tailstock !== undefined && m.tailstock < t.zMax) {
                var from = root.px(Math.max(m.tailstock, t.zMin))
                ctx.fillRect(from, top, root.px(t.zMax) - from, bottom - top)
            }
        }

        function rulers(ctx, t, s, m) {
            var left = root.px(t.zMin), right = root.px(t.zMax)
            var top = root.py(t.xMin), bottom = root.py(t.xMax)
            ctx.lineWidth = 1
            ctx.font = root.tickFont
            ctx.textAlign = "center"
            for (var z = Math.ceil(t.zMin / s.minor - 1e-9) * s.minor; z <= t.zMax + 1e-9; z += s.minor) {
                var cx = root.px(z), len = tickLength(z, s)
                ctx.strokeStyle = outOfReach(z, m) ? root.disabledTickColor : root.zTickColor
                ctx.fillStyle = ctx.strokeStyle
                ctx.beginPath()
                ctx.moveTo(cx, top); ctx.lineTo(cx, top - len)
                ctx.moveTo(cx, bottom); ctx.lineTo(cx, bottom + len)
                ctx.stroke()
                if (isMultiple(z, s.major)) {
                    ctx.textBaseline = "bottom"
                    ctx.fillText(Math.round(z).toString(), cx, top - len - 2)
                    ctx.textBaseline = "top"
                    ctx.fillText(Math.round(z).toString(), cx, bottom + len + 2)
                }
            }
            ctx.strokeStyle = root.xTickColor
            ctx.fillStyle = root.xTickColor
            ctx.textBaseline = "middle"
            for (var x = Math.ceil(t.xMin / s.minor - 1e-9) * s.minor; x <= t.xMax + 1e-9; x += s.minor) {
                var cy = root.py(x), lenX = tickLength(x, s)
                ctx.beginPath()
                ctx.moveTo(left, cy); ctx.lineTo(left - lenX, cy)
                ctx.moveTo(right, cy); ctx.lineTo(right + lenX, cy)
                ctx.stroke()
                if (isMultiple(x, s.major)) {
                    ctx.textAlign = "right"
                    ctx.fillText(Math.round(x).toString(), left - lenX - 2, cy)
                    ctx.textAlign = "left"
                    ctx.fillText(Math.round(x).toString(), right + lenX + 2, cy)
                }
            }
            ctx.textBaseline = "alphabetic"
        }

        // a limit: a line past the grid at ``z``, an arrow from its top up
        // to the bottom of its card (``card``, laid over the canvas)
        function limitLine(ctx, t, z, card, color, solid) {
            var x = root.px(z)
            var top = root.py(t.xMin) - root.lineOver, bottom = root.py(t.xMax) + root.lineUnder
            ctx.strokeStyle = color
            ctx.lineWidth = solid ? 2 : 1
            ctx.setLineDash(solid ? [] : [6, 4])
            ctx.beginPath()
            ctx.moveTo(x, bottom)
            ctx.lineTo(x, top)
            ctx.stroke()
            ctx.setLineDash([])
            var origin = card.mapToItem(root, 0, 0)
            Arrow.paintUpToBox(ctx, x, top, { x: origin.x, y: origin.y, width: card.width, height: card.height },
                               color, 0)
        }

        // the tool's ``outline`` (currentToolOutline: [x, z] mm from its tip)
        // with its tip at ``tip`` {x, z}
        function paintTool(ctx, outline, tip) {
            if (!outline || !tip)
                return
            function trace(points, close) {
                for (var i = 0; i < points.length; i++) {
                    var cx = root.px(tip.z + points[i][1]), cy = root.py(tip.x + points[i][0])
                    if (i === 0) ctx.moveTo(cx, cy)
                    else ctx.lineTo(cx, cy)
                }
                if (close)
                    ctx.closePath()
            }
            ctx.lineWidth = 1
            ctx.strokeStyle = root.toolEdgeColor
            ctx.fillStyle = root.toolBodyColor
            // the body, its hole left open: the grid shows through
            ctx.beginPath()
            trace(outline.loop, true)
            if (outline.rings.length > 0)
                trace(outline.rings[0], true)
            ctx.fillRule = Qt.OddEvenFill
            ctx.fill()
            ctx.fillRule = Qt.WindingFill
            ctx.stroke()
            for (var r = 1; r < outline.rings.length; r++) {
                ctx.beginPath()
                trace(outline.rings[r], true)
                ctx.stroke()
            }
            for (var l = 0; l < outline.lines.length; l++) {
                ctx.beginPath()
                trace(outline.lines[l], false)
                ctx.stroke()
            }
        }

        // the tool offsets: from the machine position's sign to the
        // tool's ``tip`` along each axis, solid with an arrow at both ends and
        // the offset beside it, outside the rectangle (its dashed sides are
        // paintToolOffsetGuides')
        function paintToolOffsets(ctx, tip) {
            if (!tip)
                return
            var mX = root.viewModel.machineXValue, mZ = root.viewModel.machineZValue
            var offX = mX - tip.x, offZ = mZ - tip.z
            var cx = root.px(mZ), cy = root.py(mX)
            var tx = root.px(tip.z), ty = root.py(tip.x)
            var color = root.toolOffsetColor

            // from the machine position sign's edge
            var r = root.machineMarkRadius
            if (Math.abs(tx - cx) > r)
                dimension(ctx, cx + (tx > cx ? r : -r), cy, tx, cy, color)
            if (Math.abs(ty - cy) > r)
                dimension(ctx, cx, cy + (ty > cy ? r : -r), cx, ty, color)

            ctx.font = "bold " + Theme.fontSmall + "px sans-serif"
            ctx.fillStyle = color
            // Z: under the line when the rectangle is above it, else over it
            ctx.textAlign = "center"
            ctx.textBaseline = ty <= cy ? "top" : "bottom"
            if (Math.abs(tx - cx) > 1)
                ctx.fillText("Z " + offZ.toFixed(3), (cx + tx) / 2, cy + (ty <= cy ? 4 : -4))
            // X: on the side of its line away from the rectangle
            ctx.textBaseline = "middle"
            ctx.textAlign = tx <= cx ? "left" : "right"
            if (Math.abs(ty - cy) > 1)
                ctx.fillText("X " + offX.toFixed(3), cx + (tx <= cx ? 6 : -6), (cy + ty) / 2)
            ctx.textBaseline = "alphabetic"
        }

        // the tool offsets' rectangle, its dashed sides: from the tool's
        // ``tip`` back to the solid ones
        function paintToolOffsetGuides(ctx, tip) {
            if (!tip)
                return
            var cx = root.px(root.viewModel.machineZValue), cy = root.py(root.viewModel.machineXValue)
            var tx = root.px(tip.z), ty = root.py(tip.x)
            ctx.save()
            ctx.strokeStyle = root.toolOffsetColor
            ctx.lineWidth = 1
            ctx.setLineDash([5, 4])
            ctx.beginPath()
            ctx.moveTo(tx, ty); ctx.lineTo(tx, cy)
            ctx.moveTo(tx, ty); ctx.lineTo(cx, ty)
            ctx.stroke()
            ctx.restore()
        }

        // a solid line from (x1, y1) to (x2, y2), an arrowhead at both ends -
        // a plain line where it is too short for them
        function dimension(ctx, x1, y1, x2, y2, color) {
            var length = Math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1))
            if (length < 1)
                return
            if (length > 2 * (Arrow.headLength + 2)) {
                var mx = (x1 + x2) / 2, my = (y1 + y2) / 2
                Arrow.paint(ctx, mx, my, x1, y1, color, 0)
                Arrow.paint(ctx, mx, my, x2, y2, color, 0)
                return
            }
            ctx.save()
            ctx.setLineDash([])
            ctx.strokeStyle = color
            ctx.lineWidth = Arrow.lineWidth
            ctx.beginPath()
            ctx.moveTo(x1, y1); ctx.lineTo(x2, y2)
            ctx.stroke()
            ctx.restore()
        }

        // a position: a target as the profile canvases' start position, unfilled
        // (StartPositionActor), its name beside it - ``corner`` 0 its top
        // right, 1 its bottom right, 2 its top left, 3 its bottom left
        function target(ctx, x, y, color, name, corner) {
            var r = root.targetRadius
            ctx.strokeStyle = color
            ctx.lineWidth = 1.5
            ctx.beginPath()
            ctx.arc(x, y, r, 0, 2 * Math.PI)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(x - r * 1.6, y); ctx.lineTo(x + r * 1.6, y)
            ctx.moveTo(x, y - r * 1.6); ctx.lineTo(x, y + r * 1.6)
            ctx.stroke()
            ctx.font = "bold " + Theme.fontSmall + "px sans-serif"
            ctx.fillStyle = color
            var right = corner === 0 || corner === 1, below = corner === 1 || corner === 3
            ctx.textAlign = right ? "left" : "right"
            ctx.textBaseline = below ? "top" : "bottom"
            ctx.fillText(name, x + (right ? r : -r), y + (below ? r : -r))
            ctx.textBaseline = "alphabetic"
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var m = root.map
            if (!m || !m.travel)
                return
            var t = m.travel, s = steps(root.viewScale)

            grid(ctx, t, s)
            veilOutOfReach(ctx, t, m)

            // the limits, an arrow from each to its card
            limitLine(ctx, t, m.chuck, chuckCard, root.chuckColor, m.chuckSet)
            if (m.tailstock !== null && m.tailstock !== undefined)
                limitLine(ctx, t, m.tailstock, tailstockCard, root.tailstockColor, m.tailstockOn)

            // the ticks over the limits' lines
            rulers(ctx, t, s, m)

            // the current loaded tool, its tip where its tool offset puts it;
            // all that follows is drawn over it
            var hasTool = !!root.viewModel.currentToolOutline
            paintTool(ctx, root.viewModel.currentToolOutline, root.viewModel.toolTipPosition)

            // its tool offsets
            if (hasTool) {
                paintToolOffsets(ctx, root.viewModel.toolTipPosition)
                paintToolOffsetGuides(ctx, root.viewModel.toolTipPosition)
            }

            // Home - where homing leaves the axes - M6, G28, G30: a target
            // each; where one is at another's point, its name goes round to
            // the next corner
            var placed = []
            var positions = m.home ? [{ name: "Home", x: m.home.x, z: m.home.z }].concat(m.positions)
                                   : m.positions
            for (var i = 0; i < positions.length; i++) {
                var p = positions[i], corner = 0
                for (var j = 0; j < placed.length; j++)
                    if (Math.abs(placed[j].x - p.x) < 1e-6 && Math.abs(placed[j].z - p.z) < 1e-6)
                        corner++
                placed.push(p)
                target(ctx, root.px(p.z), root.py(p.x), p.name === "Home" ? root.homeColor : root.positionColor(p.name), p.name, corner % 4)
            }

            // the work offset in use: its zero, the origin sign
            var wo = root.viewModel.workOffsetOrigin
            if (wo) {
                workOrigin.originX = root.px(wo.z)
                workOrigin.originY = root.py(wo.x)
                workOrigin.paint(ctx)
                ctx.font = "bold " + Theme.fontSmall + "px sans-serif"
                ctx.fillStyle = workOrigin.strokeColor
                ctx.textAlign = "left"
                ctx.textBaseline = "bottom"
                ctx.fillText(wo.name, workOrigin.originX + workOrigin.circleR + 2,
                             workOrigin.originY - workOrigin.circleR)
                ctx.textBaseline = "alphabetic"
            }

            // where the machine is now: an origin sign, only its quadrant
            // from 12 to 3 o'clock filled
            machineMark.originX = root.px(root.viewModel.machineZValue)
            machineMark.originY = root.py(root.viewModel.machineXValue)
            machineMark.paint(ctx)
        }
    }

    // ── panning and zooming: under the cards, over the canvas ─────────────
    PinchArea {
        anchors.fill: parent
        property real lastScale: 1
        onPinchStarted: lastScale = 1
        onPinchUpdated: function(pinch) {
            root.zoomAt(pinch.scale / lastScale, pinch.center.x, pinch.center.y)
            lastScale = pinch.scale
            root.originX += pinch.center.x - pinch.previousCenter.x
            root.originY += pinch.center.y - pinch.previousCenter.y
        }

        MouseArea {
            anchors.fill: parent
            property real lastX: 0
            property real lastY: 0
            onPressed: function(mouse) {
                lastX = mouse.x; lastY = mouse.y
                root.bubbleName = ""
            }
            onPositionChanged: function(mouse) {
                root.originX += mouse.x - lastX
                root.originY += mouse.y - lastY
                lastX = mouse.x; lastY = mouse.y
                root.userMoved = true
                canvas.requestPaint()
            }
            onDoubleClicked: root.fitToWidth()
            onWheel: function(wheel) {
                root.zoomAt(wheel.angleDelta.y > 0 ? 1.15 : 1 / 1.15, wheel.x, wheel.y)
            }
        }
    }

    // ── the cards over the canvas ─────────────────────────────────────────
    Item {
        id: topCards
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.spacingLarge
        height: tailstockCard.height

        // Chuck Limit: its Z, machine coordinates - the line is drawn there
        Rectangle {
            id: chuckCard
            anchors.left: parent.left
            width: tailstockCard.width
            height: tailstockCard.height
            radius: Theme.radius
            color: Theme.surfaceSunken
            border.color: root.chuckColor
            // keeps taps on the card from panning the canvas
            MouseArea { anchors.fill: parent }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: tailstockCard.contentMargin
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    Layout.preferredHeight: tailstockCard.buttonHeight
                    text: "Chuck Limit"
                    font.pixelSize: Theme.fontBody
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: tailstockCard.sectionSpacing
                    Layout.bottomMargin: tailstockCard.sectionSpacing
                    height: Theme.hairline
                    color: Theme.outline
                }
                NumpadField {
                    Layout.fillWidth: true
                    value: root.viewModel.chuckValue
                    settingName: "smart_numpad.chuck-limit"
                    description: "Chuck limit, Z in machine coordinates"
                    hAlign: Text.AlignRight
                    formatter: tailstockCard.formatLimitValue
                    parser: function(s) { return String(s) }
                    onOpenRequested: function(field) { root.openNumPadRequested(field) }
                    onValueCommitted: function(value) {
                        root.viewModel.commitLimit("chuck", tailstockCard.formatLimitValue(value))
                    }
                }
            }
        }

        // Tailstock Limit: as the front's
        TeachableLimit {
            id: tailstockCard
            anchors.right: parent.right
            title: "Tailstock Limit"
            value: root.viewModel.tailstockValue
            settingName: "smart_numpad.tailstock-limit"
            description: "Tailstock limit"
            status: root.viewModel.tailstockStatus
            toggleText: root.viewModel.tailstockToggleText
            toggleEnabled: root.viewModel.tailstockToggleEnabled
            onTeachClicked: root.viewModel.teachLimit("tailstock")
            onToggleClicked: root.viewModel.toggleLimit("tailstock")
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onCommitted: function(value) { root.viewModel.commitLimit("tailstock", value) }
            // keeps taps on the card from panning the canvas
            MouseArea { anchors.fill: parent; z: -1 }
        }
    }

    // ── the bubble: a position's X and Z, over its target ─────────────────
    Item {
        id: bubble
        readonly property var position: root.bubblePosition
        readonly property color accent: root.positionColor(root.bubbleName)
        // the tail: its width where it leaves the box, and how far down its
        // tip is
        readonly property real tailWidth: 16
        readonly property real tailHeight: 14
        visible: position !== null
        width: bubbleBox.width
        height: bubbleBox.height + tailHeight
        x: position ? root.px(position.z) - width / 2 : 0
        y: position ? root.py(position.x) - root.targetRadius * 1.6 - root.bubbleGap - height : 0

        Rectangle {
            id: bubbleBox
            width: bubbleText.implicitWidth + 2 * Theme.spacing
            height: bubbleText.implicitHeight + 2 * Theme.spacingSmall
            radius: Theme.radius
            color: Theme.surface
            border.color: bubble.accent
            border.width: Arrow.lineWidth

            Text {
                id: bubbleText
                anchors.centerIn: parent
                text: bubble.position
                      ? "X: " + Number(bubble.position.x).toFixed(3) + "\nZ: " + Number(bubble.position.z).toFixed(3)
                      : ""
                color: bubble.accent
                font.family: "Noto Sans Mono"
                font.pixelSize: Theme.fontTitle
                font.bold: true
            }
        }
        // the tail, from the box's bottom edge - its border open there - down
        // to the tip
        Canvas {
            x: (parent.width - bubble.tailWidth) / 2 - Arrow.lineWidth
            y: bubbleBox.height - Arrow.lineWidth
            width: bubble.tailWidth + 2 * Arrow.lineWidth
            height: bubble.tailHeight + Arrow.lineWidth
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var w = Arrow.lineWidth, left = w, right = w + bubble.tailWidth, mid = width / 2
                ctx.fillStyle = Theme.surface
                ctx.beginPath()
                ctx.moveTo(left, 0); ctx.lineTo(mid, height - w); ctx.lineTo(right, 0)
                ctx.closePath()
                ctx.fill()
                ctx.strokeStyle = bubble.accent
                ctx.lineWidth = w
                ctx.beginPath()
                ctx.moveTo(left, w / 2); ctx.lineTo(mid, height - w); ctx.lineTo(right, w / 2)
                ctx.stroke()
            }
            Connections {
                target: bubble
                function onAccentChanged() { parent.requestPaint() }
            }
        }
    }

    // ── M6, G28, G30: in a row in the bottom right corner ─────────────────
    Row {
        id: bottomCards
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: Theme.spacingLarge
        spacing: Theme.spacingLarge

        PositionCard {
            name: "M6"
            onTeach: root.viewModel.teachToolChange()
        }
        PositionCard {
            name: "G28"
            // G28.1
            onTeach: root.viewModel.teachG28()
        }
        PositionCard {
            name: "G30"
            // G30.1
            onTeach: root.viewModel.teachG30()
        }
    }

    // ── zoom in, out, fit: in the middle of the top ───────────────────────
    CanvasViewButtons {
        canvas: root
        showMirror: false
        anchors.left: undefined
        anchors.horizontalCenter: parent.horizontalCenter
    }

    // the cards' names as wide as the widest, so the cards are as wide
    TextMetrics {
        id: positionNameMetrics
        font.pixelSize: Theme.fontBody
        text: "G30 Position"
    }

    // A position's card: its name and its TeachIn, the card in its colour; a
    // tap on it shows its X and Z in the bubble
    component PositionCard: CanvasBox {
        id: card
        property string name
        signal teach()

        accent: root.positionColor(name)
        onClicked: root.toggleBubble(name)

        RowLayout {
            spacing: 20
            Label {
                Layout.preferredWidth: Math.ceil(positionNameMetrics.advanceWidth)
                text: card.name + " Position"
                color: card.accent
                font.pixelSize: Theme.fontBody
            }
            TeachInButton { onClicked: card.teach() }
        }
    }
}
