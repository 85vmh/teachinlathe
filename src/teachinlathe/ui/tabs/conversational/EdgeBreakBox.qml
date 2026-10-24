// EdgeBreakBox.qml — Parting's edge break, laid over the profile canvas:
// none, a chamfer or a fillet, and its size (BlendPicker); with none,
// "<- Edge Break" in their place.
import QtQuick
import theme

CanvasBox {
    id: root

    property string label: "Edge Break"
    property color  color: Theme.foreground
    property string blendType: "none"     // "none" | "chamfer" | "fillet"
    property real   chamferWidth: 0.0
    property real   filletRadius: 0.0

    // a whole edge_break, as the op keeps it
    signal edited(var edgeBreak)
    signal openNumPadRequested(var field)

    accent: color

    BlendPicker {
        blendType: root.blendType
        chamferWidth: root.chamferWidth
        filletRadius: root.filletRadius
        // the part's edge as Parting has it
        iconsFlipped: true
        // with none, what the drop-down is for, in the box's colour
        noneText: "\u2190 " + root.label
        noneTextColor: root.color
        chamferSettingName: "parting.edge_break_chamfer"
        filletSettingName: "parting.edge_break_radius"
        onEdited: function(blendType, chamferWidth, filletRadius) {
            root.edited({ blend_type: blendType, chamfer_width: chamferWidth, fillet_radius: filletRadius })
        }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
    }
}
