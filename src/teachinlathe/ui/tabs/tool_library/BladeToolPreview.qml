import QtQuick
import theme
import "shapes/blade.js" as BladeShape

// The blade as it sits in the holder: the Z and X axes fixed through the
// middle of the view, the middle of the blade's cutting end - its control
// point - where they cross. The blade is drawn as far back as
// `editor.bladeLength`, its corners rounded as set, each marked L or R.
//
// The scale is fixed by the view's size, not by the blade, so changing the
// width visibly changes the drawing.
Rectangle {
    id: root

    property var editor: null          // BladeToolEditorViewModel, or a BladeToolView

    //: The longest blade drawn (20 mm, at 5 mm wide) and a little over; the
    //: scale is chosen so it fits whichever way it points.
    readonly property real maxReachMm: 22
    readonly property real pxPerMm: Math.max(1, (Math.min(width, height) / 2 - Theme.margin) / maxReachMm)

    readonly property point centre: Qt.point(width / 2, height / 2)

    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        readonly property var inputs: root.editor
            ? [root.editor.bladeWidth, root.editor.leftRadius, root.editor.rightRadius,
               root.editor.bladeLength, root.editor.bladeRotation, root.editor.bladeMirrored]
            : []
        onInputsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        // A point of the blade's own frame (mm, x across, y up toward the
        // cutting end, origin at the control point) on the screen: mirrored
        // top to bottom when the blade is, then turned.
        function toScreen(x, y) {
            if (root.editor.bladeMirrored) y = -y
            var a = root.editor.bladeRotation * Math.PI / 180, k = root.pxPerMm
            return Qt.point(root.centre.x + k * (x * Math.cos(a) - y * Math.sin(a)),
                            root.centre.y - k * (x * Math.sin(a) + y * Math.cos(a)))
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var p = root.centre

            // Axes.
            ctx.strokeStyle = Theme.foregroundFaint
            ctx.lineWidth = 1
            ctx.setLineDash([6, 4])
            ctx.beginPath()
            ctx.moveTo(0, p.y); ctx.lineTo(width, p.y)
            ctx.moveTo(p.x, 0); ctx.lineTo(p.x, height)
            ctx.stroke()
            ctx.setLineDash([])

            if (!root.editor)
                return
            var w = root.editor.bladeWidth
            var k = root.pxPerMm

            // The blade, as blade.js draws it everywhere.
            BladeShape.paint(ctx, {
                width: w, length: root.editor.bladeLength,
                leftRadius: root.editor.leftRadius, rightRadius: root.editor.rightRadius,
                rotation: root.editor.bladeRotation, mirrored: root.editor.bladeMirrored,
                pxPerMm: k, tipX: p.x, tipY: p.y,
                bodyColor: root.editor.bodyColor, edgeColor: root.editor.edgeColor, lineWidth: 1.5
            })

            // Which corner is which, just behind each.
            ctx.fillStyle = Theme.foregroundMuted
            ctx.font = "bold " + Theme.fontSmall + "px sans-serif"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            var off = w / 2 + 14 / k
            var l = toScreen(-off, -1.5), r = toScreen(off, -1.5)
            ctx.fillText("L", l.x, l.y)
            ctx.fillText("R", r.x, r.y)

            // The control point.
            var arm = 10
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
            text: root.editor ? "Blade " + Number(root.editor.bladeWidth.toFixed(3)) + " mm" : ""
            color: Theme.foreground
            font.pixelSize: Theme.fontTitle
            font.bold: true
        }
        Text {
            text: !root.editor ? ""
                  : "L R" + Number(root.editor.leftRadius.toFixed(3))
                    + "  ·  R R" + Number(root.editor.rightRadius.toFixed(3))
                    + "  ·  Q" + root.editor.orientation
            color: Theme.foregroundSubtle
            font.pixelSize: Theme.fontSmall
        }
    }
}
