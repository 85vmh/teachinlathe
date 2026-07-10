// UndercutDin509BlendCard.qml
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

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()
    signal blendClearRequested(int idx)

    // Colors
    readonly property color clrCardBg:            "#f5f7fb"
    readonly property color clrCardBgSel:         "#dbeafe"
    readonly property color clrBorder:            "#cccccc"
    readonly property color clrBorderSel:         "#3b82f6"
    readonly property color clrSeparator:         "#d0d0d0"
    readonly property color clrBtnBorder:         "#BDBDBD"
    readonly property color clrDeleteHover:       "#ffebee"
    readonly property color clrDeleteBorder:      "#C62828"

    // Sizes
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

    function _commitUndercutField(field, v) {
        var d = JSON.parse(JSON.stringify(primData))
        if (!d.blend) d.blend = { type: "undercut_din509" }
        d.blend[field] = v
        root.primUpdated(primIdx, d)
    }

    function _undercutValue(field, defaultValue) {
        if (!primData || !primData.blend) return defaultValue
        return primData.blend[field] !== undefined ? primData.blend[field] : defaultValue
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
                source: "../icons/undercut.svg"
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
            Layout.maximumWidth:   szGridWidth

            Label { text: "Radius"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Undercut blend radius"
                Layout.preferredWidth: szInputWidth
                settingName: "blend." + primIdx + ".undercut_radius"
                validatorObject: dblVal
                value: root._undercutValue("undercut_radius", 0.4)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root._commitUndercutField("undercut_radius", value)
            }

            Label { text: "Depth"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Undercut depth in mm/radius"
                Layout.preferredWidth: szInputWidth
                settingName: "blend." + primIdx + ".undercut_depth"
                validatorObject: dblVal
                value: root._undercutValue("undercut_depth", 0.4)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root._commitUndercutField("undercut_depth", value)
            }

            Label { text: "Length"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Undercut overall length"
                Layout.preferredWidth: szInputWidth
                settingName: "blend." + primIdx + ".undercut_length"
                validatorObject: dblVal
                value: root._undercutValue("undercut_length", 2.5)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root._commitUndercutField("undercut_length", value)
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
