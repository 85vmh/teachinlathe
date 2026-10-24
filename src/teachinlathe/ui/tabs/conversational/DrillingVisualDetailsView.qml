// DrillingVisualDetailsView.qml — Drilling on the profile canvas, laid out
// as Facing's: the header's stock, and on the centre line the drill the last
// Change Tool above puts in, its point at Z Start + Clearance, where it
// starts and every peck retracts to. Its values in boxes down the right
// edge; Z Start, Z End and the clearance's Z each drawn as a line across the
// centre line, with an arrow from it to its box; each peck as the drill's
// point, one of them dimensioned, to the Peck Depth / Dwell Time box. Saves
// every change through updateDrilling.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the program header's stock, and the tool in when this drills
    property var    workpiece: ({})
    property var    tool: ({})
    // the same tool as its Tool Library card shows it: {tool_no, card,
    // view}; {} with none
    property var    toolCard: ({})

    // the values the boxes on the canvas show and edit
    property real   zStart: 0.0
    property real   zEnd: 0.0
    property real   toolClearance: 0.0
    property real   peckDepth: 0.0
    property real   dwellTime: 0.0
    // where the drill starts and every peck retracts to
    readonly property real retractZ: zStart + Math.abs(toolClearance)

    // the boxes' and their targets' colours
    readonly property color zStartColor:   "#1565c0"
    readonly property color zEndColor:     profileCanvas.endPositionColor
    readonly property color clearanceColor: "#00838f"
    readonly property color peckColor:     profileCanvas.feedColor
    signal openNumPadRequested(var field)

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.drilling_parameters = op.drilling_parameters || {}
        op.drilling_parameters.z_start = zStart
        op.drilling_parameters.z_end = zEnd
        op.drilling_parameters.tool_clearance = Math.abs(toolClearance)
        op.drilling_parameters.peck_depth = peckDepth
        op.drilling_parameters.dwell_time = dwellTime
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
        tool      = editor ? (editor.tool || {}) : {}
        toolCard  = editor ? (editor.toolCard || {}) : {}

        var dp = opData.drilling_parameters || {}
        zStart    = dp.z_start    !== undefined ? Number(dp.z_start)    : 0
        zEnd      = dp.z_end      !== undefined ? Number(dp.z_end)      : 0
        toolClearance = dp.tool_clearance !== undefined ? Math.abs(Number(dp.tool_clearance)) : 0
        peckDepth = dp.peck_depth !== undefined ? Number(dp.peck_depth) : 0
        dwellTime = dp.dwell_time !== undefined ? Number(dp.dwell_time) : 0

        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Drilling runs in RPM only; its feed rate is the drilling_parameters'
        OperationHeader {
            id: header
            rpmOnly: true
            // Pause to Inspect may also stay where the tool is
            allowStayInPlace: true
            // only the way the tool in turns
            onlyClockwise: root.tool && root.tool.spindle_direction === 3 ? true
                         : root.tool && root.tool.spindle_direction === 4 ? false : null
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
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            // the drill and the stock whole, both halves
            mirrorAcrossCenterline: true
            // fitted to the stock, the drill's point in; its body runs on
            // off the right edge as far as it is long
            fitAxialToolLength: false
            // a dot at both ends of each arrow to a box
            arrowStartDots: true
            primitives: []
            // the header's stock, broken off after Z End as Facing's
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                w.break_after_z = root.zEnd
                return w
            }
            // the drill in, its point where it starts; none when it is not a drill
            axialTool: root.tool && root.tool.kind === "drill"
                       ? { kind: "drill", diameter: root.tool.diameter, tip_angle: root.tool.tip_angle,
                           right_hand: root.tool.right_hand, z: root.retractZ }
                       : null
            // where each peck ends: every Peck Depth on from Z Start while
            // short of Z End, and the last at Z End
            axialToolPecks: {
                var out = []
                if (root.peckDepth > 0)
                    for (var z = root.zStart - root.peckDepth; z > root.zEnd + 1e-6 && out.length < 1000;
                         z -= root.peckDepth)
                        out.push(z)
                if (root.zEnd < root.zStart) out.push(root.zEnd)
                return out
            }
            axialToolPeckColor: root.peckColor
            axialToolPecksFrom: root.zStart
            // one peck's depth - the full peck nearest halfway between Z
            // Start and Z End, between the arms' ends of the Vs at its ends
            // (Z Start for the first) - under the drill's lower edge, its
            // leader from its middle to the Peck Depth box
            dimensions: peckDimensions.concat(clearanceDimension ? [clearanceDimension] : [])
            readonly property var peckDimensions: {
                var pecks = axialToolPecks
                var d = root.tool && root.tool.kind === "drill" ? Number(root.tool.diameter) : 0
                if (!(d > 0) || !(root.peckDepth > 0) || pecks.length === 0) return []
                var ends = [root.zStart].concat(pecks), full = []
                for (var i = 0; i + 1 < ends.length; i++)
                    if (Math.abs(ends[i] - ends[i + 1] - root.peckDepth) < 1e-6) full.push(i)
                if (full.length === 0) return []
                var middle = (root.zStart + root.zEnd) / 2, k = full[0]
                for (var j = 1; j < full.length; j++) {
                    var c = (ends[full[j]] + ends[full[j] + 1]) / 2
                    if (Math.abs(c - middle) < Math.abs((ends[k] + ends[k + 1]) / 2 - middle)) k = full[j]
                }
                var a = ends[k], b = ends[k + 1]
                var point = drillPoint
                return [{ axis: "z", from: b + point, to: a + point, x: d,
                          // below the Z lines' lower ends, clear of the clearance's
                          offset: (zLineDiameter - d) / 2 * _scale + 28,
                          color: root.peckColor, arrowToRect: peckBox.rect, leaderAt: 0.5,
                          arrowsOutside: true }]
            }
            // the clearance, between the Z Start and Clearance lines at their
            // lower ends, its leader from its middle to the Clearance box
            readonly property var clearanceDimension: root.toolClearance > 0
                ? { axis: "z", from: root.zStart, to: root.retractZ, x: zLineDiameter, offset: 0,
                    color: root.clearanceColor, arrowToRect: clearanceBox.rect, leaderAt: 0.5,
                    arrowsOutside: true, noExtensionLines: true }
                : null
            // how far the drill's point reaches back from its tip, in mm
            readonly property real drillPoint: axialTool ? axialToolPeckBack() : 0
            // at each Z, a line across the centre line longer than the
            // drill is wide, an arrow from it to its box; Peck Depth none yet
            readonly property real zLineDiameter: (root.tool && root.tool.kind === "drill"
                                                   && Number(root.tool.diameter) > 0
                                                   ? Number(root.tool.diameter) : 10) * 1.6
            markers: [
                { line: true, x: zLineDiameter, z: root.zStart,   color: root.zStartColor,   arrowToRect: zStartBox.rect },
                { line: true, x: zLineDiameter, z: root.zEnd,     color: root.zEndColor,     arrowToRect: zEndBox.rect },
                // its arrow to the box is the clearance dimension's
                { line: true, x: zLineDiameter, z: root.retractZ, color: root.clearanceColor, arrowToRect: null }
            ]

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(zStartBox.implicitWidth, zEndBox.implicitWidth,
                                                      clearanceBox.implicitWidth, peckBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            // two pairs, a gap apart within each: Z Start over Z End at the
            // top, as wide as each other; Clearance over Peck Depth at the
            // bottom
            readonly property real zBoxWidth: Math.max(zStartBox.implicitWidth, zEndBox.implicitWidth)

            ZPositionBox {
                id: zStartBox
                width: profileCanvas.zBoxWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                accent: root.zStartColor
                label: "Z Start"
                settingName: "drilling.z_start"
                value: root.zStart
                onValueEdited: function(value) { root.zStart = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: zEndBox
                width: profileCanvas.zBoxWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: zStartBox.y + zStartBox.height + profileCanvas.boxGap
                accent: root.zEndColor
                label: "Z End"
                settingName: "drilling.z_end"
                value: root.zEnd
                onValueEdited: function(value) { root.zEnd = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // how far in front of Z Start the drill starts and retracts to:
            // a length, never negative, so no TeachIn
            DimensionBox {
                id: clearanceBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: peckBox.y - height - profileCanvas.boxGap
                label: "Clearance"
                dimensionColor: root.clearanceColor
                settingName: "drilling.tool_clearance"
                value: root.toolClearance
                onValueEdited: function(value) { root.toolClearance = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            PeckBox {
                id: peckBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                color: root.peckColor
                peckDepth: root.peckDepth
                dwellTime: root.dwellTime
                onPeckDepthEdited: function(value) { root.peckDepth = value; root.save() }
                onDwellTimeEdited: function(value) { root.dwellTime = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - only a drill
            ToolBox {
                id: toolBox
                x: (profileCanvas.width - width) / 2
                // lined up with the view buttons, as tall as they are
                y: viewButtons.y
                rowHeight: viewButtons.height
                toolCard: root.toolCard
                onClicked: toolPicker.open()
            }

            ToolPickerPopup {
                id: toolPicker

                toolsModel: root.editor ? root.editor.touchedOffTools : null
                contentWidth: root.width
                toolKinds: ["Drill Tool"]
                currentToolNo: root.toolCard && root.toolCard.tool_no ? root.toolCard.tool_no : 0
                currentToolchangePosition: root.toolCard && root.toolCard.toolchange_position
                                           ? root.toolCard.toolchange_position : "G28"
                onToolChosen: function(toolNo, position) {
                    if (root.editor)
                        root.editor.useTool(toolNo, position)
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
