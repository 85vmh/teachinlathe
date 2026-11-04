// GrooveBidirectionalVisualDetailsView.qml — BiDirectional Grooving on the
// groove's canvas (GrooveDetailsView): the tool where it starts - over the
// groove's mouth, the clearance out from the start diameter - the S it cuts,
// its arrows the way it goes, and the boxes down the right edge: the stock to
// leave, the clearance, the Depth of Cut and the dwell after each plunge down
// a flank.
import QtQuick

GrooveDetailsView {
    id: root

    // what an operation saved without a value has: a new one's, as
    // conversational/model/factories.py makes it
    readonly property var defaults: ({ profileId: 1, retract: 1.0, doc: 1.0, dwellTime: 0.0 })

    // the values the boxes on the canvas show and edit
    property real retract: defaults.retract
    property real doc: defaults.doc
    property real dwellTime: defaults.dwellTime

    draftOp: function() {
        var op = copyOf(opData)
        op.grooving_parameters = { profile_id: profileId }
        op.cutting_parameters = { doc: doc, retract: retract, dwell_time: dwellTime }
        return withStock(op)
    }

    readData: function(data) {
        var cp = data.cutting_parameters || {}
        profileId = profileIdIn(data.grooving_parameters, defaults.profileId)
        retract   = numberIn(cp, "retract", defaults.retract)
        doc       = numberIn(cp, "doc", defaults.doc)
        dwellTime = numberIn(cp, "dwell_time", defaults.dwellTime)
        readStock(data)
    }

    // where the tool starts, as the G-code goes there
    canvas.startPosition: groovePreview && groovePreview.start ? groovePreview.start : null
    canvas.clearance: retract
    canvas.boxWidth: Math.max(stockBox.implicitWidth, clearanceBox.implicitWidth, docBox.implicitWidth)

    // top to bottom: stock to leave, clearance, Depth of Cut - the first at
    // the top, the last at the bottom, the space between them shared out
    readonly property real boxSpacing: (canvas.height - 2 * canvas.boxGap - stockBox.height
                                        - clearanceBox.height - docBox.height) / 2

    StockToLeaveBox {
        id: stockBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: root.canvas.boxGap
        labelColor: root.canvas.stockToLeaveColor
        radial: root.stockRadial
        axial: root.stockAxial
        onRadialEdited: function(value) { root.stockRadial = value; root.save() }
        onAxialEdited: function(value) { root.stockAxial = value; root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    // how far out from the start diameter the tool starts and backs off to:
    // the cutting_parameters' retract
    DimensionBox {
        id: clearanceBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: stockBox.y + stockBox.height + root.boxSpacing
        label: "Clearance"
        dimensionColor: root.canvas.clearanceColor
        settingName: "groove_bidirectional.clearance"
        value: root.retract
        onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    PeckBox {
        id: docBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: root.canvas.height - height - root.canvas.boxGap
        color: root.canvas.feedColor
        depthLabel: "DoC"
        peckSettingName: "groove_bidirectional.doc"
        peckDepth: root.doc
        dwellTime: root.dwellTime
        onPeckDepthEdited: function(value) { root.doc = value; root.save() }
        onDwellTimeEdited: function(value) { root.dwellTime = value; root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
