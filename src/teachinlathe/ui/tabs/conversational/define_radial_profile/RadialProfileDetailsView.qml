import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this shows (OperationEditorViewModel.py):
    // the one place what the view shows comes from
    required property var editor
    readonly property var op: editor.operation
    readonly property int profileId: op.profile_id !== undefined ? Math.round(Number(op.profile_id)) : 0
    readonly property var primitives: op.profile_primitives || []
    readonly property var workpiece: op.workpiece || ({})

    // another operation: the drawing fitted to it
    onEditorChanged: canvas.resetView()

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
                text: "Edit Radial Profile  P" + root.profileId
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
