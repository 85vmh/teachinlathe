import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var viewModel
    readonly property var actions: viewModel ? viewModel.actions : null
    color: "#f5f5f5"
    border.color: "#cccccc"
    border.width: 1

    RowLayout {
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
            leftMargin: 16
            rightMargin: 16
        }
        spacing: 20

        // ── Cycle Abort ───────────────────────────────────────────────
        MachineButton {
            text: "Cycle\nAbort"
            enabled: actions ? actions.stopAction.enabled : false
            active: false
            centerColor:       "#6a0000"
            midColor:          "#c62828"
            rimColor:          "#ef9a9a"
            activeCenterColor: "#c62828"
            activeRimColor:    "#ef9a9a"
            onClicked: if (actions) actions.triggerStop()
        }

        // ── Cycle Start / Pause / Resume ──────────────────────────────
        MachineButton {
            text:    actions ? actions.cycleStartAction.text    : "Cycle\nStart"
            enabled: actions ? actions.cycleStartAction.enabled : false
            active:  actions ? actions.cycleStartAction.active  : false
            centerColor:       "#1a5e20"
            midColor:          "#2e7d32"
            rimColor:          "#a5d6a7"
            activeCenterColor: "#2e7d32"
            activeRimColor:    "#81c784"
            onClicked: if (actions) actions.triggerCycleStart()
        }

        // ── spacer ────────────────────────────────────────────────────
        Item { Layout.fillWidth: true }

        // ── Feed Override ─────────────────────────────────────────────
        OverrideSelector {
            label: "Rapid Override"
            maxSpeed: 6000
            value: 100
            Layout.alignment: Qt.AlignVCenter
            onSelected: function(v) { /* TODO: wire to HAL feed override pin */ }
        }
    }
}
