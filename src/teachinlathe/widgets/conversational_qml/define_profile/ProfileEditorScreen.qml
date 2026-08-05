// ProfileEditorScreen.qml — full-screen editor for Define Profile primitives
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"

Item {
    id: root
    objectName: "profileEditorScreen"
    anchors.fill: parent

    // ── Public API ──────────────────────────────────────────────────────────────
    property int    opIndex:             -1
    property var    opData:              null
    property int    profileId:           0
    property string profileType:         "od"
    property bool   _loading:            false
    property var    primitives:          []
    property int    selectedPrimIndex:   -1
    property int    selectedBlendIndex:  -1
    property int    _pendingDeleteIndex: -1

    signal backRequested()
    signal updateDefineProfile(int opIdx, var payload)
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

    function emitSave() {
        if (_loading) return
        var merged = JSON.parse(JSON.stringify(opData || {}))
        merged.profile_id         = root.profileId
        merged.profile_type       = root.profileType
        merged.profile_primitives = root.primitives
        opData = merged
        root.updateDefineProfile(root.opIndex, merged)
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
        var nextIdx = (newLen === 0) ? -1 : Math.min(idx, newLen - 1)
        root.selectedPrimIndex  = nextIdx
        root.selectedBlendIndex = -1
        root.emitSave()
        if (nextIdx >= 0) {
            Qt.callLater(function() {
                Qt.callLater(function() {
                    root._scrollTo(nextIdx, idx >= newLen)
                })
            })
        }
    }

    function _refEndCoords(refIdx) {
        if (refIdx < 0 || refIdx >= root.primitives.length) return { x: 0, z: 0 }
        var currentX = 0
        var currentZ = 0
        for (var i = 0; i <= refIdx; i++) {
            var item = root.primitives[i]
            if (!item) continue
            if (item.type === "startPoint") {
                currentX = item.x_start !== undefined ? Number(item.x_start) : 0
                currentZ = item.z_start !== undefined ? Number(item.z_start) : 0
            } else if (item.type === "lineTo") {
                var mode = String(item.input !== undefined ? item.input : "xz").toLowerCase()
                if (mode !== "xz" && mode !== "ax" && mode !== "az") mode = "xz"
                var endX = item.x_end !== undefined ? Number(item.x_end) : 0
                var endZ = item.z_end !== undefined ? Number(item.z_end) : 0
                if (mode === "az") {
                    var azTan = Math.tan((Number(item.angle || 0) * Math.PI) / 180.0)
                    currentX = currentX + 2.0 * (endZ - currentZ) * azTan
                    currentZ = endZ
                } else if (mode === "ax") {
                    var axTan = Math.tan((Number(item.angle || 0) * Math.PI) / 180.0)
                    var radialDelta = (endX - currentX) / 2.0
                    currentZ = Math.abs(axTan) < 1e-12 ? currentZ : currentZ + radialDelta / axTan
                    currentX = endX
                } else {
                    currentX = endX
                    currentZ = endZ
                }
            } else if (item.type === "arcTo") {
                currentX = item.x_end !== undefined ? Number(item.x_end) : 0
                currentZ = item.z_end !== undefined ? Number(item.z_end) : 0
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
        Qt.callLater(function() {
            Qt.callLater(function() {
                root._scrollTo(actualIdx, true)
            })
        })
    }

    function addPrimitiveAbove(primType) {
        if (root.selectedPrimIndex <= 0) return
        var ref = root._refEndCoords(root.selectedPrimIndex - 1)
        root.primInserted(root.selectedPrimIndex, primType, ref.x, ref.z)
    }

    function addPrimitiveBelow(primType) {
        var idx = root.selectedPrimIndex < 0
                ? root.primitives.length
                : root.selectedPrimIndex + 1
        var ref = root._refEndCoords(root.selectedPrimIndex)
        root.primInserted(idx, primType, ref.x, ref.z)
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

        background: Rectangle {
            radius: 8; color: "#ffffff"
            border.color: "#d6dce7"; border.width: 1
        }

        contentItem: Column {
            id: delCol
            spacing: 12
            width: deleteConfirmPopup.contentWidth
            padding: 16

            Text { text: "Delete Primitive"; font.pointSize: 13; font.bold: true; color: "#1e2430" }

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
                font.pointSize: 11; color: "#4a5568"; wrapMode: Text.WordWrap
            }

            Rectangle { width: deleteConfirmPopup.contentWidth - 32; height: 1; color: "#d6dce7" }

            Item {
                width: deleteConfirmPopup.contentWidth - 32; height: 44

                Button {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    text: "Cancel"; width: 100; height: 40
                    font.pointSize: 11; font.family: "Noto Sans"
                    onClicked: { root._pendingDeleteIndex = -1; deleteConfirmPopup.close() }
                }

                Button {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    text: "Delete"; width: 120; height: 40
                    contentItem: Text {
                        text: parent.text; color: "white"
                        font.pointSize: 11; font.family: "Noto Sans"
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 6; color: parent.pressed ? "#B71C1C" : "#C62828"
                        border.color: "#e53935"; border.width: 1
                    }
                    onClicked: {
                        if (root._pendingDeleteIndex > 0) root.primDeleted(root._pendingDeleteIndex)
                        root._pendingDeleteIndex = -1
                        deleteConfirmPopup.close()
                    }
                }
            }
        }
    }

    // ── Screen background ────────────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: "#f5f7fb"
    }

    // ── Full layout ──────────────────────────────────────────────────────────────
    // No title bar here — AppShellWidget title bar is used (Back/Done driven via headerState)
    Item {
        anchors.fill: parent

        // ── Editor area: 35% list | 65% canvas ───────────────────────────────────
        Item {
            anchors.fill: parent

            // ── Left panel ────────────────────────────────────────────────────────
            Rectangle {
                id: leftPanelBg
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: parent.width * 0.35
                color: "#ffffff"

                ColumnLayout {
                    id: leftPanel
                    anchors.fill: parent
                    spacing: 8

                    // Profile ID + Type row
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80
                        Layout.leftMargin: 12; Layout.rightMargin: 12

                        // Left half: Profile ID
                        RowLayout {
                            anchors { left: parent.left; right: centerDivider.left; top: parent.top; bottom: parent.bottom }
                            spacing: 8
                            Label {
                                text: "Profile ID:"
                                font.pointSize: 11; font.family: "Noto Sans"
                                color: "#1e2430"
                            }
                            NumpadField {
                                Layout.preferredWidth: 70
                                settingName: "defineProfile.profile_id"
                                validatorObject: intVal
                                value: root.profileId
                                formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                                hAlign: Text.AlignHCenter
                                onOpenRequested: root.openNumPadRequested(field)
                                onValueCommitted: { root.profileId = Math.round(value); root.emitSave() }
                            }
                        }

                        Rectangle {
                            id: centerDivider
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1; height: 48; color: "#d6dce7"
                        }

                        // Right half: Type OD/ID
                        RowLayout {
                            anchors { left: centerDivider.right; right: parent.right; top: parent.top; bottom: parent.bottom }
                            spacing: 8
                            Item { Layout.preferredWidth: 8 }
                            Label {
                                text: "Type:"
                                font.pointSize: 11; font.family: "Noto Sans"
                                color: "#1e2430"
                            }
                            ButtonGroup { id: profileTypeGroup }
                            RadioButton {
                                text: "OD"
                                font.pointSize: 11; font.family: "Noto Sans"
                                checked: root.profileType === "od"
                                ButtonGroup.group: profileTypeGroup
                                onToggled: if (checked) { root.profileType = "od"; root.emitSave() }
                            }
                            RadioButton {
                                text: "ID"
                                font.pointSize: 11; font.family: "Noto Sans"
                                checked: root.profileType === "id"
                                ButtonGroup.group: profileTypeGroup
                                onToggled: if (checked) { root.profileType = "id"; root.emitSave() }
                            }
                        }
                    }

                    // Divider
                    Rectangle {
                        Layout.fillWidth: true; height: 1
                        color: "#e8ecf2"
                        Layout.leftMargin: 4; Layout.rightMargin: 4
                    }

                    // Scrollable primitive cards
                    Item {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        Layout.leftMargin: 6; Layout.rightMargin: 6

                    ScrollView {
                        id: primScroll
                        anchors.fill: parent
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        contentWidth: availableWidth
                        background: Rectangle { color: "#ffffff" }

                        Column {
                            width: primScroll.availableWidth
                            spacing: 8
                            topPadding: 4; bottomPadding: 8

                            Repeater {
                                id: primRepeater
                                model: root.primitives

                                delegate: Column {
                                    property var md: modelData
                                    property int mi: index
                                    width: parent ? parent.width : 0
                                    spacing: 8

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

                    // Top fade
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; top: parent.top }
                        height: 40; z: 1
                        visible: primScroll.contentItem.contentY > 0
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "#ffffff" }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                    }

                    // Bottom fade
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 40; z: 1
                        visible: primScroll.contentItem.contentY + primScroll.height < primScroll.contentHeight - 1
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#ffffff" }
                        }
                    }

                    } // Item wrapper for scroll + fades

                    Rectangle {
                        Layout.fillWidth: true; height: 1
                        color: "#e8ecf2"
                        Layout.leftMargin: 4; Layout.rightMargin: 4
                    }

                    // Add primitive buttons
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.verticalCenterOffset: -4
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 24

                            Repeater {
                                model: [
                                    { label: "LineTo", direction: "Above", type: "lineTo", iconEnd: "../icons/move_up_icon.svg" },
                                    { label: "ArcTo", direction: "Above", type: "arcTo", iconEnd: "../icons/move_up_icon.svg" },
                                    { label: "LineTo", direction: "Below", type: "lineTo", iconEnd: "../icons/move_down_icon.svg" },
                                    { label: "ArcTo", direction: "Below", type: "arcTo", iconEnd: "../icons/move_down_icon.svg" }
                                ]

                                delegate: Button {
                                    id: addPrimitiveButton
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 60
                                    enabled: modelData.direction === "Above" ? root.selectedPrimIndex > 0 : root.primitives.length > 0
                                    font.pixelSize: 16
                                    font.family: "Noto Sans"

                                    contentItem: RowLayout {
                                        spacing: 4

                                        Image {
                                            Layout.preferredWidth: 36
                                            Layout.preferredHeight: 36
                                            sourceSize.width: 36
                                            sourceSize.height: 36
                                            source: "../icons/add_op_icon.svg"
                                            fillMode: Image.PreserveAspectFit
                                            opacity: addPrimitiveButton.enabled ? 1.0 : 0.35
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.label
                                            font: addPrimitiveButton.font
                                            color: "#1e2430"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 1
                                            opacity: addPrimitiveButton.enabled ? 1.0 : 0.35
                                        }

                                        Image {
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                            sourceSize.width: 32
                                            sourceSize.height: 32
                                            source: modelData.iconEnd
                                            fillMode: Image.PreserveAspectFit
                                            opacity: addPrimitiveButton.enabled ? 1.0 : 0.35
                                        }
                                    }

                                    background: Rectangle {
                                        radius: 6
                                        color: parent.pressed ? "#e5edf9" : parent.hovered ? "#eef3fb" : "#f5f7fb"
                                        border.color: "#c5d0df"
                                        border.width: 1
                                        opacity: parent.enabled ? 1.0 : 0.55
                                    }

                                    onClicked: {
                                        if (modelData.direction === "Above")
                                            root.addPrimitiveAbove(modelData.type)
                                        else
                                            root.addPrimitiveBelow(modelData.type)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Vertical separator
            Rectangle {
                anchors { left: leftPanelBg.right; top: parent.top; bottom: parent.bottom }
                width: 1; color: "#d6dce7"
            }

            // ── Right panel: canvas ────────────────────────────────────────────────
            ColumnLayout {
                anchors {
                    left:   leftPanelBg.right; right:  parent.right
                    top:    parent.top;         bottom: parent.bottom
                    leftMargin: 14; rightMargin: 12
                    topMargin: 10;  bottomMargin: 10
                }
                spacing: 8

                Item {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true

                    ProfileCanvas {
                        id: profileCanvas
                        anchors.fill: parent
                        primitives:         root.primitives
                        profileType:        root.profileType
                        selectedPrimIndex:  root.selectedPrimIndex
                        selectedBlendIndex: root.selectedBlendIndex
                        onPrimitiveSelected: function(idx) {
                            root.selectedPrimIndex  = idx
                            root.selectedBlendIndex = -1
                        }
                        onSelectionCleared: {
                            root.selectedPrimIndex = -1
                            root.selectedBlendIndex = -1
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: "#d6dce7"; border.width: 1
                        }
                    }

                    // Zoom icon buttons — top-left overlay
                    Row {
                        anchors { top: parent.top; left: parent.left; topMargin: 24; leftMargin: 24 }
                        spacing: 32

                        Repeater {
                            model: [
                                { icon: "../icons/zoom-in.svg",  action: "zoomIn"      },
                                { icon: "../icons/zoom-out.svg", action: "zoomOut"     },
                                { icon: "../icons/zoom-fit.svg", action: "fitToScreen" }
                            ]
                            Rectangle {
                                width: 60; height: 60
                                radius: 6
                                color: iconMa.pressed ? "#e5edf9" : iconMa.containsMouse ? "#eef3fb" : "#f5f7fb"
                                border.color: "#c5d0df"; border.width: 1

                                Image {
                                    anchors.centerIn: parent
                                    width: 40; height: 40
                                    source: modelData.icon
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                }

                                MouseArea {
                                    id: iconMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        if (modelData.action === "zoomIn")       profileCanvas.zoomIn()
                                        else if (modelData.action === "zoomOut") profileCanvas.zoomOut()
                                        else                                     profileCanvas.fitToScreen()
                                    }
                                }
                            }
                        }
                    }
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
