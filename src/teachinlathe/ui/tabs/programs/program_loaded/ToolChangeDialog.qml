import QtQuick
import QtQuick.Layouts
import theme
import "../../tool_library/ToolTitles.js" as ToolTitles

// The tool the program asks for, while the machine waits for it. Modal: till
// the change is answered, with the machine's Cycle Start or Cycle Abort,
// nothing else on the screen takes a touch - and what is behind is dimmed to
// say so.
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
    modal: true
    dim: true

    ProgramPromptDialog.Line {
        text: "Tool Change"
        font.pixelSize: Theme.fontTitle
        font.bold: true
    }

    ProgramPromptDialog.Line {
        // The tool as the Manual Turning list names it, its comment after.
        readonly property string toolTitle: !root.viewModel || !root.viewModel.toolView ? ""
            : ToolTitles.listTitle(root.viewModel.toolView, root.titleColors)
              + (root.viewModel.toolComment === "" ? ""
                 : " (" + root.escapeHtml(root.viewModel.toolComment) + ")")
        text: "Please load <b>" + root.escapeHtml(root.viewModel.toolNoText) + "</b>"
            + (toolTitle.length > 0 ? " [" + toolTitle + "]" : "")
    }

    Item { Layout.preferredHeight: Theme.spacingLarge }

    ProgramPromptDialog.Line {
        text: root.press("Cycle Start", root.startColor, "to confirm the tool change")
    }

    ProgramPromptDialog.Line {
        text: root.press("Cycle Abort", root.abortColor, "to stop the program.")
    }
}
