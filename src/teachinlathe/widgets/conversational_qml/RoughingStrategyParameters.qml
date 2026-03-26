// RoughingStrategyParameters.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

GroupBox {
    id: root
    title: "Roughing Strategy"
    Layout.fillWidth: true

    property string movement:  "axially"   // "axially" | "radially" | "diagonal"
    property string cutToward: "interior"  // "interior" | "exterior"

    property bool _loading: false

    signal saveRequested(var payload)

    function applyData(data) {
        _loading = true
        var m = (data && data.movement)   ? data.movement   : "axially"
        var c = (data && data.cut_toward) ? data.cut_toward : "interior"
        movement  = m
        cutToward = c
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            roughing_strategy: {
                movement:   movement,
                cut_toward: cutToward
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- Movement ---
        Label {
            text: "Pass type"
            font.pixelSize: 14
            font.bold: true
        }

        RowLayout {
            spacing: 20
            RadioButton {
                id: rbAxial
                text: "Axial Passes"
                font.pixelSize: 15
                checked: root.movement === "axially"
                onToggled: if (checked) { root.movement = "axially"; root.emitSave() }
            }
            RadioButton {
                id: rbRadial
                text: "Radial Passes"
                font.pixelSize: 15
                checked: root.movement === "radially"
                onToggled: if (checked) { root.movement = "radially"; root.emitSave() }
            }
            RadioButton {
                id: rbDiagonal
                text: "45° Passes"
                font.pixelSize: 15
                checked: root.movement === "diagonal"
                onToggled: if (checked) { root.movement = "diagonal"; root.emitSave() }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#bdbdbd"
        }

        // --- Cut direction ---
        Label {
            text: "Cut direction"
            font.pixelSize: 14
            font.bold: true
        }

        RowLayout {
            spacing: 20
            RadioButton {
                id: rbInterior
                text: "Cut toward interior"
                font.pixelSize: 15
                checked: root.cutToward === "interior"
                onToggled: if (checked) { root.cutToward = "interior"; root.emitSave() }
            }
            RadioButton {
                id: rbExterior
                text: "Cut toward exterior"
                font.pixelSize: 15
                checked: root.cutToward === "exterior"
                onToggled: if (checked) { root.cutToward = "exterior"; root.emitSave() }
            }
        }
    }
}
