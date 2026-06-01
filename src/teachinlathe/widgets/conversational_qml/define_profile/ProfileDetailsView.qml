// ProfileDetailsView.qml — canvas-only view; full editing opens ProfileEditorScreen via navigation
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "../"

Item {
    id: root
    anchors.fill: parent

    property int    opIndex:     -1
    property var    opData:      null
    property int    profileId:   0
    property string profileType: "od"
    property bool   _loading:    false
    property var    primitives:  []

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

        Label {
            text: {
                var typeStr = (root.profileType === "id") ? "ID" : "OD"
                if (root.opData && root.opData.type)
                    return "Define " + typeStr + " Profile — Op #" + (root.opData.order !== undefined ? root.opData.order : "N/A")
                return "Define " + typeStr + " Profile"
            }
            font.pixelSize: 18; font.bold: true
        }

        // Canvas with zoom icon buttons overlaid top-left
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            ProfileCanvas {
                id: profileCanvas
                anchors.fill: parent
                primitives:   root.primitives
                profileType:  root.profileType

                Rectangle {
                    anchors.fill: parent
                    color: "transparent"
                    border.color: "#cccccc"; border.width: 1
                }
            }

            // Edit Profile button — top-right overlay
            Rectangle {
                id: editProfileBtn
                anchors { top: parent.top; right: parent.right; topMargin: 24; rightMargin: 24 }
                height: 60
                width: editProfileRow.implicitWidth + 32
                radius: 6
                color: editProfileMa.pressed ? "#e1f0ff" : "transparent"
                border.color: editProfileMa.pressed ? "#8ec5ff" : "#BDBDBD"; border.width: 1

                RowLayout {
                    id: editProfileRow
                    anchors.centerIn: parent
                    spacing: 8

                    Item {
                        width: 28; height: 28
                        Image {
                            id: editProfileIcon
                            anchors.fill: parent
                            source: "../icons/edit-profile.svg"
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            visible: false
                        }
                        ColorOverlay {
                            anchors.fill: editProfileIcon
                            source: editProfileIcon
                            color: "#2E7D32"
                        }
                    }

                    Text {
                        text: "Edit Profile P" + root.profileId
                        color: "#2E7D32"
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

            // Zoom icon buttons — top-left overlay
            Row {
                anchors { top: parent.top; left: parent.left; topMargin: 24; leftMargin: 24 }
                spacing: 32

                Repeater {
                    model: [
                        { icon: "../icons/zoom-in.svg",  action: "zoomIn"      },
                        { icon: "../icons/zoom-out.svg", action: "zoomOut"     },
                        { icon: "../icons/zoom-fit.svg", action: "fitToScreen" }
                    ]
                    Rectangle {
                        width: 60; height: 60
                        radius: 6
                        color: zoomMa.pressed ? "#e5edf9" : zoomMa.containsMouse ? "#eef3fb" : "#f5f7fb"
                        border.color: "#c5d0df"; border.width: 1

                        Image {
                            anchors.centerIn: parent
                            width: 40; height: 40
                            source: modelData.icon
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                        }

                        MouseArea {
                            id: zoomMa
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (modelData.action === "zoomIn")       profileCanvas.zoomIn()
                                else if (modelData.action === "zoomOut") profileCanvas.zoomOut()
                                else                                     profileCanvas.fitToScreen()
                            }
                        }
                    }
                }
            }
        }

    }
}
