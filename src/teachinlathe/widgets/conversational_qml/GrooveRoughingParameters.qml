import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "../touchable_input"

GroupBox {
    id: root
    title: "Grooving Parameters"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: 16

    property int profile_id: 1
    property string strategy: "start_center"
    property real initial_offset: 1.5
    property real afterwards_offset: 1.0
    property bool _loading: false

    signal saveRequested(var payload)
    signal openNumPadRequested(var field)

    function applyData(data) {
        _loading = true
        var d = data || {}
        profile_id = d.profile_id !== undefined ? Math.round(Number(d.profile_id)) : 1
        strategy = d.strategy !== undefined ? String(d.strategy) : "start_center"
        initial_offset = d.initial_offset !== undefined ? Number(d.initial_offset) : 1.5
        afterwards_offset = d.afterwards_offset !== undefined ? Number(d.afterwards_offset) : 1.0
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            roughing_parameters: {
                profile_id: Number(profile_id),
                strategy: strategy,
                initial_offset: Number(initial_offset),
                afterwards_offset: Number(afterwards_offset)
            }
        })
    }

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: intVal; bottom: 1; top: 999 }

    GridLayout {
        anchors.fill: parent
        columns: 3
        columnSpacing: 20
        rowSpacing: 16

        Label { text: "Profile ID"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.profile_id"
            value: root.profile_id
            validatorObject: intVal
            formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.profile_id = Math.round(value); root.emitSave() }
        }
        Label { text: ""; font.pixelSize: 16 }

        Label { text: "Strategy"; font.pixelSize: 16 }
        ComboBox {
            id: strategyCombo
            Layout.preferredWidth: 200
            Layout.preferredHeight: 48
            font.pixelSize: 20
            textRole: "label"
            valueRole: "value"
            model: [
                { label: "Start Center", value: "start_center" },
                { label: "Start Right", value: "start_right" },
                { label: "Start Left", value: "start_left" }
            ]
            Component.onCompleted: currentIndex = indexOfValue(root.strategy)
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: parent.displayText
                font: parent.font
                color: "#0f172a"
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: parent.width
                height: 48
                text: modelData.label
                font.pixelSize: 20
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
        Label { text: ""; font.pixelSize: 16 }

        Label { text: "Initial Offset"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.initial_offset"
            value: root.initial_offset
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.initial_offset = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: 16 }

        Label { text: "Afterwards Offset"; font.pixelSize: 16 }
        NumpadField {
            Layout.preferredWidth: 100
            settingName: "groove_roughing.afterwards_offset"
            value: root.afterwards_offset
            validatorObject: dblVal
            formatter: function(v) { return v == null ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: root.openNumPadRequested(field)
            onValueCommitted: { root.afterwards_offset = value; root.emitSave() }
        }
        Label { text: "(mm)"; font.pixelSize: 16 }
    }
}
