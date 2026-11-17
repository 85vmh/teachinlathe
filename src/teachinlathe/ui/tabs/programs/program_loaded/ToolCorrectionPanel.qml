import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common.touchable_input

// The current loaded tool corrected at an M1: ΔØ and ΔZ, the tool's offsets
// now and as they leave them, and Arm - the remap applies it on Cycle Start.
// On the numpad dialogs' frame. Everything it shows is the view model's
// (ToolCorrectionViewModel); each entry goes to it as it is made.
NumpadPopup {
    id: root

    required property var correction

    width: 500

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
        NumberAnimation { property: "scale"; from: 0.95; to: 1; duration: 150; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 }
    }

    // the correction can no longer be armed - the program went on: close
    Connections {
        target: root.correction
        function onChanged() { if (root.opened && !root.correction.canCorrect) root.close() }
    }

    SmartNumpadDialog { id: numpad }

    // what an entry does, after it: a fixed room, so the dialog does not
    // move as it changes
    component EffectText: Text {
        Layout.preferredWidth: 280
        textFormat: Text.StyledText
        color: Theme.foregroundMuted
        font.pixelSize: Theme.fontBody
    }

    readonly property var formatter: function(v) { return v === null || v === undefined ? "" : Number(v).toFixed(3) }

    contentItem: ColumnLayout {
        spacing: Theme.spacingLarge

        Text {
            text: root.correction.buttonText
            font.pixelSize: Theme.fontTitle
            font.bold: true
            color: Theme.foreground
        }

        // the inputs, as far apart as the boxes on a canvas (boxGap)
        GridLayout {
            columns: 3
            columnSpacing: Theme.spacingLarge
            rowSpacing: Theme.spacingLarge

            Text { text: "ΔØ"; color: Theme.foreground; font.pixelSize: Theme.fontBody }
            NumpadField {
                Layout.preferredWidth: 100
                settingName: "inspect.d_diameter"
                description: "ΔØ (− cuts smaller on the diameter)"
                seedNumpadFromValue: true
                value: root.correction.dDiameter
                formatter: root.formatter
                onOpenRequested: function(field, settingName) { numpad.openFor(field, settingName, description) }
                onValueCommitted: function(value) { root.correction.setDDiameter(value) }
            }
            EffectText { text: root.correction.diameterEffectText }

            Text { text: "ΔZ"; color: Theme.foreground; font.pixelSize: Theme.fontBody }
            NumpadField {
                Layout.preferredWidth: 100
                settingName: "inspect.dz"
                description: "ΔZ (− cuts further toward Z−)"
                seedNumpadFromValue: true
                value: root.correction.dz
                formatter: root.formatter
                onOpenRequested: function(field, settingName) { numpad.openFor(field, settingName, description) }
                onValueCommitted: function(value) { root.correction.setDz(value) }
            }
            EffectText { text: root.correction.zEffectText }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.hairline
            color: Theme.outline
        }

        // the offsets: now, and as the correction leaves them
        Grid {
            id: offsets
            Layout.alignment: Qt.AlignHCenter
            columns: 5
            rowSpacing: 0
            columnSpacing: 0
            verticalItemAlignment: Grid.AlignVCenter

            readonly property int cellWidth: 130
            readonly property int cellHeight: 36

            // a row: its name, the value now, a separator, the corrected value
            component Cell: Text {
                property bool strong: false
                width: offsets.cellWidth
                height: offsets.cellHeight
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
                font.bold: strong
            }
            component VLine: Rectangle {
                width: Theme.hairline
                height: offsets.cellHeight
                color: Theme.outline
            }
            component HLine: Rectangle {
                width: offsets.cellWidth
                height: Theme.hairline
                color: Theme.outline
            }
            component Cross: Rectangle {
                width: Theme.hairline
                height: Theme.hairline
                color: Theme.outline
            }

            Cell { text: "" }
            VLine {}
            Cell { text: "Current"; color: Theme.foregroundMuted }
            VLine {}
            Cell { text: "Corrected"; color: Theme.foregroundMuted }

            HLine {} Cross {} HLine {} Cross {} HLine {}

            Cell { text: "X Offset (r)"; horizontalAlignment: Text.AlignLeft }
            VLine {}
            Cell { text: root.correction.currentXText }
            VLine {}
            Cell { text: root.correction.correctedXText; strong: root.correction.xCorrected }

            HLine {} Cross {} HLine {} Cross {} HLine {}

            Cell { text: "Z Offset"; horizontalAlignment: Text.AlignLeft }
            VLine {}
            Cell { text: root.correction.currentZText }
            VLine {}
            Cell { text: root.correction.correctedZText; strong: root.correction.zCorrected }
        }

        Text {
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.correction.errorText
            color: Theme.warning
            font.pixelSize: Theme.fontBody
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.hairline
            color: Theme.outline
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: Theme.spacingLarge

            RunActionButton {
                text: "Cancel"
                fill: Theme.foregroundMuted
                pressedFill: Theme.foreground
                edge: Theme.outline
                onClicked: root.close()
            }
            RunActionButton {
                text: "Arm correction"
                enabled: root.correction.canArm
                onClicked: {
                    if (root.correction.arm() === "")
                        root.close()
                }
            }
        }
    }
}
