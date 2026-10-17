// DrillingVisualDetailsView.qml — Drilling on the profile canvas, laid out
// as Facing's: the header's stock, and on the centre line the drill the last
// Change Tool above puts in, its point at Z Start. Its four values in boxes
// down the right edge; each Z drawn as a line across the centre line, with
// an arrow from it to its box. Edits the same data as DrillingDetailsView
// and saves every change through the same updateDrilling slot.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "profile_canvas"
import theme 1.0

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    // the program header's stock, and the tool in when this drills
    property var    workpiece: ({})
    property var    tool: ({})

    // the values the boxes on the canvas show and edit
    property real   zStart: 0.0
    property real   zEnd: 0.0
    property real   zRetract: 0.0
    property real   peckDepth: 0.0

    // the boxes' and their targets' colours
    readonly property color zStartColor:   "#1565c0"
    readonly property color zEndColor:     profileCanvas.endPositionColor
    readonly property color zRetractColor: "#00838f"
    readonly property color peckColor:     profileCanvas.feedColor

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.drilling_parameters = op.drilling_parameters || {}
        op.drilling_parameters.z_start = zStart
        op.drilling_parameters.z_end = zEnd
        op.drilling_parameters.z_retract = zRetract
        op.drilling_parameters.peck_depth = peckDepth
        return op
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || _draftOp()
        root.saveRequested({index: opIndex, payload: opData})
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}

        var bridge = (typeof conversationalQml !== "undefined" && conversationalQml) ? conversationalQml : null
        workpiece = bridge ? (bridge.currentWorkpiece() || {}) : {}
        tool      = bridge ? (bridge.toolBefore(index) || {}) : {}

        var dp = opData.drilling_parameters || {}
        zStart    = dp.z_start    !== undefined ? Number(dp.z_start)    : 0
        zEnd      = dp.z_end      !== undefined ? Number(dp.z_end)      : 0
        zRetract  = dp.z_retract  !== undefined ? Number(dp.z_retract)  : 0
        peckDepth = dp.peck_depth !== undefined ? Number(dp.peck_depth) : 0

        header.applyData(opData, dp.feed_rate)
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
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpindleEdited: function(spindle) {
                var op = root._draftOp()
                op.spindle_parameters = spindle
                root.save(op)
            }
            onFeedRateEdited: function(value) {
                var op = root._draftOp()
                op.drilling_parameters.feed_rate = value
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
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            // the drill and the stock whole, both halves
            mirrorAcrossCenterline: true
            primitives: []
            // the header's stock, broken off after Z End as Facing's
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                w.break_after_z = root.zEnd
                return w
            }
            // the drill in, its point at Z Start; none when it is not a drill
            drill: root.tool && root.tool.kind === "drill"
                   ? { diameter: root.tool.diameter, tip_angle: root.tool.tip_angle,
                       right_hand: root.tool.right_hand, z: root.zStart }
                   : null
            // where each peck ends: every Peck Depth on from Z Start while
            // short of Z End, and the last at Z End
            drillPecks: {
                var out = []
                if (root.peckDepth > 0)
                    for (var z = root.zStart - root.peckDepth; z > root.zEnd + 1e-6 && out.length < 1000;
                         z -= root.peckDepth)
                        out.push(z)
                if (root.zEnd < root.zStart) out.push(root.zEnd)
                return out
            }
            drillPeckColor: root.peckColor
            drillPecksFrom: root.zStart
            // one peck's depth, between the arms' ends of the first two Vs -
            // or Z Start and the first, when there is only one full peck -
            // under the drill's lower edge, its leader from its middle to
            // the Peck Depth box
            dimensions: {
                var pecks = drillPecks
                var d = root.tool && root.tool.kind === "drill" ? Number(root.tool.diameter) : 0
                if (!(d > 0) || !(root.peckDepth > 0) || pecks.length === 0) return []
                var a, b
                if (pecks.length >= 2 && Math.abs(pecks[0] - pecks[1] - root.peckDepth) < 1e-6) {
                    a = pecks[0]; b = pecks[1]
                } else if (Math.abs(root.zStart - pecks[0] - root.peckDepth) < 1e-6) {
                    a = root.zStart; b = pecks[0]
                } else {
                    return []
                }
                var point = drillPoint
                return [{ axis: "z", from: b + point, to: a + point, x: d,
                          offset: 28, color: root.peckColor, arrowToRect: peckBox.rect, leaderAt: 0.5 }]
            }
            // how far the drill's point reaches back from its tip, in mm
            readonly property real drillPoint: {
                if (!(root.tool && root.tool.kind === "drill")) return 0
                var r = Number(root.tool.diameter) / 2
                var angle = root.tool.tip_angle !== undefined ? Number(root.tool.tip_angle) : 118
                return angle >= 179.999 ? 0 : r / Math.tan(angle / 2 * Math.PI / 180)
            }
            // at each Z, a line across the centre line longer than the
            // drill is wide, an arrow from it to its box; Peck Depth none yet
            readonly property real zLineDiameter: (root.tool && root.tool.kind === "drill"
                                                   && Number(root.tool.diameter) > 0
                                                   ? Number(root.tool.diameter) : 10) * 1.6
            markers: [
                { line: true, x: zLineDiameter, z: root.zStart,   color: root.zStartColor,   arrowToRect: zStartBox.rect },
                { line: true, x: zLineDiameter, z: root.zEnd,     color: root.zEndColor,     arrowToRect: zEndBox.rect },
                { line: true, x: zLineDiameter, z: root.zRetract, color: root.zRetractColor, arrowToRect: zRetractBox.rect }
            ]

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(zStartBox.implicitWidth, zEndBox.implicitWidth,
                                                      zRetractBox.implicitWidth, peckBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            // top to bottom: Z Start, Z End, Z Retract, Peck Depth - the
            // first at the top, the last at the bottom, the space between
            // them shared out equally
            readonly property real boxSpacing: (height - 2 * boxGap - zStartBox.height - zEndBox.height
                                                - zRetractBox.height - peckBox.height) / 3

            ZPositionBox {
                id: zStartBox
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
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: zStartBox.y + zStartBox.height + profileCanvas.boxSpacing
                accent: root.zEndColor
                label: "Z End"
                settingName: "drilling.z_end"
                value: root.zEnd
                onValueEdited: function(value) { root.zEnd = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: zRetractBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: zEndBox.y + zEndBox.height + profileCanvas.boxSpacing
                accent: root.zRetractColor
                label: "Z Retract"
                settingName: "drilling.z_retract"
                value: root.zRetract
                onValueEdited: function(value) { root.zRetract = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: peckBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                label: "Peck Depth"
                dimensionColor: root.peckColor
                settingName: "drilling.peck_depth"
                value: root.peckDepth
                onValueEdited: function(value) { root.peckDepth = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: profileCanvas
            }
        }
    }
}
