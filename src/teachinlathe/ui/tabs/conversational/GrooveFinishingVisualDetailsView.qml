// GrooveFinishingVisualDetailsView.qml — Groove Finishing on the groove's
// canvas (GrooveDetailsView), laid out as Groove Roughing: the stock the
// roughing above left on the profile - what this takes off - the contour its
// strategy goes along, the blade where it starts - over the groove's middle,
// between P1 and P4 - and the boxes down the right edge: the strategy
// (GroovingBox) and the clearance. It has no inspection stop.
import QtQuick

GrooveDetailsView {
    id: root
    hasM1: false

    // what an operation saved without a value has: a new one's, as
    // conversational/model/factories.py makes it
    readonly property var defaults: ({ profileId: 1, strategy: "towards_center", retract: 1.0 })

    readonly property var strategies: [
        { label: "Towards Center", value: "towards_center" },
        { label: "Towards Left", value: "towards_left" },
        { label: "Towards Right", value: "towards_right" }
    ]

    // the values the boxes on the canvas show and edit
    property string strategy: defaults.strategy
    property real   retract: defaults.retract

    draftOp: function() {
        var op = copyOf(opData)
        op.finishing_parameters = { profile_id: profileId, strategy: strategy }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.retract = retract
        return op
    }

    readData: function(data) {
        var fp = data.finishing_parameters || {}
        profileId = profileIdIn(fp, defaults.profileId)
        strategy  = fp.strategy !== undefined ? String(fp.strategy) : defaults.strategy
        retract   = numberIn(data.cutting_parameters, "retract", defaults.retract)
    }

    // where the blade starts: over the groove's middle, the clearance out
    // from the start diameter - the pulley's outside with the stock the
    // roughing left on it - as the G-code goes there (retract is the clearance)
    canvas.startPosition: groovePreview && groovePreview.start ? groovePreview.start : null
    canvas.clearance: retract
    canvas.boxWidth: Math.max(groovingBox.implicitWidth, clearanceBox.implicitWidth)

    GroovingBox {
        id: groovingBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: root.canvas.boxGap
        accent: root.canvas.groovingColor
        strategies: root.strategies
        showOffsets: false
        strategy: root.strategy
        onStrategyEdited: function(value) { root.strategy = value; root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }

    // how far out from the start diameter the blade starts and backs off to:
    // the cutting_parameters' retract
    DimensionBox {
        id: clearanceBox
        x: root.canvas.width - width - root.canvas.boxGap
        y: groovingBox.y + groovingBox.height + root.canvas.boxGap
        label: "Clearance"
        dimensionColor: root.canvas.clearanceColor
        settingName: "groove_finishing.clearance"
        value: root.retract
        onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
