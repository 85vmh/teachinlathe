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
    readonly property var _fp: op.finishing_parameters || ({})
    profileId: profileIdIn(_fp, defaults.profileId)

    // what the boxes on the canvas show
    readonly property string strategy: _fp.strategy !== undefined ? String(_fp.strategy) : defaults.strategy
    readonly property real   retract: numberIn(op.cutting_parameters, "retract", defaults.retract)

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
        onStrategyEdited: function(value) { root.editor.edit({ finishing_parameters: { profile_id: root.profileId, strategy: value } }) }
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
        onValueEdited: function(value) { root.editCutting({ retract: Math.abs(value) }) }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
