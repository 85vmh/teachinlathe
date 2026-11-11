// ProfileContourVisualDetailsView.qml — Profile Contour with a profile viewer,
// laid out as Profile Roughing's. It keeps nothing of its own: all it shows
// is its editor's operation, and every change is the editor's edit, which
// the operation then shows.
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
    readonly property var _pp: op.profiling_parameters || ({})
    readonly property var _cp: op.cutting_parameters || ({})
    readonly property var _st: op.stock_to_leave || ({})

    // the last profile defined above this operation
    readonly property var _profileOp: editor.lastProfile || ({})
    readonly property var primitives: _profileOp.profile_primitives || []
    readonly property string profileType: _profileOp.profile_type !== undefined ? String(_profileOp.profile_type) : "od"
    // the stock broken off right after the profile, as the Program Header
    // draws its stock
    readonly property var workpiece: {
        var stock = JSON.parse(JSON.stringify(_profileOp.workpiece || {}))
        stock.break_after_profile = true
        return stock
    }
    // the tool it cuts with, as its Tool Library card shows it: editor.toolCard,
    // a ToolCard
    readonly property var toolCard: editor.toolCard

    // what the boxes on the canvas show; X Start the editor gives a value
    // from the profile when it has none
    readonly property real xStart: Number(_pp.x_start || 0)
    readonly property real zStart: Number(_pp.z_start || 0)
    readonly property bool stockEnabled: !!op.stock_to_leave_enabled
    readonly property real stockRadial: Number(_st.radial || 0)
    readonly property real stockAxial: Number(_st.axial || 0)
    readonly property real retract: Number(_cp.retract || 0)
    readonly property string finishDirection: op.profile_contour_strategy && op.profile_contour_strategy.finishing_direction
                                              ? op.profile_contour_strategy.finishing_direction : "towards_z_minus"
    readonly property bool isIdProfile: String(profileType).toLowerCase() === "id"

    // what the contour cuts
    readonly property var contourPreview: primitives.length > 0 ? editor.preview : null
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    function editProfiling(changes) { editor.edit({ profiling_parameters: changes }) }
    function editStock(changes) { editor.edit({ stock_to_leave: changes }) }

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Profile Contour has no M1, so that width is left empty
        OperationHeader {
            id: header
            editor: root.editor
            hasM1: false
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
            // the profile in the stock's outline colour and weight
            profileLineColor: "#6b7280"
            profileLineWidth: 1.5
            fitDiameterMargin: 10
            primitives:  root.primitives
            profileType: root.profileType
            workpiece:   root.workpiece
            startPosition: root.primitives.length > 0 ? { x: root.xStart, z: root.zStart } : null
            // the contour, thick with arrows the way it cuts; the stock to
            // leave, and its arrow, only while it is on
            roughingPreview: (!root.contourPreview || root.stockEnabled) ? root.contourPreview
                             : { profile: root.contourPreview.profile, offset: [],
                                 feeds: root.contourPreview.feeds, rapids: [] }
            startPositionArrowRect: null
            stockToLeaveArrowRect:  root.stockEnabled ? stockBox.rect : null

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The cards stack down the right edge, as on Profile Roughing.
            readonly property real boxWidth: Math.max(finishDirectionBox.implicitWidth,
                retractBox.implicitWidth, p1Box.implicitWidth, stockCheck.implicitWidth,
                stockBox.implicitWidth)
            readonly property real boxGap: profileCanvas.tickBand
            readonly property real firstBoxY: profileCanvas.tickBand
            fitInsetRight: root.primitives.length > 0 ? boxWidth + profileCanvas.tickBand : 0

            TurningFinishDirectionBox {
                id: finishDirectionBox
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.firstBoxY
                direction: root.finishDirection
                onDirectionEdited: function(value) {
                    root.editor.edit({ profile_contour_strategy: { profiling_type: root.profileType,
                                                                  finishing_direction: value } })
                }
            }

            DepthOfCutBox {
                id: retractBox
                visible: root.primitives.length > 0
                showDoc: false
                retractLabel: "Tool Clearance"
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: finishDirectionBox.y + finishDirectionBox.height + Theme.spacingSmall
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                retract: root.retract
                onRetractEdited: function(value) { root.editor.edit({ cutting_parameters: { retract: value } }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            TurningPointBox {
                id: p1Box
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: retractBox.y + retractBox.height + Theme.spacingSmall
                point: 1
                settingPrefix: "profile_contour"
                xValue: root.xStart
                zValue: root.zStart
                onFieldEdited: function(axis, value) {
                    root.editProfiling(axis === "x" ? { x_start: value } : { z_start: value })
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // turns the stock to leave on and off, in its colour
            ModelCheckBox {
                id: stockCheck
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: p1Box.y + p1Box.height + Theme.spacingSmall
                text: "Stock to Leave"
                font.pixelSize: Theme.fontBody
                font.bold: true
                checked: root.stockEnabled
                onToggledTo: function(on) { root.editor.edit({ stock_to_leave_enabled: on }) }
                contentItem: Text {
                    text: stockCheck.text
                    font: stockCheck.font
                    color: profileCanvas.stockToLeaveColor
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: stockCheck.indicator.width + stockCheck.spacing
                }
            }

            StockToLeaveBox {
                id: stockBox
                visible: root.primitives.length > 0
                enabled: root.stockEnabled
                opacity: root.stockEnabled ? 1.0 : 0.5
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: stockCheck.y + stockCheck.height + Theme.spacingSmall
                labelColor: profileCanvas.stockToLeaveColor
                radial: root.stockRadial
                axial: root.stockAxial
                onRadialEdited: function(value) { root.editStock({ radial: value }) }
                onAxialEdited: function(value) { root.editStock({ axial: value }) }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            readonly property real p1TagOffset: 56
            readonly property real p1TagX: root.isIdProfile
                ? _cx(root.zStart) + p1TagOffset
                : _cx(root.zStart) - p1TagOffset - p1Tag.width
            readonly property real p1TagY: _cy(root.xStart) + p1TagOffset
            markers: root.primitives.length > 0 ? [
                { leader: true, x: root.xStart, z: root.zStart, color: "#1565c0",
                  toZ: root.zStart, dx: root.isIdProfile ? p1TagOffset : -p1TagOffset, slope: 1 }
            ] : []
            Radial.GroovePointTag {
                id: p1Tag
                visible: root.primitives.length > 0
                point: 1
                axes: "XZ"
                x: profileCanvas.p1TagX
                y: profileCanvas.p1TagY - height / 2
            }

            // the tool - a turning tool's insert or a blade - its control
            // point on the start position, turned as its orientation has it,
            // inside the ticks; in the fit too
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var pts = canvasTool.outlineFromTip, out = []
                for (var i = 0; i < pts.length; i++)
                    out.push({ x: root.xStart + 2 * pts[i].y, z: root.zStart + pts[i].x })
                return out
            }
            onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
            CanvasTool {
                id: canvasTool
                inset: profileCanvas.tickBand
                card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                pxPerMm: profileCanvas._scale
                tipX: profileCanvas._cx(root.zStart)
                tipY: profileCanvas._cy(root.xStart)
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - a turning tool for an OD profile, a boring bar for
            // an ID one
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
                visible: root.primitives.length > 0
            }

            Label {
                anchors.centerIn: parent
                visible: root.primitives.length === 0
                text: "No profile defined above this operation"
                color: Theme.foregroundMuted
                font.pixelSize: Theme.fontBody
            }
        }
    }
}
