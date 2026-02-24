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
    property int  _pendingDeleteIndex: -1

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

    // Called from the confirmed delete popup
    function primDeleted(idx) {
        if (idx <= 0) return
        var arr = JSON.parse(JSON.stringify(root.primitives))
        arr.splice(idx, 1)
        root.primitives = _renumber(arr)
        var newLen = root.primitives.length
        root.selectedPrimIndex = (newLen === 0) ? -1 : Math.min(idx, newLen - 1)
        root.emitSave()
    }

    // insertIdx < 0 or >= arr.length → append; never inserts before startPoint (idx 0)
    function primInserted(insertIdx, primType) {
        var arr = JSON.parse(JSON.stringify(root.primitives))
        var newPrim
        if (primType === "lineTo") {
            newPrim = { type: "lineTo", primitive_id: 0,
                        x_end: 0, z_end: 0, blend: { type: "none" } }
        } else {
            newPrim = { type: "arcTo", primitive_id: 0, direction: "cw", arc_radius: 10,
                        x_end: 0, z_end: 0, x_center: 0, z_center: 0, blend: { type: "none" } }
        }
        var actualIdx = (insertIdx < 0 || insertIdx >= arr.length)
                        ? arr.length
                        : Math.max(1, insertIdx)
        arr.splice(actualIdx, 0, newPrim)
        root.primitives = _renumber(arr)
        root.selectedPrimIndex = actualIdx
        root.emitSave()
    }

    // ── Blend helpers ───────────────────────────────────────────────────────────
    function blendType(pd) {
        return (pd && pd.blend && pd.blend.type) ? pd.blend.type : "none"
    }
    function cycleBlend(pd, idx) {
        var d   = JSON.parse(JSON.stringify(pd))
        var cur = blendType(d)
        var nxt = cur === "none" ? "chamfer" : (cur === "chamfer" ? "fillet" : "none")
        if (!d.blend) d.blend = {}
        d.blend.type = nxt
        if (nxt === "chamfer" && d.blend.chamfer_width === undefined) d.blend.chamfer_width = 1.0
        if (nxt === "fillet"  && d.blend.fillet_radius === undefined) d.blend.fillet_radius = 1.0
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

    // ── Scroll selected card into view ──────────────────────────────────────────
    onSelectedPrimIndexChanged: Qt.callLater(_scrollToSelected)

    function _scrollToSelected() {
        if (root.selectedPrimIndex < 0) return
        var col = primRepeater.parent
        if (!col) return
        for (var i = 0; i < col.children.length; i++) {
            var child = col.children[i]
            if (typeof child.mi !== "undefined" && child.mi === root.selectedPrimIndex) {
                var childY = child.y
                var childH = child.height
                var fl     = primScroll.contentItem
                var visTop = fl.contentY
                var visBot = visTop + primScroll.height
                if (childY < visTop)
                    fl.contentY = Math.max(0, childY - 8)
                else if (childY + childH > visBot)
                    fl.contentY = childY + childH - primScroll.height + 8
                break
            }
        }
    }

    IntValidator    { id: intVal; bottom: 1; top: 999 }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    // ── Delete confirm popup ────────────────────────────────────────────────────
    Popup {
        id: deleteConfirmPopup
        parent: Overlay.overlay
        modal: true; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: parent
        contentWidth: 360
        contentHeight: delCol.implicitHeight
        padding: 0

        background: Rectangle {
            radius: 10; color: "#202225"
            border.color: "#3A3D41"; border.width: 1
        }

        contentItem: Column {
            id: delCol
            spacing: 12
            width: deleteConfirmPopup.contentWidth
            padding: 16

            Text { text: "Delete Primitive"; font.pixelSize: 18; font.bold: true; color: "white" }

            Text {
                width: deleteConfirmPopup.contentWidth - 32
                text: {
                    var idx = root._pendingDeleteIndex
                    if (idx > 0 && idx < root.primitives.length) {
                        var p = root.primitives[idx]
                        return "Delete primitive " + idx + " (" + (p ? p.type : "") + ")?"
                    }
                    return "Delete this primitive?"
                }
                font.pixelSize: 15; color: "#cccccc"; wrapMode: Text.WordWrap
            }

            Rectangle { width: deleteConfirmPopup.contentWidth - 32; height: 1; color: "#3A3D41" }

            Item {
                width: deleteConfirmPopup.contentWidth - 32; height: 44

                Button {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    text: "Cancel"; width: 100; height: 40
                    onClicked: {
                        root._pendingDeleteIndex = -1
                        deleteConfirmPopup.close()
                    }
                }

                Button {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    text: "Delete"; width: 120; height: 40
                    contentItem: Text {
                        text: parent.text; color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font: parent.font
                    }
                    background: Rectangle {
                        radius: 4
                        color: parent.pressed ? "#B71C1C" : "#C62828"
                    }
                    onClicked: {
                        if (root._pendingDeleteIndex > 0)
                            root.primDeleted(root._pendingDeleteIndex)
                        root._pendingDeleteIndex = -1
                        deleteConfirmPopup.close()
                    }
                }
            }
        }
    }

    // ── Add primitive popup ─────────────────────────────────────────────────────
    Popup {
        id: addPrimPopup
        parent: Overlay.overlay
        modal: true; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: parent
        contentWidth: 420
        contentHeight: addCol.implicitHeight
        padding: 0

        property string selectedType: ""
        onAboutToShow: selectedType = ""

        background: Rectangle {
            radius: 10; color: "#202225"
            border.color: "#3A3D41"; border.width: 1
        }

        contentItem: Column {
            id: addCol
            spacing: 12
            width: addPrimPopup.contentWidth
            padding: 16

            Text { text: "Add Primitive"; font.pixelSize: 18; font.bold: true; color: "white" }

            // Type selector buttons
            Row {
                spacing: 8

                Repeater {
                    model: [
                        { label: "LineTo", type: "lineTo" },
                        { label: "ArcTo",  type: "arcTo"  }
                    ]
                    delegate: Button {
                        readonly property bool isSelected: addPrimPopup.selectedType === modelData.type
                        width: 150; height: 44
                        text: modelData.label
                        font.pixelSize: 15

                        background: Rectangle {
                            radius: 4
                            color: {
                                if (isSelected)      return "#1E88E5"
                                if (parent.pressed)  return "#3A4A5A"
                                if (parent.hovered)  return "#2A3540"
                                return "#2D3035"
                            }
                            border.color: isSelected ? "#1565C0" : "#4A4D52"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text; font: parent.font; color: "white"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            addPrimPopup.selectedType =
                                (addPrimPopup.selectedType === modelData.type) ? "" : modelData.type
                        }
                    }
                }
            }

            Rectangle { width: addPrimPopup.contentWidth - 32; height: 1; color: "#3A3D41" }

            // Footer: Cancel | Insert Above | Insert Below
            Item {
                width: addPrimPopup.contentWidth - 32; height: 44

                Button {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    text: "Cancel"; width: 100; height: 40
                    onClicked: addPrimPopup.close()
                }

                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Button {
                        text: "Insert Above"; width: 130; height: 40
                        // enabled only when a type is chosen AND something other than startPoint is selected
                        enabled: addPrimPopup.selectedType !== "" && root.selectedPrimIndex > 0
                        onClicked: {
                            root.primInserted(root.selectedPrimIndex, addPrimPopup.selectedType)
                            addPrimPopup.close()
                        }
                    }

                    Button {
                        text: "Insert Below"; width: 130; height: 40
                        enabled: addPrimPopup.selectedType !== ""
                        onClicked: {
                            var idx = root.selectedPrimIndex < 0
                                      ? root.primitives.length
                                      : root.selectedPrimIndex + 1
                            root.primInserted(idx, addPrimPopup.selectedType)
                            addPrimPopup.close()
                        }
                    }
                }
            }
        }
    }

    // ── Card: StartPoint ────────────────────────────────────────────────────────
    Component {
        id: startPointComp
        Rectangle {
            property var primData: ({})
            property int primIdx:  0

            readonly property bool isSelected: root.selectedPrimIndex === primIdx
            color:  isSelected ? "#dbeafe" : "white"
            radius: 4
            border.color: isSelected ? "#3b82f6" : "#cccccc"
            border.width: isSelected ? 2 : 1
            height: spCol.implicitHeight + 24

            TapHandler { onTapped: root.selectedPrimIndex = primIdx }

            ColumnLayout {
                id: spCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: (primIdx + 1) + ". Start Point"
                    font.pixelSize: 14; font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

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

            readonly property bool isSelected: root.selectedPrimIndex === primIdx
            color:  isSelected ? "#dbeafe" : "white"
            radius: 4
            border.color: isSelected ? "#3b82f6" : "#cccccc"
            border.width: isSelected ? 2 : 1
            height: ltCol.implicitHeight + 24

            TapHandler { onTapped: root.selectedPrimIndex = primIdx }

            ColumnLayout {
                id: ltCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

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
                        onClicked: {
                            root._pendingDeleteIndex = primIdx
                            deleteConfirmPopup.open()
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

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

                Rectangle { Layout.fillWidth: true; height: 1; color: "#c0c8d8" }

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

            readonly property bool isSelected: root.selectedPrimIndex === primIdx
            color:  isSelected ? "#dbeafe" : "white"
            radius: 4
            border.color: isSelected ? "#3b82f6" : "#cccccc"
            border.width: isSelected ? 2 : 1
            height: atCol.implicitHeight + 24

            TapHandler { onTapped: root.selectedPrimIndex = primIdx }

            ColumnLayout {
                id: atCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 8

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
                        onClicked: {
                            root._pendingDeleteIndex = primIdx
                            deleteConfirmPopup.open()
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e0e0" }

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

                Rectangle { Layout.fillWidth: true; height: 1; color: "#c0c8d8" }

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

            // ── Left panel ───────────────────────────────────────────────────────
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
                            id: primRepeater
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

                // Add New button — centered
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Add New"
                    font.pixelSize: 14
                    implicitWidth: 140
                    onClicked: addPrimPopup.open()
                }
            }

            // ── Right panel: canvas ──────────────────────────────────────────────
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
