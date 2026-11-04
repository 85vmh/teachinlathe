// ToolBox.qml — which tool an operation cuts with, laid over its canvas, as
// "T1 - Turning CCMT 060204" - its title as the Manual Turning list has it,
// in one colour - or "Select the tool" while there is none; on a lighter
// shade of the inserts' colour. A tool the Tool Library no longer has as it
// was chosen says so: moved to another holder, to be confirmed; changed, or
// gone, for another to be chosen.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import TeachInLathe

CanvasBox {
    id: root

    // the operation's tool, a ToolCard (its editor's toolCard); null for none
    property var toolCard: null
    // the inserts' colour - the backplot's, as the Tool Library draws them
    property color insertColor: "#e5a93b"

    // as tall as the row it is lined up with - the canvas's view buttons -
    // its text in the middle of it
    property real rowHeight: 0

    readonly property bool hasTool: !!toolCard && toolCard.hasTool
    // the tool's list title as plain text: all of it the text's colour
    readonly property string description: hasTool && toolCard.view ? toolCard.view.titleParts.text : "(empty)"
    // its border the inserts' colour, its fill that lighter: the colour this
    // much of the way from white to it - opaque, the canvas not showing through
    readonly property real fillStrength: 0.4
    accent: insertColor
    color: Qt.tint(Theme.surface, Qt.rgba(insertColor.r, insertColor.g, insertColor.b, fillStrength))
    height: Math.max(implicitHeight, rowHeight)

    Text {
        Layout.preferredHeight: root.rowHeight > 0 ? root.rowHeight - 2 * Theme.spacing : -1
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.StyledText
        font.pixelSize: Theme.fontLarge
        color: Theme.foregroundStrong
        text: !root.hasTool ? "<b>Select the tool</b>"
              : "<b>T" + root.toolCard.toolNo + "</b> - " + root.description + root.problem
    }

    // what is wrong with the tool, after its title; "" when it is as chosen
    readonly property string problem: {
        if (!hasTool) return ""
        switch (toolCard.status) {
        case ToolCard.Moved: return "<br><b>Now in T" + toolCard.suggestedToolNo + "</b>: tap to confirm"
        case ToolCard.Changed: return "<br><b>Changed in the Tool Library</b>: tap to choose"
        case ToolCard.Missing: return "<br><b>No longer in the Tool Library</b>: tap to choose"
        case ToolCard.Unfit: return "<br><b>Not a tool this operation can cut with</b>: tap to choose"
        default: return ""
        }
    }
}
