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

    toolCard: root.editor ? root.editor.toolCard : null
    onClicked: if (root.editor) picker.open()

    ToolPickerPopup {
        id: picker
        toolsModel: root.editor ? root.editor.touchedOffTools : null
        toolNos: root.editor ? root.editor.suitableToolNos : []
        contentWidth: root.pickerWidth
        currentToolNo: root.toolCard ? root.toolCard.suggestedToolNo : 0
        toolUsers: root.toolCard ? root.toolCard.users : 0
        currentToolchangePosition: root.toolCard ? root.toolCard.toolchangePosition : 0
        onToolChosen: function(toolNo, position, scope) {
            if (root.editor) root.editor.useTool(toolNo, position, scope)
        }
    }
}
