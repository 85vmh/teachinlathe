// SmartNumpadDialog.qml — QML numpad dialog, on the frame the numpad
// dialogs share (NumpadPopup).
//
// Driven by the `viewModel` property, which defaults to the app's
// NumpadDialogViewModel singleton (module TeachInLathe). Open it with:
//     dialog.openFor(field, settingName, descriptionOverride)
// where `field` is a NumpadField. On accept it writes the value back via
// field.commit(value) and persists it via viewModel.commitValue().
//
// Two modes:
//   • "select"  — predefined value buttons (when the JSON entry has options)
//   • "numpad"  — numeric keypad, NumpadKeypad (default / "Other values..." / no options)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common
import TeachInLathe

NumpadPopup {
    id: root

    // Which numpad view model drives this dialog. Each screen has its own
    // (the manual tab persists the last value, conversational does not), so
    // it is passed in rather than read from a single context property.
    property var viewModel: NumpadDialogViewModel

    // ── State for the currently edited field (targetField: NumpadPopup) ─
    // view state: the field the open numpad is for
    property string settingName: ""
    // view state: the open numpad's title
    property string titleText: "Enter value"
    // view state: what the open numpad offers
    property var    options: []
    // view state: what the open numpad offers
    property bool   hasOptions: false
    // view state: what the open numpad offers
    property string valueType: ""
    // view state: what the open numpad offers
    property string mode: "numpad"          // "select" | "numpad"
    // the select mode's buttons
    readonly property int optionHeight: 60
    readonly property int optionFontSize: 18
    readonly property int buttonSpacing: 20

    width: 500
    // as high as the numpad mode needs: the title and the keypad - the
    // select mode the same height
    height: topPadding + bottomPadding + titleLabel.implicitHeight + buttonSpacing
            + keypad.implicitHeight
    // typed into from the computer's keyboard while it is shown - not over
    // the predefined values
    keyboardItem: keypad

    // ── Public API ────────────────────────────────────────────────────
    function openFor(field, settingName, descriptionOverride) {
        root.targetField = field
        root.settingName = settingName || ""

        var cfg = root.viewModel
                    ? root.viewModel.configFor(root.settingName)
                    : ({ hasOptions: false, options: [], description: "" })

        root.options    = cfg.options || []
        root.hasOptions = !!cfg.hasOptions
        root.valueType  = cfg.valueType || ""

        var title = (descriptionOverride && String(descriptionOverride).length > 0)
                      ? descriptionOverride
                      : (cfg.description || "")
        root.titleText = title.length > 0 ? title : "Enter value"

        keypad.resetTo(field ? field.value : null, field ? field.formatter : null)
        root.mode = root.hasOptions ? "select" : "numpad"
        root.open()
    }

    function _accept(value) {
        var v = String(value)
        if (root.targetField && root.targetField.commit) {
            root.targetField.commit(v)
        }
        if (root.viewModel) {
            root.viewModel.commitValue(root.settingName, v)
        }
        root.close()
    }

    // ── Content ───────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: root.buttonSpacing

        Text {
            id: titleLabel
            Layout.fillWidth: true
            text: root.titleText
            font.pixelSize: Theme.fontTitle
            font.bold: true
            color: Theme.foreground
            elide: Text.ElideRight
        }

        // ── SELECT mode: predefined value buttons ─────────────────────
        Item {
            visible: root.mode === "select"
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flickable {
                id: optionsFlick
                anchors.fill: parent
                contentHeight: optionsFlow.implicitHeight
                clip: true

                Grid {
                    id: optionsFlow
                    width: parent.width

                    readonly property int cols: 3
                    readonly property int btnW: Math.floor((width - root.buttonSpacing * (cols - 1)) / cols)
                    columns: cols
                    columnSpacing: root.buttonSpacing
                    rowSpacing: root.buttonSpacing

                    Repeater {
                        model: root.options
                        delegate: NumpadButton {
                            width: optionsFlow.btnW
                            height: root.optionHeight
                            text: String(modelData)
                            font.pixelSize: root.optionFontSize
                            onClicked: root._accept(modelData)
                        }
                    }
                }
            }

            ScrollFades {
                anchors.fill: parent
                flickable: optionsFlick
            }
        }

        NumpadButton {
            visible: root.mode === "select" && root.valueType !== "str"
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: 266
            implicitHeight: root.optionHeight
            text: "Other values..."
            font.pixelSize: root.optionFontSize
            onClicked: {
                keypad.bufferSelected = keypad.buffer.length > 0
                root.mode = "numpad"
            }
        }

        // ── NUMPAD mode ────────────────────────────────────────────────
        NumpadKeypad {
            id: keypad
            visible: root.mode === "numpad"
            Layout.fillWidth: true
            Layout.fillHeight: true
            valueType: root.valueType
            onAccepted: function(value) { root._accept(value) }
        }
    }
}
