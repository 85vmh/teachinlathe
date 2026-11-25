import QtQuick
import tabs.programs.filesystemview
import tabs.conversational
import common
import theme

Item {
    id: root
    objectName: "importDxfProfileScreen"

    // The view model of the tab (ConversationalViewModel): the drawing chosen,
    // what it gives the profile and why it failed - all the screen shows. The
    // header's Import DXF imports it there.
    required property var viewModel
    // The sticks and SyncThing (ConversationalViewModel.dxfFileSystemViewModel).
    required property var fileSystemViewModel
    readonly property string selectedPath: viewModel.dxfSelectedPath
    readonly property string errorMessage: viewModel.dxfError
    readonly property var _preview: viewModel.dxfPreview
    readonly property var previewPrimitives: _preview && _preview.ok ? (_preview.primitives || []) : []
    readonly property string profileType: _preview && _preview.ok && _preview.profileType ? _preview.profileType : "od"
    // the drawing does not say which is the lathe's axis: it can be turned
    readonly property bool rotatable: viewModel.dxfRotatable

    signal backRequested()

    // another drawing: its preview fitted
    onPreviewPrimitivesChanged: previewCanvas.resetView()

    // ── Screen background ────────────────────────────────────────────────────
    // the window's, round the panes - as on the profile editor (ProfileEditorScreen)
    Rectangle {
        anchors.fill: parent
        color: Theme.windowBackground
    }

    // ── Left: the locations and the path in them, and the files - cards of
    // their own, a card's spacing apart ───────────────────────────────────────
    FileSystemView {
        id: leftPanel
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: (parent.width - Theme.paneGap) * 0.42
        viewModel: root.fileSystemViewModel
        showActions: false
        showActionBar: false
    }

    // ── Right: the profile the drawing gives, in its own box ──────────────────
    Card {
        id: rightPanel
        anchors {
            left: leftPanel.right; right: parent.right
            top: parent.top; bottom: parent.bottom
            leftMargin: Theme.paneGap
        }

        ProfileCanvas {
            id: previewCanvas
            anchors.fill: parent
            anchors.margins: Theme.paneInset
            primitives: root.previewPrimitives
            profileType: root.profileType
            selectedPrimIndex: -1
            selectedBlendIndex: -1
            mirrorAcrossCenterline: true
        }

        // where the drawing is symmetric both ways, and does not say which
        // is the lathe's axis: turned 90° at a time
        Row {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: Theme.paneInset + Theme.spacing
            spacing: Theme.spacingSmall
            visible: root.rotatable

            SquareIconButton {
                iconSource: Images.url("rotate_left.svg")
                onClicked: root.viewModel.rotateDxf(1)
            }
            SquareIconButton {
                iconSource: Images.url("rotate_right.svg")
                onClicked: root.viewModel.rotateDxf(-1)
            }
        }

        // over the canvas: why the drawing chosen gives no profile, or that
        // none is chosen yet
        Text {
            readonly property bool failed: root.errorMessage.length > 0
            anchors.centerIn: parent
            width: parent.width - 2 * Theme.margin
            visible: failed || root.selectedPath.length === 0
            text: failed ? root.errorMessage : "Select a DXF file to preview"
            color: failed ? Theme.danger : Theme.foregroundFaint
            font.pixelSize: failed ? Theme.fontBody : Theme.fontLarge
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }
}
