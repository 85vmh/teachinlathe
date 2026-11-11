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
    readonly property var _cp: op.cutting_parameters || ({})
    profileId: profileIdIn(op.grooving_parameters, defaults.profileId)

    // what the boxes on the canvas show
    readonly property real retract: numberIn(_cp, "retract", defaults.retract)
    readonly property real doc: numberIn(_cp, "doc", defaults.doc)
    readonly property real dwellTime: numberIn(_cp, "dwell_time", defaults.dwellTime)

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
        onRadialEdited: function(value) { root.editStock({ radial: value }) }
        onAxialEdited: function(value) { root.editStock({ axial: value }) }
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
        onValueEdited: function(value) { root.editCutting({ retract: Math.abs(value) }) }
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
        onPeckDepthEdited: function(value) { root.editCutting({ doc: value }) }
        onDwellTimeEdited: function(value) { root.editCutting({ dwell_time: value }) }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
