import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"
import theme 1.0

GroupBox {
    id: root
    title: "Finishing Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    property int profile_id: 1
    property string strategy: "towards_center"
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        var d = data || {}
        profile_id = d.profile_id !== undefined ? Math.round(Number(d.profile_id)) : 1
        strategy = d.strategy !== undefined ? String(d.strategy) : "towards_center"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            finishing_parameters: {
                profile_id: Number(profile_id),
                strategy: strategy
            }
        })
    }

    IntValidator { id: intVal; bottom: 1; top: 999 }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 16

        Label { text: "Profile ID"; font.pixelSize: Theme.fontBody }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_finishing.profile_id"
            value: root.profile_id
            validatorObject: intVal
            formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.profile_id = Math.round(value); root.emitSave() }
        }
        Label { text: ""; font.pixelSize: Theme.fontBody }

        Label { text: "Strategy"; font.pixelSize: Theme.fontBody }
        ComboBox {
            id: strategyCombo
            Layout.preferredWidth: 200
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontTitle
            textRole: "label"
            valueRole: "value"
            model: [
                { label: "Towards Center", value: "towards_center" },
                { label: "Towards Left", value: "towards_left" },
                { label: "Towards Right", value: "towards_right" }
            ]
            Component.onCompleted: currentIndex = indexOfValue(root.strategy)
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: parent.displayText
                font: parent.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: parent.width
                height: Theme.inputHeight
                text: modelData.label
                font.pixelSize: Theme.fontTitle
            }
            onActivated: {
                root.strategy = currentValue
                root.emitSave()
            }
            Connections {
                target: root
                function onStrategyChanged() {
                    strategyCombo.currentIndex = strategyCombo.indexOfValue(root.strategy)
                }
            }
        }
        Label { text: ""; font.pixelSize: Theme.fontBody }
    }
}
