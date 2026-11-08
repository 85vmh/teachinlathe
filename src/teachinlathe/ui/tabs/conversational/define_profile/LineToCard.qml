// LineToCard.qml
import QtQuick
import QtQuick.Layouts
import theme
import common

PrimitiveCard {
    id: root

    iconName: "line_to.svg"

    readonly property string _inputMode: _normalizedInput()
    readonly property string _firstFieldName:  _inputMode === "xz" ? "x_end" : "angle"
    readonly property string _secondFieldName: _inputMode === "ax" ? "x_end" : "z_end"
    readonly property string _firstLabel:      _inputMode === "xz" ? "X End" : "Angle"
    readonly property string _secondLabel:     _inputMode === "ax" ? "X End" : "Z End"
    readonly property string _firstDescription:
        _firstFieldName === "angle" ? "Line Angle from Z Axis" : "Line End on X"
    readonly property string _secondDescription:
        _secondFieldName === "x_end" ? "Line End on X" : "Line End on Z"

    readonly property int   szTabHeight:  46

    function _normalizedInput() {
        var mode = String(primData && primData.input !== undefined ? primData.input : "xz").toLowerCase()
        return (mode === "ax" || mode === "az") ? mode : "xz"
    }

    function _fieldValue(fieldName) {
        if (primData && primData[fieldName] !== undefined) return primData[fieldName]
        return 0
    }

    function _settingName(fieldName) {
        return "lt." + primIdx + "." + fieldName
    }

    function _copyPrimData() {
        var d = JSON.parse(JSON.stringify(primData || {}))
        d.type = d.type || "lineTo"
        if (d.input === undefined) d.input = "xz"
        if (d.angle === undefined) d.angle = 0
        if (d.x_end === undefined) d.x_end = 0
        if (d.z_end === undefined) d.z_end = 0
        if (!d.blend) d.blend = { type: "none" }
        return d
    }

    function _setInputMode(mode) {
        mode = (mode === "ax" || mode === "az") ? mode : "xz"
        if (mode === root._inputMode) return
        var d = _copyPrimData()
        d.input = mode
        root.tapped()
        root.primUpdated(primIdx, d)
    }

    function _updateField(fieldName, committedValue) {
        var d = _copyPrimData()
        d[fieldName] = Number(committedValue)
        root.tapped()
        root.primUpdated(primIdx, d)
    }

    function _openField(field) {
        root.tapped()
        root.openNumPadRequested(field)
    }

    ColumnLayout {
        spacing: CardMetrics.rowGap
        Layout.fillWidth: true

        // from where the first label starts to where the last input ends
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.szTabHeight

            SegmentedTabs {
                id: inputModeBar
                readonly property var modes: ["xz", "ax", "az"]
                x: firstCell.x + firstCell.contentLeft
                width: secondCell.x + secondCell.contentRight - x
                height: parent.height
                labels: ["XZ End", "Angle + X End", "Angle + Z End"]
                currentIndex: modes.indexOf(root._inputMode)
                onActivated: function(index) { root._setInputMode(modes[index]) }
            }
        }

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            ProfileField {
                id: firstCell
                label: root._firstLabel
                description: root._firstDescription
                settingName: root._settingName(root._firstFieldName)
                value: root._fieldValue(root._firstFieldName)
                onOpenRequested: function(field) { root._openField(field) }
                onCommitted: function(value) { root._updateField(root._firstFieldName, value) }
            }

            ProfileField {
                id: secondCell
                label: root._secondLabel
                description: root._secondDescription
                settingName: root._settingName(root._secondFieldName)
                value: root._fieldValue(root._secondFieldName)
                onOpenRequested: function(field) { root._openField(field) }
                onCommitted: function(value) { root._updateField(root._secondFieldName, value) }
            }
        }
    }
}
