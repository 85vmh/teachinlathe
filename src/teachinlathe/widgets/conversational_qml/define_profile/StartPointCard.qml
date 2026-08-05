// StartPointCard.qml
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

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()

    // ── Colors ────────────────────────────────────────────────────────────────
    readonly property color clrCardBg:            "#f5f7fb"
    readonly property color clrCardBgSel:         "#dbeafe"
    readonly property color clrBorder:            "#cccccc"
    readonly property color clrBorderSel:         "#3b82f6"
    readonly property color clrSeparator:         "#d0d0d0"
    readonly property color clrBlendBtnHover:     "#e1f0ff"
    readonly property color clrBlendBtnHoverBorder: "#8ec5ff"
    readonly property color clrBtnBorder:         "#BDBDBD"

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
    readonly property int szSepInset:      4
    readonly property int szSepGap:        8
    readonly property int szBtn:           50
    readonly property int szBtnIcon:       36
    readonly property int szBtnIconSrc:    112

    color:        isSelected ? clrCardBgSel : clrCardBg
    radius:       szCardRadius
    border.color: isSelected ? clrBorderSel : clrBorder
    border.width: isSelected ? 2 : 1
    height:       spRow.implicitHeight + szCardPadding

    TapHandler { onTapped: root.tapped() }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        id: spRow
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
                source: "../icons/target.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: 0; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        GridLayout {
            columns: 2
            rowSpacing: szGridRowGap; columnSpacing: szGridColGap
            Layout.preferredWidth: szGridWidth
            Layout.maximumWidth:  szGridWidth

            Label { text: "X Start"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                Layout.preferredWidth: szInputWidth
                description: "StartPoint X Start"
                settingName: "sp." + primIdx + ".x_start"
                validatorObject: dblVal
                value: primData.x_start !== undefined ? primData.x_start : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) {
                    root.tapped()
                    root.openNumPadRequested(field)
                }
                onValueCommitted: function(committedValue) {
                    root.tapped()
                    var d = JSON.parse(JSON.stringify(primData))
                    d.x_start = Number(committedValue)
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "Z Start"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                Layout.preferredWidth: szInputWidth
                description: "StartPoint Z Start"
                settingName: "sp." + primIdx + ".z_start"
                validatorObject: dblVal
                value: primData.z_start !== undefined ? primData.z_start : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) {
                    root.tapped()
                    root.openNumPadRequested(field)
                }
                onValueCommitted: function(committedValue) {
                    root.tapped()
                    var d = JSON.parse(JSON.stringify(primData))
                    d.z_start = Number(committedValue)
                    root.primUpdated(primIdx, d)
                }
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
            enabled: root._blendType === "none" && root.primCount > 1
            opacity: enabled ? 1.0 : 0.35
            color:   spChamferMA.pressed ? clrBlendBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: spChamferMA.pressed ? clrBlendBtnHoverBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/chamfer.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: spChamferMA; anchors.fill: parent; enabled: parent.enabled
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
            enabled: root._blendType === "none" && root.primCount > 1
            opacity: enabled ? 1.0 : 0.35
            color:   spFilletMA.pressed ? clrBlendBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: spFilletMA.pressed ? clrBlendBtnHoverBorder : clrBtnBorder
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                source: "../icons/fillet.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
            MouseArea {
                id: spFilletMA; anchors.fill: parent; enabled: parent.enabled
                onClicked: {
                    var d = JSON.parse(JSON.stringify(primData))
                    if (!d.blend) d.blend = {}
                    d.blend.type = "fillet"
                    if (d.blend.fillet_radius === undefined) d.blend.fillet_radius = 1.0
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
