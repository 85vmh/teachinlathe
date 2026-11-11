// DrillingVisualDetailsView.qml — Drilling on the profile canvas, laid out
// as Facing's: the header's stock, and on the center line the drill it
// cuts with, its point at Z Start + Clearance, where it
// starts and every peck retracts to. Its values in boxes down the right
// edge; Z Start, Z End and the clearance's Z each drawn as a line across the
// centre line, with an arrow from it to its box; each peck as the drill's
// point, one of them dimensioned, to the Peck Depth / Dwell Time box.
// It keeps nothing of its own: all it shows is its editor's operation, and
// every change is the editor's edit, which the operation then shows.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    readonly property var _dp: op.drilling_parameters || ({})

    // the program header's stock
    readonly property var workpiece: editor.workpiece || ({})
    // the drill it cuts with: editor.drill (a DrillingToolView), null with none
    readonly property var drill: editor.drill

    // what the boxes on the canvas show
    readonly property real zStart: Number(_dp.z_start || 0)
    readonly property real zEnd: Number(_dp.z_end || 0)
    readonly property real toolClearance: Math.abs(Number(_dp.tool_clearance || 0))
    readonly property real peckDepth: Number(_dp.peck_depth || 0)
    readonly property real dwellTime: Number(_dp.dwell_time || 0)
    // where the drill starts and every peck retracts to
    readonly property real retractZ: zStart + toolClearance

    // the boxes' and their targets' colours
    readonly property color zStartColor:   "#1565c0"
    readonly property color zEndColor:     profileCanvas.endPositionColor
    readonly property color clearanceColor: "#00838f"
    readonly property color peckColor:     profileCanvas.feedColor
    signal openNumPadRequested(var field)

    // what drilling cuts: a feed each peck
    readonly property var drillingPreview: editor.preview

    // a change to the drilling_parameters: only the fields in ``changes``
    function editDrilling(changes) {
        editor.edit({ drilling_parameters: changes })
    }

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Drilling runs in RPM only; its feed rate is the drilling_parameters'
        OperationHeader {
            id: header
            editor: root.editor
            rpmOnly: true
            // Pause to Inspect may also stay where the tool is
            allowStayInPlace: true
            // only the way the tool in turns
            onlyClockwise: root.drill ? root.drill.clockwise : null
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
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
            axialDrill: root.drill
            axialToolZ: root.retractZ
            // where each peck ends: the end of each feed of the G-code
            axialToolPecks: root.drillingPreview
                            ? root.drillingPreview.feeds.map(function(f) { return f.z1 }) : []
            axialToolPeckColor: root.peckColor
            axialToolPecksFrom: root.zStart
            // one peck's depth - the full peck nearest halfway between Z
            // Start and Z End, between the arms' ends of the Vs at its ends
            // (Z Start for the first) - under the drill's lower edge, its
            // leader from its middle to the Peck Depth box
            dimensions: peckDimensions.concat(clearanceDimension ? [clearanceDimension] : [])
            readonly property var peckDimensions: {
                var pecks = axialToolPecks
                var d = root.drill ? Number(root.drill.diameter) : 0
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
            readonly property real zLineDiameter: (root.drill ? Number(root.drill.diameter) : 10) * 1.6
            markers: [
                { line: true, x: zLineDiameter, z: root.zStart, color: root.zStartColor },
                { line: true, x: zLineDiameter, z: root.zEnd, color: root.zEndColor },
                // From the same upper ends of the Z markers, point at the
                // P1Z/P2Z tags on a 45-degree up-right leader.
                { leader: true, x: -zLineDiameter, z: root.zStart, color: root.zStartColor,
                  toZ: root.zStart, dx: 56, slope: -1 },
                { leader: true, x: -zLineDiameter, z: root.zEnd, color: root.zEndColor,
                  toZ: root.zEnd, dx: 56, slope: -1 },
                // its arrow to the box is the clearance dimension's
                { line: true, x: zLineDiameter, z: root.retractZ, color: root.clearanceColor, arrowToRect: null }
            ]
            readonly property real pointTagOffset: 56
            readonly property real p1TagX: _cx(root.zStart) + pointTagOffset
            readonly property real p1TagY: _cy(-zLineDiameter) - pointTagOffset - p1Tag.height
            readonly property real p2TagX: _cx(root.zEnd) + pointTagOffset
            readonly property real p2TagY: _cy(-zLineDiameter) - pointTagOffset - p2Tag.height
            Radial.GroovePointTag {
                id: p1Tag
                point: 1
                axes: "Z"
                x: profileCanvas.p1TagX
                y: profileCanvas.p1TagY
            }
            Radial.GroovePointTag {
                id: p2Tag
                point: 2
                axes: "Z"
                accent: profileCanvas.endPositionColor
                x: profileCanvas.p2TagX
                y: profileCanvas.p2TagY
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(zStartBox.implicitWidth, zEndBox.implicitWidth,
                                                      clearanceBox.implicitWidth, peckBox.implicitWidth)
            readonly property real boxGap: profileCanvas.tickBand
            fitInsetRight: boxWidth + profileCanvas.tickBand

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
                label: "P1Z"
                pointLabel: true
                point: 1
                settingName: "drilling.z_start"
                value: root.zStart
                onValueEdited: function(value) { root.editDrilling({ z_start: value }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: zEndBox
                width: profileCanvas.zBoxWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: zStartBox.y + zStartBox.height + profileCanvas.boxGap
                accent: root.zEndColor
                label: "P2Z"
                pointLabel: true
                point: 2
                settingName: "drilling.z_end"
                value: root.zEnd
                onValueEdited: function(value) { root.editDrilling({ z_end: value }) }
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
                onValueEdited: function(value) { root.editDrilling({ tool_clearance: Math.abs(value) }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            PeckBox {
                id: peckBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.tickBand
                color: root.peckColor
                peckDepth: root.peckDepth
                dwellTime: root.dwellTime
                onPeckDepthEdited: function(value) { root.editDrilling({ peck_depth: value }) }
                onDwellTimeEdited: function(value) { root.editDrilling({ dwell_time: value }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - only a drill
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
