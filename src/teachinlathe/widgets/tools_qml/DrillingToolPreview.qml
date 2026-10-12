import QtQuick 2.15
import theme 1.0
import "../tool_shapes"

// The drill as it sits on the spindle axis: the Z and X axes through the
// middle of the view, the drill's point - its control point - where they
// cross, the body running off to +Z (orientation 7).
//
// Drawn to the insert previews' fixed scale, so the diameter shows at its
// size; the length is not the drill's - it runs to the edge of the view.
Rectangle {
    id: root

    property var editor: null          // DrillingToolEditorViewModel, or a DrillingToolView

    readonly property point centre: Qt.point(width / 2, height / 2)

    //: As InsertPreview's: the furthest a catalogue insert reaches from its
    //: tip, and so the widest drill drawn whole (about 32 mm).
    readonly property real maxReachMm: 33
    readonly property real pxPerMm: Math.max(1, (Math.min(width, height) / 2 - Theme.margin) / maxReachMm)

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    // ── Axes, under the drill ───────────────────────────────────────────────
    Canvas {
        anchors.fill: parent
        antialiasing: true
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var p = root.centre
            ctx.strokeStyle = Theme.foregroundFaint
            ctx.lineWidth = 1
            ctx.setLineDash([6, 4])
            ctx.beginPath()
            ctx.moveTo(0, p.y); ctx.lineTo(width, p.y)
            ctx.moveTo(p.x, 0); ctx.lineTo(p.x, height)
            ctx.stroke()
        }
    }

    // ── The drill, its point on the centre ──────────────────────────────────
    Drill {
        id: drill
        width: implicitWidth
        height: implicitHeight
        x: root.centre.x - tipPoint.x
        y: root.centre.y - tipPoint.y
        diameter: root.editor ? root.editor.diameter : 10
        tipAngle: root.editor ? root.editor.tipAngle : 118
        rightHand: root.editor ? root.editor.rightHand : true
        pxPerMm: root.pxPerMm
        // From the point to the view's right edge, less the margin.
        length: Math.max(1, (root.width / 2 - Theme.margin) / root.pxPerMm)
        bodyColor: root.editor ? root.editor.bodyColor : "#e5a93b"
        edgeColor: root.editor ? root.editor.edgeColor : "#674c1b"
    }

    // ── The control point ───────────────────────────────────────────────────
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var p = root.centre, arm = 10
            ctx.strokeStyle = Theme.redHighlight
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(p.x - arm, p.y); ctx.lineTo(p.x + arm, p.y)
            ctx.moveTo(p.x, p.y - arm); ctx.lineTo(p.x, p.y + arm)
            ctx.stroke()
        }
    }

    Column {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: Theme.spacingLarge
        spacing: 4

        Text {
            text: root.editor ? "Ø" + Number(root.editor.diameter.toFixed(3)) + " mm" : ""
            color: Theme.foreground
            font.pixelSize: Theme.fontTitle
            font.bold: true
        }
        Text {
            text: !root.editor ? ""
                  : Number(root.editor.tipAngle.toFixed(1)) + "° point  ·  "
                    + (root.editor.rightHand ? "Right hand" : "Left hand")
                    + "  ·  Q" + root.editor.orientation
            color: Theme.foregroundSubtle
            font.pixelSize: Theme.fontSmall
        }
    }
}
