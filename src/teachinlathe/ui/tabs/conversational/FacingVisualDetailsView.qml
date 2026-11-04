// FacingVisualDetailsView.qml — Facing on the profile canvas, laid out as
// Profile Roughing's: no profile, so the passes are drawn over the header's
// stock, from the start position to the end position. Saves every change
// through updateFacing.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the program header's stock
    property var    workpiece: ({})
    // the tool it cuts with, as its Tool Library card
    // shows it: editor.toolCard, a ToolCard; null with none
    property var    toolCard: null

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property real   xEnd: 0.0
    property real   zEnd: 0.0
    property real   doc: 0.0
    property real   toolClearance: 0.0
    property bool   zEndBecomesNewZ0: false
    readonly property real stockDiameter: Number(workpiece && workpiece.external_diameter) > 0
                                          ? Number(workpiece.external_diameter) : Math.abs(xStart)
    // the canvas mirrored or not: on unless the editor says otherwise; the
    // mirror button changes it, and the editor keeps it for the next Facing
    property bool   canvasMirror: true
    onCanvasMirrorChanged: profileCanvas.mirrorAcrossCenterline = canvasMirror

    // what facing will cut with the values above
    readonly property var facingPreview: (opIndex >= 0 && editor)
                                         ? editor.preview(_draftOp())
                                         : null
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.geometry_parameters = { x_start: xStart, z_start: zStart, x_end: xEnd, z_end: zEnd }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.doc = doc
        op.cutting_parameters.retract = toolClearance
        op.z_end_becomes_new_z0 = zEndBecomesNewZ0
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
        toolCard = editor ? editor.toolCard : null

        var gp = opData.geometry_parameters || {}
        var cp = opData.cutting_parameters || {}
        xStart  = gp.x_start !== undefined ? Number(gp.x_start) : 0
        zStart  = gp.z_start !== undefined ? Number(gp.z_start) : 0
        xEnd    = gp.x_end   !== undefined ? Number(gp.x_end)   : 0
        zEnd    = gp.z_end   !== undefined ? Number(gp.z_end)   : 0
        doc     = cp.doc     !== undefined ? Number(cp.doc)     : 0
        toolClearance = cp.retract !== undefined ? Number(cp.retract) : 0
        zEndBecomesNewZ0 = !!opData.z_end_becomes_new_z0

        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // each edit goes into the whole op with the canvas boxes' values
        OperationHeader {
            id: header
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp()
                op.speeds_and_feeds = speeds
                root.save(op)
            }
            onM1Edited: function(m1) {
                var op = root._draftOp()
                op.m1_parameters = m1
                root.save(op)
            }
        }

        ProfileCanvas {
            id: profileCanvas
            showTransitions: false
            // no axes: the origin alone marks Z0
            showAxes: false
            showZeroLine: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            mirrorAcrossCenterline: true
            primitives: []
            // the header's stock, and in front of Z0 up to Z Start, the
            // material being faced off; mirrored, broken off after Z End
            // as Profile Roughing's after its profile
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                w.face_z = Math.max(0, root.zStart)
                w.break_after_z = root.zEnd
                w.faced_to = root.zEnd
                return w
            }
            startPosition: ({ x: root.xStart + 2 * root.toolClearance,
                              z: root.zStart + root.toolClearance })
            endPosition:   ({ x: root.xEnd,   z: root.zEnd })
            roughingPreview: root.facingPreview
            startPositionArrowRect: null
            endPositionArrowRect: null
            readonly property real p1TagOffset: 56
            readonly property real p1TagX: _cx(root.zStart) - p1TagOffset - p1Tag.width
            readonly property real p1TagY: _cy(root.xStart) + p1TagOffset
            readonly property real p2TagX: _cx(root.zEnd) + 56
            readonly property real p2TagY: _cy(root.xEnd) - 56
            markers: [
                // Extend the stock's outside diameter from Z End to Z0 on
                // both mirrored sides, matching the stock outline colour.
                { hline: true, x: root.stockDiameter, z: root.zEnd / 2,
                  half: Math.abs(root.zEnd) / 2, dash: [6, 3], color: "#6b7280" },
                { hline: true, x: -root.stockDiameter, z: root.zEnd / 2,
                  half: Math.abs(root.zEnd) / 2, dash: [6, 3], color: "#6b7280" },
                { leader: true, x: root.xStart, z: root.zStart, color: "#1565c0",
                  toZ: root.zStart, dx: -profileCanvas.p1TagOffset, slope: 1 },
                { leader: true, x: root.xEnd, z: root.zEnd, color: profileCanvas.endPositionColor,
                  toZ: root.zEnd, dx: 56, slope: -1 }
            ]
            Radial.GroovePointTag {
                id: p1Tag
                point: 1
                axes: "XZ"
                x: profileCanvas.p1TagX
                y: profileCanvas.p1TagY - height / 2
            }
            Radial.GroovePointTag {
                point: 2
                axes: "XZ"
                x: profileCanvas.p2TagX
                y: profileCanvas.p2TagY - height / 2
                accent: profileCanvas.endPositionColor
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // the mirror button changes it here; the view passes it on
            Connections {
                target: profileCanvas
                function onMirrorAcrossCenterlineChanged() { root.canvasMirror = profileCanvas.mirrorAcrossCenterline }
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(docBox.implicitWidth, z0Check.implicitWidth,
                                                      endBox.implicitWidth, startBox.implicitWidth,
                                                      retractBox.implicitWidth)
            readonly property real boxGap: profileCanvas.tickBand
            fitInsetRight: boxWidth + profileCanvas.tickBand

            // the tool it cuts with, at the top, in the middle
            OperationToolBox {
                editor: root.editor
                pickerWidth: root.width
                x: (profileCanvas.width - width) / 2
                // lined up with the view buttons, as tall as they are
                y: viewButtons.y
                rowHeight: viewButtons.height
            }

            // the tool - a turning tool's insert or a blade - its control
            // point on the start position, turned as its orientation has it,
            // inside the ticks
            // the tool in the fit too
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var pts = canvasTool.outlineFromTip, out = []
                for (var i = 0; i < pts.length; i++)
                    out.push({ x: root.xStart + 2 * root.toolClearance + 2 * pts[i].y,
                               z: root.zStart + root.toolClearance + pts[i].x })
                return out
            }
            onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
            CanvasTool {
                id: canvasTool
                inset: profileCanvas.tickBand
                card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                pxPerMm: profileCanvas._scale
                tipX: profileCanvas._cx(root.zStart + root.toolClearance)
                tipY: profileCanvas._cy(root.xStart + 2 * root.toolClearance)
            }

            // top to bottom: Tool Clearance (retract), P1, Ap, P2 and its Z0
            // option; all position cards use the same labels and teach-in UI
            DepthOfCutBox {
                id: retractBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                showDoc: false
                retractLabel: "Tool Clearance"
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                retract: root.toolClearance
                onRetractEdited: function(value) { root.toolClearance = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            TurningPointBox {
                id: startBox
                point: 1
                settingPrefix: "facing"
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: retractBox.y + retractBox.height + Theme.spacingSmall
                xValue: root.xStart
                zValue: root.zStart
                onFieldEdited: function(axis, value) {
                    if (axis === "x") root.xStart = value; else root.zStart = value
                    root.save()
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DepthOfCutBox {
                id: docBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: startBox.y + startBox.height + Theme.spacingSmall
                showRetract: false
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                doc: root.doc
                onDocEdited: function(value) { root.doc = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            TurningPointBox {
                id: endBox
                point: 2
                pointColor: profileCanvas.endPositionColor
                settingPrefix: "facing"
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: docBox.y + docBox.height + Theme.spacingSmall
                xValue: root.xEnd
                zValue: root.zEnd
                onFieldEdited: function(axis, value) {
                    if (axis === "x") root.xEnd = value; else root.zEnd = value
                    root.save()
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            CheckBox {
                id: z0Check
                x: profileCanvas.width - width - profileCanvas.tickBand
                y: endBox.y + endBox.height + Theme.spacingSmall
                text: "Set P2Z as the new Z0"
                font.pixelSize: Theme.fontBody
                font.bold: false
                checked: root.zEndBecomesNewZ0
                onToggled: { root.zEndBecomesNewZ0 = checked; root.save() }
                contentItem: Text {
                    text: "Set P<sub>2</sub><span style=\"font-size: "
                          + Math.round(Theme.fontBody * 0.78) + "px\">Z</span> as the new Z0"
                    textFormat: Text.RichText
                    font: z0Check.font
                    color: profileCanvas.endPositionColor
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: z0Check.indicator.width + z0Check.spacing
                }
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                id: viewButtons
                canvas: profileCanvas
            }
        }
    }
}
