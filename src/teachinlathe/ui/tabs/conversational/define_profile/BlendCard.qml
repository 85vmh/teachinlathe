// BlendCard.qml — a blend's card, in the colours the canvas draws a selected blend
// in: its icon, turned to its corner, and its fields.
import QtQuick
import theme

ProfileCard {
    id: root

    // "chamfer", "fillet" or "undercut_din509"
    property string blendType: "chamfer"

    color:        Theme.blendSoft
    border.color: Theme.blendStroke

    icon: BlendIcon {
        anchors.centerIn: parent
        blendType: root.blendType
        corner: root.corner
    }
}
