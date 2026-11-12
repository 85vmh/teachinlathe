// TouchOffCanvas.qml — the touch-off dialog's drawing: how the current
// loaded tool is put against the stock for the value typed in. No grid and
// no ticks: the centre line, green and dashed, the origin sign at Z0, and a
// stock as the Program Header draws it - its far end broken off, half as
// long as it is across - its face outlined. Neither the stock nor the tool
// is to scale; the tool is turned as its orientation turns it.
//
// OD - turning, OD threading (an ER insert), a parting blade (orientation
// 6): a bar with a diameter a little smaller turned in front of it.
//   X: the turned diameter dimensioned in front of the stock as G33
//      Threading dimensions Major Ø, its extension lines running on from the
//      turned diameter; the tool outside the lower one, its tip on it.
//   Z: the tool in front of the face, its tip a little under the turned
//      diameter, on a short line parallel to the face, and a two-headed
//      arrow between the face and that line. A threading insert touches the
//      line with its straight side toward the stock, not its tip; a blade
//      with its left corner, the arrow running to the point chosen on the
//      canvas - its left corner (Z-, the default), middle or right corner -
//      the blade staying put.
// ID - boring, ID threading (an IR insert), a grooving blade held for a bore
// (orientation 8): a tube. A blade chooses its Z0 point as OD.
//   X: extension lines running on from the bore, the bore dimensioned with
//      its arrows outside them pointing in at each other; the tool inside
//      the bore, its tip on the lower (X+) line.
//   Z: as OD, its tip on the tube's wall a little over the bore, the arrow
//      under the tip.
// Trepanning - a blade along Z (orientation 5, 7): a plain bar, the blade's
// middle on two thirds of its diameter.
//   X: its corner chosen on the canvas - X- (the default) or X+ -
//      dimensioned as OD's turned diameter, the blade's cutting end on its
//      extension line.
//   Z: as OD, its cutting end on the line, the arrow at its middle.
// Axial - drill, reamer, tap: a plain bar.
//   X: the tool off the centre line, as far as its point is in front of the
//      face; its axis run on from the point toward the face, and an arrow
//      between it and the centre line.
//   Z: on the centre line, as OD.
// In X the arrow is diameterArrowOffset px in front of the stock, the tool's
// tip diameterTipOffset px. Other tools show the centre line alone.
import QtQuick
import QtQuick.Controls
import theme
import tabs.conversational
import tabs.conversational.profile_canvas
import tabs.tool_library.shapes
import "../conversational/profile_canvas/brokenstock.js" as Broken

Rectangle {
    id: root

    // "x" or "z": the axis touched off
    property string axis: "x"
    // the current loaded tool, the Tool Library's view of it (a
    // TurningToolView, ...; ManualToolsViewModel) - its type read from it,
    // and CanvasTool drawn by its card, so they cannot disagree as it changes
    property var    toolView: null
    readonly property string toolType: toolView && toolView.toolType ? toolView.toolType : ""
    // a blade's point the arrow measures to, chosen on the canvas: "-1" its
    // left corner, "0" its middle, "1" its right corner - a parting or
    // grooving blade's in Z (its left corner, toward Z-, the default), a
    // trepanning blade's corner in X (its X- one the default); resetPlace()
    // view state: the choice in the open dialog, until committed
    property string bladePlace: "-1"

    // ── The tool ─────────────────────────────────────────────────────────
    readonly property bool hasView: !!toolView
    readonly property bool isTurning: toolType === "turning" && hasView
    readonly property bool isBoring: toolType === "boring" && hasView
    readonly property bool isThreading: toolType === "threading" && hasView
    readonly property bool isOdThreading: isThreading && toolView.hand === "ER"
    readonly property bool isIdThreading: isThreading && toolView.hand === "IR"
    readonly property bool isBlade: toolType === "blade" && hasView
    // a grooving blade held for a bore: at orientation 8, its cutting end
    // toward -X (ToolKind.GROOVING_BLADE)
    readonly property bool isIdBlade: isBlade && toolView.orientation === 8
    // a trepanning blade: at 5 or 7, along Z (ToolKind.TREPANNING_BLADE)
    readonly property bool isTrepanning: isBlade && (toolView.orientation === 5 || toolView.orientation === 7)
    // a parting or grooving blade: its Z0 point chosen in Z
    readonly property bool choosesZPoint: isBlade && !isTrepanning
    readonly property bool isDrill: toolType === "drilling" && hasView
    readonly property bool isReamer: toolType === "reaming" && hasView
    readonly property bool isTap: toolType === "tapping" && hasView
    readonly property bool asOd: isTurning || isOdThreading || (choosesZPoint && !isIdBlade)
    readonly property bool asId: isBoring || isIdThreading || isIdBlade
    readonly property bool isAxial: isDrill || isReamer || isTap
    // on a plain bar: an axial tool, a trepanning blade
    readonly property bool asBar: isAxial || isTrepanning
    readonly property bool showsTool: asOd || asId || asBar
    readonly property bool inZ: axis === "z"
    // a blade's point is chosen on the canvas: a parting or grooving
    // blade's in Z, a trepanning blade's in X
    readonly property bool needsPlace: choosesZPoint ? inZ : isTrepanning && !inZ

    // ── The stock, in mm ─────────────────────────────────────────────────
    readonly property real stockDiameter: 40
    readonly property real stockLength: stockDiameter / 2
    // OD: the diameter turned in front of it, and how far back from the face
    readonly property real turnedDiameter: 0.8 * stockDiameter
    readonly property real turnedLength: stockLength / 2
    // ID: the tube's bore
    readonly property real boreDiameter: 0.7 * stockDiameter
    // a trepanning blade: the diameter its middle is on
    readonly property real trepanningDiameter: 2 / 3 * stockDiameter
    // Z: the diameter the tool's tip is on - a little under the turned
    // diameter, on the tube's wall a little over the bore, on the axis
    readonly property real zTipDiameter: isAxial ? 0
                                       : isTrepanning ? trepanningDiameter
                                       : asId ? boreDiameter + 0.3 * (stockDiameter - boreDiameter)
                                       : 0.85 * turnedDiameter

    // ── Px ───────────────────────────────────────────────────────────────
    // X, all tools: the diameter's arrow in front of the stock, the tool's
    // tip, and how far the extension lines run on past the tip
    readonly property real diameterArrowOffset: 30
    readonly property real diameterTipOffset: 60
    readonly property real diameterLinePastTip: 12
    // the extension lines past the arrow: out past the tool's tip
    readonly property real diameterExtensionPast: diameterTipOffset - diameterArrowOffset + diameterLinePastTip
    // Z: the line the tool touches in front of the face, the arrow above
    // its tip - under it in the tube, clear of the insert - and how far the
    // line runs past the arrow and the tip
    readonly property real zLineOffset: 50
    readonly property real zArrowAbove: 24
    // - a trepanning blade's at the middle of its cutting end
    readonly property real zArrowFromTip: isTrepanning ? 0 : asId ? zArrowAbove : -zArrowAbove
    readonly property real zLineOvershoot: 12
    // an insert or blade's biggest dimension; an axial tool's diameter and
    // how far of it is kept in view
    readonly property real insertSize: 80
    readonly property real axialToolSize: 28
    readonly property real axialToolRoom: 140
    // kept free round the drawing
    readonly property real margin: 32
    readonly property color dimensionColor: "#00838f"

    // ── An insert or blade ───────────────────────────────────────────────
    // a blade's corners, mm about its control point (blade.js): its left
    // corner first, then its right
    readonly property var bladeCorners: isBlade ? tool.outlineFromTip : []
    // its outline about its tip, mm: {minX, maxX, minY, maxY}, x along Z, y
    // down the screen
    readonly property var toolBox: {
        var pts = tool.outlineFromTip
        var box = { minX: 0, maxX: 0, minY: 0, maxY: 0 }
        for (var i = 0; i < pts.length; i++) {
            box.minX = Math.min(box.minX, pts[i].x); box.maxX = Math.max(box.maxX, pts[i].x)
            box.minY = Math.min(box.minY, pts[i].y); box.maxY = Math.max(box.maxY, pts[i].y)
        }
        return box
    }
    // drawn insertSize px at its biggest
    readonly property real toolPxPerMm: {
        var span = Math.max(toolBox.maxX - toolBox.minX, toolBox.maxY - toolBox.minY)
        return span > 0 ? insertSize / span : 1
    }
    // a blade's points to choose from, px about its control point - the
    // middle of its cutting end
    readonly property var bladePoints: bladeCorners.length >= 2
        ? { "-1": { x: bladeCorners[0].x * toolPxPerMm, y: bladeCorners[0].y * toolPxPerMm },
            "0": { x: 0, y: 0 },
            "1": { x: bladeCorners[1].x * toolPxPerMm, y: bladeCorners[1].y * toolPxPerMm } }
        : ({})
    // a blade's point by its place - the middle while there is none (no
    // blade, or for a moment while the tool changes)
    function bladePoint(place) { return bladePoints[place] || ({ x: 0, y: 0 }) }
    readonly property var bladeChosen: bladePoint(bladePlace)
    // a trepanning blade's corners, as they lie on the screen: the one
    // toward X- (nearer the centre line) and the one toward X+
    readonly property string xMinusPlace: bladePoint("-1").y <= bladePoint("1").y ? "-1" : "1"
    readonly property string xPlusPlace: xMinusPlace === "-1" ? "1" : "-1"
    // the points to choose from, and the buttons' names for them
    readonly property var placeChoices: isTrepanning
        ? [{ place: xMinusPlace, text: "X-" }, { place: xPlusPlace, text: "X+" }]
        : [{ place: "-1", text: "Left" }, { place: "0", text: "Center" }, { place: "1", text: "Right" }]

    function resetPlace() { bladePlace = isTrepanning ? xMinusPlace : "-1" }
    // Z: where the tool touches the line, px about its control point - a
    // threading insert's straight side toward the stock, as high as the
    // insert; a blade's left corner, wherever the arrow runs to; else the tip
    readonly property var zContact: {
        if (isThreading)
            return { x: toolBox.minX * toolPxPerMm, top: toolBox.minY * toolPxPerMm,
                     bottom: toolBox.maxY * toolPxPerMm }
        // a trepanning blade's cutting end, corner to corner
        if (isTrepanning)
            return { x: 0, top: Math.min(bladePoint("-1").y, bladePoint("1").y),
                     bottom: Math.max(bladePoint("-1").y, bladePoint("1").y) }
        if (choosesZPoint)
            return { x: bladePoint("-1").x, top: bladePoint("-1").y, bottom: bladePoint("-1").y }
        return { x: 0, top: 0, bottom: 0 }
    }
    // Z: the line the arrow runs to, px in front of the face - a blade's at
    // its point chosen, the blade staying put
    readonly property real zLineAt: zLineOffset + (choosesZPoint ? bladeChosen.x - zContact.x : 0)
    // its tip: px in front of the face, and the diameter it is on
    readonly property real tipOffset: inZ ? zLineOffset - zContact.x : diameterTipOffset
    readonly property real tipDiameter: inZ ? zTipDiameter : isTrepanning ? trepanningDiameter
                                                           : asId ? boreDiameter : turnedDiameter

    // ── An axial tool ────────────────────────────────────────────────────
    readonly property real axialPxPerMm: isAxial && toolView.diameter > 0 ? axialToolSize / toolView.diameter : 1
    // its point: in front of the face, and in X as far off the centre line
    readonly property real axialTipX: cx(0) + (inZ ? zLineOffset : diameterTipOffset)
    readonly property real axialTipY: originY + (inZ ? 0 : diameterTipOffset)

    // ── Laid out ─────────────────────────────────────────────────────────
    // kept free over the drawing - and as much under it - for a blade's
    // choice of point
    readonly property real placeRoom: needsPlace ? placeCard.y + placeCard.height + 8 - margin : 0
    // px per mm, and where Z0 and the centre line are: the stock - its
    // broken end bulging out past its length - and, right of its face, the
    // tool and the dimension's lines, in the middle of the canvas; the
    // tool's reach under its tip kept free, and as much over the stock
    readonly property real rightRoom: isAxial ? (inZ ? zLineOffset : diameterTipOffset) + axialToolRoom
                                              : tipOffset + Math.max(inZ ? 0 : diameterLinePastTip,
                                                                     toolBox.maxX * toolPxPerMm)
    readonly property real belowTip: Math.max(0, toolBox.maxY * toolPxPerMm)
    readonly property real drawnLength: stockLength + Broken.reach(1.0) * stockDiameter / 2
    readonly property real scale: Math.max(0.1, Math.min(
        (width - 2 * margin - rightRoom) / drawnLength,
        (height / 2 - margin - placeRoom) / (stockDiameter / 2),
        (height / 2 - margin - placeRoom - belowTip) / (tipDiameter / 2)))
    readonly property real originX: (width - (drawnLength * scale + rightRoom)) / 2 + drawnLength * scale
    readonly property real originY: height / 2

    function cx(z) { return originX + z * scale }
    function cy(x) { return originY + (x / 2) * scale }

    color: Theme.surface
    border.color: Theme.outline
    border.width: Theme.hairline
    radius: Theme.radius
    clip: true

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        readonly property var inputs: [root.width, root.height, root.showsTool, root.asId, root.asOd,
                                       root.inZ, root.scale, root.originX, root.zContact, root.zLineAt,
                                       root.isAxial, root.toolView, root.axialPxPerMm, root.bladeChosen]
        onInputsChanged: requestPaint()

        CenterLineActor {
            id: centerLine
            width: root.width
            originY: root.originY
        }

        // the origin sign at Z0 on the centre line, as the profile canvases
        // have it
        OriginActor {
            id: origin
            originX: root.cx(0)
            originY: root.originY
            circleR: 8
        }

        StockActor {
            id: stock
            workpiece: ({ external_diameter: root.stockDiameter,
                          internal_diameter: root.asId ? root.boreDiameter : 0,
                          stock_length: root.stockLength, break_far_end: true })
            cx: root.cx
            cy: root.cy
            mirrorAcrossCenterline: true
        }

        // a drill or a tap, its point at axialTipX, axialTipY (a reamer is
        // the Reamer item over the canvas)
        AxialToolActor {
            id: axialTool
            drill: root.isDrill ? root.toolView : null
            tap: root.isTap ? root.toolView : null
            z: (root.axialTipX - root.originX) / root.scale
            pointX: 2 * (root.axialTipY - root.originY) / root.scale
            cx: root.cx
            cy: root.cy
            scale: root.axialPxPerMm
            bodyColor: root.isAxial ? root.toolView.bodyColor : "#e5a93b"
            edgeColor: root.isAxial ? root.toolView.edgeColor : "#674c1b"
        }

        DimensionActor {
            id: dimension
            cx: root.cx
            cy: root.cy
            dimensions: {
                var c = root.dimensionColor
                // Z: from the line the tool touches back to the face
                if (root.inZ)
                    return [{ axis: "z", from: root.zLineAt / root.scale, to: 0, x: root.zTipDiameter,
                              offset: root.zArrowFromTip, noExtensionLines: true, color: c }]
                // an axial tool's X: from the centre line - no extension line
                // on it - to the tool's axis, its extension line the axis run
                // on from the point toward the face
                if (root.isAxial)
                    return [{ axis: "x", from: 0, to: 2 * root.diameterTipOffset / root.scale, z: 0,
                              offset: root.diameterArrowOffset, noFromExtension: true,
                              extensionPast: root.diameterTipOffset - root.diameterArrowOffset, color: c }]
                // a trepanning blade's: to its corner chosen; the bore, its
                // arrows outside its lines; the turned diameter
                var d = root.isTrepanning ? root.trepanningDiameter + 2 * root.bladeChosen.y / root.scale
                      : root.asId ? root.boreDiameter : root.turnedDiameter
                return [{ axis: "x", from: -d, to: d, z: 0, offset: root.diameterArrowOffset,
                          arrowsOutside: root.asId, extensionPast: root.diameterExtensionPast, color: c }]
            }
        }

        // OD: the turned diameter's step - what is turned off cleared to the
        // ground, and the outline round it (its face is paintFace's)
        function paintTurnedStep(ctx) {
            var back = root.cx(-root.turnedLength), face = root.cx(0)
            var D = root.stockDiameter, d = root.turnedDiameter, pad = 2
            ctx.fillStyle = root.color
            ctx.fillRect(back, root.cy(-D) - pad, face - back + pad, root.cy(-d) - root.cy(-D) + pad)
            ctx.fillRect(back, root.cy(d), face - back + pad, root.cy(D) - root.cy(d) + pad)
            ctx.strokeStyle = stock.outlineColor
            ctx.lineWidth = stock.outlineWidth
            ctx.beginPath()
            ctx.moveTo(back, root.cy(-D)); ctx.lineTo(back, root.cy(-d)); ctx.lineTo(face, root.cy(-d))
            ctx.moveTo(face, root.cy(d)); ctx.lineTo(back, root.cy(d)); ctx.lineTo(back, root.cy(D))
            ctx.stroke()
        }

        // the face, from ``outer`` in to ``inner`` on both halves: a broken
        // stock's ends have no outline, the Program Header's Z0 line marks
        // it there
        function paintFace(ctx, outer, inner) {
            var face = root.cx(0)
            ctx.strokeStyle = stock.outlineColor
            ctx.lineWidth = stock.outlineWidth
            ctx.beginPath()
            ctx.moveTo(face, root.cy(-outer)); ctx.lineTo(face, root.cy(-inner))
            ctx.moveTo(face, root.cy(inner)); ctx.lineTo(face, root.cy(outer))
            ctx.stroke()
        }

        // Z: the short line parallel to the face the tool touches, from past
        // the arrow to past where it touches it - a blade's at its point
        // chosen
        function paintZLine(ctx) {
            var x = root.cx(0) + root.zLineAt, tipY = root.cy(root.zTipDiameter)
            var top = root.choosesZPoint ? root.bladeChosen.y : root.zContact.top
            var bottom = root.choosesZPoint ? root.bladeChosen.y : root.zContact.bottom
            var arrowY = tipY + root.zArrowFromTip
            ctx.strokeStyle = root.dimensionColor
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(x, Math.min(tipY + top, arrowY) - root.zLineOvershoot)
            ctx.lineTo(x, Math.max(tipY + bottom, arrowY) + root.zLineOvershoot)
            ctx.stroke()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (root.showsTool) {
                stock.paint(ctx)
                if (root.asOd) {
                    paintTurnedStep(ctx)
                    paintFace(ctx, root.turnedDiameter, 0)
                } else {
                    paintFace(ctx, root.stockDiameter, root.asId ? root.boreDiameter : 0)
                }
            }
            // the centre line over the stock, as the profile canvases draw it
            centerLine.paint(ctx)
            origin.paint(ctx)
            if (!root.showsTool) return
            if (root.inZ) paintZLine(ctx)
            axialTool.paint(ctx)
            dimension.paint(ctx)
        }
    }

    // a reamer, its point - the middle of its end - on the left of its middle
    Reamer {
        visible: root.isReamer
        x: root.axialTipX
        y: root.axialTipY - height / 2
        width: implicitWidth
        height: implicitHeight
        diameter: root.isReamer ? Number(root.toolView.diameter) : 10
        helixAngle: root.isReamer ? Number(root.toolView.helixAngle) : 10
        pxPerMm: root.axialPxPerMm
        bodyColor: root.isReamer ? root.toolView.bodyColor : "#e5a93b"
        edgeColor: root.isReamer ? root.toolView.edgeColor : "#674c1b"
    }

    // an insert or blade, its tip on the lower extension line in X, on the
    // line parallel to the face in Z
    CanvasTool {
        id: tool
        visible: root.showsTool && !root.isAxial
        view: root.showsTool && !root.isAxial ? root.toolView : null
        pxPerMm: root.toolPxPerMm
        tipX: root.cx(0) + root.tipOffset
        tipY: root.cy(root.tipDiameter)
    }

    // ── A blade's point ──────────────────────────────────────────────────
    // a dot on each point it can be measured at (placeChoices), the one
    // chosen filled, and over the drawing the card with the buttons that
    // choose
    readonly property color placeColor: "#ef6c00"
    readonly property real placeDotRadius: 5

    Repeater {
        model: root.needsPlace ? root.placeChoices : []
        delegate: Rectangle {
            // none for a moment while the tool or the axis changes: hidden
            readonly property var point: root.bladePoint(modelData.place)
            readonly property bool chosen: root.bladePlace === modelData.place
            visible: !!root.bladePoints[modelData.place]
            width: 2 * root.placeDotRadius
            height: width
            radius: width / 2
            x: tool.tipX + point.x - width / 2
            y: tool.tipY + point.y - height / 2
            color: chosen ? root.placeColor : Theme.surface
            border.color: root.placeColor
            border.width: 2
            // a fingertip's room to tap it
            TapHandler {
                margin: 16
                onTapped: root.bladePlace = modelData.place
            }
        }
    }

    CanvasBox {
        id: placeCard
        visible: root.needsPlace
        anchors.top: parent.top
        anchors.topMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        // a trepanning blade's: the corner its diameter is measured at
        title: root.inZ ? "Z0 Point" : "\u00d8 Point"
        titleCentred: true
        accent: root.placeColor

        Row {
            spacing: 16
            Repeater {
                model: root.placeChoices
                delegate: Button {
                    readonly property bool chosen: root.bladePlace === modelData.place
                    width: 96
                    height: 44
                    // the dialog keeps the keyboard's focus
                    focusPolicy: Qt.NoFocus
                    text: modelData.text
                    font.pixelSize: Theme.fontBody
                    font.bold: chosen
                    background: Rectangle {
                        radius: 8
                        color: parent.chosen ? root.placeColor : parent.pressed ? Theme.selection : Theme.surface
                        border.color: parent.chosen ? root.placeColor : "#9aa3b0"
                        border.width: Theme.hairline
                    }
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: parent.chosen ? "white" : Theme.foreground
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: root.bladePlace = modelData.place
                }
            }
        }
    }
}
