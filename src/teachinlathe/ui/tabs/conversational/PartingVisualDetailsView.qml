// PartingVisualDetailsView.qml — Parting on the profile canvas, laid out as
// Drilling's: the header's stock, broken off after Z Position, and the
// parting blade it cuts with, where it starts: its
// cutting end at X Start + the clearance (a radius, X Start a diameter), its
// right side on Z Position. X Start, where Fz2 takes over and X End each a
// short line across the blade's path at their diameter, Z Position a line
// across the centre line on the blade's right, the clearance dimensioned
// above X Start - each with an arrow to its box down the right edge. A new
// Parting starts at the stock's outside, ends at its bore, and slows to Fz2
// a blade's width before the end. Saves through updateParting.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import "profile_canvas/brokenstock.js" as Broken
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the program header's stock, and the tool in when this parts, as its
    // Tool Library card shows it: editor.toolCard, a ToolCard; null with none
    property var    workpiece: ({})
    property var    toolCard: null

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   xEnd: 0.0
    property real   zPos: 0.0
    property real   xFz2: 0.0          // where the second feed rate takes over
    property real   xClearance: 1.0
    // none, a chamfer or a fillet on the part's edge, as the op keeps it
    property var    edgeBreak: ({ blend_type: "none", chamfer_width: 0, fillet_radius: 0 })

    // the boxes' and their marks' colours
    readonly property color zPosColor:      "#00838f"
    readonly property color xStartColor:    "#1565c0"
    readonly property color xFz2Color:      profileCanvas.feedColor
    readonly property color xEndColor:      profileCanvas.endPositionColor
    readonly property color clearanceColor: "#6d4c41"
    readonly property color edgeBreakColor: "#ad1457"

    // the blade in, if it is one
    readonly property bool hasBlade: !!(toolCard && toolCard.card === "blade" && toolCard.view)
    readonly property real bladeWidth: hasBlade ? Number(toolCard.view.bladeWidth) : 3
    // where the blade starts: the clearance is a radius, X a diameter
    readonly property real startX: xStart + 2 * Math.abs(xClearance)
    // the stock as drawn: as big as Start Ø, or the header's until that is set
    readonly property real stockDiameter: xStart > 0 ? xStart : (Number(workpiece && workpiece.external_diameter) || 0)

    // Further from Z0 than its diameter, the stock's middle is left out, as
    // the Program Header leaves it out (brokenstock.js), and what is drawn is
    // short: the piece at the face 0.3 Ø, a gap, then the far piece with the
    // blade in its middle - Z Position 0.25 Ø on from the gap, and as far
    // past the blade to the far break.
    // ``shift`` is how far right a real Z there is drawn; the axis marks the
    // real Z.
    readonly property bool breakMiddle: stockDiameter > 0 && Math.abs(zPos) > stockDiameter
    readonly property real breakBend: Broken.reach(1.0) * stockDiameter / 2
    readonly property real breakGap: (Broken.reach(1.0) + 0.06) * stockDiameter
    readonly property real breakNear: -0.3 * stockDiameter
    readonly property real breakFar: breakNear - breakGap
    readonly property real zShift: breakMiddle ? (breakFar - 0.25 * stockDiameter) - zPos : 0
    // past Z Position to the far break: the blade, then as far again as
    // from the gap to it, so it is in the far piece's middle
    readonly property real breakSetback: 0.25 * stockDiameter + bladeWidth
    // Z Position where it is drawn
    readonly property real zDrawn: zPos + zShift
    // the middle of the blade's cutting end - Z Position is its right side -
    // where it is drawn
    readonly property real bladeZ: zDrawn - bladeWidth / 2
    signal openNumPadRequested(var field)

    // opData with the values edited in the boxes
    // what parting will cut with the values above, as its G-code moves - drawn
    // where the canvas draws the blade: along Z by zShift, as the stock is
    // broken to fit
    readonly property var partingPreview: {
        if (opIndex < 0 || !editor) return null
        var preview = editor.preview(_draftOp())
        function shifted(lines) {
            return (lines || []).map(function(l) {
                var m = JSON.parse(JSON.stringify(l))
                m.z0 += root.zShift
                m.z1 += root.zShift
                return m
            })
        }
        preview.feeds = shifted(preview.feeds)
        preview.rapids = shifted(preview.rapids)
        return preview
    }

    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.parting_parameters = op.parting_parameters || {}
        var pp = op.parting_parameters
        pp.x_start = xStart
        pp.x_end = xEnd
        pp.z_pos = zPos
        pp.second_feed_x_pos = xFz2
        pp.x_clearance = xClearance
        op.edge_break = JSON.parse(JSON.stringify(edgeBreak))
        return op
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || _draftOp()
        root.editor.save(opData)
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        workpiece = editor ? (editor.workpiece || {}) : {}
        toolCard  = editor ? editor.toolCard : null

        var pp = opData.parting_parameters || {}
        xStart = pp.x_start !== undefined ? Number(pp.x_start) : 0
        xEnd   = pp.x_end   !== undefined ? Number(pp.x_end)   : 0
        zPos   = pp.z_pos   !== undefined ? Number(pp.z_pos)   : 0
        xFz2   = pp.second_feed_x_pos !== undefined ? Number(pp.second_feed_x_pos) : 0
        xClearance = pp.x_clearance !== undefined ? Number(pp.x_clearance) : 1
        var eb = opData.edge_break || {}
        edgeBreak = { blend_type: eb.blend_type !== undefined ? String(eb.blend_type) : "none",
                      chamfer_width: eb.chamfer_width !== undefined ? Number(eb.chamfer_width) : 0,
                      fillet_radius: eb.fillet_radius !== undefined ? Number(eb.fillet_radius) : 0 }

        header.applyData(opData)

        // a new one - X Start never set - from the stock: start at its
        // outside, end at its bore, Fz2 from a blade's width before the end
        if (!(xStart > 0) && Number(workpiece.external_diameter) > 0) {
            xStart = Number(workpiece.external_diameter)
            xEnd = Math.max(0, Number(workpiece.internal_diameter) || 0)
            xFz2 = xEnd + bladeWidth
            save()
        }
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Parting has no M1; both its feed rates are the header's, Fz1 and Fz2
        OperationHeader {
            id: header
            hasM1: false
            feedKind: SpeedsAndFeeds.FeedKind.Parting
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp()
                op.speeds_and_feeds = speeds
                root.save(op)
            }
        }

        ProfileCanvas {
            id: profileCanvas
            showTransitions: false
            // no axes: the origin alone marks Z0
            showAxes: false
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            // the blade and the stock whole, both halves
            mirrorAcrossCenterline: true
            // a dot at both ends of each arrow to a box
            arrowStartDots: true
            primitives: []
            // the G-code's moves
            roughingPreview: root.partingPreview
            // the header's stock, as big as Start Ø, broken off after where it
            // is parted - and its middle left out when that is far down it
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                if (root.stockDiameter > 0) w.external_diameter = root.stockDiameter
                w.break_after_z = root.zDrawn
                w.break_middle = root.breakMiddle ? { near: root.breakNear, far: root.breakFar } : null
                if (root.breakMiddle) w.break_after_setback = root.breakSetback
                return w
            }
            axisBreak: root.breakMiddle ? { near: root.breakNear, far: root.breakFar, shift: root.zShift } : null

            // where the dashed lines of the blade's path end: below, past
            // where it starts; above, past the stock's outside - or, with
            // the mirror off, at End Ø
            readonly property real zLineBottom: Math.max(root.startX, 10) * 1.15
            readonly property real zLineTop: mirrorAcrossCenterline ? -(root.stockDiameter + 4) : root.xEnd
            // how far either side of the blade's middle the X lines reach,
            // mm: xLinePast past each dashed line of its path
            readonly property real xLinePast: 2
            readonly property real xLineHalf: root.bladeWidth / 2 + xLinePast
            markers: [
                // Z Position: across the centre line, past the blade's start
                // the blade's path: a dashed line either side of it - Z
                // Position on its right - from past where it starts, below,
                // to just past the stock's outside, above; with the mirror
                // off, to End Ø. The arrow to the Z Position box from the
                // right one, 2/3 of the radius above the centre line - with
                // the mirror off, from its top
                { line: true, z: root.zDrawn, bottom: zLineBottom, top: zLineTop, dash: [6, 3],
                  arrowAt: profileCanvas.mirrorAcrossCenterline ? -root.stockDiameter * 2 / 3 : zLineTop,
                  color: root.zPosColor, arrowToRect: zPosBox.rect },
                { line: true, z: root.zDrawn - root.bladeWidth, bottom: zLineBottom, top: zLineTop,
                  dash: [6, 3], color: root.zPosColor },
                // where the blade starts: X Start + the clearance - past the
                // blade on the right twice as far as on the left, the
                // clearance dimensioned in the middle of that stretch
                { hline: true, x: root.startX, z: root.bladeZ, half: xLineHalf,
                  halfRight: root.bladeWidth / 2 + 2 * xLinePast,
                  color: root.clearanceColor },
                // Start Ø at the blade - dimensioned in front of the stock
                // (startDimension); with the mirror off, its arrow from here
                { hline: true, x: root.xStart, z: root.bladeZ, half: xLineHalf,
                  color: root.xStartColor,
                  arrowToRect: profileCanvas.mirrorAcrossCenterline ? null : xStartBox.rect },
                // Fz2 Ø at the blade, and its mirror - dimensioned in front of
                // the stock (fz2Dimension); with the mirror off, the lower one
                // alone, its arrow from here
                { hline: true, x: root.xFz2, z: root.bladeZ, half: xLineHalf,
                  color: root.xFz2Color,
                  arrowToRect: profileCanvas.mirrorAcrossCenterline ? null : xFz2Box.rect },
                { hline: true, x: -root.xFz2, z: root.bladeZ, half: xLineHalf, color: root.xFz2Color,
                  visible: profileCanvas.mirrorAcrossCenterline },
                { hline: true, x: root.xEnd, z: root.bladeZ, half: xLineHalf,
                  color: root.xEndColor },
                // the edge break on the part's corner, at Start Ø on Z
                // Position's side, and its mirror; what it takes off in red
                { blend: root.edgeBreak.blend_type, x: root.xStart, z: root.zDrawn,
                  size: root.edgeBreak.blend_type === "fillet" ? root.edgeBreak.fillet_radius
                                                                : root.edgeBreak.chamfer_width,
                  mirror: profileCanvas.mirrorAcrossCenterline,
                  color: root.edgeBreakColor, fill: "#e53935" }
            ]
            // the clearance, between the X Start line and the blade's start
            // line, its arrows outside them pointing in; its leader from the
            // bottom end of the lower arrow to the X Clearance box
            dimensions: (root.xClearance > 0
                         ? [{ axis: "x", from: root.xStart, to: root.startX,
                              z: root.bladeZ + root.bladeWidth / 2 + xLinePast, offset: 0,
                              color: root.clearanceColor,
                              arrowToRect: clearanceBox.rect, arrowsOutside: true,
                              leaderFromOutsideEnd: "to" }]
                         : []).concat(startDimension ? [startDimension] : [])
                                 .concat(fz2Dimension ? [fz2Dimension] : [])
            // Start Ø - the stock's - first in front of the stock, from -Ø to
            // +Ø, at the middle of its extension lines out from the face; its
            // leader from a dot above the centre line to the Start Ø box.
            // Mirrored only
            readonly property var startDimension: mirrorAcrossCenterline && root.xStart > 0
                ? { axis: "x", from: -root.xStart, to: root.xStart, z: 0, offset: 24,
                    extensionsCentred: true,
                    color: root.xStartColor, arrowToRect: xStartBox.rect, leaderAt: 0.25 }
                : null
            // Fz2 Ø in front of the stock, past Start Ø, at the middle of its
            // extension lines out from the face, its arrows outside them
            // pointing in; its leader from the top end of the upper arrow to
            // the Fz2 Ø box. Mirrored only
            readonly property var fz2Dimension: mirrorAcrossCenterline && root.xFz2 > 0
                ? { axis: "x", from: -root.xFz2, to: root.xFz2, z: 0, offset: 48,
                    extensionsCentred: true,
                    color: root.xFz2Color,
                    arrowToRect: xFz2Box.rect, arrowsOutside: true, leaderFromOutsideEnd: "from" }
                : null

            // the blade where it starts, inside the ticks; in the fit too
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var pts = canvasTool.outlineFromTip, out = []
                for (var i = 0; i < pts.length; i++)
                    out.push({ x: root.startX + 2 * pts[i].y, z: root.bladeZ + pts[i].x })
                return out
            }
            onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
            CanvasTool {
                id: canvasTool
                inset: profileCanvas.tickBand
                card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                pxPerMm: profileCanvas._scale
                tipX: profileCanvas._cx(root.bladeZ)
                tipY: profileCanvas._cy(root.startX)
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(zPosBox.implicitWidth, xStartBox.implicitWidth,
                                                      xFz2Box.implicitWidth, xEndBox.implicitWidth,
                                                      edgeBreakBox.implicitWidth, clearanceBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            // top to bottom: Z Position at the top, then Start, End and Fz2
            // together, a gap apart; Clearance at the bottom.
            // The position boxes as wide as each other
            readonly property real positionBoxWidth: Math.max(zPosBox.implicitWidth, xStartBox.implicitWidth,
                                                              xFz2Box.implicitWidth, xEndBox.implicitWidth)
            // their labels as wide as the widest, so the fields line up
            readonly property real positionLabelWidth: Math.max(zPosBox.labelImplicitWidth,
                                                                xStartBox.labelImplicitWidth,
                                                                xFz2Box.labelImplicitWidth,
                                                                xEndBox.labelImplicitWidth)
            readonly property real xGroupY: zPosBox.y + zPosBox.height + boxGap

            ZPositionBox {
                id: zPosBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                accent: root.zPosColor
                label: "Z Position"
                settingName: "parting.z_pos"
                value: root.zPos
                onValueEdited: function(value) { root.zPos = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: xStartBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.xGroupY
                axis: "x"
                accent: root.xStartColor
                label: "Start \u00d8"
                settingName: "parting.x_start"
                value: root.xStart
                onValueEdited: function(value) { root.xStart = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // where the second feed rate takes over
            ZPositionBox {
                id: xFz2Box
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: xEndBox.y + xEndBox.height + profileCanvas.boxGap
                axis: "x"
                accent: root.xFz2Color
                label: "Fz2 \u00d8"
                settingName: "parting.second_feed_x_pos"
                value: root.xFz2
                onValueEdited: function(value) { root.xFz2 = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: xEndBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: xStartBox.y + xStartBox.height + profileCanvas.boxGap
                axis: "x"
                accent: root.xEndColor
                label: "End \u00d8"
                settingName: "parting.x_end"
                value: root.xEnd
                onValueEdited: function(value) { root.xEnd = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the edge break, at the bottom
            EdgeBreakBox {
                id: edgeBreakBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                color: root.edgeBreakColor
                blendType: root.edgeBreak.blend_type
                chamferWidth: root.edgeBreak.chamfer_width
                filletRadius: root.edgeBreak.fillet_radius
                onEdited: function(edgeBreak) { root.edgeBreak = edgeBreak; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // just above the edge break
            DimensionBox {
                id: clearanceBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: edgeBreakBox.y - height - profileCanvas.boxGap
                label: "Clearance"
                dimensionColor: root.clearanceColor
                settingName: "parting.x_clearance"
                value: root.xClearance
                onValueEdited: function(value) { root.xClearance = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the tool it parts with, at the top, in the middle; tapped, to
            // pick it - only a parting blade
            OperationToolBox {
                editor: root.editor
                pickerWidth: root.width
                x: (profileCanvas.width - width) / 2
                // lined up with the view buttons, as tall as they are
                y: viewButtons.y
                rowHeight: viewButtons.height
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                id: viewButtons
                canvas: profileCanvas
            }
        }
    }
}
