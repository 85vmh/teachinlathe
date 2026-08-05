// LineToCard.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"

Rectangle {
    id: root

    property var  primData:   ({})
    property int  primIdx:    0
    property int  primCount:  0
    property bool isSelected: false

    readonly property string _blendType:
        (primData && primData.blend && primData.blend.type) ? primData.blend.type : "none"
    readonly property string _inputMode: _normalizedInput()
    readonly property string _firstFieldName:  _inputMode === "xz" ? "x_end" : "angle"
    readonly property string _secondFieldName: _inputMode === "ax" ? "x_end" : "z_end"
    readonly property string _firstLabel:      _inputMode === "xz" ? "X End" : "Angle"
    readonly property string _secondLabel:     _inputMode === "ax" ? "X End" : "Z End"
    readonly property string _firstDescription:
        _firstFieldName === "angle" ? "Line Angle from Z Axis" : "Line End on X"
    readonly property string _secondDescription:
        _secondFieldName === "x_end" ? "Line End on X" : "Line End on Z"

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()
    signal deleteRequested(int idx)

    // ── Colors ────────────────────────────────────────────────────────────────
    readonly property color clrCardBg:            "#f5f7fb"
    readonly property color clrCardBgSel:         "#dbeafe"
    readonly property color clrBorder:            "#cccccc"
    readonly property color clrBorderSel:         "#3b82f6"
    readonly property color clrSeparator:         "#d0d0d0"
    readonly property color clrBlendBtnHover:     "#e1f0ff"
    readonly property color clrBlendBtnHoverBorder: "#8ec5ff"
    readonly property color clrBtnBorder:         "#BDBDBD"
    readonly property color clrDeleteHover:       "#ffebee"
    readonly property color clrDeleteBorder:      "#C62828"

    // ── Sizes ─────────────────────────────────────────────────────────────────
    readonly property int szCardRadius:    8
    readonly property int szCardPadding:   24
    readonly property int szMargin:        12
    readonly property int szSpacing:       8
    readonly property int szIconArea:      56
    readonly property int szIconSize:      56
    readonly property int szFont:          16
    readonly property int szGridRowGap:    20
    readonly property int szGridColGap:    8
    readonly property int szGridWidth:     196
    readonly property int szInputWidth:    120
    readonly property int szTabHeight:     46
    readonly property int szTabFont:       16
    readonly property int szSepInset:      4
    readonly property int szSepGap:        8
    readonly property int szBtn:           50
    readonly property int szBtnIcon:       36
    readonly property int szBtnIconSrc:    112

    color:        isSelected ? clrCardBgSel : clrCardBg
    radius:       szCardRadius
    border.color: isSelected ? clrBorderSel : clrBorder
    border.width: isSelected ? 2 : 1
    height:       ltRow.implicitHeight + szCardPadding

    TapHandler { onTapped: root.tapped() }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

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

    RowLayout {
        id: ltRow
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: szMargin }
        spacing: szSpacing

        Item {
            implicitWidth: szIconArea
            Layout.fillHeight: true

            Text {
                anchors.top: parent.top
                anchors.left: parent.left
                text: (primIdx + 1) + "."
                font.pixelSize: szFont; font.bold: true
            }

            Image {
                anchors.centerIn: parent
                width: szIconSize; height: szIconSize
                sourceSize.width: szIconSize; sourceSize.height: szIconSize
                source: "../icons/line_to.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: 0; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        ColumnLayout {
            spacing: szGridRowGap
            Layout.fillWidth: true

            Rectangle {
                id: inputModeBar
                Layout.fillWidth: true
                Layout.preferredHeight: szTabHeight
                radius: 8
                color: "transparent"

                Row {
                    anchors.fill: parent

                Repeater {
                    model: [
                        { label: "X & Z End",     mode: "xz" },
                        { label: "Angle & X End",     mode: "ax" },
                        { label: "Angle & Z End",     mode: "az" }
                    ]
                    delegate: Item {
                        id: tabItem
                        readonly property bool selected: root._inputMode === modelData.mode
                        readonly property color tabColor: selected ? "#1f6feb" : "#ffffff"
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
                            width: 1
                            color: "#cbd5e1"
                            z: 1
                        }

                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.selected ? "#ffffff" : "#1f2937"
                            font.pixelSize: szTabFont
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
                    border.color: "#cbd5e1"
                    border.width: 1
                    z: 3
                }
            }

            RowLayout {
                spacing: szSpacing
                Layout.fillWidth: true

            GridLayout {
                columns: 2
                rowSpacing: szGridRowGap; columnSpacing: szGridColGap
                Layout.preferredWidth: szGridWidth
                Layout.maximumWidth:  szGridWidth

                Label { text: root._firstLabel; font.pixelSize: szFont; Layout.fillWidth: true }
                NumpadField {
                    description: root._firstDescription
                    Layout.preferredWidth: szInputWidth
                    settingName: root._settingName(root._firstFieldName)
                    validatorObject: dblVal
                    value: root._fieldValue(root._firstFieldName)
                    formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                    hAlign: Text.AlignRight
                    onOpenRequested: {
                        root.tapped()
                        root.openNumPadRequested(field)
                    }
                    onValueCommitted: root._updateField(root._firstFieldName, value)
                }

                Label { text: root._secondLabel; font.pixelSize: szFont; Layout.fillWidth: true }
                NumpadField {
                    description: root._secondDescription
                    Layout.preferredWidth: szInputWidth
                    settingName: root._settingName(root._secondFieldName)
                    validatorObject: dblVal
                    value: root._fieldValue(root._secondFieldName)
                    formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                    hAlign: Text.AlignRight
                    onOpenRequested: {
                        root.tapped()
                        root.openNumPadRequested(field)
                    }
                    onValueCommitted: root._updateField(root._secondFieldName, value)
                }
            }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: szSepGap; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            enabled: root._blendType === "none" && root.primIdx < root.primCount - 1
            opacity: enabled ? 1.0 : 0.35
            color:   chamferMA.pressed ? clrBlendBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: chamferMA.pressed ? clrBlendBtnHoverBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/chamfer.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: chamferMA; anchors.fill: parent; enabled: parent.enabled
                onClicked: {
                    var d = JSON.parse(JSON.stringify(primData))
                    if (!d.blend) d.blend = {}
                    d.blend.type = "chamfer"
                    if (d.blend.chamfer_width === undefined) d.blend.chamfer_width = 1.0
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Item {
            Layout.preferredWidth: 8
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            enabled: root._blendType === "none" && root.primIdx < root.primCount - 1
            opacity: enabled ? 1.0 : 0.35
            color:   filletMA.pressed ? clrBlendBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: filletMA.pressed ? clrBlendBtnHoverBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/fillet.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: filletMA; anchors.fill: parent; enabled: parent.enabled
                onClicked: {
                    var d = JSON.parse(JSON.stringify(primData))
                    if (!d.blend) d.blend = {}
                    d.blend.type = "fillet"
                    if (d.blend.fillet_radius === undefined) d.blend.fillet_radius = 1.0
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Item {
            Layout.preferredWidth: 8
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            enabled: root._blendType === "none" && root.primIdx < root.primCount - 1
            opacity: enabled ? 1.0 : 0.35
            color:   undercutMA.pressed ? clrBlendBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: undercutMA.pressed ? clrBlendBtnHoverBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/undercut.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: undercutMA; anchors.fill: parent; enabled: parent.enabled
                onClicked: {
                    var d = JSON.parse(JSON.stringify(primData))
                    if (!d.blend) d.blend = {}
                    d.blend.type = "undercut_din509"
                    if (d.blend.undercut_radius === undefined) d.blend.undercut_radius = 0.4
                    if (d.blend.undercut_depth === undefined) d.blend.undercut_depth = 0.4
                    if (d.blend.undercut_length === undefined) d.blend.undercut_length = 2.5
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: szSepGap; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            color:   delMA.pressed ? clrDeleteHover : "transparent"
            border.width: 1
            border.color: delMA.pressed ? clrDeleteBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/delete_icon.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: delMA; anchors.fill: parent
                onClicked: root.deleteRequested(primIdx)
            }
        }
    }
}
