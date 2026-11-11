// ProfileDetailsView.qml — canvas-only view; full editing opens ProfileEditorScreen via navigation
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import theme
import common

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this shows (OperationEditorViewModel.py):
    // the one place what the view shows comes from
    required property var editor
    readonly property var op: editor.operation
    readonly property int    profileId: op.profile_id !== undefined ? Math.round(Number(op.profile_id)) : 0
    readonly property string profileType: op.profile_type !== undefined ? String(op.profile_type) : "od"
    readonly property var    primitives: op.profile_primitives || []
    readonly property var    workpiece: op.workpiece || ({})
    signal openNumPadRequested(var field)

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    // ── Main layout ──────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // Canvas with zoom icon buttons overlaid top-left
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            ProfileCanvas {
                id: profileCanvas
                anchors.fill: parent
                // only where the profile starts and where it ends across
                // the centre line
                showTransitions: false
                // the profile in the stock's outline colour and weight, as
                // the operations draw it
                profileLineColor: "#6b7280"
                profileLineWidth: 1.5
                primitives:   root.primitives
                profileType:  root.profileType
                workpiece:    root.workpiece

                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: Theme.outline; border.width: Theme.hairline
                }
            }

            EditProfileButton {
                text: "Edit Profile  P" + root.profileId
                onClicked: root.editor.openEditor()
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: profileCanvas
            }
        }

    }
}
