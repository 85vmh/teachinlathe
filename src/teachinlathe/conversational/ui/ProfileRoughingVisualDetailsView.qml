// ProfileRoughingVisualDetailsView.qml — Profile Roughing with a profile viewer.
// Edits the same data as ProfileRoughingDetailsView and saves every change
// through the same updateProfileRoughing slot.
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

    // the last profile defined above this operation
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property real   stockRadial: 0.0
    property real   stockAxial: 0.0
    property real   doc: 0.0
    property real   retract: 0.0
    property string passType: "axial"

    // what roughing will cut with the values above
    readonly property var roughingPreview: (opIndex >= 0 && primitives.length > 0
                                            && typeof conversationalQml !== "undefined" && conversationalQml)
                                           ? conversationalQml.profileRoughingPreview(opIndex, _draftOp())
                                           : null

    signal saveRequested(var updated)
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
        root.saveRequested({index: opIndex, payload: opData})
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}

        var profileOp = (typeof conversationalQml !== "undefined" && conversationalQml)
                        ? (conversationalQml.lastProfileBefore(index) || {}) : {}
        primitives  = JSON.parse(JSON.stringify(profileOp.profile_primitives || []))
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
        workpiece   = JSON.parse(JSON.stringify(profileOp.workpiece || {}))

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
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
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
