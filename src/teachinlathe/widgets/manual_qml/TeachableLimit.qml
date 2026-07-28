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
    property int minimumCardWidth: 220
    property int buttonHeight: 48
    property int contentMargin: 8
    property int sectionSpacing: 8

    signal teachClicked()
    signal toggleClicked()
    signal openNumPadRequested(Item field)
    signal committed(string value)

    readonly property color disabledColor: "#323232"
    readonly property color enabledColor: "#1a5fb4"
    readonly property color pendingColor: "#ff8c00"
    readonly property color reachedColor: "#ff0000"
    readonly property color activeColor: status === 0 ? enabledColor : status === 2 ? pendingColor : status === 3 ? reachedColor : disabledColor
    readonly property string limitName: title.indexOf("Limit ") === 0 ? title.substring(6) : title.replace(" Limit", "")
    readonly property string limitActionText: toggleText.indexOf("Disable") === 0
        ? "Disable " + limitName + " Limit"
        : toggleText.indexOf("Pending") === 0
            ? toggleText
            : "Enable " + limitName + " Limit"
    function formatLimitValue(v) {
        if (v === null || v === undefined || v === "" || v === "--none--") {
            return (v === null || v === undefined) ? "" : String(v)
        }
        var numberValue = Number(String(v).trim())
        return isNaN(numberValue) ? String(v) : numberValue.toFixed(3)
    }

    width: Math.max(minimumCardWidth, toggleButton.implicitWidth + 32)
    height: contentMargin * 2 + buttonHeight * 2 + sectionSpacing * 2 + 1
    radius: 6
    color: "#f5f5f5"
    border.color: activeColor
    border.width: status === 1 ? 1 : 3

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.contentMargin
        spacing: 0

        Button {
            id: toggleButton
            Layout.fillWidth: true
            Layout.preferredHeight: root.buttonHeight
            text: root.limitActionText
            enabled: root.toggleEnabled
            font.pixelSize: 16
            onClicked: root.toggleClicked()
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: root.sectionSpacing
            Layout.bottomMargin: root.sectionSpacing
            height: 1
            color: "#ccc"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            NumpadField {
                id: limitInput
                Layout.preferredWidth: 110
                enabled: root.status === 1
                value: root.value
                settingName: root.settingName
                description: root.description
                hAlign: Text.AlignRight
                formatter: root.formatLimitValue
                parser: function(s) { return String(s) }
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: {
                    var formattedValue = root.formatLimitValue(value)
                    limitInput.value = formattedValue
                    root.committed(formattedValue)
                }
            }

            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: root.buttonHeight
                text: "TeachIn"
                enabled: root.teachEnabled && root.status === 1
                font.pixelSize: 16
                onClicked: root.teachClicked()
            }
        }
    }

    function setDisplayValue(v) {
        root.value = v
    }
}
