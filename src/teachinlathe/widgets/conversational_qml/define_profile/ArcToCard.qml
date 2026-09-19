// ArcToCard.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"
import "../../touchable_input"
import theme 1.0

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
    signal deleteRequested(int idx)

    // ── Colors ────────────────────────────────────────────────────────────────
    readonly property color clrCardBg:            Theme.surfaceAlt
    readonly property color clrCardBgSel:         Theme.selection
    readonly property color clrBorder:            Theme.outline
    readonly property color clrBorderSel:         Theme.accent
    readonly property color clrSeparator:         "#d0d0d0"
    readonly property color clrDirBtnActiveBg:    "#e3f2fd"
    readonly property color clrDirBtnActiveBorder: Theme.accentStrong
    readonly property color clrBtnHover:          Theme.accentSoft
    readonly property color clrBtnHoverBorder:    Theme.accentBorder
    readonly property color clrBtnBorder:         Theme.outlineStrong
    readonly property color clrDeleteHover:       Theme.dangerSoft
    readonly property color clrDeleteBorder:      Theme.danger

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
    height:       atRow.implicitHeight + szCardPadding

    TapHandler { onTapped: root.tapped() }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    RowLayout {
        id: atRow
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
                source: "../icons/arc_to.svg"
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
            Layout.maximumWidth:  szGridWidth

            Label { text: "Direction"; font.pixelSize: szFont; Layout.fillWidth: true }
            RowLayout {
                spacing: szSpacing + 10
                Rectangle {
                    implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
                    property bool _active: primData.direction === "cw"
                    color:   _active ? clrDirBtnActiveBg : (cwMA.pressed ? clrBtnHover : "transparent")
                    border.width: Theme.hairline
                    border.color: _active ? clrDirBtnActiveBorder : (cwMA.pressed ? clrBtnHoverBorder : clrBtnBorder)
                    Image {
                        anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                        sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                        source: "../icons/cw_arrrow.svg"
                        fillMode: Image.PreserveAspectFit; smooth: true
                    }
                    MouseArea {
                        id: cwMA; anchors.fill: parent
                        onClicked: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.direction = "cw"
                            root.primUpdated(primIdx, d)
                        }
                    }
                }
                Rectangle {
                    implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
                    property bool _active: primData.direction === "ccw"
                    color:   _active ? clrDirBtnActiveBg : (ccwMA.pressed ? clrBtnHover : "transparent")
                    border.width: Theme.hairline
                    border.color: _active ? clrDirBtnActiveBorder : (ccwMA.pressed ? clrBtnHoverBorder : clrBtnBorder)
                    Image {
                        anchors.centerIn: parent; width: szBtnIcon; height: szBtnIcon
                        sourceSize.width: szBtnIconSrc; sourceSize.height: szBtnIconSrc
                        source: "../icons/ccw_arrow.svg"
                        fillMode: Image.PreserveAspectFit; smooth: true
                    }
                    MouseArea {
                        id: ccwMA; anchors.fill: parent
                        onClicked: {
                            var d = JSON.parse(JSON.stringify(primData))
                            d.direction = "ccw"
                            root.primUpdated(primIdx, d)
                        }
                    }
                }
            }

            Label { text: "Radius"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Arc radius"
                Layout.preferredWidth: szInputWidth
                settingName: "at." + primIdx + ".arc_radius"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: primData.arc_radius !== undefined ? primData.arc_radius : 10
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.arc_radius = value
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "X Center"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Arc Center on X"
                Layout.preferredWidth: szInputWidth
                settingName: "at." + primIdx + ".x_center"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: primData.x_center !== undefined ? primData.x_center : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.x_center = value
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "Z Center"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Arc Center on Z"
                Layout.preferredWidth: szInputWidth
                settingName: "at." + primIdx + ".z_center"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: primData.z_center !== undefined ? primData.z_center : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.z_center = value
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "X End"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Arc End on X"
                Layout.preferredWidth: szInputWidth
                settingName: "at." + primIdx + ".x_end"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: primData.x_end !== undefined ? primData.x_end : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.x_end = value
                    root.primUpdated(primIdx, d)
                }
            }

            Label { text: "Z End"; font.pixelSize: szFont; Layout.fillWidth: true }
            NumpadField {
                description: "Arc End on Z"
                Layout.preferredWidth: szInputWidth
                settingName: "at." + primIdx + ".z_end"
                validatorObject: dblVal
                seedNumpadFromValue: true
                value: primData.z_end !== undefined ? primData.z_end : 0
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var d = JSON.parse(JSON.stringify(primData))
                    d.z_end = value
                    root.primUpdated(primIdx, d)
                }
            }
        }

        Rectangle {
            width: Theme.hairline; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: szSepGap; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            enabled: root._blendType === "none" && root.primIdx < root.primCount - 1
            opacity: enabled ? 1.0 : 0.35
            color:   chamferMA.pressed ? clrBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: chamferMA.pressed ? clrBtnHoverBorder : clrBtnBorder
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
            color:   filletMA.pressed ? clrBtnHover : "transparent"
            border.width: enabled ? 1 : 0
            border.color: filletMA.pressed ? clrBtnHoverBorder : clrBtnBorder
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

        Item { Layout.fillWidth: true }

        Rectangle {
            width: Theme.hairline; Layout.fillHeight: true
            Layout.topMargin: szSepInset; Layout.bottomMargin: szSepInset
            Layout.leftMargin: szSepGap; Layout.rightMargin: szSepGap
            color: clrSeparator
        }

        Rectangle {
            implicitWidth: szBtn; implicitHeight: szBtn; radius: szCardRadius
            color:   delMA.pressed ? clrDeleteHover : "transparent"
            border.width: Theme.hairline
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
