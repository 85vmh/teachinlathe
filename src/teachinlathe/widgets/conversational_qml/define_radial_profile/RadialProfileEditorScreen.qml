import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"

Item {
    id: root
    objectName: "radialProfileEditorScreen"
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null
    property int profileId: 0
    property string profileType: "od"
    property var primitives: []
    property var workpiece: ({})
    property int selectedIndex: -1
    property bool _loading: false

    signal backRequested()
    signal updateDefineRadialProfile(int opIdx, var payload)
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}
        profileId = opData.profile_id !== undefined ? Math.round(Number(opData.profile_id)) : 0
        profileType = opData.profile_type !== undefined ? String(opData.profile_type) : "od"
        primitives = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        workpiece = JSON.parse(JSON.stringify(opData.workpiece || {}))
        selectedIndex = primitives.length > 0 ? 0 : -1
        _loading = false
        canvas.resetView()
    }

    function emitSave() {
        if (_loading) return
        var merged = JSON.parse(JSON.stringify(opData || {}))
        merged.profile_id = root.profileId
        merged.profile_type = root.profileType
        merged.profile_primitives = root._renumber(root.primitives)
        opData = merged
        root.updateDefineRadialProfile(root.opIndex, merged)
    }

    function _renumber(arr) {
        var out = JSON.parse(JSON.stringify(arr || []))
        var ordered = []
        for (var i = 0; i < out.length; i++)
            ordered.push(_orderPrimitive(out[i], i + 1))
        return ordered
    }

    function _orderPrimitive(primitive, primitiveId) {
        var p = primitive || {}
        var ordered = {
            primitive_id: primitiveId,
            type: p.type || "groove"
        }
        if (ordered.type === "groove") {
            ordered.right_flank = p.right_flank || {}
            ordered.bottom = p.bottom || {}
            ordered.left_flank = p.left_flank || {}
        }
        for (var key in p) {
            if (ordered[key] === undefined)
                ordered[key] = p[key]
        }
        return ordered
    }

    function primUpdated(idx, data) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        arr[idx] = data
        root.primitives = root._renumber(arr)
        root.emitSave()
    }

    function primDeleted(idx) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        if (idx < 0 || idx >= arr.length) return
        arr.splice(idx, 1)
        root.primitives = root._renumber(arr)
        root.selectedIndex = root.primitives.length > 0 ? Math.min(idx, root.primitives.length - 1) : -1
        root.emitSave()
    }

    function _emptyBlend() {
        return { type: "none", chamfer_width: 0.0, fillet_radius: 0.0 }
    }

    function _newGroove() {
        return {
            primitive_id: 0,
            type: "groove",
            right_flank: {
                x_start: 30.0,
                z_start: 0.0,
                angle: 0.0,
                start_blend: _emptyBlend()
            },
            bottom: {
                x_end_right: 20.0,
                x_end_left: 20.0,
                blend_right: _emptyBlend(),
                blend_left: _emptyBlend()
            },
            left_flank: {
                x_start: 30.0,
                z_start: -5.0,
                angle: 0.0,
                start_blend: _emptyBlend()
            }
        }
    }

    function _newRepeat() {
        return {
            primitive_id: 0,
            type: "repeat",
            repeat_primitive_id: 1,
            repeat_count: 1,
            z_offset: -5.0
        }
    }

    function addPrimitive(type) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        arr.push(type === "repeat" ? _newRepeat() : _newGroove())
        root.primitives = root._renumber(arr)
        root.selectedIndex = root.primitives.length - 1
        root.emitSave()
    }

    IntValidator { id: intVal; bottom: 1; top: 999 }

    Rectangle { anchors.fill: parent; color: "#f5f7fb" }

    Item {
        anchors.fill: parent

        Rectangle {
            id: leftPanelBg
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.width * 0.42
            color: "#ffffff"

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    spacing: 10

                    Label {
                        text: "Profile ID:"
                        font.pixelSize: 16
                    }

                    NumpadField {
                        Layout.preferredWidth: 82
                        settingName: "defineRadialProfile.profile_id"
                        validatorObject: intVal
                        value: root.profileId
                        formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
                        hAlign: Text.AlignHCenter
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: { root.profileId = Math.round(value); root.emitSave() }
                    }

                    Rectangle {
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 42
                        color: "#d6dce7"
                    }

                    Label {
                        text: "Type:"
                        font.pixelSize: 16
                    }

                    ButtonGroup { id: profileTypeGroup }

                    RadioButton {
                        text: "OD"
                        font.pixelSize: 15
                        checked: root.profileType === "od"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "od"; root.emitSave() }
                    }

                    RadioButton {
                        text: "ID"
                        font.pixelSize: 15
                        checked: root.profileType === "id"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "id"; root.emitSave() }
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: "Groove"
                        Layout.preferredWidth: 110
                        onClicked: root.addPrimitive("groove")
                    }

                    Button {
                        text: "Repeat"
                        Layout.preferredWidth: 110
                        onClicked: root.addPrimitive("repeat")
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#e8ecf2"
                }

                ScrollView {
                    id: cardScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    contentWidth: availableWidth

                    Column {
                        width: cardScroll.availableWidth
                        spacing: 8
                        padding: 8

                        Repeater {
                            model: root.primitives
                            delegate: Loader {
                                width: parent.width - 16
                                sourceComponent: {
                                    if (!modelData) return null
                                    if (modelData.type === "repeat") return repeatCardComp
                                    return grooveCardComp
                                }
                                onLoaded: {
                                    item.primData = modelData
                                    item.primIdx = index
                                    item.isSelected = Qt.binding(function() { return root.selectedIndex === index })
                                    item.tapped.connect(function() { root.selectedIndex = index })
                                    item.primUpdated.connect(root.primUpdated)
                                    item.deleteRequested.connect(root.primDeleted)
                                    item.openNumPadRequested.connect(root.openNumPadRequested)
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            anchors.left: leftPanelBg.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: "#d6dce7"
        }

        ColumnLayout {
            anchors.left: leftPanelBg.right
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: 12
            spacing: 8

            RadialProfileCanvas {
                id: canvas
                Layout.fillWidth: true
                Layout.fillHeight: true
                primitives: root.primitives
                workpiece: root.workpiece
                profileType: root.profileType
                selectedIndex: root.selectedIndex

                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: "#ccc"
                    border.width: 1
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                Item { Layout.fillWidth: true }
                Button { text: "Zoom In"; onClicked: canvas.zoomIn() }
                Button { text: "Zoom Out"; onClicked: canvas.zoomOut() }
                Button { text: "Fit"; onClicked: canvas.fitToScreen() }
            }
        }
    }

    Component { id: grooveCardComp; GrooveProfileCard {} }
    Component { id: repeatCardComp; RepeatProfileCard {} }
}
