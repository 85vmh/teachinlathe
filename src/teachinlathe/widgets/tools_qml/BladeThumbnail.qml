import QtQuick 2.15
import theme 1.0

// A blade, small: InsertThumbnail's frame and red cross, the cross on the
// middle of the blade's cutting end. It draws as BladeToolPreview does -
// same corners, mirroring and turn - at the scale every insert thumbnail
// does, so a blade sits beside a CCMT at their true sizes; it is centred on
// its outline.
Item {
    id: root

    property var view: null            // BladeToolView
    property real size: 50
    //: Length of each arm of the tip cross, from the tip, in pixels.
    property real crossArm: 10
    //: Space between the frame and the reference insert, in pixels.
    property real padding: 5

    width: size
    height: size
    // The control point is on the blade's end, so its cross reaches past it.
    clip: true

    Rectangle {
        anchors.fill: parent
        z: 2
        color: "transparent"
        radius: Theme.radiusSmall
        border.width: Theme.hairline
        border.color: Theme.outline
    }

    readonly property real bladeWidth: view ? view.bladeWidth : 1.5
    readonly property real bladeLength: view ? view.bladeLength : 11.25
    readonly property real rotation_: view ? view.bladeRotation : 0
    readonly property bool mirrored: view ? view.bladeMirrored : false

    // A point of the blade's own frame, in mm, mirrored and turned as it is
    // drawn and flipped to screen y - still in mm, about the control point.
    function turned(x, y) {
        if (mirrored) y = -y
        var a = rotation_ * Math.PI / 180
        return Qt.point(x * Math.cos(a) - y * Math.sin(a),
                        -(x * Math.sin(a) + y * Math.cos(a)))
    }

    // The turned blade's extent, in mm, about its control point.
    readonly property var bounds: {
        var w = bladeWidth / 2, l = bladeLength
        var verts = [turned(-w, 0), turned(w, 0), turned(w, -l), turned(-w, -l)]
        var b = { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity }
        for (var i = 0; i < verts.length; i++) {
            b.left = Math.min(b.left, verts[i].x); b.right = Math.max(b.right, verts[i].x)
            b.top = Math.min(b.top, verts[i].y); b.bottom = Math.max(b.bottom, verts[i].y)
        }
        return b
    }
    readonly property real pxPerMm: (size - 2 * padding)
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
            var w = root.bladeWidth, len = root.bladeLength, k = root.pxPerMm
            ctx.translate(root.tip.x, root.tip.y)
            ctx.rotate(-root.rotation_ * Math.PI / 180)
            ctx.scale(k, root.mirrored ? k : -k)
            ctx.beginPath()
            ctx.moveTo(-w / 2, -len)
            ctx.arcTo(-w / 2, 0, w / 2, 0, root.view.leftRadius)
            ctx.arcTo(w / 2, 0, w / 2, -len, root.view.rightRadius)
            ctx.lineTo(w / 2, -len)
            ctx.closePath()
            ctx.fillStyle = root.view.bodyColor
            ctx.fill()
            ctx.lineJoin = "round"
            ctx.lineWidth = 1 / k
            ctx.strokeStyle = root.view.edgeColor
            ctx.stroke()
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
