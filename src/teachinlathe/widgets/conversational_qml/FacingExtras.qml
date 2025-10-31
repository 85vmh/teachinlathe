// FacingExtras.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GroupBox {
    id: root
    font.pixelSize: 16
    title: "Facing Extras"
    Layout.fillWidth: true
    Layout.minimumWidth: 360
    Layout.preferredWidth: 520

    // bridge
    property int  opIndex: -1
    property var  opData: null

    signal saveRequested(var updated)

    property bool z_end_becomes_new_z0: false
    property bool _loading: false

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}
        z_end_becomes_new_z0 = !!(opData.z_end_becomes_new_z0 !== undefined ? opData.z_end_becomes_new_z0 : false)
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        var payload = {
            order: (opData && opData.order !== undefined) ? opData.order : 0,
            type: (opData && opData.type) ? opData.type : "",
            generate_gcode: (opData && opData.generate_gcode !== undefined) ? opData.generate_gcode : true,
            is_optional_block: (opData && opData.is_optional_block !== undefined) ? opData.is_optional_block : false,
            z_end_becomes_new_z0: !!z_end_becomes_new_z0
        }
        root.saveRequested({index: opIndex, payload: payload})
    }

    CheckBox {
        text: "When finished, set 'Z End' as the new datum (Z0)"
        font.pixelSize: 16
        checked: root.z_end_becomes_new_z0
        onToggled: { root.z_end_becomes_new_z0 = checked; root.emitSave() }
    }
}
