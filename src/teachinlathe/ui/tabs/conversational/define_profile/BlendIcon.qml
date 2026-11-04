// BlendIcon.qml — a blend's icon, turned to the corner it is on (``corner``, from
// Geometry.cornersOf): a chamfer's and a fillet's are rotated, their two sides
// being alike; an undercut's, whose are not, flipped.
import QtQuick
import common

Image {
    id: root

    // "chamfer", "fillet" or "undercut_din509"
    property string blendType: "chamfer"
    property var corner: null

    readonly property bool _undercut: blendType === "undercut_din509"

    width: CardMetrics.iconSize
    height: CardMetrics.iconSize
    sourceSize.width: width
    sourceSize.height: height
    source: Images.url(_undercut ? "undercut.svg" : blendType + ".svg")
    rotation: !_undercut && corner ? corner.rotation : 0
    transform: Scale {
        origin.x: root.width / 2
        origin.y: root.height / 2
        xScale: root._undercut && root.corner ? root.corner.scaleX : 1
        yScale: root._undercut && root.corner ? root.corner.scaleY : 1
    }
    fillMode: Image.PreserveAspectFit
    smooth: true
}
