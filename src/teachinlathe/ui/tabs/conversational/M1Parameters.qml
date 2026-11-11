// M1Parameters.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common
import TeachInLathe

TitledCard {
    id: root
    title: "Pause to Inspect"
    Layout.fillWidth: true
    Layout.minimumWidth: 420
    Layout.preferredWidth: 560
    font.pixelSize: Theme.fontBody

    /* --- Public API --- */
    // the operation's m1_parameters, as its editor has it: all it shows
    property var    m1: ({})
    readonly property bool include_m1: m1 && m1.include_m1 !== undefined ? !!m1.include_m1 : true
    // where it stops, a PauseToInspect.Position
    readonly property int inspect_position: m1 && m1.inspect_position !== undefined
                                            ? m1.inspect_position : PauseToInspect.G28
    // offer a third place to stop: where the tool is (IN_PLACE) - Drilling's
    // and Tapping's
    property bool   allowStayInPlace: false

    // the whole m1_parameters, with the change made; the panel itself keeps
    // nothing, and shows the change once ``m1`` has it
    signal m1Edited(var m1)

    property bool readOnly: false

    // how wide each Retract button's half of the row is, for rows elsewhere
    // that space their buttons the same
    readonly property real optionWidth: rbG28.width

    function _edit(includeM1, inspectPosition) {
        root.m1Edited({ include_m1: !!includeM1, inspect_position: inspectPosition })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- master toggle ---
        RowLayout {
            Layout.fillWidth: true
            ModelCheckBox {
                id: includeBox
                text: "Allow inspection after each pass"
                checked: root.include_m1
                enabled: !root.readOnly
                onToggledTo: function(on) { root._edit(on, root.inspect_position) }
            }
            Item { Layout.fillWidth: true }
        }

        // --- horizontal separator ---
        Rectangle {
            Layout.fillWidth: true
            height: Theme.hairline
            color: Theme.outlineStrong
        }

        // --- Inspect position radio buttons ---
        // each takes half the row, so what the texts leave falls between them
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            enabled: root.include_m1 && !root.readOnly
            opacity: root.include_m1 ? 1.0 : 0.5

            ModelRadioButton {
                id: rbInPlace
                visible: root.allowStayInPlace
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                text: "Stay there"
                font.pixelSize: Theme.fontBody
                checked: root.inspect_position === PauseToInspect.InPlace
                onChosen: root._edit(root.include_m1, PauseToInspect.InPlace)
            }

            ModelRadioButton {
                id: rbG28
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                text: "Move to <b>G28</b>"
                font.pixelSize: Theme.fontBody
                checked: root.inspect_position === PauseToInspect.G28
                onChosen: root._edit(root.include_m1, PauseToInspect.G28)
            }

            ModelRadioButton {
                id: rbG30
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                text: "Move to <b>G30</b>"
                font.pixelSize: Theme.fontBody
                checked: root.inspect_position === PauseToInspect.G30
                onChosen: root._edit(root.include_m1, PauseToInspect.G30)
            }
        }

    }
}
