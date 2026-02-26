// BlendCard.qml
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
    signal blendClearRequested(int idx)

    readonly property string _blendType:
        (primData && primData.blend && primData.blend.type) ? primData.blend.type : "none"
    readonly property real _blendValue: {
        if (!primData || !primData.blend) return 0
        if (primData.blend.type === "chamfer")
            return primData.blend.chamfer_width  !== undefined ? primData.blend.chamfer_width  : 0
        if (primData.blend.type === "fillet")
            return primData.blend.fillet_radius  !== undefined ? primData.blend.fillet_radius  : 0
        return 0
    }

    function _commitBlend(v) {
        var d = JSON.parse(JSON.stringify(primData))
        if (!d.blend) d.blend = { type: "chamfer" }
        if (d.blend.type === "chamfer") d.blend.chamfer_width = v
        else if (d.blend.type === "fillet") d.blend.fillet_radius = v
        root.primUpdated(primIdx, d)
    }

    color:        isSelected ? "#fef9c3" : "#f5f5f5"
    radius:       4
    border.color: isSelected ? "#d97706" : "#c0c8d8"
    border.width: isSelected ? 2 : 1
    height:       blendRow.implicitHeight + 24

    TapHandler { onTapped: root.tapped() }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    // Left accent bar
    Rectangle {
        id: blendAccent
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
        width: 4; radius: 2
        color: isSelected ? "#d97706" : "#94a3b8"
    }

    RowLayout {
        id: blendRow
        anchors {
            left: blendAccent.right; right: parent.right
            top: parent.top; margins: 12; leftMargin: 8
        }
        spacing: 4

        Item {
            implicitWidth: 56
            Layout.fillHeight: true

            Text {
                anchors.top: parent.top
                anchors.left: parent.left
                text: (primIdx + 1) + "."
                font.pixelSize: 14; font.bold: true
                color: "#F2992E"
            }

            Image {
                anchors.centerIn: parent
                width: 40; height: 40
                sourceSize.width: 40; sourceSize.height: 40
                source: root._blendType === "chamfer" ? "../icons/chamfer.svg" : "../icons/fillet.svg"
                fillMode: Image.PreserveAspectFit; smooth: true
            }
        }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: 4; Layout.bottomMargin: 4
            Layout.leftMargin: 0; Layout.rightMargin: 8
            color: "#d0d0d0"
        }

        RowLayout {
            spacing: 8
            Layout.preferredWidth: 180
            Layout.maximumWidth:   180

            Label {
                text: root._blendType === "chamfer" ? "Width" : "Radius"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: true
            }

            NumpadField {
                Layout.preferredWidth: 110
                settingName: "blend." + primIdx + ".value"
                validatorObject: dblVal
                value: root._blendValue
                formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
                hAlign: Text.AlignRight; fontPixelSize: 14
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root._commitBlend(value)
            }
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            width: 1; Layout.fillHeight: true
            Layout.topMargin: 4; Layout.bottomMargin: 4
            Layout.leftMargin: 8; Layout.rightMargin: 0
            color: "#d0d0d0"
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            implicitWidth: 40; implicitHeight: 40; radius: 4
            color:   delMA.pressed ? "#ffebee" : "transparent"
            border.width: 1
            border.color: delMA.pressed ? "#C62828" : "#BDBDBD"
            Layout.alignment: Qt.AlignVCenter
            Image {
                anchors.centerIn: parent; width: 28; height: 28
                sourceSize.width: 112; sourceSize.height: 112
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