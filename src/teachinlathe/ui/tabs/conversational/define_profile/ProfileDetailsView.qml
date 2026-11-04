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

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int    opIndex:     -1
    property var    opData:      null
    property int    profileId:   0
    property string profileType: "od"
    property bool   _loading:    false
    property var    primitives:  []
    property var    workpiece:   ({})
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        _loading    = true
        opIndex     = index
        opData      = data || {}
        profileId   = opData.profile_id   !== undefined ? Math.round(Number(opData.profile_id)) : 0
        profileType = opData.profile_type !== undefined ? String(opData.profile_type) : "od"
        primitives  = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        workpiece   = JSON.parse(JSON.stringify(opData.workpiece || {}))
        _loading    = false
        profileCanvas.resetView()
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        opData = out
        return out
    }

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
                text: "Edit Profile P" + root.profileId
                onClicked: root.editor.openEditor()
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: profileCanvas
            }
        }

    }
}
