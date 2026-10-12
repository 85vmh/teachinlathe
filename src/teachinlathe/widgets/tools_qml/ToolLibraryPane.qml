import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// One of the Tool Library's two panes: a titled, outlined box. Whatever is
// declared inside it fills the space under the title; whatever is put in
// `headerActions` sits at the right end of the title bar.
Rectangle {
    id: root

    property string title: ""
    default property alias content: body.data
    property alias headerActions: actions.data
    //: From the title bar's right edge to the last of `headerActions`.
    property real headerActionsRightMargin: Theme.spacing
    property alias headerActionsSpacing: actions.spacing

    color: Theme.surfaceSunken
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.hairline
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.headerHeight
            color: Theme.surfaceAlt
            radius: Theme.radius

            Text {
                anchors.centerIn: parent
                text: root.title
                color: Theme.foreground
                font.pixelSize: Theme.fontLarge
                font.bold: true
            }

            Row {
                id: actions
                anchors.right: parent.right
                anchors.rightMargin: root.headerActionsRightMargin
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.spacingSmall
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: Theme.hairline
                color: Theme.separator
            }
        }

        Item {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
