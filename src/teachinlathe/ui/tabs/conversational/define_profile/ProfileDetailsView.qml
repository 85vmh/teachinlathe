// ProfileDetailsView.qml — canvas-only view; full editing opens ProfileEditorScreen via navigation
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt5Compat.GraphicalEffects
import "../"
import theme 1.0
import common 1.0

Item {
    id: root
    anchors.fill: parent

    property int    opIndex:     -1
    property var    opData:      null
    property int    profileId:   0
    property string profileType: "od"
    property bool   _loading:    false
    property var    primitives:  []
    property var    workpiece:   ({})

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal openProfileEditorRequested(int opIndex, var opData)

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

            // Edit Profile button — top-right overlay
            Rectangle {
                id: editProfileBtn
                anchors { top: parent.top; right: parent.right; topMargin: 24; rightMargin: 24 }
                height: 60
                width: editProfileRow.implicitWidth + 32
                radius: Theme.radius
                color: editProfileMa.pressed ? Theme.accentSoft : "transparent"
                border.color: editProfileMa.pressed ? Theme.accentBorder : Theme.outlineStrong; border.width: Theme.hairline

                RowLayout {
                    id: editProfileRow
                    anchors.centerIn: parent
                    spacing: Theme.spacingSmall

                    Item {
                        width: 28; height: 28
                        Image {
                            id: editProfileIcon
                            anchors.fill: parent
                            source: Images.url("edit-profile.svg")
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            visible: false
                        }
                        ColorOverlay {
                            anchors.fill: editProfileIcon
                            source: editProfileIcon
                            color: Theme.success
                        }
                    }

                    Text {
                        text: "Edit Profile P" + root.profileId
                        color: Theme.success
                        font.pointSize: 11; font.family: "Noto Sans"
                    }
                }

                MouseArea {
                    id: editProfileMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.openProfileEditorRequested(root.opIndex, root.opData)
                }
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: profileCanvas
            }
        }

    }
}
