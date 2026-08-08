import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null
    property int profileId: 0
    property var primitives: []
    property var workpiece: ({})

    signal openRadialProfileEditorRequested(int opIndex, var opData)

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
            font.pixelSize: 18
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

            Button {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 24
                anchors.rightMargin: 24
                text: "Edit Radial Profile P" + root.profileId
                height: 54
                onClicked: root.openRadialProfileEditorRequested(root.opIndex, root.opData)
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: "#ccc"
                border.width: 1
            }
        }
    }
}
