// TappingVisualDetailsView.qml — Tapping on the profile canvas, laid out
// as Drilling's: the header's stock, and on the centre line the tap it
// cuts with, its point at Z Start + Clearance, where it
// starts and every peck comes back to. Its pitch is the tap's, not edited
// here. Its values in boxes down the right edge; Z Start, Z End and the
// clearance's Z each drawn as a line across the centre line; each peck as a
// line across the tap's diameter, one of them dimensioned. It keeps nothing
// of its own: all it shows is its editor's operation, and every change is
// the editor's edit, which the operation then shows.
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
    // the one place what the view shows comes from, and every edit goes to;
    // it keeps the tap's pitch in the operation
    required property var editor
    readonly property var op: editor.operation
    readonly property var _tp: op.tapping_parameters || ({})

    // the program header's stock
    readonly property var workpiece: editor.workpiece || ({})
    // the tap it cuts with: editor.tap (a TappingToolView), null with none
    readonly property var tap: editor.tap
    // the same tool as its Tool Library card shows it: editor.toolCard, a ToolCard
    readonly property var toolCard: editor.toolCard

    // what the boxes on the canvas show
    readonly property real zStart: Number(_tp.z_start || 0)
    readonly property real zEnd: Number(_tp.z_end || 0)
    readonly property real toolClearance: Math.abs(Number(_tp.tool_clearance || 0))
    readonly property real peckDepth: Number(_tp.peck_depth || 0)
    // where the tap starts and every peck comes back to
    readonly property real retractZ: zStart + toolClearance

    // the boxes' and their targets' colours
    readonly property color zStartColor:   "#1565c0"
    readonly property color zEndColor:     profileCanvas.endPositionColor
    readonly property color clearanceColor: "#00838f"
    readonly property color peckColor:     profileCanvas.feedColor
    signal openNumPadRequested(var field)

    function editTapping(changes) { editor.edit({ tapping_parameters: changes }) }

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Tapping runs in RPM only, and the pitch sets its feed: the
        // header's feed rate is left disabled
        OperationHeader {
            id: header
            editor: root.editor
            rpmOnly: true
            // Pause to Inspect may also stay where the tool is
            allowStayInPlace: true
            // only the way the tool in turns
            onlyClockwise: root.tap ? root.tap.clockwise : null
            feedEnabled: false
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
            // the tap and the stock whole, both halves
            mirrorAcrossCenterline: true
            // fitted to the stock, the tap's point in; its body runs on off
            // the right edge as far as it is long
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
            // the tap in, its point where it starts; none when it is not a tap
            axialTap: root.tap
            axialToolZ: root.retractZ
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
            // Start and Z End, between the marks at its ends - under the
            // tap's lower edge, its
            // leader from its middle to the Peck Depth box
            dimensions: peckDimensions.concat(clearanceDimension ? [clearanceDimension] : [])
            readonly property var peckDimensions: {
                var pecks = axialToolPecks
                var d = root.tap ? Number(root.tap.diameter) : 0
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
                return [{ axis: "z", from: b, to: a, x: d,
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
            // at each Z, a line across the centre line longer than the tap
            // is wide, an arrow from it to its box
            readonly property real zLineDiameter: (root.tap ? Number(root.tap.diameter) : 10) * 1.6
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
                settingName: "tapping.z_start"
                value: root.zStart
                onValueEdited: function(value) { root.editTapping({ z_start: value }) }
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
                settingName: "tapping.z_end"
                value: root.zEnd
                onValueEdited: function(value) { root.editTapping({ z_end: value }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // how far in front of Z Start the tap starts and comes back to:
            // a length, never negative, so no TeachIn
            DimensionBox {
                id: clearanceBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: peckBox.y - height - profileCanvas.boxGap
                label: "Clearance"
                dimensionColor: root.clearanceColor
                settingName: "tapping.tool_clearance"
                value: root.toolClearance
                onValueEdited: function(value) { root.editTapping({ tool_clearance: Math.abs(value) }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: peckBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                label: "Peck Depth"
                dimensionColor: root.peckColor
                settingName: "tapping.peck_depth"
                value: root.peckDepth
                onValueEdited: function(value) { root.editTapping({ peck_depth: value }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - only a tap
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
