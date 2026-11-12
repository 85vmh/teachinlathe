// FacingVisualDetailsView.qml — Facing on the profile canvas, laid out as
// Profile Roughing's: no profile, so the passes are drawn over the header's
// stock, from the start position to the end position. It keeps nothing of
// its own: all it shows is its editor's operation, and every change is the
// editor's edit, which the operation then shows.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial
import common

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    readonly property var _gp: op.geometry_parameters || ({})
    readonly property var _cp: op.cutting_parameters || ({})

    // the program header's stock
    readonly property var workpiece: editor.workpiece || ({})
    // the tool it cuts with, as its Tool Library card shows it: editor.toolCard,
    // a ToolCard
    readonly property var toolCard: editor.toolCard

    // what the boxes on the canvas show
    readonly property real xStart: Number(_gp.x_start || 0)
    readonly property real zStart: Number(_gp.z_start || 0)
    readonly property real xEnd: Number(_gp.x_end || 0)
    readonly property real zEnd: Number(_gp.z_end || 0)
    readonly property real doc: Number(_cp.doc || 0)
    readonly property real toolClearance: Number(_cp.retract || 0)
    readonly property bool zEndBecomesNewZ0: !!op.z_end_becomes_new_z0
    readonly property real stockDiameter: Number(workpiece && workpiece.external_diameter) > 0
                                          ? Number(workpiece.external_diameter) : Math.abs(xStart)

    // what facing cuts
    readonly property var facingPreview: editor.preview
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    function editGeometry(changes) { editor.edit({ geometry_parameters: changes }) }
    function editCutting(changes) { editor.edit({ cutting_parameters: changes }) }

    // another operation: the drawing fitted to it, mirrored as the editor
    // keeps it for every Facing
    function _showEditor() {
        profileCanvas.mirrorAcrossCenterline = editor.canvasMirror
        profileCanvas.resetView()
    }
    onEditorChanged: _showEditor()
    Component.onCompleted: _showEditor()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        OperationHeader {
            id: header
            editor: root.editor
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
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

            // the mirror button changes it here; the editor keeps it for the next Facing
            onMirrorAcrossCenterlineChanged: root.editor.canvasMirror = mirrorAcrossCenterline

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
                onRetractEdited: function(value) { root.editCutting({ retract: value }) }
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
                    root.editGeometry(axis === "x" ? { x_start: value } : { z_start: value })
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
                onDocEdited: function(value) { root.editCutting({ doc: value }) }
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
                    root.editGeometry(axis === "x" ? { x_end: value } : { z_end: value })
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ModelCheckBox {
                id: z0Check
                x: profileCanvas.width - width - profileCanvas.tickBand
                y: endBox.y + endBox.height + Theme.spacingSmall
                text: "Set P2Z as the new Z0"
                font.pixelSize: Theme.fontBody
                font.bold: false
                checked: root.zEndBecomesNewZ0
                onToggledTo: function(on) { root.editor.edit({ z_end_becomes_new_z0: on }) }
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
