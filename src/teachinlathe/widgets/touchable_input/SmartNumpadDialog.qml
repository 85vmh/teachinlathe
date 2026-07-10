// SmartNumpadDialog.qml — QML replacement for the old QWidget SmartNumPadDialog.
//
// Driven by `numpadDialogViewModel` (context property). Open it with:
//     dialog.openFor(field, settingName, descriptionOverride)
// where `field` is a NumpadField. On accept it writes the value back via
// field.commit(value) and persists it via numpadDialogViewModel.commitValue().
//
// Two modes:
//   • "select"  — predefined value buttons (when the JSON entry has options)
//   • "numpad"  — numeric keypad (default / "Other values..." / no options)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root

    // ── State for the currently edited field ──────────────────────────
    property var    targetField: null
    property string settingName: ""
    property string titleText: "Enter value"
    property var    options: []
    property bool   hasOptions: false
    property string valueType: ""
    property string mode: "numpad"          // "select" | "numpad"
    property string buffer: ""
    readonly property int buttonHeight: mode === "numpad" ? 70 : 60
    readonly property int buttonFontSize: mode === "numpad" ? 24 : 18
    readonly property int buttonSpacing: 20
    readonly property int buttonRadius: 8
    readonly property color buttonBorderColor: "#9aa3b0"
    readonly property color buttonBg: "#ffffff"
    readonly property color buttonPressedBg: "#dbeafe"
    readonly property color buttonDisabledBg: "#e1e5ea"

    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    parent: Overlay.overlay
    x: parent ? (parent.width  - width)  / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    width: 500
    height: 660
    leftPadding: 24
    rightPadding: 24
    topPadding: 24
    bottomPadding: 24

    background: Rectangle {
        color: "#f3f3f3"
        border.color: "#9aa3b0"
        border.width: 1
        radius: 8
    }

    // ── Public API ────────────────────────────────────────────────────
    function openFor(field, settingName, descriptionOverride) {
        root.targetField = field
        root.settingName = settingName || ""

        var cfg = (typeof numpadDialogViewModel !== "undefined" && numpadDialogViewModel)
                    ? numpadDialogViewModel.configFor(root.settingName)
                    : ({ hasOptions: false, options: [], description: "" })

        root.options    = cfg.options || []
        root.hasOptions = !!cfg.hasOptions
        root.valueType  = cfg.valueType || ""

        var title = (descriptionOverride && String(descriptionOverride).length > 0)
                      ? descriptionOverride
                      : (cfg.description || "")
        root.titleText = title.length > 0 ? title : "Enter value"

        root.buffer = ""
        root.mode = root.hasOptions ? "select" : "numpad"
        root.open()
    }

    function _accept(value) {
        var v = String(value)
        if (root.targetField && root.targetField.commit) {
            root.targetField.commit(v)
        }
        if (typeof numpadDialogViewModel !== "undefined" && numpadDialogViewModel) {
            numpadDialogViewModel.commitValue(root.settingName, v)
        }
        root.close()
    }

    onClosed: {
        if (targetField && targetField.defocus) targetField.defocus()
        targetField = null
    }

    // ── Content ───────────────────────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: root.buttonSpacing

        Text {
            Layout.fillWidth: true
            text: root.titleText
            font.pixelSize: 20
            font.bold: true
            color: "#1e2430"
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
                        delegate: Button {
                            width: optionsFlow.btnW
                            height: root.buttonHeight
                            text: String(modelData)
                            font.pixelSize: root.buttonFontSize
                            background: Rectangle {
                                radius: root.buttonRadius
                                color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                                border.color: root.buttonBorderColor
                                border.width: 1
                            }
                            onClicked: root._accept(modelData)
                        }
                    }
                }
            }

            // Top fade — appears when scrolled down
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 40
                visible: optionsFlick.contentY > 0
                z: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#f3f3f3" }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            // Bottom fade — appears when more values extend below the viewport
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 40
                visible: optionsFlick.contentY + optionsFlick.height < optionsFlick.contentHeight - 1
                z: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 1.0; color: "#f3f3f3" }
                }
            }
        }

        Button {
            visible: root.mode === "select" && root.valueType !== "str"
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: 266
            implicitHeight: root.buttonHeight
            text: "Other values..."
            font.pixelSize: root.buttonFontSize
            background: Rectangle {
                radius: root.buttonRadius
                color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                border.color: root.buttonBorderColor
                border.width: 1
            }
            onClicked: { root.buffer = ""; root.mode = "numpad" }
        }

        // ── NUMPAD mode ────────────────────────────────────────────────
        ColumnLayout {
            visible: root.mode === "numpad"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: root.buttonSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: root.buttonSpacing

                Label {
                    id: display
                    Layout.fillWidth: true
                    Layout.preferredHeight: 60
                    text: root.buffer
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    padding: 10
                    font.pixelSize: 24
                    font.family: "Noto Sans Mono"
                    color: "#141414"
                    background: Rectangle {
                        color: "#f6f5f4"
                        border.color: "#77767b"
                        radius: 5
                    }
                }
                Button {
                    Layout.preferredWidth: 60
                    Layout.preferredHeight: root.buttonHeight
                    text: "←"
                    font.pixelSize: root.buttonFontSize
                    background: Rectangle {
                        radius: root.buttonRadius
                        color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                        border.color: root.buttonBorderColor
                        border.width: 1
                    }
                    onClicked: root.buffer = root.buffer.slice(0, -1)
                }
                Button {
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: root.buttonHeight
                    text: "Clear"
                    font.pixelSize: root.buttonFontSize
                    background: Rectangle {
                        radius: root.buttonRadius
                        color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                        border.color: root.buttonBorderColor
                        border.width: 1
                    }
                    onClicked: root.buffer = ""
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 4 * root.buttonHeight + 3 * root.buttonSpacing
                columns: 3
                columnSpacing: root.buttonSpacing
                rowSpacing: root.buttonSpacing

                Repeater {
                    model: ["7", "8", "9", "4", "5", "6", "1", "2", "3"]
                    delegate: Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.buttonHeight
                        text: modelData
                        font.pixelSize: root.buttonFontSize
                        background: Rectangle {
                            radius: root.buttonRadius
                            color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                            border.color: root.buttonBorderColor
                            border.width: 1
                        }
                        onClicked: root.buffer += modelData
                    }
                }

                Button {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.buttonHeight
                    text: "±"
                    font.pixelSize: root.buttonFontSize
                    background: Rectangle {
                        radius: root.buttonRadius
                        color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                        border.color: root.buttonBorderColor
                        border.width: 1
                    }
                    onClicked: {
                        root.buffer = root.buffer.charAt(0) === "-"
                                    ? root.buffer.slice(1)
                                    : "-" + root.buffer
                    }
                }
                Button {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.buttonHeight
                    text: "0"
                    font.pixelSize: root.buttonFontSize
                    background: Rectangle {
                        radius: root.buttonRadius
                        color: parent.pressed ? root.buttonPressedBg : root.buttonBg
                        border.color: root.buttonBorderColor
                        border.width: 1
                    }
                    onClicked: root.buffer += "0"
                }
                Button {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.buttonHeight
                    text: "."
                    font.pixelSize: root.buttonFontSize
                    enabled: root.buffer.indexOf(".") === -1
                    background: Rectangle {
                        radius: root.buttonRadius
                        color: parent.enabled ? (parent.pressed ? root.buttonPressedBg : root.buttonBg) : root.buttonDisabledBg
                        border.color: root.buttonBorderColor
                        border.width: 1
                    }
                    onClicked: root.buffer += "."
                }
            }

            Item {
                Layout.fillHeight: true
            }

            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: root.buttonHeight
                text: "Input"
                font.pixelSize: root.buttonFontSize
                enabled: root.buffer.length > 0 && root.buffer !== "-" && root.buffer !== "."
                background: Rectangle {
                    radius: root.buttonRadius
                    color: parent.enabled ? (parent.pressed ? root.buttonPressedBg : root.buttonBg) : root.buttonDisabledBg
                    border.color: root.buttonBorderColor
                    border.width: 1
                }
                onClicked: root._accept(root.buffer)
            }
        }
    }
}
