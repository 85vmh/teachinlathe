import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../touchable_input"

Rectangle {
    id: root

    property var primData: ({})
    property int primIdx: 0
    property bool isSelected: false

    signal primUpdated(int idx, var data)
    signal deleteRequested(int idx)
    signal openNumPadRequested(var field)
    signal tapped()

    color: isSelected ? "#dbeafe" : "#f5f7fb"
    radius: 8
    border.color: isSelected ? "#3b82f6" : "#cccccc"
    border.width: isSelected ? 2 : 1
    height: content.implicitHeight + 24

    TapHandler { onTapped: root.tapped() }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    function _clone() {
        var d = JSON.parse(JSON.stringify(primData || {}))
        d.type = "groove"
        if (!d.right_flank) d.right_flank = {}
        if (!d.bottom) d.bottom = {}
        if (!d.left_flank) d.left_flank = {}
        if (!d.right_flank.start_blend) d.right_flank.start_blend = _emptyBlend()
        if (!d.bottom.blend_right) d.bottom.blend_right = _emptyBlend()
        if (!d.bottom.blend_left) d.bottom.blend_left = _emptyBlend()
        if (!d.left_flank.start_blend) d.left_flank.start_blend = _emptyBlend()
        return d
    }

    function _emptyBlend() {
        return { type: "none", chamfer_width: 0, fillet_radius: 0 }
    }

    function _fieldValue(section, key, fallback) {
        return primData && primData[section] && primData[section][key] !== undefined
            ? Number(primData[section][key])
            : fallback
    }

    function _blend(section, key) {
        return primData && primData[section] && primData[section][key]
            ? primData[section][key]
            : _emptyBlend()
    }

    function _blendValue(blend, key) {
        return blend && blend[key] !== undefined ? Number(blend[key]) : 0
    }

    function _blendType(blend) {
        if (!blend || !blend.type) return "none"
        return blend.type === "radius" ? "fillet" : blend.type
    }

    function _commit(section, key, value) {
        var d = _clone()
        d[section][key] = Number(value)
        root.primUpdated(primIdx, d)
    }

    function _commitBlend(section, blendKey, blendType, valueKey, value) {
        var d = _clone()
        if (!d[section][blendKey]) d[section][blendKey] = _emptyBlend()
        if (blendType !== null) d[section][blendKey].type = blendType
        if (valueKey) d[section][blendKey][valueKey] = Number(value)
        root.primUpdated(primIdx, d)
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: (primIdx + 1) + ". Groove"
                font.pixelSize: 16
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Delete"
                Layout.preferredWidth: 84
                onClicked: root.deleteRequested(primIdx)
            }
        }

        FlankSection {
            Layout.fillWidth: true
            title: "Right Flank"
            sectionName: "right_flank"
            blendKey: "start_blend"
            xValue: root._fieldValue("right_flank", "x_start", 30)
            zValue: root._fieldValue("right_flank", "z_start", 0)
            angleValue: root._fieldValue("right_flank", "angle", 0)
            blendData: root._blend("right_flank", "start_blend")
            settingPrefix: "radial_profile.right_flank"
            onFieldCommitted: root._commit(section, key, value)
            onBlendTypeCommitted: root._commitBlend(section, blend, blendType, "", 0)
            onBlendValueCommitted: root._commitBlend(section, blend, null, key, value)
            onOpenNumPadRequested: root.openNumPadRequested(field)
        }

        BottomSection {
            Layout.fillWidth: true
            xEndLeft: root._fieldValue("bottom", "x_end_left", 20)
            xEndRight: root._fieldValue("bottom", "x_end_right", 20)
            leftBlend: root._blend("bottom", "blend_left")
            rightBlend: root._blend("bottom", "blend_right")
            onFieldCommitted: root._commit("bottom", key, value)
            onBlendTypeCommitted: root._commitBlend("bottom", blend, blendType, "", 0)
            onBlendValueCommitted: root._commitBlend("bottom", blend, null, key, value)
            onOpenNumPadRequested: root.openNumPadRequested(field)
        }

        FlankSection {
            Layout.fillWidth: true
            title: "Left Flank"
            sectionName: "left_flank"
            blendKey: "start_blend"
            xValue: root._fieldValue("left_flank", "x_start", 30)
            zValue: root._fieldValue("left_flank", "z_start", -5)
            angleValue: root._fieldValue("left_flank", "angle", 0)
            blendData: root._blend("left_flank", "start_blend")
            settingPrefix: "radial_profile.left_flank"
            onFieldCommitted: root._commit(section, key, value)
            onBlendTypeCommitted: root._commitBlend(section, blend, blendType, "", 0)
            onBlendValueCommitted: root._commitBlend(section, blend, null, key, value)
            onOpenNumPadRequested: root.openNumPadRequested(field)
        }
    }

    component NumberRow: RowLayout {
        id: numberRow

        property string label: ""
        property string settingName: ""
        property real value: 0
        property bool teachable: true
        signal committed(real value)
        signal teachRequested()
        signal openNumPadRequested(var field)

        Layout.fillWidth: true
        spacing: 8

        Label {
            text: numberRow.label
            Layout.preferredWidth: 70
            font.pixelSize: 13
        }

        NumpadField {
            Layout.preferredWidth: 96
            settingName: numberRow.settingName
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: numberRow.value
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: numberRow.openNumPadRequested(field)
            onValueCommitted: numberRow.committed(Number(value))
        }

        Button {
            visible: numberRow.teachable
            Layout.preferredWidth: numberRow.teachable ? 76 : 0
            text: "TeachIn"
            onClicked: numberRow.teachRequested()
        }
    }

    component BlendEditor: GridLayout {
        id: blendRoot

        property string title: ""
        property var blendData: ({ type: "none" })
        property string settingPrefix: ""
        property string activeType: root._blendType(blendData)
        signal blendTypeCommitted(string blendType)
        signal blendValueCommitted(string key, real value)
        signal openNumPadRequested(var field)

        Layout.fillWidth: true
        columns: 3
        columnSpacing: 10
        rowSpacing: 8

        ButtonGroup { id: modeGroup }

        Label {
            text: blendRoot.title
            font.pixelSize: 13
            font.bold: true
            Layout.columnSpan: 3
        }

        RadioButton {
            text: "None"
            font.pixelSize: 13
            checked: blendRoot.activeType === "none"
            ButtonGroup.group: modeGroup
            Layout.columnSpan: 3
            onToggled: if (checked) blendRoot.blendTypeCommitted("none")
        }

        RadioButton {
            text: "Chamfer"
            font.pixelSize: 13
            checked: blendRoot.activeType === "chamfer"
            ButtonGroup.group: modeGroup
            onToggled: if (checked) blendRoot.blendTypeCommitted("chamfer")
        }
        NumpadField {
            Layout.preferredWidth: 96
            enabled: blendRoot.activeType === "chamfer"
            opacity: enabled ? 1.0 : 0.4
            settingName: blendRoot.settingPrefix + ".chamfer_width"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: root._blendValue(blendRoot.blendData, "chamfer_width")
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: blendRoot.openNumPadRequested(field)
            onValueCommitted: blendRoot.blendValueCommitted("chamfer_width", Number(value))
        }
        Label {
            text: "(mm)"
            font.pixelSize: 13
            opacity: blendRoot.activeType === "chamfer" ? 1.0 : 0.4
        }

        RadioButton {
            text: "Fillet"
            font.pixelSize: 13
            checked: blendRoot.activeType === "fillet"
            ButtonGroup.group: modeGroup
            onToggled: if (checked) blendRoot.blendTypeCommitted("fillet")
        }
        NumpadField {
            Layout.preferredWidth: 96
            enabled: blendRoot.activeType === "fillet"
            opacity: enabled ? 1.0 : 0.4
            settingName: blendRoot.settingPrefix + ".fillet_radius"
            validatorObject: dblVal
            seedNumpadFromValue: true
            value: root._blendValue(blendRoot.blendData, "fillet_radius")
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: blendRoot.openNumPadRequested(field)
            onValueCommitted: blendRoot.blendValueCommitted("fillet_radius", Number(value))
        }
        Label {
            text: "(mm)"
            font.pixelSize: 13
            opacity: blendRoot.activeType === "fillet" ? 1.0 : 0.4
        }
    }

    component FlankSection: GroupBox {
        id: flankRoot

        property string sectionName: ""
        property string blendKey: ""
        property real xValue: 0
        property real zValue: 0
        property real angleValue: 0
        property var blendData: ({ type: "none" })
        property string settingPrefix: ""
        signal fieldCommitted(string section, string key, real value)
        signal blendTypeCommitted(string section, string blend, string blendType)
        signal blendValueCommitted(string section, string blend, string key, real value)
        signal openNumPadRequested(var field)

        font.pixelSize: 14
        Layout.fillWidth: true

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 8

                NumberRow {
                    label: "X Start"
                    settingName: flankRoot.settingPrefix + ".x_start"
                    value: flankRoot.xValue
                    onOpenNumPadRequested: flankRoot.openNumPadRequested(field)
                    onCommitted: flankRoot.fieldCommitted(flankRoot.sectionName, "x_start", value)
                    onTeachRequested: flankRoot.fieldCommitted(flankRoot.sectionName, "x_start", positionsBridge.teachInX() * 2)
                }
                NumberRow {
                    label: "Z Start"
                    settingName: flankRoot.settingPrefix + ".z_start"
                    value: flankRoot.zValue
                    onOpenNumPadRequested: flankRoot.openNumPadRequested(field)
                    onCommitted: flankRoot.fieldCommitted(flankRoot.sectionName, "z_start", value)
                    onTeachRequested: flankRoot.fieldCommitted(flankRoot.sectionName, "z_start", positionsBridge.teachInZ())
                }
                NumberRow {
                    label: "Angle"
                    settingName: flankRoot.settingPrefix + ".angle"
                    value: flankRoot.angleValue
                    teachable: false
                    onOpenNumPadRequested: flankRoot.openNumPadRequested(field)
                    onCommitted: flankRoot.fieldCommitted(flankRoot.sectionName, "angle", value)
                }
            }

            BlendEditor {
                Layout.fillWidth: true
                title: "Start Blend"
                blendData: flankRoot.blendData
                settingPrefix: flankRoot.settingPrefix + ".start_blend"
                onBlendTypeCommitted: flankRoot.blendTypeCommitted(flankRoot.sectionName, flankRoot.blendKey, blendType)
                onBlendValueCommitted: flankRoot.blendValueCommitted(flankRoot.sectionName, flankRoot.blendKey, key, value)
                onOpenNumPadRequested: flankRoot.openNumPadRequested(field)
            }
        }
    }

    component BottomSection: GroupBox {
        id: bottomRoot

        title: "Bottom"
        property real xEndLeft: 0
        property real xEndRight: 0
        property var leftBlend: ({ type: "none" })
        property var rightBlend: ({ type: "none" })
        signal fieldCommitted(string key, real value)
        signal blendTypeCommitted(string blend, string blendType)
        signal blendValueCommitted(string blend, string key, real value)
        signal openNumPadRequested(var field)

        font.pixelSize: 14
        Layout.fillWidth: true

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 10

                NumberRow {
                    label: "X End Left"
                    settingName: "radial_profile.bottom.x_end_left"
                    value: bottomRoot.xEndLeft
                    onOpenNumPadRequested: bottomRoot.openNumPadRequested(field)
                    onCommitted: bottomRoot.fieldCommitted("x_end_left", value)
                    onTeachRequested: bottomRoot.fieldCommitted("x_end_left", positionsBridge.teachInX() * 2)
                }

                BlendEditor {
                    title: "Left Flank Blend"
                    blendData: bottomRoot.leftBlend
                    settingPrefix: "radial_profile.bottom.blend_left"
                    onBlendTypeCommitted: bottomRoot.blendTypeCommitted("blend_left", blendType)
                    onBlendValueCommitted: bottomRoot.blendValueCommitted("blend_left", key, value)
                    onOpenNumPadRequested: bottomRoot.openNumPadRequested(field)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 10

                NumberRow {
                    label: "X End Right"
                    settingName: "radial_profile.bottom.x_end_right"
                    value: bottomRoot.xEndRight
                    onOpenNumPadRequested: bottomRoot.openNumPadRequested(field)
                    onCommitted: bottomRoot.fieldCommitted("x_end_right", value)
                    onTeachRequested: bottomRoot.fieldCommitted("x_end_right", positionsBridge.teachInX() * 2)
                }

                BlendEditor {
                    title: "Right Flank Blend"
                    blendData: bottomRoot.rightBlend
                    settingPrefix: "radial_profile.bottom.blend_right"
                    onBlendTypeCommitted: bottomRoot.blendTypeCommitted("blend_right", blendType)
                    onBlendValueCommitted: bottomRoot.blendValueCommitted("blend_right", key, value)
                    onOpenNumPadRequested: bottomRoot.openNumPadRequested(field)
                }
            }
        }
    }
}
