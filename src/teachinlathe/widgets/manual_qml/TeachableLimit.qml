import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"

Rectangle {
    id: root

    property string title: ""
    property string value: "--none--"
    property string settingName: ""
    property string description: ""
    property int status: 1
    property string toggleText: "Enable Limit"
    property bool toggleEnabled: false
    property bool teachEnabled: true

    signal teachClicked()
    signal toggleClicked()
    signal openNumPadRequested(var field)
    signal committed(var value)

    readonly property color disabledColor: "#323232"
    readonly property color enabledColor: "#1a5fb4"
    readonly property color pendingColor: "#ff8c00"
    readonly property color reachedColor: "#ff0000"
    readonly property color activeColor: status === 0 ? enabledColor : status === 2 ? pendingColor : status === 3 ? reachedColor : disabledColor

    width: 205
    height: 118
    radius: 8
    color: "#e6e6e6"
    border.color: activeColor
    border.width: status === 1 ? 1 : 3

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Text {
            Layout.fillWidth: true
            text: root.title
            color: root.activeColor
            font.pixelSize: 16
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            NumpadField {
                id: limitInput
                Layout.preferredWidth: 105
                Layout.preferredHeight: 36
                enabled: root.status === 1
                value: root.value
                settingName: root.settingName
                description: root.description
                fontPixelSize: 15
                hAlign: Text.AlignRight
                formatter: function(v) { return (v === null || v === undefined) ? "" : String(v) }
                parser: function(s) { return String(s) }
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: root.committed(value)
            }

            Button {
                Layout.preferredWidth: 76
                Layout.preferredHeight: 36
                text: "TeachIn"
                enabled: root.teachEnabled && root.status === 1
                font.pixelSize: 13
                onClicked: root.teachClicked()
            }
        }

        Button {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            text: root.toggleText
            enabled: root.toggleEnabled
            font.pixelSize: 14
            onClicked: root.toggleClicked()
        }
    }

    function setDisplayValue(v) {
        root.value = v
    }
}
