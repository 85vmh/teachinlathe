import QtQuick
import QtQuick.Controls
import common.touchable_input
import tabs.conversational.define_profile as DefineProfile
import tabs.conversational.define_radial_profile as DefineRadialProfile
import tabs.conversational.import_dxf_profile as ImportDxfProfile
import TeachInLathe
import theme

// The Conversational tab: a stack of screens, kept in step with the view
// model's `screens` - the program list at the bottom, the program open in
// the editor over it, and a profile editor or the DXF import over that.
// The view model decides what is open; this pushes and pops to match, binds
// each screen to it and connects the screen's signals to its slots.
//
Item {
    id: root

    readonly property var viewModel: ConversationalViewModel

    // The names of the screens on the stack, bottom to top, as last synced.
    property var _names: []
    property var _pendingKeyboardField: null

    function openNumpad(field) {
        if (!field)
            return
        numpadDialog.openFor(field, field.settingName, field.description)
    }

    function openKeyboard(field) {
        if (!field)
            return
        root._pendingKeyboardField = field
        if (!keyboardDialogLoader.active)
            keyboardDialogLoader.active = true
        if (keyboardDialogLoader.item) {
            keyboardDialogLoader.item.openFor(field, field.titleText)
            root._pendingKeyboardField = null
        }
    }

    // Pop to what the stack and the view model still share, then push the rest.
    function syncStack() {
        var target = root.viewModel.screens
        var keep = 0
        while (keep < root._names.length && keep < target.length && root._names[keep] === target[keep])
            keep++

        if (keep === 0)
            stack.clear(StackView.Immediate)
        else if (keep < stack.depth)
            stack.pop(stack.get(keep - 1), root.visible ? StackView.Transition : StackView.Immediate)

        var names = root._names.slice(0, keep)
        // More than one screen at once - the first sync, or a program opened
        // from elsewhere - lands in place rather than sliding in step by step,
        // as does anything that changes while the tab is not on screen.
        var immediate = stack.depth === 0 || target.length - keep > 1 || !root.visible
        for (var i = keep; i < target.length; ++i) {
            if (immediate)
                stack.push(screenComponents[target[i]], {}, StackView.Immediate)
            else
                stack.push(screenComponents[target[i]])
            names.push(target[i])
        }
        root._names = names
    }

    Connections {
        target: root.viewModel
        function onScreensChanged() { root.syncStack() }
        function onGcodeGenerationStarted() { buildGcodeProgressDialog.open() }
        function onGcodeGenerationFinished() { buildGcodeProgressDialog.close() }
        function onGcodeRefused(problems) {
            gcodeRefusedPopup.problems = problems
            gcodeRefusedPopup.open()
        }
    }

    Component.onCompleted: syncStack()

    StackView {
        id: stack
        anchors.fill: parent
    }

    readonly property var screenComponents: ({
        "programs": programsScreen,
        "program": programScreen,
        "profileEditor": profileEditorScreen,
        "radialProfileEditor": radialProfileEditorScreen,
        "dxfImport": dxfImportScreen
    })

    Component {
        id: programsScreen
        MainScreen {
            programsModel: root.viewModel.programsModel
            selectedProgramId: root.viewModel.selectedProgramId
            onAddNewProgramRequested: root.viewModel.addNewProgram()
            onEditProgramRequested: function(arg) { root.viewModel.openProgram(arg) }
            onDeleteProgramRequested: function(index) { root.viewModel.deleteProgram(index) }
            onDuplicateProgramRequested: function(index) { root.viewModel.duplicateProgram(index) }
        }
    }

    Component {
        id: programScreen
        ChildScreen {
            selectedProgram: root.viewModel.selectedProgram
            operationsModel: root.viewModel.operationsModel
            activeOpIndex: root.viewModel.activeOpIndex
            editor: root.viewModel.editor

            onBackRequested: root.viewModel.back()
            onGenerateGcodeRequested: root.viewModel.generateGcode()
            onDetailsRequested: function(index) { root.viewModel.showDetails(index) }
            onAddOperationTypeChosen: function(type, insertIndex) { root.viewModel.addOperation(type, insertIndex) }
            onMoveOperationRequested: function(fromIndex, toIndex) { root.viewModel.moveOperation(fromIndex, toIndex) }
            onDeleteOperationRequested: function(index) { root.viewModel.deleteOperation(index) }
            onDuplicateOperationRequested: function(index) { root.viewModel.duplicateOperation(index) }
            onToggleGenerateGcode: function(index, checked) { root.viewModel.setGenerateGcode(index, checked) }
            onToggleOptionalBlock: function(index, checked) { root.viewModel.setOptionalBlock(index, checked) }
            onOpenNumPadRequested: function(field) { root.openNumpad(field) }
            onOpenKeyboardRequested: function(field) { root.openKeyboard(field) }
        }
    }

    // The profile editors and the DXF import work on the operation the view
    // model opened them for, through its editor - which the list underneath
    // leaves alone while they are open.
    Component {
        id: profileEditorScreen
        DefineProfile.ProfileEditorScreen {
            id: profileEditor
            editor: root.viewModel.editor
            onBackRequested: root.viewModel.back()
            onOpenNumPadRequested: function(field) { root.openNumpad(field) }
            Component.onCompleted: Qt.callLater(function() {
                profileEditor.applyData(profileEditor.editor.opIndex, profileEditor.editor.operation)
            })
        }
    }

    Component {
        id: radialProfileEditorScreen
        DefineRadialProfile.RadialProfileEditorScreen {
            id: radialProfileEditor
            editor: root.viewModel.editor
            onBackRequested: root.viewModel.back()
            onOpenNumPadRequested: function(field) { root.openNumpad(field) }
            Component.onCompleted: Qt.callLater(function() {
                radialProfileEditor.applyData(radialProfileEditor.editor.opIndex, radialProfileEditor.editor.operation)
            })
        }
    }

    Component {
        id: dxfImportScreen
        ImportDxfProfile.ImportDxfProfileScreen {
            id: dxfImport
            editor: root.viewModel.editor
            fileSystemViewModel: root.viewModel.dxfFileSystemViewModel
            onBackRequested: root.viewModel.back()
            onSelectedPathChanged: root.viewModel.setDxfSelectedPath(selectedPath)
            Component.onCompleted: Qt.callLater(function() {
                dxfImport.applyData(dxfImport.editor.opIndex, dxfImport.editor.operation)
            })

            Connections {
                target: root.viewModel
                function onImportDxfRequested() { dxfImport.importSelectedDxf() }
                function onDxfImportFailed(message) { dxfImport.setError(message) }
            }
        }
    }

    SmartNumpadDialog {
        id: numpadDialog
        viewModel: root.viewModel.numpadViewModel
    }
    Loader {
        id: keyboardDialogLoader
        active: false
        sourceComponent: Component { QwertyKeyboardDialog {} }

        onLoaded: {
            if (item && root._pendingKeyboardField) {
                item.openFor(root._pendingKeyboardField, root._pendingKeyboardField.titleText)
                root._pendingKeyboardField = null
            }
        }
    }
    BuildGcodeProgressDialog { id: buildGcodeProgressDialog }

    // no G-code: what is wrong with the program's tools
    Popup {
        id: gcodeRefusedPopup
        property string problems: ""
        parent: Overlay.overlay
        modal: true
        focus: true
        anchors.centerIn: parent
        padding: 24
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusXLarge
            color: Theme.surfaceSunken
            border.color: Theme.dialogBorder
            border.width: Theme.hairline
        }

        contentItem: Column {
            spacing: 24

            Text {
                text: "The G-code was not generated"
                font.pixelSize: Theme.fontLarge
                font.bold: true
                color: Theme.foreground
            }
            Text {
                text: gcodeRefusedPopup.problems
                font.pixelSize: Theme.fontBody
                color: Theme.foreground
            }
            Button {
                anchors.right: parent.right
                text: "OK"
                width: 180
                height: Theme.buttonHeightTouch
                font.pixelSize: 16
                onClicked: gcodeRefusedPopup.close()
            }
        }
    }
}
