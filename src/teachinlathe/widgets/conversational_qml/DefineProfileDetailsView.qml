// DefineProfileDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData:  null
    property int selectedPrimIndex: -1

    property int  profileId: 0
    property bool _loading:  false
    property var  primitives: []

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        _loading  = true
        opIndex   = index
        opData    = data || {}
        profileId = opData.profile_id !== undefined ? Math.round(Number(opData.profile_id)) : 0
        primitives = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        selectedPrimIndex = -1
        _loading  = false
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        opData = out
        return out
    }

    function emitSave() {
        if (_loading) return
        var merged = root.mergeIntoOp({
            profile_id: root.profileId,
            profile_primitives: root.primitives
        })
        root.saveRequested({ index: root.opIndex, payload: merged })
    }

    function _renumber(arr) {
        for (var i = 0; i < arr.length; i++)
            arr[i].primitive_id = i + 1
        return arr
    }

    function primUpdated(idx, newData) {
        var arr = JSON.parse(JSON.stringify(root.primitives))
        arr[idx] = newData
        root.primitives = _renumber(arr)
        root.emitSave()
    }

    function primDeleted(idx) {
        if (idx === 0) return  // protect startPoint
        var arr = JSON.parse(JSON.stringify(root.primitives))
        arr.splice(idx, 1)
        root.primitives = _renumber(arr)
        root.emitSave()
    }

    function primAdded(primType) {
        var arr = JSON.parse(JSON.stringify(root.primitives))
        var newPrim
        if (primType === "lineTo") {
            newPrim = { type: "lineTo", primitive_id: 0,
                        x_end: 0, z_end: 0, blend: { type: "none" } }
        } else {
            newPrim = { type: "arcTo", primitive_id: 0, direction: "cw", arc_radius: 10,
                        x_end: 0, z_end: 0, x_center: 0, z_center: 0, blend: { type: "none" } }
        }
        arr.push(newPrim)
        root.primitives = _renumber(arr)
        root.emitSave()
    }

    IntValidator    { id: intVal; bottom: 1; top: 999 }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    // ── Blend cycling helper ────────────────────────────────────────────────────
    function blendType(pd) {
        return (pd && pd.blend && pd.blend.type) ? pd.blend.type : "none"
    }
    function cycleBlend(pd, idx) {
        var d   = JSON.parse(JSON.stringify(pd))
        var cur = blendType(d)
        var nxt = cur === "none" ? "chamfer" : (cur === "chamfer" ? "fillet" : "none")
        if (!d.blend) d.blend = {}
        d.blend.type = nxt
        if (nxt === "chamfer" && d.blend.chamfer_width  === undefined) d.blend.chamfer_width  = 1.0
        if (nxt === "fillet"  && d.blend.fillet_radius  === undefined) d.blend.fillet_radius  = 1.0
        root.primUpdated(idx, d)
    }
    function blendValue(pd) {
        if (!pd || !pd.blend) return 0
        if (pd.blend.type === "chamfer") return pd.blend.chamfer_width  !== undefined ? pd.blend.chamfer_width  : 0
        if (pd.blend.type === "fillet")  return pd.blend.fillet_radius  !== undefined ? pd.blend.fillet_radius  : 0
        return 0
    }
    function commitBlend(pd, idx, v) {
        var d = JSON.parse(JSON.stringify(pd))
        if (!d.blend) d.blend = { type: "chamfer" }
        if (d.blend.type === "chamfer") d.blend.chamfer_width  = v
        else if (d.blend.type === "fillet")  d.blend.fillet_radius  = v
        root.primUpdated(idx, d)
    }

    // ── Card: StartPoint ────────────────────────────────────────────────────────
    Component {
        id: startPointComp
        Rectangle {
            property var primData: ({})
            property int primIdx:  0

            color: "white"; radius: 4
            border.color: "#cccccc"; border.width: 1
            height: spCol.implicitHeight + 24

            ColumnLayout {
                id: spCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

                // Header row (no delete on startPoint)
                Text {
                    Layout.fillWidth: true
                    text: (primIdx + 1) + ". Start Point"
                    font.pixelSize: 14; font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

                // X Start
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "X Start"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "sp." + primIdx + ".x_start"
                        validatorObject: dblVal
                        value: primData.x_start !== undefined ? primData.x_start : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.x_start = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }

                // Z Start
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Z Start"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "sp." + primIdx + ".z_start"
                        validatorObject: dblVal
                        value: primData.z_start !== undefined ? primData.z_start : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.z_start = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }
            }
        }
    }

    // ── Card: LineTo ────────────────────────────────────────────────────────────
    Component {
        id: lineToComp
        Rectangle {
            property var primData: ({})
            property int primIdx:  0

            color: "white"; radius: 4
            border.color: "#cccccc"; border.width: 1
            height: ltCol.implicitHeight + 24

            ColumnLayout {
                id: ltCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

                // Header row with delete button
                RowLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text {
                        Layout.fillWidth: true
                        text: (primIdx + 1) + ". LineTo"
                        font.pixelSize: 14; font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Button {
                        text: "✕"; font.pixelSize: 11; padding: 2
                        Layout.preferredWidth: 24; Layout.preferredHeight: 24
                        onClicked: root.primDeleted(primIdx)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

                // X End
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "X End"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "lt." + primIdx + ".x_end"
                        validatorObject: dblVal
                        value: primData.x_end !== undefined ? primData.x_end : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.x_end = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }

                // Z End
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Z End"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "lt." + primIdx + ".z_end"
                        validatorObject: dblVal
                        value: primData.z_end !== undefined ? primData.z_end : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.z_end = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }

                // Blend separator
                Rectangle { Layout.fillWidth: true; height: 1; color: "#c0c8d8" }

                // Blend row
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Blend:"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    Button {
                        text: root.blendType(primData)
                        font.pixelSize: 12; Layout.preferredWidth: 80
                        onClicked: root.cycleBlend(primData, primIdx)
                    }
                    NumpadField {
                        visible: root.blendType(primData) !== "none"
                        Layout.preferredWidth: 90
                        settingName: "lt." + primIdx + ".blend_val"
                        validatorObject: dblVal
                        value: root.blendValue(primData)
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.commitBlend(primData, primIdx, value)
                    }
                }
            }
        }
    }

    // ── Card: ArcTo ─────────────────────────────────────────────────────────────
    Component {
        id: arcToComp
        Rectangle {
            property var primData: ({})
            property int primIdx:  0

            color: "white"; radius: 4
            border.color: "#cccccc"; border.width: 1
            height: atCol.implicitHeight + 24

            ColumnLayout {
                id: atCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

                // Header row with delete button
                RowLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text {
                        Layout.fillWidth: true
                        text: (primIdx + 1) + ". ArcTo"
                        font.pixelSize: 14; font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Button {
                        text: "✕"; font.pixelSize: 11; padding: 2
                        Layout.preferredWidth: 24; Layout.preferredHeight: 24
                        onClicked: root.primDeleted(primIdx)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

                // Arc direction toggle
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Arc Type:"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    Button {
                        text: "CW"; font.pixelSize: 12; Layout.preferredWidth: 50
                        highlighted: primData.direction === "cw"
                        onClicked: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.direction = "cw"
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button {
                        text: "CCW"; font.pixelSize: 12; Layout.preferredWidth: 50
                        highlighted: primData.direction === "ccw"
                        onClicked: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.direction = "ccw"
                            root.primUpdated(primIdx, d)
                        }
                    }
                }

                // Arc Radius
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Radius"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "at." + primIdx + ".arc_radius"
                        validatorObject: dblVal
                        value: primData.arc_radius !== undefined ? primData.arc_radius : 10
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.arc_radius = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                }

                // X End
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "X End"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "at." + primIdx + ".x_end"
                        validatorObject: dblVal
                        value: primData.x_end !== undefined ? primData.x_end : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.x_end = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }

                // Z End
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Z End"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "at." + primIdx + ".z_end"
                        validatorObject: dblVal
                        value: primData.z_end !== undefined ? primData.z_end : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.z_end = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                    Button { text: "Teach"; enabled: false; font.pixelSize: 12; opacity: 0.5
                             Layout.preferredWidth: 60 }
                }

                // X Center
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "X Center"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "at." + primIdx + ".x_center"
                        validatorObject: dblVal
                        value: primData.x_center !== undefined ? primData.x_center : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.x_center = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                }

                // Z Center
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Z Center"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    NumpadField {
                        Layout.preferredWidth: 110
                        settingName: "at." + primIdx + ".z_center"
                        validatorObject: dblVal
                        value: primData.z_center !== undefined ? primData.z_center : 0
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.z_center = value
                            root.primUpdated(primIdx, d)
                        }
                    }
                }

                // Blend separator
                Rectangle { Layout.fillWidth: true; height: 1; color: "#c0c8d8" }

                // Blend row
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Label { text: "Blend:"; font.pixelSize: 14; Layout.preferredWidth: 70 }
                    Button {
                        text: root.blendType(primData)
                        font.pixelSize: 12; Layout.preferredWidth: 80
                        onClicked: root.cycleBlend(primData, primIdx)
                    }
                    NumpadField {
                        visible: root.blendType(primData) !== "none"
                        Layout.preferredWidth: 90
                        settingName: "at." + primIdx + ".blend_val"
                        validatorObject: dblVal
                        value: root.blendValue(primData)
                        formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                        hAlign: Text.AlignRight; fontPixelSize: 14
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.commitBlend(primData, primIdx, value)
                    }
                }
            }
        }
    }

    // ── Main layout ─────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 16

        Label {
            text: (opData && opData.type)
                  ? ("Define Profile — Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : "Define Profile"
            font.pixelSize: 18; font.bold: true
            bottomPadding: 4
        }

        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // ── Left panel: Profile ID + scrollable cards + add buttons ──────────
            ColumnLayout {
                id: leftPanel
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: 480
                spacing: 8

                // Profile ID row
                RowLayout {
                    spacing: 12
                    Label { text: "Profile ID"; font.pixelSize: 16 }
                    NumpadField {
                        Layout.preferredWidth: 80
                        settingName: "defineProfile.profile_id"
                        validatorObject: intVal
                        value: root.profileId
                        formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                        hAlign: Text.AlignRight; fontPixelSize: 16
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.profileId = Math.round(value); root.emitSave() }
                    }
                }

                // Scrollable cards
                ScrollView {
                    id: primScroll
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    contentWidth: availableWidth

                    Column {
                        width: primScroll.availableWidth
                        spacing: 8
                        topPadding: 2
                        bottomPadding: 4

                        Repeater {
                            model: root.primitives

                            delegate: Loader {
                                property var md: modelData
                                property int mi: index
                                width: parent ? parent.width : 0

                                sourceComponent: {
                                    if (!md) return null
                                    if (md.type === "startPoint") return startPointComp
                                    if (md.type === "lineTo")     return lineToComp
                                    if (md.type === "arcTo")      return arcToComp
                                    return null
                                }

                                onLoaded: {
                                    item.primData = md
                                    item.primIdx  = mi
                                }
                            }
                        }
                    }
                }

                // Add buttons row
                RowLayout {
                    spacing: 8
                    Button {
                        text: "+ LineTo"
                        font.pixelSize: 14
                        onClicked: root.primAdded("lineTo")
                    }
                    Button {
                        text: "+ ArcTo"
                        font.pixelSize: 14
                        onClicked: root.primAdded("arcTo")
                    }
                }
            }

            // ── Right panel: profile canvas ──────────────────────────────────────
            ProfileCanvas {
                id: profileCanvas
                anchors {
                    left:   leftPanel.right
                    right:  parent.right
                    top:    parent.top
                    bottom: parent.bottom
                    leftMargin: 12
                }
                primitives:        root.primitives
                selectedPrimIndex: root.selectedPrimIndex
                onPrimitiveSelected: function(idx) { root.selectedPrimIndex = idx }

                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: "#cccccc"
                    border.width: 1
                }
            }
        }
    }
}
