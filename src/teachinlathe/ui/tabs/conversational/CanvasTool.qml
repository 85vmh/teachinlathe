// CanvasTool.qml — the tool an operation cuts with, on the profile canvas,
// drawn as the Tool Library draws it, at the canvas's scale, its control
// point on ``tipX``, ``tipY`` (canvas px):
//   - a turning tool's insert (TurningInsertBase, from its TurningToolView:
//     shape, size, corner radius, colours, the turn its orientation and
//     angles give it), its cutting tip there;
//   - a blade (blade.js, from its BladeToolView: width, corners, mirroring
//     and turn), the middle of its cutting end there;
//   - a threading insert (ThreadingInsert, from its ThreadingToolView: size,
//     pitch, hand and turn), the tip of its tooth there.
// The Tool Library draws with y up and the canvas has X growing down the
// screen, so the drawing goes on as it is. Laid over the whole canvas,
// clipped ``inset`` px in from its edges - inside the ticks.
import QtQuick
import theme
import tabs.tool_library.shapes
import "../tool_library/shapes/blade.js" as BladeShape

Item {
    id: root

    property string card: ""          // "turning", "blade" or "threading", as the Tool Library's cards
    property var  view: null          // TurningToolView, BladeToolView or ThreadingToolView
    property real pxPerMm: 1
    property real tipX: 0
    property real tipY: 0
    property real inset: 0
    // only its outline, the inside clear: where it goes next, over the tool
    property bool outlineOnly: false

    readonly property bool isInsert: card === "turning" && !!view
    readonly property bool isBlade: card === "blade" && !!view
    readonly property bool isThreading: card === "threading" && !!view
    // whether it draws anything
    readonly property bool drawn: isInsert || isBlade || (isThreading && threadingInsert.specValid)

    anchors.fill: parent
    anchors.margins: inset
    clip: true

    // A point of the insert's own frame, in mm, turned as it is drawn and
    // flipped to screen y - as InsertThumbnail turns it.
    function turned(p) {
        var a = insert.orientation * Math.PI / 180
        return Qt.point(p.x * Math.cos(a) - p.y * Math.sin(a),
                        -(p.x * Math.sin(a) + p.y * Math.cos(a)))
    }

    // The same for the threading insert: its points come mirrored already.
    function turnedThreading(p) {
        var a = threadingInsert.orientation * Math.PI / 180
        return Qt.point(p.x * Math.cos(a) - p.y * Math.sin(a),
                        -(p.x * Math.sin(a) + p.y * Math.cos(a)))
    }

    function _blade() {
        return { width: view.bladeWidth, length: view.bladeLength,
                 leftRadius: view.leftRadius, rightRadius: view.rightRadius,
                 rotation: view.bladeRotation, mirrored: view.bladeMirrored,
                 pxPerMm: pxPerMm, tipX: tipX - inset, tipY: tipY - inset,
                 bodyColor: outlineOnly ? "transparent" : view.bodyColor, edgeColor: view.edgeColor,
                 lineWidth: 1 }
    }

    // The tool's outline about its control point, in mm, as the canvas
    // draws it: x along Z, y down the screen (radius) - [{x, y}], for a fit
    // to take in.
    readonly property var outlineFromTip: {
        if (isBlade) return BladeShape.corners(_blade())
        if (isThreading) {
            if (!threadingInsert.specValid) return []
            var tt = turnedThreading(threadingInsert.activeTip()), pts = threadingInsert.outlinePoints(), res = []
            for (var j = 0; j < pts.length; j++) {
                var q = turnedThreading(pts[j])
                res.push({ x: q.x - tt.x, y: q.y - tt.y })
            }
            return res
        }
        if (!isInsert) return []
        var o = insert.outline()
        var t = turned(insert.activeTip()), out = []
        if (o.round) {
            var r = insert.ic / 2
            var c = Qt.point(-t.x, -t.y)
            return [{ x: c.x - r, y: c.y - r }, { x: c.x + r, y: c.y + r }]
        }
        for (var i = 0; i < o.verts.length; i++) {
            var p = turned(o.verts[i])
            out.push({ x: p.x - t.x, y: p.y - t.y })
        }
        return out
    }

    // Its middle, in canvas px: an insert's centre - its hole, about which
    // the insert is drawn - or the middle of a blade's outline.
    readonly property point threadingCentre: {
        var t = turnedThreading(threadingInsert.activeTip())
        return Qt.point(tipX - pxPerMm * t.x, tipY - pxPerMm * t.y)
    }
    readonly property point centre: {
        if (isBlade) {
            var cs = outlineFromTip, sx = 0, sy = 0
            for (var i = 0; i < cs.length; i++) { sx += cs[i].x; sy += cs[i].y }
            return Qt.point(tipX + pxPerMm * sx / cs.length, tipY + pxPerMm * sy / cs.length)
        }
        var t = turned(insert.activeTip())
        return Qt.point(tipX - pxPerMm * t.x, tipY - pxPerMm * t.y)
    }

    TurningInsertBase {
        id: insert
        visible: root.isInsert
        // as big as the insert at any turn, about its own middle - a long
        // one (VBMT) reaches well past its inscribed circle
        width: 2 * insert.maxRadius() * root.pxPerMm + 4
        height: width
        x: root.centre.x - root.inset - width / 2
        y: root.centre.y - root.inset - height / 2
        shape: root.isInsert ? root.view.shapeLetter : "C"
        insertType: root.isInsert ? root.view.insertType : "T"
        ic: root.isInsert ? root.view.ic : 6.35
        noseRadius: root.isInsert ? root.view.noseRadiusMm : 0.4
        orientation: root.isInsert ? root.view.insertRotation : 0
        pxPerMm: root.pxPerMm
        openHole: true
        bodyColor: root.outlineOnly ? "transparent" : root.isInsert ? root.view.insertBodyColor : "#e5a93b"
        edgeColor: root.isInsert ? root.view.insertEdgeColor : "#674c1b"
    }

    ThreadingInsert {
        id: threadingInsert
        visible: root.isThreading
        // drawn about its own middle, the insert's centre
        width: 2.2 * ic * root.pxPerMm + 4
        height: width
        x: root.threadingCentre.x - root.inset - width / 2
        y: root.threadingCentre.y - root.inset - height / 2
        insertSize: root.isThreading ? root.view.sizeCode : "16"
        pitch: root.isThreading ? root.view.pitch : 1.5
        hand: root.isThreading ? root.view.drawnHand : "R"
        orientation: root.isThreading ? root.view.insertRotation : 0
        pxPerMm: root.pxPerMm
        bodyColor: root.isThreading ? root.view.insertBodyColor : "#e5a93b"
        edgeColor: root.isThreading ? root.view.insertEdgeColor : "#674c1b"
        holeColor: Theme.surface
    }

    Canvas {
        id: bladeCanvas
        anchors.fill: parent
        visible: root.isBlade
        antialiasing: true
        readonly property var inputs: root.isBlade
            ? [root.view.bladeWidth, root.view.bladeLength, root.view.leftRadius, root.view.rightRadius,
               root.view.bladeRotation, root.view.bladeMirrored, root.pxPerMm, root.tipX, root.tipY,
               root.outlineOnly]
            : []
        onInputsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (root.isBlade) BladeShape.paint(ctx, root._blade())
        }
    }
}
