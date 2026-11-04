// UndercutDin509BlendCard.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import common.touchable_input
import theme
import common

Rectangle {
    id: root

    property var  primData:   ({})
    property int  primIdx:    0
    property bool isSelected: false

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()

    // Colors
    readonly property color clrCardBg:            Theme.surfaceAlt
    readonly property color clrCardBgSel:         Theme.selection
    readonly property color clrBorder:            Theme.outline
    readonly property color clrBorderSel:         Theme.accent
    readonly property color clrSeparator:         "#d0d0d0"

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
                source: Images.url("undercut.svg")
                fillMode: Image.PreserveAspectFit; smooth: true
            }
        }

        Rectangle {
            width: Theme.hairline; Layout.fillHeight: true
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
                seedNumpadFromValue: true
                value: root._undercutValue("undercut_radius", 0.4)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._commitUndercutField("undercut_radius", value) }
            }

            Label { text: "Depth"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Undercut depth in mm/radius"
                Layout.preferredWidth: szInputWidth
                settingName: "blend." + primIdx + ".undercut_depth"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: root._undercutValue("undercut_depth", 0.4)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._commitUndercutField("undercut_depth", value) }
            }

            Label { text: "Length"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Undercut overall length"
                Layout.preferredWidth: szInputWidth
                settingName: "blend." + primIdx + ".undercut_length"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: root._undercutValue("undercut_length", 2.5)
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                onValueCommitted: function(value) { root._commitUndercutField("undercut_length", value) }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
