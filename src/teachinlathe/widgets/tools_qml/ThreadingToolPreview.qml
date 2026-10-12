import QtQuick 2.15
import theme 1.0
import "../tool_shapes"

// The threading insert as it sits in the holder: the Z and X axes fixed
// through the middle of the view, the insert's tooth tip where they cross.
// As InsertPreview does for a turning insert, minus the angle dimensions -
// a threading insert has none to set.
//
// The scale is fixed by the view's size, not by the insert, so changing the
// insert size visibly changes the drawing.
Rectangle {
    id: root

    property var editor: null          // ThreadingToolEditorViewModel

    //: The furthest the biggest threading insert (22, IC 12.7) reaches
    //: from its tooth tip; the scale is chosen so it fits whichever way it
    //: points.
    readonly property real maxReachMm: 26
    readonly property real pxPerMm: Math.max(1, (Math.min(width, height) / 2 - Theme.margin) / maxReachMm)

    readonly property point centre: Qt.point(width / 2, height / 2)

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    // ── Axes, under the insert ──────────────────────────────────────────────
    Canvas {
        anchors.fill: parent
        antialiasing: true
        z: 0
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

    // ── The insert, its tip on the centre ───────────────────────────────────
    ThreadingInsert {
        id: insert
        z: 1
        width: root.width
        height: root.height

        // Where the tip lands with the insert centred, from the centre, in
        // pixels; the insert is moved back by that much. ThreadingInsert
        // turns counter-clockwise, as TurningInsertBase does.
        readonly property point tipOffset: {
            var t = activeTip()
            var a = orientation * Math.PI / 180
            var k = pxPerMm
            return Qt.point(k * (t.x * Math.cos(a) - t.y * Math.sin(a)),
                            -k * (t.x * Math.sin(a) + t.y * Math.cos(a)))
        }
        x: -tipOffset.x
        y: -tipOffset.y

        insertSize: root.editor ? root.editor.sizeCode : "16"
        pitch: root.editor ? root.editor.pitch : 1.5
        hand: root.editor ? root.editor.drawnHand : "R"
        orientation: root.editor ? root.editor.insertRotation : 0
        pxPerMm: root.pxPerMm
        bodyColor: root.editor ? root.editor.insertBodyColor : "#e5a93b"
        edgeColor: root.editor ? root.editor.insertEdgeColor : "#674c1b"
    }

    // ── The tip, marked as the turning preview marks it ─────────────────────
    Canvas {
        z: 2
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
        z: 3
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: Theme.spacingLarge
        spacing: 4

        Text {
            text: root.editor ? root.editor.isoCode : ""
            color: Theme.foreground
            font.pixelSize: Theme.fontTitle
            font.bold: true
        }
        Text {
            text: root.editor ? "Pitch " + root.editor.pitch + " mm  ·  Q" + root.editor.orientation : ""
            color: Theme.foregroundSubtle
            font.pixelSize: Theme.fontSmall
        }
    }
}
