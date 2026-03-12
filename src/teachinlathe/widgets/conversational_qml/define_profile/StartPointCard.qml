// StartPointCard.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: root

    property var  primData:   ({})
    property int  primIdx:    0
    property bool isSelected: false

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()

    // ── Colors ────────────────────────────────────────────────────────────────
    readonly property color clrCardBg:        "white"
    readonly property color clrCardBgSel:     "#dbeafe"
    readonly property color clrBorder:        "#cccccc"
    readonly property color clrBorderSel:     "#3b82f6"
    readonly property color clrSeparator:     "#d0d0d0"

    // ── Sizes ─────────────────────────────────────────────────────────────────
    readonly property int szCardRadius:    4
    readonly property int szCardPadding:   24
    readonly property int szMargin:        12
    readonly property int szSpacing:       4
    readonly property int szIconArea:      56
    readonly property int szIconSize:      56
    readonly property int szFont:          14
    readonly property int szGridRowGap:    6
    readonly property int szGridColGap:    8
    readonly property int szGridWidth:     180
    readonly property int szInputWidth:    110
    readonly property int szSepInset:      4
    readonly property int szSepGap:        8

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
                settingName: "sp." + primIdx + ".x_start"
                validatorObject: dblVal
                value: primData.x_start !== undefined ? primData.x_start : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight; fontPixelSize: szFont
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.x_start = value
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "Z Start"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                Layout.preferredWidth: szInputWidth
                settingName: "sp." + primIdx + ".z_start"
                validatorObject: dblVal
                value: primData.z_start !== undefined ? primData.z_start : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight; fontPixelSize: szFont
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.z_start = value
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}