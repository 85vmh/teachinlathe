import QtQuick
import QtQuick.Controls
import theme
import TeachInLathe

// The Tool Library tab: a stack of screens. The library itself is always at
// the bottom; adding or editing a cutting tool pushes its screen on top,
// and the top bar's Back and Save take it off again.
//
Item {
    id: root

    readonly property var viewModel: ToolsTabViewModel

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: ToolLibraryHome { viewModel: root.viewModel }
    }

    Component {
        id: turningEditor
        TurningToolEditor {}
    }

    Component {
        id: boringEditor
        BoringToolEditor {}
    }

    Component {
        id: threadingEditor
        ThreadingToolEditor {}
    }

    Component {
        id: bladeEditor
        BladeToolEditor {}
    }

    Component {
        id: drillingEditor
        DrillingToolEditor {}
    }

    Component {
        id: reamingEditor
        ReamingToolEditor {}
    }

    Component {
        id: tappingEditor
        TappingToolEditor {}
    }

    // The screen for each kind of tool the view model can open an editor on.
    readonly property var editorScreens: ({
        "turning": turningEditor,
        "boring": boringEditor,
        "threading": threadingEditor,
        "blade": bladeEditor,
        "drilling": drillingEditor,
        "reaming": reamingEditor,
        "tapping": tappingEditor
    })

    Connections {
        target: root.viewModel
        function onEditorChanged() {
            var editor = root.viewModel.editor
            if (editor)
                stack.push(root.editorScreens[editor.toolType], { editor: editor })
            else if (stack.depth > 1)
                stack.pop()
        }
    }
}
