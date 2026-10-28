// ProfileContourVisualDetailsView.qml — Profile Contour with a profile viewer,
// laid out as Profile Roughing's. Saves every change through
// updateProfileContour.
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

    // the last profile defined above this operation
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})
    // the tool it cuts with, as its Tool Library card
    // shows it: editor.toolCard, a ToolCard; null with none
    property var    toolCard:    null

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property bool   stockEnabled: false
    property real   stockRadial: 0.0
    property real   stockAxial: 0.0
    property real   retract: 0.0

    // what the contour will cut with the values above
    readonly property var contourPreview: (opIndex >= 0 && primitives.length > 0 && editor)
                                          ? editor.preview(_draftOp())
                                          : null
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    Geometry { id: geom }

    function _maxProfileDiameter() {
        var b = geom.computeBounds(geom.resolvePrimitives(primitives))
        return b ? b.fXMax : 0
    }

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.profiling_parameters = op.profiling_parameters || {}
        op.profiling_parameters.x_start = xStart
        op.profiling_parameters.z_start = zStart
        op.stock_to_leave_enabled = stockEnabled
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.retract = retract
        op.profile_contour_strategy = { profiling_type: profileType }
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

        var profileOp = editor ? (editor.lastProfile || {}) : {}
        primitives  = JSON.parse(JSON.stringify(profileOp.profile_primitives || []))
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
        // the stock broken off right after the profile, as the Program
        // Header draws its stock - set before it is handed on
        var stock = JSON.parse(JSON.stringify(profileOp.workpiece || {}))
        stock.break_after_profile = true
        workpiece   = stock
        toolCard    = editor ? editor.toolCard : null

        // X Start defaults to the profile's largest diameter plus the retract
        var pp = opData.profiling_parameters || {}
        var cp = opData.cutting_parameters || {}
        var st = opData.stock_to_leave || {}
        var savedX = pp.x_start !== undefined ? Number(pp.x_start) : 0
        retract = cp.retract !== undefined ? Number(cp.retract) : 0
        xStart  = savedX !== 0 ? savedX : _maxProfileDiameter() + retract
        zStart  = pp.z_start !== undefined ? Number(pp.z_start) : 0
        stockEnabled = !!opData.stock_to_leave_enabled
        stockRadial = st.radial !== undefined ? Number(st.radial) : 0
        stockAxial  = st.axial !== undefined ? Number(st.axial) : 0

        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // each edit goes into the whole op with the canvas boxes' values;
        // Profile Contour has no M1, so that width is left empty
        OperationHeader {
            id: header
            hasM1: false
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
            startPositionArrowRect: startBox.rect
            stockToLeaveArrowRect:  root.stockEnabled ? stockBox.rect : null

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(stockCheck.implicitWidth, stockBox.implicitWidth,
                                                      retractBox.implicitWidth, startBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: root.primitives.length > 0 ? boxWidth + boxGap : 0

            // turns the stock to leave on and off, in its colour
            CheckBox {
                id: stockCheck
                visible: root.primitives.length > 0
                x: stockBox.x
                y: profileCanvas.boxGap
                text: "Stock to Leave"
                font.pixelSize: Theme.fontBody
                font.bold: true
                checked: root.stockEnabled
                onToggled: { root.stockEnabled = checked; root.save() }
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
                onRadialEdited: function(value) { root.stockRadial = value; root.save() }
                onAxialEdited: function(value) { root.stockAxial = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // a single pass: retract only, no depth of cut
            DepthOfCutBox {
                id: retractBox
                visible: root.primitives.length > 0
                showDoc: false
                x: profileCanvas.width - width - profileCanvas.boxGap
                // halfway between the stock to leave and start position boxes
                y: (stockBox.y + stockBox.height + startBox.y - height) / 2
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                retract: root.retract
                onRetractEdited: function(value) { root.retract = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            StartPositionBox {
                id: startBox
                visible: profileCanvas.startPosition !== null
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                xStart: root.xStart
                zStart: root.zStart
                onXStartEdited: function(value) { root.xStart = value; root.save() }
                onZStartEdited: function(value) { root.zStart = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
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
