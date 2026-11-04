import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null
    property int profileId: 0
    property var primitives: []
    property var workpiece: ({})

    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        profileId = opData.profile_id !== undefined ? Math.round(Number(opData.profile_id)) : 0
        primitives = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        workpiece = JSON.parse(JSON.stringify(opData.workpiece || {}))
        canvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Label {
            text: "Define Radial Profile" + (root.profileId ? " P" + root.profileId : "")
            font.pixelSize: Theme.fontLarge
            font.bold: true
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RadialProfileCanvas {
                id: canvas
                anchors.fill: parent
                primitives: root.primitives
                workpiece: root.workpiece
            }

            EditProfileButton {
                text: "Edit Radial Profile P" + root.profileId
                onClicked: root.editor.openEditor()
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: canvas
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline
                border.width: Theme.hairline
            }
        }
    }
}
