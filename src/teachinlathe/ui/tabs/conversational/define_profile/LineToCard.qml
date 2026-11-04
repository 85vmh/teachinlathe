// LineToCard.qml
import QtQuick
import QtQuick.Layouts
import theme

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

    readonly property color clrTabBorder: "#cbd5e1"
    readonly property color clrTabText:   "#1f2937"
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

            Rectangle {
                id: inputModeBar
                x: firstCell.x + firstCell.contentLeft
                width: secondCell.x + secondCell.contentRight - x
                height: parent.height
                radius: Theme.radiusLarge
                color: "transparent"

                Row {
                    anchors.fill: parent

                    Repeater {
                        model: [
                            { label: "XZ End",        mode: "xz" },
                            { label: "Angle + X End", mode: "ax" },
                            { label: "Angle + Z End", mode: "az" }
                        ]
                        delegate: Item {
                            id: tabItem
                            readonly property bool selected: root._inputMode === modelData.mode
                            readonly property color tabColor: selected ? Theme.outlineDisabled : Theme.surface
                            readonly property bool isFirst: index === 0
                            readonly property bool isLast: index === 2
                            width: inputModeBar.width / 3
                            height: inputModeBar.height

                            Rectangle {
                                anchors.fill: parent
                                radius: (tabItem.isFirst || tabItem.isLast) ? inputModeBar.radius : 0
                                color: tabItem.tabColor

                                Rectangle {
                                    anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                                    width: inputModeBar.radius
                                    visible: tabItem.isFirst
                                    color: parent.color
                                }

                                Rectangle {
                                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                                    width: inputModeBar.radius
                                    visible: tabItem.isLast
                                    color: parent.color
                                }
                            }

                            Rectangle {
                                visible: !tabItem.isLast
                                anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                                width: Theme.hairline
                                color: root.clrTabBorder
                                z: 1
                            }

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: parent.selected ? Theme.surfaceInverse : root.clrTabText
                                font.pixelSize: Theme.fontBody
                                font.bold: parent.selected
                                z: 2
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: root._setInputMode(modelData.mode)
                            }
                        }
                }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: inputModeBar.radius
                    color: "transparent"
                    border.color: root.clrTabBorder
                    border.width: Theme.hairline
                    z: 3
                }
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
