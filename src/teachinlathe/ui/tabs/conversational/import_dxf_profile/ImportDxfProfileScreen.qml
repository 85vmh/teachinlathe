import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.programs.filesystemview
import tabs.conversational
import theme

Item {
    id: root
    objectName: "importDxfProfileScreen"

    // The view model of the tab (ConversationalViewModel): the drawing chosen,
    // what it gives the profile and why it failed - all the screen shows. The
    // header's Import DXF imports it there.
    required property var viewModel
    // The DXF Profiles folder (ConversationalViewModel.dxfFileSystemViewModel).
    required property var fileSystemViewModel
    readonly property string selectedPath: viewModel.dxfSelectedPath
    readonly property string errorMessage: viewModel.dxfError
    readonly property var _preview: viewModel.dxfPreview
    readonly property var previewPrimitives: _preview && _preview.ok ? (_preview.primitives || []) : []
    readonly property string profileType: _preview && _preview.ok && _preview.profileType ? _preview.profileType : "od"

    signal backRequested()

    // another drawing: its preview fitted
    onPreviewPrimitivesChanged: previewCanvas.resetView()

    Rectangle {
        anchors.fill: parent
        color: Theme.surfaceSunken
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        handle: Rectangle {
            implicitWidth: 6
            implicitHeight: 6
            color: Theme.surface
        }

        FileSystemView {
            viewModel: root.fileSystemViewModel
            showActionBar: false
            showActions: false
            SplitView.preferredWidth: parent.width * 0.42
            SplitView.minimumWidth: 320
        }

        Rectangle {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 360
            color: Theme.surface

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.buttonHeight
                    color: Theme.surfaceAlt
                    border.color: Theme.separator
                    border.width: Theme.hairline
                    radius: Theme.radius

                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        text: root.selectedPath.length > 0 ? root.selectedPath : "Select a DXF file"
                        color: root.selectedPath.length > 0 ? Theme.foreground : "#7b8494"
                        font.pixelSize: Theme.fontSmall
                        elide: Text.ElideMiddle
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Theme.surface
                    border.color: Theme.separator
                    border.width: Theme.hairline
                    radius: Theme.radius

                    ProfileCanvas {
                        id: previewCanvas
                        anchors.fill: parent
                        anchors.margins: 8
                        primitives: root.previewPrimitives
                        profileType: root.profileType
                        selectedPrimIndex: -1
                        selectedBlendIndex: -1
                        mirrorAcrossCenterline: true
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 48
                        visible: root.selectedPath.length === 0
                        text: "Select a DXF file to preview"
                        color: "#7b8494"
                        font.pixelSize: Theme.fontLarge
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 48
                        visible: root.errorMessage.length > 0
                        text: root.errorMessage
                        color: "#b00020"
                        font.pixelSize: Theme.fontBody
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
