import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../programs_qml/filesystemview"
import "../"

Item {
    id: root
    objectName: "importDxfProfileScreen"
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null
    property var fileSystemViewModel: dxfProfileFileSystemViewModel
    property string selectedPath: ""
    property string errorMessage: ""
    property var previewPrimitives: []
    property string profileType: "od"

    signal backRequested()
    signal headerRefreshRequested()
    signal importDxfProfileRequested(int opIndex, string dxfFilePath)

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        selectedPath = opData.dxfFilePath || ""
        profileType = opData.profile_type !== undefined ? String(opData.profile_type) : "od"
        errorMessage = ""
        previewPrimitives = []
        if (selectedPath.length > 0)
            loadPreview(selectedPath)
        headerRefreshRequested()
    }

    function setError(message) {
        errorMessage = String(message || "")
    }

    function importSelectedDxf() {
        if (selectedPath.length > 0)
            root.importDxfProfileRequested(root.opIndex, root.selectedPath)
    }

    function loadPreview(path) {
        previewPrimitives = []
        errorMessage = ""
        if (!path || path.length === 0)
            return
        var result = conversationalQml.previewDxfProfile(path)
        if (result && result.ok) {
            previewPrimitives = result.primitives || []
            profileType = result.profileType || profileType
            previewCanvas.resetView()
        } else {
            errorMessage = result && result.error ? String(result.error) : "Could not preview DXF."
        }
    }

    Connections {
        target: root.fileSystemViewModel
        function onSelectionChanged() {
            var path = root.fileSystemViewModel ? root.fileSystemViewModel.selectedAbsolutePath : ""
            root.selectedPath = path || ""
            root.loadPreview(root.selectedPath)
            root.headerRefreshRequested()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#f2f3f5"
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        handle: Rectangle {
            implicitWidth: 6
            implicitHeight: 6
            color: "#ffffff"
        }

        FileSystemView {
            viewModel: root.fileSystemViewModel
            showActionBar: false
            SplitView.preferredWidth: parent.width * 0.42
            SplitView.minimumWidth: 320
        }

        Rectangle {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 360
            color: "#ffffff"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    color: "#f5f7fb"
                    border.color: "#d6dce7"
                    border.width: 1
                    radius: 6

                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        text: root.selectedPath.length > 0 ? root.selectedPath : "Select a DXF file"
                        color: root.selectedPath.length > 0 ? "#1e2430" : "#7b8494"
                        font.pixelSize: 15
                        elide: Text.ElideMiddle
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#ffffff"
                    border.color: "#d6dce7"
                    border.width: 1
                    radius: 6

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
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 48
                        visible: root.errorMessage.length > 0
                        text: root.errorMessage
                        color: "#b00020"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
