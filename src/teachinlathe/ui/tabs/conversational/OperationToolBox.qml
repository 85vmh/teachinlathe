// OperationToolBox.qml — the tool an operation cuts with, over its canvas
// (ToolBox), and tapped, the picker to choose it (ToolPickerPopup): only the
// tools its editor says it can cut with, chosen through the editor.
import QtQuick

ToolBox {
    id: root

    // the operation's editor: its toolCard, suitableToolNos, touchedOffTools
    // and useTool
    required property var editor
    // the picker's width: the details pane's
    property real pickerWidth: 1000

    toolCard: editor.toolCard || ({})
    onClicked: picker.open()

    ToolPickerPopup {
        id: picker
        toolsModel: root.editor.touchedOffTools
        toolNos: root.editor.suitableToolNos
        contentWidth: root.pickerWidth
        currentToolNo: root.toolCard.suggested_tool_no || 0
        toolUsers: root.toolCard.users || 0
        currentToolchangePosition: root.toolCard.toolchange_position || "G28"
        onToolChosen: function(toolNo, position, scope) {
            root.editor.useTool(toolNo, position, scope)
        }
    }
}
