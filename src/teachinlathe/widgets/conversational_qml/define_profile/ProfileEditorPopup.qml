// ProfileEditorPopup.qml — full-screen editor for Define Profile primitives
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"

Popup {
    id: root

    parent: Overlay.overlay
    x: 0; y: 0
    width:  Overlay.overlay ? Overlay.overlay.width  : 800
    height: Overlay.overlay ? Overlay.overlay.height : 600
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose
    padding: 0

    // ── Public API ──────────────────────────────────────────────────────────────
    property int    opIndex:            -1
    property var    opData:             null
    property int    profileId:          0
    property string profileType:        "od"
    property bool   _loading:           false
    property var    primitives:         []
    property int    selectedPrimIndex:  -1
    property int    selectedBlendIndex: -1
    property int    _pendingDeleteIndex: -1

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    // ── Data functions ──────────────────────────────────────────────────────────
    function applyData(index, data) {
        _loading  = true
        opIndex   = index
        opData    = data || {}
        profileId   = opData.profile_id   !== undefined ? Math.round(Number(opData.profile_id)) : 0
        profileType = opData.profile_type !== undefined ? String(opData.profile_type) : "od"
        primitives  = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        selectedPrimIndex  = -1
        selectedBlendIndex = -1
        _loading  = false
        profileCanvas.resetView()
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
            profile_id:         root.profileId,
            profile_type:       root.profileType,
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
        if (idx <= 0) return
        var arr = JSON.parse(JSON.stringify(root.primitives))
        arr.splice(idx, 1)
        root.primitives = _renumber(arr)
        var newLen = root.primitives.length
        root.selectedPrimIndex  = (newLen === 0) ? -1 : Math.min(idx, newLen - 1)
        root.selectedBlendIndex = -1
        root.emitSave()
    }

    function _refEndCoords(refIdx) {
        if (refIdx < 0 || refIdx >= root.primitives.length) return { x: 0, z: 0 }
        var currentX = 0
        var currentZ = 0
        for (var i = 0; i <= refIdx; i++) {
            var p = root.primitives[i]
            if (!p) continue
            if (p.type === "startPoint") {
                currentX = p.x_start !== undefined ? Number(p.x_start) : 0
                currentZ = p.z_start !== undefined ? Number(p.z_start) : 0
            } else if (p.type === "lineTo") {
                var mode = String(p.input !== undefined ? p.input : "xz").toLowerCase()
                if (mode !== "xz" && mode !== "ax" && mode !== "az") mode = "xz"
                var endX = p.x_end !== undefined ? Number(p.x_end) : 0
                var endZ = p.z_end !== undefined ? Number(p.z_end) : 0
                var angleTan = Math.tan((Number(p.angle || 0) * Math.PI) / 180.0)
                if (mode === "az") {
                    currentX = currentX + 2.0 * (endZ - currentZ) * angleTan
                    currentZ = endZ
                } else if (mode === "ax") {
                    currentZ = Math.abs(angleTan) < 1e-12 ? currentZ : currentZ + ((endX - currentX) / 2.0) / angleTan
                    currentX = endX
                } else {
                    currentX = endX
                    currentZ = endZ
                }
            } else if (p.type === "arcTo") {
                currentX = p.x_end !== undefined ? Number(p.x_end) : 0
                currentZ = p.z_end !== undefined ? Number(p.z_end) : 0
            }
        }
        return { x: currentX, z: currentZ }
    }

    function primInserted(insertIdx, primType, refX, refZ) {
        var arr = JSON.parse(JSON.stringify(root.primitives))
        var rx = (refX !== undefined) ? refX : 0
        var rz = (refZ !== undefined) ? refZ : 0
        var newPrim
        if (primType === "lineTo") {
            newPrim = { type: "lineTo", primitive_id: 0, input: "xz", angle: 0,
                        x_end: rx, z_end: rz, blend: { type: "none" } }
        } else {
            newPrim = { type: "arcTo", primitive_id: 0, direction: "cw", arc_radius: 10,
                        x_end: rx, z_end: rz, x_center: 0, z_center: 0, blend: { type: "none" } }
        }
        var actualIdx = (insertIdx < 0 || insertIdx >= arr.length)
                        ? arr.length
                        : Math.max(1, insertIdx)
        arr.splice(actualIdx, 0, newPrim)
        root.primitives = _renumber(arr)
        root.selectedPrimIndex  = actualIdx
        root.selectedBlendIndex = -1
        root.emitSave()
    }

    onSelectedPrimIndexChanged:  Qt.callLater(_scrollToSelected)
    onSelectedBlendIndexChanged: Qt.callLater(_scrollToBlend)

    function _scrollToSelected() {
        if (root.selectedPrimIndex < 0) return
        _scrollTo(root.selectedPrimIndex, false)
    }
    function _scrollToBlend() {
        if (root.selectedBlendIndex < 0) return
        _scrollTo(root.selectedBlendIndex, true)
    }

    function _scrollTo(targetIdx, scrollBottom) {
        var col = primRepeater.parent
        if (!col) return
        for (var i = 0; i < col.children.length; i++) {
            var child = col.children[i]
            if (typeof child.mi !== "undefined" && child.mi === targetIdx) {
                var childY = child.y
                var childH = child.height
                var fl     = primScroll.contentItem
                var visTop = fl.contentY
                var visBot = visTop + primScroll.height
                if (scrollBottom) {
                    if (childY + childH > visBot)
                        fl.contentY = childY + childH - primScroll.height + 8
                    else if (childY < visTop)
                        fl.contentY = Math.max(0, childY - 8)
                } else {
                    if (childY < visTop)
                        fl.contentY = Math.max(0, childY - 8)
                    else if (childY + childH > visBot)
                        fl.contentY = childY + childH - primScroll.height + 8
                }
                break
            }
        }
    }

    // ── Validators ──────────────────────────────────────────────────────────────
    IntValidator { id: intVal; bottom: 1; top: 999 }

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
        z: 200

        background: Rectangle { radius: 10; color: "#202225"; border.color: "#3A3D41"; border.width: 1 }

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
                    onClicked: { root._pendingDeleteIndex = -1; deleteConfirmPopup.close() }
                }

                Button {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    text: "Delete"; width: 120; height: 40
                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font: parent.font }
                    background: Rectangle { radius: 4; color: parent.pressed ? "#B71C1C" : "#C62828" }
                    onClicked: {
                        if (root._pendingDeleteIndex > 0) root.primDeleted(root._pendingDeleteIndex)
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
        z: 200

        property string selectedType: ""
        onAboutToShow: selectedType = ""

        background: Rectangle { radius: 10; color: "#202225"; border.color: "#3A3D41"; border.width: 1 }

        contentItem: Column {
            id: addCol
            spacing: 12
            width: addPrimPopup.contentWidth
            padding: 16

            Text { text: "Add Primitive"; font.pixelSize: 18; font.bold: true; color: "white" }

            Row {
                spacing: 8
                Repeater {
                    model: [{ label: "LineTo", type: "lineTo" }, { label: "ArcTo", type: "arcTo" }]
                    delegate: Button {
                        readonly property bool isSelected: addPrimPopup.selectedType === modelData.type
                        width: 150; height: 44
                        text: modelData.label
                        font.pixelSize: 15
                        background: Rectangle {
                            radius: 4
                            color: { if (isSelected) return "#1E88E5"; if (parent.pressed) return "#3A4A5A"; if (parent.hovered) return "#2A3540"; return "#2D3035" }
                            border.color: isSelected ? "#1565C0" : "#4A4D52"; border.width: 1
                        }
                        contentItem: Text { text: parent.text; font: parent.font; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: addPrimPopup.selectedType = (addPrimPopup.selectedType === modelData.type) ? "" : modelData.type
                    }
                }
            }

            Rectangle { width: addPrimPopup.contentWidth - 32; height: 1; color: "#3A3D41" }

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
                        enabled: addPrimPopup.selectedType !== "" && root.selectedPrimIndex > 0
                        onClicked: {
                            var ref = root._refEndCoords(root.selectedPrimIndex - 1)
                            root.primInserted(root.selectedPrimIndex, addPrimPopup.selectedType, ref.x, ref.z)
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
                            var ref = root._refEndCoords(root.selectedPrimIndex)
                            root.primInserted(idx, addPrimPopup.selectedType, ref.x, ref.z)
                            addPrimPopup.close()
                        }
                    }
                }
            }
        }
    }

    // ── Background ──────────────────────────────────────────────────────────────
    background: Rectangle { color: "#16191e" }

    // ── Main content ────────────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: 0

        // ── Title bar ────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "#f5f7fb"

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width; height: 1
                color: "#d6dce7"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20; anchors.rightMargin: 20
                spacing: 12

                // Back button
                Button {
                    text: "← Back"
                    implicitHeight: 40
                    Layout.alignment: Qt.AlignVCenter
                    contentItem: Text {
                        text: parent.text; color: "#1e2430"
                        font.pixelSize: 15; font.family: "Noto Sans"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment:   Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.pressed ? "#e5edf9" : parent.hovered ? "#eef3fb" : "#eef3fb"
                        radius: 6; border.color: "#c5d0df"; border.width: 1
                    }
                    onClicked: root.close()
                }

                // Title
                Text {
                    Layout.fillWidth: true
                    text: {
                        var typeStr = (root.profileType === "id") ? "ID" : "OD"
                        var opNum = (root.opData && root.opData.order !== undefined) ? root.opData.order : ""
                        return "Define " + typeStr + " Profile" + (opNum !== "" ? " Op #" + opNum : "")
                    }
                    color: "#1e2430"
                    font.pixelSize: 17; font.bold: true; font.family: "Noto Sans"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment:   Text.AlignVCenter
                }

                // Done button
                Button {
                    text: "Done"
                    implicitHeight: 40
                    Layout.alignment: Qt.AlignVCenter
                    contentItem: Text {
                        text: parent.text; color: "white"
                        font.pixelSize: 15; font.family: "Noto Sans"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment:   Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.pressed ? "#25673a" : parent.hovered ? "#348a50" : "#2d7d46"
                        radius: 6; border.color: "#3fb950"; border.width: 1
                    }
                    onClicked: root.close()
                }
            }
        }

        // ── Editor area: 30% list | 70% canvas ───────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // ── Left panel: primitive list ──────────────────────────────────
            ColumnLayout {
                id: leftPanel
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: parent.width * 0.30
                spacing: 8
                clip: true

                // Profile ID + Type row
                RowLayout {
                    Layout.leftMargin: 10; Layout.rightMargin: 10; Layout.topMargin: 8
                    spacing: 12

                    Label { text: "Profile ID"; font.pixelSize: 15 }
                    NumpadField {
                        Layout.preferredWidth: 70
                        settingName: "defineProfile.profile_id"
                        validatorObject: intVal
                        value: root.profileId
                        formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                        hAlign: Text.AlignRight
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.profileId = Math.round(value); root.emitSave() }
                    }

                    Rectangle { width: 1; height: 20; color: "#555" }

                    ButtonGroup { id: profileTypeGroup }
                    RadioButton {
                        text: "OD"; font.pixelSize: 14
                        checked: root.profileType === "od"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "od"; root.emitSave() }
                    }
                    RadioButton {
                        text: "ID"; font.pixelSize: 14
                        checked: root.profileType === "id"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "id"; root.emitSave() }
                    }
                }

                // Scrollable primitive cards
                ScrollView {
                    id: primScroll
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    Layout.leftMargin: 6; Layout.rightMargin: 6
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    contentWidth: availableWidth

                    Column {
                        width: primScroll.availableWidth
                        spacing: 6
                        topPadding: 2; bottomPadding: 4

                        Repeater {
                            id: primRepeater
                            model: root.primitives

                            delegate: Column {
                                property var md: modelData
                                property int mi: index
                                width: parent ? parent.width : 0
                                spacing: 4

                                onMdChanged: {
                                    if (primLdr.item)  primLdr.item.primData  = md
                                    if (blendLdr.item) blendLdr.item.primData = md
                                }

                                Loader {
                                    id: primLdr
                                    width: parent.width
                                    sourceComponent: {
                                        if (!md) return null
                                        if (md.type === "startPoint") return startPointComp
                                        if (md.type === "lineTo")     return lineToComp
                                        if (md.type === "arcTo")      return arcToComp
                                        return null
                                    }
                                    onLoaded: {
                                        item.primData   = md
                                        item.primIdx    = mi
                                        item.primCount  = Qt.binding(function() { return root.primitives.length })
                                        item.isSelected = Qt.binding(function() { return root.selectedPrimIndex === mi })
                                        item.tapped.connect(function() {
                                            root.selectedPrimIndex  = mi
                                            root.selectedBlendIndex = -1
                                        })
                                        item.primUpdated.connect(root.primUpdated)
                                        item.openNumPadRequested.connect(root.openNumPadRequested)
                                        if (typeof item.deleteRequested !== "undefined") {
                                            item.deleteRequested.connect(function(idx) {
                                                root._pendingDeleteIndex = idx
                                                deleteConfirmPopup.open()
                                            })
                                        }
                                    }
                                }

                                Loader {
                                    id: blendLdr
                                    width: parent.width
                                    active:  md !== null && md !== undefined &&
                                             md.blend !== undefined && md.blend !== null &&
                                             md.blend.type !== "none"
                                    visible: active
                                    sourceComponent: {
                                        if (!md || !md.blend) return null
                                        if (md.blend.type === "undercut_din509") return undercutDin509BlendComp
                                        if (md.blend.type === "chamfer" || md.blend.type === "fillet") return chamferFilletBlendComp
                                        return null
                                    }
                                    onLoaded: {
                                        item.primData   = md
                                        item.primIdx    = mi
                                        item.isSelected = Qt.binding(function() { return root.selectedBlendIndex === mi })
                                        item.tapped.connect(function() {
                                            root.selectedBlendIndex = mi
                                            root.selectedPrimIndex  = -1
                                        })
                                        item.primUpdated.connect(root.primUpdated)
                                        item.openNumPadRequested.connect(root.openNumPadRequested)
                                        item.blendClearRequested.connect(function(idx) {
                                            var d = JSON.parse(JSON.stringify(root.primitives[idx]))
                                            d.blend = { type: "none" }
                                            root.primUpdated(idx, d)
                                            if (root.selectedBlendIndex === idx)
                                                root.selectedBlendIndex = -1
                                        })
                                    }
                                }
                            }
                        }
                    }
                }

                // Add New button
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: 8
                    text: "Add New"
                    font.pixelSize: 13
                    implicitWidth: 120
                    onClicked: {
                        var hasStart = root.primitives.length > 0 && root.primitives[0].type === "startPoint"
                        if (!hasStart) {
                            var arr = JSON.parse(JSON.stringify(root.primitives))
                            arr.unshift({ type: "startPoint", primitive_id: 0,
                                          x_start: 0, z_start: 0, blend: { type: "none" } })
                            root.primitives     = _renumber(arr)
                            root.selectedPrimIndex  = 0
                            root.selectedBlendIndex = -1
                            root.emitSave()
                        } else {
                            addPrimPopup.open()
                        }
                    }
                }
            }

            // Vertical separator
            Rectangle {
                anchors { left: leftPanel.right; top: parent.top; bottom: parent.bottom }
                width: 1; color: "#3A3D41"
            }

            // ── Right panel: canvas ─────────────────────────────────────────
            ColumnLayout {
                anchors {
                    left:   leftPanel.right; right:  parent.right
                    top:    parent.top;      bottom: parent.bottom
                    leftMargin: 14; rightMargin: 10
                    topMargin: 8;   bottomMargin: 8
                }
                spacing: 6

                ProfileCanvas {
                    id: profileCanvas
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    primitives:         root.primitives
                    profileType:        root.profileType
                    selectedPrimIndex:  root.selectedPrimIndex
                    selectedBlendIndex: root.selectedBlendIndex
                    onPrimitiveSelected: function(idx) {
                        root.selectedPrimIndex  = idx
                        root.selectedBlendIndex = -1
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.color: "#555"; border.width: 1
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Button { text: "Zoom In";       Layout.fillWidth: true; implicitHeight: 34; font.pixelSize: 13; onClicked: profileCanvas.zoomIn() }
                    Button { text: "Zoom Out";      Layout.fillWidth: true; implicitHeight: 34; font.pixelSize: 13; onClicked: profileCanvas.zoomOut() }
                    Button { text: "Fit to Screen"; Layout.fillWidth: true; implicitHeight: 34; font.pixelSize: 13; onClicked: profileCanvas.fitToScreen() }
                }
            }
        }
    }

    // ── Card component references ────────────────────────────────────────────────
    Component { id: startPointComp; StartPointCard {} }
    Component { id: lineToComp;     LineToCard {}     }
    Component { id: arcToComp;      ArcToCard {}      }
    Component { id: chamferFilletBlendComp; ChamferFilletBlendCard {} }
    Component { id: undercutDin509BlendComp; UndercutDin509BlendCard {} }
}
