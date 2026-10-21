// ProfileRoughingVisualDetailsView.qml — Profile Roughing with a profile viewer.
// Saves every change through updateProfileRoughing.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "profile_canvas"
import theme 1.0

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
    // the tool the last Change Tool above puts in, as its Tool Library card
    // shows it: {tool_no, card, view}; {} with none
    property var    toolCard:    ({})

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property real   stockRadial: 0.0
    property real   stockAxial: 0.0
    property real   doc: 0.0
    property real   retract: 0.0
    property string passType: "axial"

    // what roughing will cut with the values above
    readonly property var roughingPreview: (opIndex >= 0 && primitives.length > 0 && editor)
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
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.doc = doc
        op.cutting_parameters.retract = retract
        op.profile_roughing_strategy = { profiling_type: profileType, pass_type: passType }
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
        toolCard    = editor ? (editor.toolCard || {}) : {}

        // X Start defaults to the profile's largest diameter plus the retract
        var pp = opData.profiling_parameters || {}
        var cp = opData.cutting_parameters || {}
        var st = opData.stock_to_leave || {}
        var savedX = pp.x_start !== undefined ? Number(pp.x_start) : 0
        retract = cp.retract !== undefined ? Number(cp.retract) : 0
        doc     = cp.doc !== undefined ? Number(cp.doc) : 0
        xStart  = savedX !== 0 ? savedX : _maxProfileDiameter() + retract
        zStart  = pp.z_start !== undefined ? Number(pp.z_start) : 0
        stockRadial = st.radial !== undefined ? Number(st.radial) : 0
        stockAxial  = st.axial !== undefined ? Number(st.axial) : 0
        var strategy = opData.profile_roughing_strategy || {}
        passType = strategy.pass_type ? String(strategy.pass_type) : "axial"

        header.applyData(opData, cp.feed_rate)
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
            onSpindleEdited: function(spindle) {
                var op = root._draftOp()
                op.spindle_parameters = spindle
                root.save(op)
            }
            onFeedRateEdited: function(value) {
                var op = root._draftOp()
                op.cutting_parameters.feed_rate = value
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
            // the profile in the stock's outline colour and weight
            profileLineColor: "#6b7280"
            profileLineWidth: 1.5
            fitDiameterMargin: 10
            primitives:  root.primitives
            profileType: root.profileType
            workpiece:   root.workpiece
            startPosition: root.primitives.length > 0 ? { x: root.xStart, z: root.zStart } : null
            roughingPreview: root.roughingPreview
            startPositionArrowRect: startBox.rect
            stockToLeaveArrowRect:  stockBox.rect

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(strategyBox.implicitWidth, stockBox.implicitWidth,
                                                      docBox.implicitWidth, startBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            // top to bottom: strategy, stock to leave, Ap / retract, start -
            // the first at the top, the last at the bottom, the space between
            // them shared out equally
            readonly property real boxSpacing: (height - 2 * boxGap - strategyBox.height - stockBox.height
                                                - docBox.height - startBox.height) / 3
            fitInsetRight: root.primitives.length > 0 ? boxWidth + boxGap : 0

            ProfilingTypeBox {
                id: strategyBox
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                profilingType: root.profileType
                passType: root.passType
                onPassTypeEdited: function(value) { root.passType = value; root.save() }
            }

            StockToLeaveBox {
                id: stockBox
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: strategyBox.y + strategyBox.height + profileCanvas.boxSpacing
                labelColor: profileCanvas.stockToLeaveColor
                radial: root.stockRadial
                axial: root.stockAxial
                onRadialEdited: function(value) { root.stockRadial = value; root.save() }
                onAxialEdited: function(value) { root.stockAxial = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DepthOfCutBox {
                id: docBox
                visible: root.primitives.length > 0
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: stockBox.y + stockBox.height + profileCanvas.boxSpacing
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                doc: root.doc
                retract: root.retract
                onDocEdited: function(value) { root.doc = value; root.save() }
                onRetractEdited: function(value) { root.retract = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            StartPositionBox {
                id: startBox
                visible: profileCanvas.startPosition !== null
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: docBox.y + docBox.height + profileCanvas.boxSpacing
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
            ToolBox {
                id: toolBox
                x: (profileCanvas.width - width) / 2
                y: profileCanvas.boxGap
                toolCard: root.toolCard
                onClicked: toolPicker.open()
            }

            ToolPickerPopup {
                id: toolPicker

                toolsModel: root.editor ? root.editor.touchedOffTools : null
                contentWidth: root.width
                toolKinds: String(root.profileType).toLowerCase() === "id" ? ["Boring Tool"] : ["Turning Tool"]
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
