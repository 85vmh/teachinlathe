// ChamferFilletBlendCard.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"

Rectangle {
    id: root

    property var  primData:   ({})
    property int  primIdx:    0
    property bool isSelected: false

    readonly property string _blendType:
        (primData && primData.blend && primData.blend.type) ? primData.blend.type : "none"
    readonly property real _blendValue: {
        if (!primData || !primData.blend) return 0
        if (primData.blend.type === "chamfer")
            return primData.blend.chamfer_width !== undefined ? primData.blend.chamfer_width : 0
        if (primData.blend.type === "fillet")
            return primData.blend.fillet_radius !== undefined ? primData.blend.fillet_radius : 0
        return 0
    }

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()
    signal blendClearRequested(int idx)

    // Colors
    readonly property color clrCardBg:            "white"
    readonly property color clrCardBgSel:         "#dbeafe"
    readonly property color clrBorder:            "#cccccc"
    readonly property color clrBorderSel:         "#3b82f6"
    readonly property color clrSeparator:         "#d0d0d0"
    readonly property color clrBtnBorder:         "#BDBDBD"
    readonly property color clrDeleteHover:       "#ffebee"
    readonly property color clrDeleteBorder:      "#C62828"

    // Sizes
    readonly property int szCardRadius:    4
    readonly property int szCardPadding:   24
    readonly property int szMargin:        12
    readonly property int szSpacing:       4
    readonly property int szIconArea:      56
    readonly property int szIconSize:      56
    readonly property int szFont:          14
    readonly property int szGridColGap:    8
    readonly property int szGridWidth:     180
    readonly property int szInputWidth:    110
    readonly property int szSepInset:      4
    readonly property int szSepGap:        8
    readonly property int szBtn:           40
    readonly property int szBtnIcon:       28
    readonly property int szBtnIconSrc:    112

    function _commitBlend(v) {
        var d = JSON.parse(JSON.stringify(primData))
        if (!d.blend) d.blend = { type: "chamfer" }
        if (d.blend.type === "chamfer") d.blend.chamfer_width = v
        else if (d.blend.type === "fillet") d.blend.fillet_radius = v
        root.primUpdated(primIdx, d)
    }

    color:        isSelected ? clrCardBgSel : clrCardBg
    radius:       szCardRadius
    border.color: isSelected ? clrBorderSel : clrBorder
    border.width: isSelected ? 2 : 1
    height:       blendRow.implicitHeight + szCardPadding

    TapHandler { onTapped: root.tapped() }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        id: blendRow
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
                source: root._blendType === "chamfer" ? "../icons/chamfer.svg" : "../icons/fillet.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: 0; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        RowLayout {
            spacing: szGridColGap
            Layout.preferredWidth: szGridWidth
            Layout.maximumWidth:   szGridWidth

            Label {
                text: root._blendType === "chamfer" ? "Width" : "Radius"
                font.pixelSize: szFont
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: true
            }

            NumpadField {
                Layout.preferredWidth: szInputWidth
                settingName: root._blendType === "chamfer" ? "profiling.chamfer_width" : "profiling.fillet_radius"
                validatorObject: dblVal
                value: root._blendValue
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight; fontPixelSize: szFont
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root._commitBlend(value)
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: szSepGap; Layout.rightMargin: 0
            color: clrSeparator
        }

        Item { Layout.fillWidth: true }

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
                onClicked: root.blendClearRequested(primIdx)
            }
        }
    }
}
