import QtQuick
import QtQuick.Layouts
import theme
import "../../tool_library/ToolTitles.js" as ToolTitles

// The tool the program asks for, while the machine waits for it - answered
// with the machine's Cycle Start or Cycle Abort.
ProgramPromptDialog {
    id: root

    required property var viewModel
    // The common run screen also shows simulations; machine tool-change
    // requests must not put this dialog over a simulated run.
    property bool enabledForMode: true
    // the colours ToolTitles gives a title's parts, light enough for the dark
    // background (the theme's are for a light one)
    readonly property var titleColors: ({ accentStrong: "#60a5fa", foregroundStrong: Theme.surface,
                                          success: root.startColor })

    visible: enabledForMode && viewModel.requested

    ProgramPromptDialog.Title {
        text: "Tool Change"
    }

    ProgramPromptDialog.Line {
        // The tool as the Manual Turning list names it.
        readonly property string toolTitle: !root.viewModel.toolView ? ""
            : ToolTitles.listTitle(root.viewModel.toolView, root.titleColors)
        // two spaces either side of the tool number (&nbsp;: rich text
        // collapses spaces); none after it at the end of the line
        text: "Load&nbsp;&nbsp;<span style=\"font-size:" + Theme.fontPromptTool + "px\"><b>"
            + root.escapeHtml(root.viewModel.toolNoText) + "</b></span>"
            + (toolTitle.length > 0 ? "&nbsp;&nbsp;[" + toolTitle + "]" : "")
    }

    // its comment, on a line of its own under it
    ProgramPromptDialog.Line {
        visible: root.viewModel.toolComment !== ""
        text: "(" + root.escapeHtml(root.viewModel.toolComment) + ")"
        font.italic: true
    }

    Item { Layout.preferredHeight: Theme.spacingLarge }

    ProgramPromptDialog.Line {
        text: root.press("Cycle Start", root.startColor, "to confirm the tool change")
    }

    ProgramPromptDialog.Line {
        text: root.press("Cycle Abort", root.abortColor, "to stop the program.")
    }
}
