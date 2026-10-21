// ToolBox.qml — which tool an operation cuts with, laid over its canvas: the
// tool the last Change Tool above puts in, as "T1" and its title as the
// Manual Turning list has it ("Turning CCMT 060204"), or "Select the tool"
// while there is none - in the inserts' colour.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import "../tool_library/ToolTitles.js" as ToolTitles

CanvasBox {
    id: root

    // {tool_no, card, view} as conversationalQml.toolCardBefore gives it
    property var toolCard: ({})
    // the inserts' colour - the backplot's, as the Tool Library draws them
    property color insertColor: "#e5a93b"

    readonly property bool hasTool: !!(toolCard && toolCard.tool_no)
    accent: insertColor

    Text {
        textFormat: Text.StyledText
        font.pixelSize: Theme.fontBody
        font.bold: !root.hasTool
        color: root.hasTool ? Theme.foregroundStrong : root.insertColor
        text: !root.hasTool ? "Select the tool"
              : "<b>T" + root.toolCard.tool_no + "</b>"
                + (root.toolCard.view ? "  " + ToolTitles.listTitle(root.toolCard.card, root.toolCard.view, Theme)
                                      : "  (empty)")
    }
}
