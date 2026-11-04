// ChamferFilletBlendCard.qml
import QtQuick
import QtQuick.Layouts

BlendCard {
    id: root

    readonly property string _blendType:
        (primData && primData.blend && primData.blend.type) ? primData.blend.type : "none"
    readonly property real _blendValue: {
        if (!primData || !primData.blend) return 0
        if (primData.blend.type === "chamfer")
            return primData.blend.chamfer_width !== undefined ? primData.blend.chamfer_width : 0
        if (primData.blend.type === "fillet")
            return primData.blend.fillet_radius !== undefined ? primData.blend.fillet_radius : 0
        return 0
    }

    function _commitBlend(v) {
        var d = JSON.parse(JSON.stringify(primData))
        if (!d.blend) d.blend = { type: "chamfer" }
        if (d.blend.type === "chamfer") d.blend.chamfer_width = v
        else if (d.blend.type === "fillet") d.blend.fillet_radius = v
        root.primUpdated(primIdx, d)
    }

    blendType: _blendType === "chamfer" ? "chamfer" : "fillet"

    ProfileField {
        label: root._blendType === "chamfer" ? "Width" : "Radius"
        settingName: root._blendType === "chamfer" ? "profiling.chamfer_width" : "profiling.fillet_radius"
        value: root._blendValue
        onOpenRequested: function(field) { root.openNumPadRequested(field) }
        onCommitted: function(value) { root._commitBlend(value) }
    }

    // the second field's place
    Item { Layout.fillWidth: true; Layout.preferredWidth: 0 }
}
