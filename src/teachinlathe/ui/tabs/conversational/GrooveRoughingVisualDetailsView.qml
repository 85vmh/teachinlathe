// GrooveRoughingVisualDetailsView.qml — Groove Roughing on the groove's
// canvas (GrooveDetailsView), laid out as Profile Roughing: the blade where it
// starts - over its first plunge, the clearance out from the start diameter -
// its outline over the second, and the boxes down the right edge: its own
// parameters (GroovingBox), the stock to leave, the clearance as Parting has
// it, the peck depth and dwell time as Drilling has them.
import QtQuick

GrooveDetailsView {
    id: root

    // what an operation saved without a value has: a new one's, as
    // conversational/model/factories.py makes it
    readonly property var defaults: ({
        profileId: 1, strategy: "start_center", initialOffset: 1.5, afterwardsOffset: 1.0,
        retract: 1.0, peckDepth: 3.0, dwellTime: 0.5
    })

    // the values the boxes on the canvas show and edit
    property string strategy: defaults.strategy
    property real   initialOffset: defaults.initialOffset
    property real   afterwardsOffset: defaults.afterwardsOffset
    property real   retract: defaults.retract
    property real   peckDepth: defaults.peckDepth
    property real   dwellTime: defaults.dwellTime

    draftOp: function() {
        var op = copyOf(opData)
        op.roughing_parameters = {
            profile_id: profileId, strategy: strategy,
            initial_offset: initialOffset, afterwards_offset: afterwardsOffset
        }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.peck_depth = peckDepth
        op.cutting_parameters.retract = retract
        op.cutting_parameters.dwell_time = dwellTime
        return withStock(op)
    }

    readData: function(data) {
        var rp = data.roughing_parameters || {}
        var cp = data.cutting_parameters || {}
        profileId        = profileIdIn(rp, defaults.profileId)
        strategy         = rp.strategy !== undefined ? String(rp.strategy) : defaults.strategy
        initialOffset    = numberIn(rp, "initial_offset", defaults.initialOffset)
        afterwardsOffset = numberIn(rp, "afterwards_offset", defaults.afterwardsOffset)
        retract          = numberIn(cp, "retract", defaults.retract)
        peckDepth        = numberIn(cp, "peck_depth", defaults.peckDepth)
        dwellTime        = numberIn(cp, "dwell_time", defaults.dwellTime)
        readStock(data)
    }

    // the plunges, in the order the G-code makes them; the groove's middle
    // until there is a plan
    readonly property var plunges: {
        if (groovePreview && groovePreview.plunges && groovePreview.plunges.length > 0)
            return groovePreview.plunges
        var p = canvas.groovePoints
        return p.length === 4 ? [(p[0].z + p[3].z) / 2] : []
    }
    readonly property color peckColor: canvas.feedColor

    // where the blade starts: over its first plunge, the clearance out from
    // the start diameter - the groove's mouth with the radial stock to leave
    // on it - as the G-code goes there
    canvas.startPosition: plunges.length > 0 && groovePreview && groovePreview.bladeX != null
                          ? { z: plunges[0], x: groovePreview.bladeX } : null
    canvas.clearance: retract
    canvas.boxWidth: Math.max(groovingBox.implicitWidth, stockBox.implicitWidth,
                              clearanceBox.implicitWidth, peckBox.implicitWidth)

    // between the two plunges in the middle, each peck's number in the order
    // they are made, level with its arrowhead - half the head's length back
    // from where it ends - on its own plunge's side, so two at the same depth
    // stay apart
    canvas.extraMarkers: {
        var out = []
        var order = groovePreview && groovePreview.order ? groovePreview.order : []
        for (var i = 0; i < order.length; i++) {
            // down the canvas is toward larger X
            var back = order[i].x0 > order[i].x ? 1 : -1
            out.push({ text: order[i].n, x: order[i].x, z: order[i].z,
                       dy: back * canvas.toolpathArrowLength / 2, color: peckColor })
        }
        return out
    }

    // top to bottom: grooving, stock to leave, clearance, peck - the first at
    // the top, the last at the bottom, the space between them shared out
    readonly property real boxSpacing: (canvas.height - 2 * canvas.boxGap - groovingBox.height - stockBox.height
                                        - clearanceBox.height - peckBox.height) / 3

    // over the blade, its outline where it plunges next: the Initial Offset
    // to its left
    CanvasTool {
        visible: !!root.canvas.startPosition && root.plunges.length > 1
        outlineOnly: true
        inset: root.canvas.tickBand
        card: root.canvas.startTool.card
        view: root.canvas.startTool.view
        pxPerMm: root.canvas.pxPerMm
        tipX: root.plunges.length > 1 ? root.canvas.px(root.plunges[1]) : 0
        tipY: root.canvas.startTool.tipY
    }

    GroovingBox {
        id: groovingBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: root.canvas.boxGap
        accent: root.canvas.groovingColor
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
        x: root.canvas.width - width - root.canvas.boxGap
        y: groovingBox.y + groovingBox.height + root.boxSpacing
        labelColor: root.canvas.stockToLeaveColor
        radial: root.stockRadial
        axial: root.stockAxial
        onRadialEdited: function(value) { root.stockRadial = value; root.save() }
        onAxialEdited: function(value) { root.stockAxial = value; root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    // how far out from the start diameter the blade starts and each peck
    // backs off to: the cutting_parameters' retract
    DimensionBox {
        id: clearanceBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: stockBox.y + stockBox.height + root.boxSpacing
        label: "Clearance"
        dimensionColor: root.canvas.clearanceColor
        settingName: "groove_roughing.clearance"
        value: root.retract
        onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    PeckBox {
        id: peckBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: root.canvas.height - height - root.canvas.boxGap
        color: root.peckColor
        peckSettingName: "groove_roughing.peck_depth"
        peckDepth: root.peckDepth
        dwellTime: root.dwellTime
        onPeckDepthEdited: function(value) { root.peckDepth = value; root.save() }
        onDwellTimeEdited: function(value) { root.dwellTime = value; root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
