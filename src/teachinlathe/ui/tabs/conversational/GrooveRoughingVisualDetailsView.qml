// GrooveRoughingVisualDetailsView.qml — Groove Roughing on the groove's
// canvas (GrooveCanvas), laid out as Profile Roughing: the blade where it
// starts - over its first plunge, the clearance out from the start diameter -
// its outline over the second, and the boxes down the right edge: its own
// parameters (GroovingBox), the stock to leave, the clearance as Parting has
// it, the peck depth and dwell time as Drilling has them, each dimensioned on
// the canvas.
import QtQuick
import QtQuick.Layouts
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the radial profile it roughs, and the header's stock
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})
    // the tool the last Change Tool above puts in: {tool_no, card, view}; {} with none
    property var    toolCard:    ({})

    // what an operation saved without a value has: a new one's, as
    // conversational/model/factories.py makes it
    readonly property var defaults: ({
        profileId: 1, strategy: "start_center", initialOffset: 1.5, afterwardsOffset: 1.0,
        retract: 1.0, peckDepth: 3.0, dwellTime: 0.5
    })

    // the values the boxes on the canvas show and edit
    property int    profileId: defaults.profileId
    property string strategy: defaults.strategy
    property real   initialOffset: defaults.initialOffset
    property real   afterwardsOffset: defaults.afterwardsOffset
    property real   retract: defaults.retract
    property real   peckDepth: defaults.peckDepth
    property real   dwellTime: defaults.dwellTime
    property real   stockRadial: 0.0
    property real   stockAxial: 0.0

    readonly property bool hasGroove: profileCanvas.hasGroove
    // the plunges, in the order the G-code makes them; the groove's middle
    // until there is a plan
    readonly property var plunges: {
        if (groovePreview && groovePreview.plunges && groovePreview.plunges.length > 0)
            return groovePreview.plunges
        var p = profileCanvas.groovePoints
        return p.length === 4 ? [(p[0].z + p[3].z) / 2] : []
    }
    // where the blade starts: over its first plunge, the clearance out from
    // the start diameter - the groove's mouth with the radial stock to leave
    // on it - as the G-code goes there
    readonly property var startPosition: plunges.length > 0 && groovePreview && groovePreview.bladeX != null
        ? { z: plunges[0], x: groovePreview.bladeX } : null
    readonly property color peckColor: profileCanvas.feedColor

    // what it will cut with the values above: the pecks and the finish
    // contour of its G-code, and the stock to leave
    readonly property var groovePreview: (opIndex >= 0 && hasGroove && editor)
                                         ? editor.preview(_draftOp()) : null

    signal openNumPadRequested(var field)

    function _loadProfile() {
        var profileOp = editor ? (editor.radialProfile(profileId) || {}) : {}
        primitives  = JSON.parse(JSON.stringify(profileOp.profile_primitives || []))
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
    }

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.roughing_parameters = {
            profile_id: profileId, strategy: strategy,
            initial_offset: initialOffset, afterwards_offset: afterwardsOffset
        }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.peck_depth = peckDepth
        op.cutting_parameters.retract = retract
        op.cutting_parameters.dwell_time = dwellTime
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        op.stock_to_leave_enabled = stockRadial > 0 || stockAxial > 0
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
        toolCard  = editor ? (editor.toolCard || {}) : {}

        var rp = opData.roughing_parameters || {}
        var cp = opData.cutting_parameters || {}
        var st = opData.stock_to_leave || {}
        profileId        = rp.profile_id !== undefined && Number(rp.profile_id) > 0
                           ? Math.round(Number(rp.profile_id)) : defaults.profileId
        strategy         = rp.strategy !== undefined ? String(rp.strategy) : defaults.strategy
        initialOffset    = rp.initial_offset !== undefined ? Number(rp.initial_offset) : defaults.initialOffset
        afterwardsOffset = rp.afterwards_offset !== undefined ? Number(rp.afterwards_offset)
                                                              : defaults.afterwardsOffset
        retract    = cp.retract !== undefined ? Number(cp.retract) : defaults.retract
        peckDepth  = cp.peck_depth !== undefined ? Number(cp.peck_depth) : defaults.peckDepth
        dwellTime  = cp.dwell_time !== undefined ? Number(cp.dwell_time) : defaults.dwellTime
        var stockOn = !!opData.stock_to_leave_enabled
        stockRadial = stockOn && st.radial !== undefined ? Number(st.radial) : 0
        stockAxial  = stockOn && st.axial !== undefined ? Number(st.axial) : 0

        _loadProfile()
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

        GrooveCanvas {
            id: profileCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
            toolCard: root.toolCard
            profileId: root.profileId
            primitives: root.primitives
            profileType: root.profileType
            workpiece: root.workpiece
            preview: root.groovePreview
            stockToLeaveArrowRect: root.stockRadial > 0 || root.stockAxial > 0 ? stockBox.rect : null
            startPosition: root.startPosition
            startDiameter: root.groovePreview && root.groovePreview.startDiameter != null
                           ? root.groovePreview.startDiameter : 0
            clearance: root.retract
            clearanceBoxRect: clearanceBox.rect
            boxWidth: Math.max(groovingBox.implicitWidth, stockBox.implicitWidth,
                               clearanceBox.implicitWidth, peckBox.implicitWidth)

            // from the middle of one peck - on the first plunge toward Z+
            // after the two in the middle - an arrow to the Peck Depth box
            extraMarkers: {
                var out = []
                var peck = root.groovePreview ? root.groovePreview.peck : null
                if (peck)
                    out.push({ dot: true, x: (peck.from + peck.to) / 2, z: peck.z,
                               color: root.peckColor, arrowToRect: peckBox.rect })
                // between the two plunges in the middle, each peck's number
                // in the order they are made, level with its arrowhead - half
                // the head's length back from where it ends - on its own
                // plunge's side, so two at the same depth stay apart
                var order = root.groovePreview && root.groovePreview.order ? root.groovePreview.order : []
                for (var i = 0; i < order.length; i++) {
                    // down the canvas is toward larger X
                    var back = order[i].x0 > order[i].x ? 1 : -1
                    out.push({ text: order[i].n, x: order[i].x, z: order[i].z,
                               dy: back * profileCanvas.toolpathArrowLength / 2,
                               color: root.peckColor })
                }
                return out
            }

            // over the blade, its outline where it plunges next: the Initial
            // Offset to its left
            CanvasTool {
                visible: !!root.startPosition && root.plunges.length > 1
                outlineOnly: true
                inset: profileCanvas.tickBand
                card: profileCanvas.startTool.card
                view: profileCanvas.startTool.view
                pxPerMm: profileCanvas.pxPerMm
                tipX: root.plunges.length > 1 ? profileCanvas.px(root.plunges[1]) : 0
                tipY: profileCanvas.startTool.tipY
            }

            // top to bottom: grooving, stock to leave, clearance, peck - the
            // first at the top, the last at the bottom, the space between
            // them shared out
            readonly property real boxSpacing: (height - 2 * boxGap - groovingBox.height - stockBox.height
                                                - clearanceBox.height - peckBox.height) / 3

            GroovingBox {
                id: groovingBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                accent: profileCanvas.groovingColor
                strategy: root.strategy
                initialOffset: root.initialOffset
                afterwardsOffset: root.afterwardsOffset
                onStrategyEdited: function(value) { root.strategy = value; root.save() }
                onInitialOffsetEdited: function(value) { root.initialOffset = value; root.save() }
                onAfterwardsOffsetEdited: function(value) { root.afterwardsOffset = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            StockToLeaveBox {
                id: stockBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: groovingBox.y + groovingBox.height + profileCanvas.boxSpacing
                labelColor: profileCanvas.stockToLeaveColor
                radial: root.stockRadial
                axial: root.stockAxial
                onRadialEdited: function(value) { root.stockRadial = value; root.save() }
                onAxialEdited: function(value) { root.stockAxial = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // how far out from the start diameter the blade starts and each
            // peck backs off to: the cutting_parameters' retract
            DimensionBox {
                id: clearanceBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: stockBox.y + stockBox.height + profileCanvas.boxSpacing
                label: "Clearance"
                dimensionColor: profileCanvas.clearanceColor
                settingName: "groove_roughing.clearance"
                value: root.retract
                onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            PeckBox {
                id: peckBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                color: root.peckColor
                peckSettingName: "groove_roughing.peck_depth"
                peckDepth: root.peckDepth
                dwellTime: root.dwellTime
                onPeckDepthEdited: function(value) { root.peckDepth = value; root.save() }
                onDwellTimeEdited: function(value) { root.dwellTime = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }
        }
    }
}
