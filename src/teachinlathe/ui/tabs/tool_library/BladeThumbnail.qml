import QtQuick
import theme
import "shapes/blade.js" as BladeShape

// A blade, small: InsertThumbnail's frame and red cross, the cross on the
// middle of the blade's cutting end. It draws as BladeToolPreview does -
// same corners, mirroring and turn - at the scale every insert thumbnail
// does - times ``scaleFactor``, 2 unless set, a blade being thin; it is
// centred on its outline.
Item {
    id: root

    property var view: null            // BladeToolView
    property real size: 50
    //: Whether the frame round it is drawn.
    property bool framed: true
    //: Length of each arm of the tip cross, from the tip, in pixels.
    property real crossArm: 10
    //: Space between the frame and the reference insert, in pixels.
    property real padding: 5
    //: How much bigger than the insert thumbnails' common scale the blade
    //: is drawn: a blade is thin, and at that scale hard to make out. The
    //: backplot keeps it true to size.
    property real scaleFactor: 2

    width: size
    height: size
    // The control point is on the blade's end, so its cross reaches past it.
    clip: true

    Rectangle {
        anchors.fill: parent
        z: 2
        visible: root.framed
        color: "transparent"
        radius: Theme.radiusSmall
        border.width: Theme.hairline
        border.color: Theme.outline
    }

    readonly property real bladeWidth: view ? view.bladeWidth : 1.5
    readonly property real bladeLength: view ? view.bladeLength : 3 * bladeWidth
    readonly property real rotation_: view ? view.bladeRotation : 0
    readonly property bool mirrored: view ? view.bladeMirrored : false

    // the blade as blade.js draws it
    function shape() {
        return { width: bladeWidth, length: bladeLength,
                 leftRadius: view ? view.leftRadius : 0, rightRadius: view ? view.rightRadius : 0,
                 rotation: rotation_, mirrored: mirrored, pxPerMm: pxPerMm,
                 tipX: tip.x, tipY: tip.y,
                 bodyColor: view ? view.bodyColor : "#e5a93b", edgeColor: view ? view.edgeColor : "#674c1b",
                 lineWidth: 1 }
    }

    // The turned blade's extent, in mm, about its control point.
    readonly property var bounds: {
        var verts = BladeShape.corners({ width: bladeWidth, length: bladeLength,
                                          rotation: rotation_, mirrored: mirrored })
        var b = { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }
        for (var i = 0; i < verts.length; i++) {
            b.left = Math.min(b.left, verts[i].x); b.right = Math.max(b.right, verts[i].x)
            b.top = Math.min(b.top, verts[i].y); b.bottom = Math.max(b.bottom, verts[i].y)
        }
        return b
    }
    readonly property real pxPerMm: scaleFactor * (size - 2 * padding)
                                    / Math.max(2 * (view ? view.catalogReachMm : 16), 0.001)
    // Where the control point goes so the blade's outline is centred.
    readonly property point tip: Qt.point(
        width / 2 - pxPerMm * (bounds.left + bounds.right) / 2,
        height / 2 - pxPerMm * (bounds.top + bounds.bottom) / 2)

    Canvas {
        id: blade
        anchors.fill: parent
        antialiasing: true
        z: 1

        readonly property var inputs: root.view
            ? [root.bladeWidth, root.view.leftRadius, root.view.rightRadius,
               root.bladeLength, root.rotation_, root.mirrored, root.tip]
            : []
        onInputsChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (!root.view)
                return
            BladeShape.paint(ctx, root.shape())
        }
    }

    Canvas {
        id: cross
        // Bigger than the square: the cross may reach past it. Under the
        // blade, as the insert thumbnails have it.
        x: -root.crossArm; y: -root.crossArm
        width: root.width + 2 * root.crossArm
        height: root.height + 2 * root.crossArm
        z: 0
        readonly property point at: Qt.point(root.tip.x + root.crossArm, root.tip.y + root.crossArm)
        onAtChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = Theme.redHighlight
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(at.x - root.crossArm, at.y); ctx.lineTo(at.x + root.crossArm, at.y)
            ctx.moveTo(at.x, at.y - root.crossArm); ctx.lineTo(at.x, at.y + root.crossArm)
            ctx.stroke()
        }
    }
}
