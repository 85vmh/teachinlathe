// GrooveCanvas.qml — the profile canvas of a groove operation, Groove Roughing
// or Groove Finishing: the radial profile it cuts drawn on the header's stock,
// filled as the pulley, what it would cut (preview), the blade where it
// starts - the clearance out from the start diameter, dimensioned to the
// view's Clearance box - the tool it cuts with at the top, picked among
// blades and tools held neutral, and why there is nothing to draw. The view
// lays its own boxes down the right edge over it, boxWidth the widest of them.
import QtQuick
import QtQuick.Controls
import tabs.conversational.define_radial_profile
import theme

RadialProfileCanvas {
    id: root

    // The view model of the operation (OperationEditorViewModel.py).
    property var editor: null
    // the tool it cuts with: editor.toolCard, a ToolCard; null with none
    property var toolCard: null
    property int profileId: 1
    // what it would cut, as the view model's preview has it
    property var preview: null
    // where the blade starts, {x: diameter, z}, and the start diameter
    property var startPosition: null
    property real startDiameter: 0
    // the clearance between them, and the box that edits it, in canvas px
    property real clearance: 0
    property var clearanceBoxRect: null
    // the view's own marks, drawn with the clearance's
    property var extraMarkers: []
    // the widest of the view's boxes; the drawing is fitted into what it leaves
    property real boxWidth: 0
    readonly property real boxGap: Theme.spacingLarge

    // the blade drawn where it starts: its card, view and tip, for another
    // drawn beside it
    readonly property alias startTool: canvasTool

    readonly property bool hasGroove: groovePoints.length === 4
    // mm, the blade's width - before one is chosen, as wide as a usual one,
    // for the marks drawn beside it
    readonly property real defaultBladeWidth: 3
    readonly property real bladeWidth: toolCard && toolCard.card === "blade" && toolCard.view
                                       ? Number(toolCard.view.bladeWidth) : defaultBladeWidth
    // how far either side of the blade the clearance's lines reach, mm
    readonly property real xLinePast: 2

    readonly property color groovingColor: "#1565c0"
    readonly property color clearanceColor: "#6d4c41"

    roughingPreview: preview
    // the pulley: its profile and its mirror joined at both ends - no lines
    // across it between them - and filled as an OD profile
    showTransitions: false
    fillProfile: true
    fitInsetRight: boxWidth + boxGap

    // the clearance between the start diameter and where the blade starts,
    // a line at each beside the blade, dimensioned between them on its right
    readonly property bool _showsClearance: !!startPosition && clearance > 0
    markers: {
        if (!_showsClearance) return extraMarkers
        var line = { hline: true, z: startPosition.z, half: bladeWidth / 2 + xLinePast,
                     halfRight: bladeWidth / 2 + 2 * xLinePast, color: clearanceColor }
        return [Object.assign({}, line, { x: startDiameter }),
                Object.assign({}, line, { x: startPosition.x })].concat(extraMarkers)
    }
    dimensions: _showsClearance
                ? [{ axis: "x", from: startDiameter, to: startPosition.x,
                     z: startPosition.z + bladeWidth / 2 + xLinePast, offset: 0,
                     color: clearanceColor, arrowToRect: clearanceBoxRect,
                     arrowsOutside: true, leaderFromOutsideEnd: "to" }]
                : []

    // the blade where it starts, inside the ticks; in the fit too
    fitExtraPositions: {
        if (!canvasTool.drawn || !startPosition) return []
        var pts = canvasTool.outlineFromTip, out = []
        for (var i = 0; i < pts.length; i++)
            out.push({ x: startPosition.x + 2 * pts[i].y, z: startPosition.z + pts[i].x })
        return out
    }
    CanvasTool {
        id: canvasTool
        visible: !!root.startPosition
        inset: root.tickBand
        card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
        view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
        pxPerMm: root.pxPerMm
        tipX: root.startPosition ? root.px(root.startPosition.z) : 0
        tipY: root.startPosition ? root.py(root.startPosition.x) : 0
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Theme.outline; border.width: Theme.hairline
    }

    // the tool it cuts with, at the top, in the canvas's middle; tapped, to
    // pick it - a blade, or a tool held neutral (tool_fit.py)
    OperationToolBox {
        editor: root.editor
        pickerWidth: root.width
        x: (root.width - width) / 2
        // lined up with the view buttons, as tall as they are
        y: viewButtons.y
        rowHeight: viewButtons.height
    }

    // zoom, fit to screen and mirror - top-left, as on every profile canvas
    CanvasViewButtons {
        id: viewButtons
        canvas: root
        visible: root.hasGroove
    }

    // why there is nothing to draw: no blade, a groove narrower than it
    Rectangle {
        readonly property string message: root.preview && root.preview.error ? root.preview.error : ""
        visible: message !== "" && root.hasGroove
        x: Theme.spacingLarge
        y: root.height - height - Theme.spacingLarge
        width: Math.min(errorText.implicitWidth + 2 * Theme.spacing,
                        root.width - root.boxWidth - 3 * Theme.spacingLarge)
        height: errorText.implicitHeight + 2 * Theme.spacingSmall
        radius: Theme.radius
        color: Theme.dangerSoft
        border.color: Theme.danger
        border.width: Theme.hairline

        Text {
            id: errorText
            x: Theme.spacing
            y: Theme.spacingSmall
            width: parent.width - 2 * Theme.spacing
            text: parent.message
            color: Theme.foreground
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
        }
    }

    Label {
        anchors.centerIn: parent
        visible: !root.hasGroove
        text: "No radial profile P" + root.profileId + " defined above this operation"
        color: Theme.foregroundMuted
        font.pixelSize: Theme.fontBody
    }
}
